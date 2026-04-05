"""
Skill Effectiveness Tracking and Win/Loss Pattern Analysis.

Three capabilities:
  1. **Skill rating**: Capture 1–5 effectiveness ratings per skill per proposal outcome.
  2. **Lesson injection**: Surface relevant hotwash lessons as context for a skill run.
  3. **Win/loss analysis**: Compare attributes of winning vs losing proposals.

Schema additions:
    skill_ratings — one rating row per skill + proposal + run

Configuration via environment variables:
    (none — uses DEFAULT_DB_PATH from proposal.database)

Usage:
    from proposal.skill_effectiveness import SkillTracker
    tracker = SkillTracker()
    tracker.rate(skill="bid-no-bid", proposal_id="P1", outcome="WIN", rating=4)
    lessons = tracker.inject_lessons(skill="bid-no-bid", query="competitive discriminators")
    report = tracker.win_loss_analysis()
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from proposal.database import DEFAULT_DB_PATH, get_conn
from proposal.lessons_search import LessonsSearchIndex

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SKILL_RATINGS_DDL = """
CREATE TABLE IF NOT EXISTS skill_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    outcome TEXT DEFAULT '',
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    notes TEXT DEFAULT '',
    rated_at TEXT NOT NULL
);
"""

_SKILL_RATINGS_INDEX = [
    "CREATE INDEX IF NOT EXISTS idx_skill_ratings_skill ON skill_ratings(skill_name)",
    "CREATE INDEX IF NOT EXISTS idx_skill_ratings_proposal ON skill_ratings(proposal_id)",
    "CREATE INDEX IF NOT EXISTS idx_skill_ratings_outcome ON skill_ratings(outcome)",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillRating:
    """
    One effectiveness rating for a skill on a specific proposal.

    Attributes:
        skill_name: The skill identifier (e.g., 'bid-no-bid', 'shredding').
        proposal_id: Local proposal UUID.
        outcome: Proposal outcome at rating time ('WIN', 'LOSS', 'PENDING', etc.).
        rating: Effectiveness score 1–5 (5 = highly effective).
        notes: Optional free-text notes on what worked or didn't.
        rated_at: ISO timestamp of when the rating was submitted.
        id: Database row ID (assigned on insert).
    """
    skill_name: str
    proposal_id: str
    outcome: str
    rating: int
    notes: str = ""
    rated_at: str = ""
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return as a plain dict for JSON serialization."""
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "proposal_id": self.proposal_id,
            "outcome": self.outcome,
            "rating": self.rating,
            "notes": self.notes,
            "rated_at": self.rated_at,
        }


@dataclass
class SkillStats:
    """
    Aggregate effectiveness statistics for a skill.

    Attributes:
        skill_name: The skill identifier.
        avg_rating: Mean rating across all recorded uses.
        count: Total number of rating records.
        win_avg: Mean rating on WIN proposals.
        loss_avg: Mean rating on LOSS proposals.
        ratings_by_outcome: Dict of outcome → list of ratings.
    """
    skill_name: str
    avg_rating: float
    count: int
    win_avg: Optional[float]
    loss_avg: Optional[float]
    ratings_by_outcome: Dict[str, List[int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return as a plain dict for JSON serialization."""
        return {
            "skill_name": self.skill_name,
            "avg_rating": round(self.avg_rating, 2),
            "count": self.count,
            "win_avg": round(self.win_avg, 2) if self.win_avg is not None else None,
            "loss_avg": round(self.loss_avg, 2) if self.loss_avg is not None else None,
            "ratings_by_outcome": self.ratings_by_outcome,
        }


@dataclass
class WinLossReport:
    """
    Comparative analysis of winning vs losing proposals.

    Attributes:
        total_proposals: Total number of proposals analyzed.
        wins: Number of won proposals.
        losses: Number of lost proposals.
        win_rate: Win rate as a fraction (0.0–1.0).
        avg_pwin_wins: Mean pwin_score on won proposals.
        avg_pwin_losses: Mean pwin_score on lost proposals.
        avg_value_wins: Mean estimated_value on won proposals.
        avg_value_losses: Mean estimated_value on lost proposals.
        common_win_stages: Most frequent pipeline stages at submission for wins.
        top_win_agencies: Agencies with the most wins.
        top_loss_agencies: Agencies with the most losses.
        patterns: List of human-readable pattern strings.
    """
    total_proposals: int
    wins: int
    losses: int
    win_rate: float
    avg_pwin_wins: Optional[float]
    avg_pwin_losses: Optional[float]
    avg_value_wins: Optional[float]
    avg_value_losses: Optional[float]
    top_win_agencies: List[Tuple[str, int]] = field(default_factory=list)
    top_loss_agencies: List[Tuple[str, int]] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return as a plain dict for JSON serialization."""
        return {
            "total_proposals": self.total_proposals,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate, 3),
            "avg_pwin_wins": round(self.avg_pwin_wins, 3) if self.avg_pwin_wins is not None else None,
            "avg_pwin_losses": round(self.avg_pwin_losses, 3) if self.avg_pwin_losses is not None else None,
            "avg_value_wins": self.avg_value_wins,
            "avg_value_losses": self.avg_value_losses,
            "top_win_agencies": self.top_win_agencies,
            "top_loss_agencies": self.top_loss_agencies,
            "patterns": self.patterns,
        }


# ---------------------------------------------------------------------------
# Skill tracker
# ---------------------------------------------------------------------------

class SkillTracker:
    """
    Tracks skill effectiveness, injects lessons as context, and analyzes
    win/loss patterns across the proposal pipeline.

    Example:
        tracker = SkillTracker()
        tracker.rate("bid-no-bid", "P1", "WIN", 4, notes="BNB caught key risks")
        lessons = tracker.inject_lessons("bid-no-bid", "competitive analysis")
        report = tracker.win_loss_analysis()
    """

    # Skill → relevant lesson categories for context injection
    _SKILL_LESSON_CATEGORIES: Dict[str, List[str]] = {
        "bid-no-bid": ["competitive_intelligence", "customer_relations", "other"],
        "shredding": ["proposal_process", "technical_approach"],
        "document-drafter": ["technical_approach", "management_approach", "past_performance"],
        "cost-estimator": ["cost_price"],
        "proposal-setup": ["proposal_process", "schedule_management"],
        "meeting-coordinator": ["proposal_process", "teaming"],
        "hotwash": ["proposal_process", "other"],
        "opportunity-curator": ["competitive_intelligence", "customer_relations"],
        "crm-sync": ["proposal_process"],
    }

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the skill tracker.

        Args:
            db_path: Path to the SQLite database. Defaults to DEFAULT_DB_PATH.
        """
        self._db_path = db_path or DEFAULT_DB_PATH
        self._lessons = LessonsSearchIndex(db_path=self._db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create skill_ratings table and indexes if not present."""
        with get_conn(self._db_path) as conn:
            conn.execute(_SKILL_RATINGS_DDL)
            for idx in _SKILL_RATINGS_INDEX:
                conn.execute(idx)

    def _now_iso(self) -> str:
        """Return the current UTC time as an ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    def rate(
        self,
        skill: str,
        proposal_id: str,
        outcome: str,
        rating: int,
        notes: str = "",
    ) -> SkillRating:
        """
        Record a skill effectiveness rating for a proposal.

        Args:
            skill: Skill identifier (e.g., 'bid-no-bid').
            proposal_id: Local proposal UUID.
            outcome: Proposal outcome ('WIN', 'LOSS', 'PENDING', etc.).
            rating: Effectiveness score 1–5.
            notes: Optional notes on what worked or didn't.

        Returns:
            SkillRating: The saved rating record.

        Raises:
            ValueError: If rating is not in 1–5 range.
        """
        if not (1 <= rating <= 5):
            raise ValueError(f"Rating must be 1–5, got {rating}")

        rated_at = self._now_iso()
        with get_conn(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO skill_ratings (skill_name, proposal_id, outcome, rating, notes, rated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (skill, proposal_id, outcome.upper(), rating, notes, rated_at),
            )
            row_id = cursor.lastrowid

        logger.info("Rated skill '%s' for proposal %s: %d/5 (%s)", skill, proposal_id, rating, outcome)
        return SkillRating(
            id=row_id,
            skill_name=skill,
            proposal_id=proposal_id,
            outcome=outcome.upper(),
            rating=rating,
            notes=notes,
            rated_at=rated_at,
        )

    def get_ratings(
        self,
        skill: Optional[str] = None,
        proposal_id: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> List[SkillRating]:
        """
        Retrieve skill ratings with optional filters.

        Args:
            skill: Filter by skill name.
            proposal_id: Filter by proposal ID.
            outcome: Filter by outcome.

        Returns:
            List[SkillRating]: Matching rating records.
        """
        conditions: List[str] = []
        params: List[Any] = []
        if skill:
            conditions.append("skill_name = ?")
            params.append(skill)
        if proposal_id:
            conditions.append("proposal_id = ?")
            params.append(proposal_id)
        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome.upper())
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM skill_ratings {where} ORDER BY rated_at DESC"
        with get_conn(self._db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_rating(r) for r in rows]

    def skill_stats(self, skill: str) -> Optional[SkillStats]:
        """
        Compute aggregate effectiveness statistics for a skill.

        Args:
            skill: Skill identifier.

        Returns:
            SkillStats or None if no ratings exist for this skill.
        """
        ratings = self.get_ratings(skill=skill)
        if not ratings:
            return None

        all_ratings = [r.rating for r in ratings]
        avg = sum(all_ratings) / len(all_ratings)

        by_outcome: Dict[str, List[int]] = {}
        for r in ratings:
            by_outcome.setdefault(r.outcome, []).append(r.rating)

        win_vals = by_outcome.get("WIN", [])
        loss_vals = by_outcome.get("LOSS", [])

        return SkillStats(
            skill_name=skill,
            avg_rating=avg,
            count=len(ratings),
            win_avg=sum(win_vals) / len(win_vals) if win_vals else None,
            loss_avg=sum(loss_vals) / len(loss_vals) if loss_vals else None,
            ratings_by_outcome=by_outcome,
        )

    def all_skill_stats(self) -> List[SkillStats]:
        """
        Compute aggregate stats for every rated skill.

        Returns:
            List[SkillStats]: One entry per skill, sorted by avg_rating descending.
        """
        with get_conn(self._db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT skill_name FROM skill_ratings ORDER BY skill_name"
            ).fetchall()
        stats = []
        for row in rows:
            s = self.skill_stats(row[0])
            if s:
                stats.append(s)
        return sorted(stats, key=lambda x: x.avg_rating, reverse=True)

    def _row_to_rating(self, row: sqlite3.Row) -> SkillRating:
        """Deserialize a skill_ratings row to a SkillRating."""
        d = dict(row)
        return SkillRating(
            id=d.get("id"),
            skill_name=d.get("skill_name", ""),
            proposal_id=d.get("proposal_id", ""),
            outcome=d.get("outcome", ""),
            rating=int(d.get("rating", 3)),
            notes=d.get("notes", ""),
            rated_at=d.get("rated_at", ""),
        )

    # ------------------------------------------------------------------
    # Lesson injection
    # ------------------------------------------------------------------

    def inject_lessons(
        self,
        skill: str,
        query: str = "",
        outcome_filter: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant lessons learned as context for a skill run.

        Searches the lessons index filtered by the skill's domain categories.
        Returns serializable dicts suitable for prompt injection.

        Args:
            skill: Skill identifier to inject context for.
            query: Optional search query to refine lesson retrieval.
            outcome_filter: Optionally restrict to lessons from 'WIN' or 'LOSS' proposals.
            limit: Maximum number of lessons to return.

        Returns:
            List[Dict]: Serialized LessonSearchResult dicts, most relevant first.
        """
        # Get domain categories for this skill (fallback: search all categories)
        categories = self._SKILL_LESSON_CATEGORIES.get(skill, [])

        all_results = []
        if categories:
            for cat in categories:
                results = self._lessons.search(
                    query=query,
                    category=cat,
                    outcome=outcome_filter,
                    limit=limit,
                )
                all_results.extend(results)
        else:
            all_results = self._lessons.search(
                query=query,
                outcome=outcome_filter,
                limit=limit,
            )

        # Deduplicate by lesson_id and sort by score
        seen: set = set()
        unique_results = []
        for r in sorted(all_results, key=lambda x: x.score, reverse=True):
            key = r.lesson_id or r.lesson_text[:50]
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return [r.to_dict() for r in unique_results[:limit]]

    def format_lessons_as_context(
        self,
        skill: str,
        query: str = "",
        outcome_filter: Optional[str] = None,
    ) -> str:
        """
        Format injected lessons as a human-readable prompt context block.

        Args:
            skill: Skill identifier.
            query: Optional search query.
            outcome_filter: Optionally restrict to 'WIN' or 'LOSS' lessons.

        Returns:
            str: Formatted markdown context block, or empty string if no lessons found.
        """
        lessons = self.inject_lessons(skill=skill, query=query, outcome_filter=outcome_filter)
        if not lessons:
            return ""

        lines = [f"## Relevant Lessons Learned for {skill}\n"]
        for i, lesson in enumerate(lessons, 1):
            outcome_label = f"({lesson['outcome']})" if lesson.get("outcome") else ""
            lines.append(
                f"{i}. **[{lesson['category']}]** {lesson['lesson_text']} {outcome_label}"
            )
            if lesson.get("recommended_action"):
                lines.append(f"   → *Action*: {lesson['recommended_action']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Win/Loss pattern analysis
    # ------------------------------------------------------------------

    def win_loss_analysis(self, limit_agencies: int = 5) -> WinLossReport:
        """
        Analyze patterns across won vs lost proposals.

        Reads from the proposals table — no hotwash data required.

        Args:
            limit_agencies: Number of top agencies to include in the report.

        Returns:
            WinLossReport: Populated comparison report.
        """
        with get_conn(self._db_path) as conn:
            all_rows = conn.execute(
                "SELECT pipeline_stage, agency, estimated_value, pwin_score "
                "FROM proposals WHERE pipeline_stage IN ('awarded', 'lost')"
            ).fetchall()

        wins = [dict(r) for r in all_rows if r["pipeline_stage"] == "awarded"]
        losses = [dict(r) for r in all_rows if r["pipeline_stage"] == "lost"]

        total = len(wins) + len(losses)
        win_rate = len(wins) / total if total > 0 else 0.0

        def _avg(rows: List[Dict], field: str) -> Optional[float]:
            vals = [r[field] for r in rows if r.get(field) is not None]
            return sum(vals) / len(vals) if vals else None

        def _top_agencies(rows: List[Dict], n: int) -> List[Tuple[str, int]]:
            counts: Dict[str, int] = {}
            for r in rows:
                agency = str(r.get("agency") or "Unknown").strip()
                counts[agency] = counts.get(agency, 0) + 1
            return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

        patterns = self._derive_patterns(wins, losses)

        return WinLossReport(
            total_proposals=total,
            wins=len(wins),
            losses=len(losses),
            win_rate=win_rate,
            avg_pwin_wins=_avg(wins, "pwin_score"),
            avg_pwin_losses=_avg(losses, "pwin_score"),
            avg_value_wins=_avg(wins, "estimated_value"),
            avg_value_losses=_avg(losses, "estimated_value"),
            top_win_agencies=_top_agencies(wins, limit_agencies),
            top_loss_agencies=_top_agencies(losses, limit_agencies),
            patterns=patterns,
        )

    def _derive_patterns(
        self,
        wins: List[Dict[str, Any]],
        losses: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Derive human-readable pattern statements from win/loss data.

        Args:
            wins: List of awarded proposal dicts.
            losses: List of lost proposal dicts.

        Returns:
            List[str]: Observed patterns as readable strings.
        """
        patterns: List[str] = []

        def _mean(vals: List[float]) -> Optional[float]:
            return sum(vals) / len(vals) if vals else None

        # pWin accuracy pattern
        win_pwins = [r["pwin_score"] for r in wins if r.get("pwin_score") is not None]
        loss_pwins = [r["pwin_score"] for r in losses if r.get("pwin_score") is not None]
        if win_pwins and loss_pwins:
            avg_w = _mean(win_pwins)
            avg_l = _mean(loss_pwins)
            if avg_w and avg_l:
                diff = avg_w - avg_l
                if abs(diff) > 0.05:
                    direction = "higher" if diff > 0 else "lower"
                    patterns.append(
                        f"pWin estimates on won proposals average {direction} "
                        f"({avg_w:.0%} vs {avg_l:.0%} on losses) — "
                        f"{'calibration looks reasonable' if diff > 0 else 'we may be overconfident on losses'}"
                    )

        # Contract value pattern
        win_vals = [r["estimated_value"] for r in wins if r.get("estimated_value")]
        loss_vals = [r["estimated_value"] for r in losses if r.get("estimated_value")]
        if win_vals and loss_vals:
            avg_w = _mean(win_vals)
            avg_l = _mean(loss_vals)
            if avg_w and avg_l and avg_w != avg_l:
                if avg_w < avg_l:
                    patterns.append(
                        f"We win more on smaller contracts (avg ${avg_w:,.0f} won vs "
                        f"${avg_l:,.0f} lost) — consider focusing pursuit resources there"
                    )
                else:
                    patterns.append(
                        f"We win more on larger contracts (avg ${avg_w:,.0f} won vs "
                        f"${avg_l:,.0f} lost)"
                    )

        # Volume sanity
        if not wins and not losses:
            patterns.append("No awarded/lost proposals in the database yet — add outcomes to unlock analysis")
        elif len(wins) + len(losses) < 3:
            patterns.append("Limited data — patterns will improve with more proposal outcomes recorded")

        return patterns
