"""
Lessons Learned Search — RAG over hotwash reports.

Builds a SQLite FTS5 full-text search index from lessons stored in the
hotwash_events table. Supports keyword search (always available) and
optional Ollama-powered semantic search (falls back gracefully).

The lessons_index table is rebuilt via build_index() whenever new hotwash
events are added. Search queries are filtered by category, impact level,
and proposal outcome.

Configuration via environment variables:
    OLLAMA_BASE_URL  — Ollama endpoint (default: http://localhost:11434)
    OLLAMA_EMBED_MODEL — embedding model (default: nomic-embed-text)

Usage:
    from proposal.lessons_search import LessonsSearchIndex
    idx = LessonsSearchIndex()
    idx.build_index()
    results = idx.search("past performance gaps", category="past_performance")
    for r in results:
        print(r.lesson, r.score)
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from proposal.database import DEFAULT_DB_PATH, get_conn
from proposal.hotwash import IMPACT_LEVELS, LESSON_CATEGORIES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Schema for the flat lessons index table
_INDEX_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS lessons_index (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id TEXT NOT NULL,
    lesson_text TEXT NOT NULL,
    recommended_action TEXT DEFAULT '',
    category TEXT NOT NULL,
    impact TEXT NOT NULL,
    source TEXT DEFAULT 'internal',
    owner TEXT DEFAULT '',
    proposal_id TEXT NOT NULL,
    proposal_title TEXT DEFAULT '',
    solicitation_number TEXT DEFAULT '',
    outcome TEXT DEFAULT '',
    conducted_date TEXT DEFAULT '',
    hotwash_id TEXT NOT NULL
);
"""

_FTS_TABLE_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS lessons_fts
USING fts5(
    lesson_text,
    recommended_action,
    category,
    proposal_title,
    content='lessons_index',
    content_rowid='rowid'
);
"""

# Trigger to keep FTS table in sync with lessons_index
_FTS_INSERT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS lessons_index_ai
AFTER INSERT ON lessons_index BEGIN
    INSERT INTO lessons_fts(rowid, lesson_text, recommended_action, category, proposal_title)
    VALUES (new.rowid, new.lesson_text, new.recommended_action, new.category, new.proposal_title);
END;
"""

_FTS_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS lessons_index_ad
AFTER DELETE ON lessons_index BEGIN
    INSERT INTO lessons_fts(lessons_fts, rowid, lesson_text, recommended_action, category, proposal_title)
    VALUES ('delete', old.rowid, old.lesson_text, old.recommended_action, old.category, old.proposal_title);
END;
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LessonSearchResult:
    """
    A single lesson returned from a search query.

    Attributes:
        lesson_id: Unique lesson identifier (e.g., 'LL-001').
        lesson_text: The lesson description.
        recommended_action: Suggested process improvement.
        category: Lesson category (see LESSON_CATEGORIES).
        impact: Impact level ('critical', 'high', 'medium', 'low').
        source: Origin of lesson ('debrief', 'internal', 'evaluator').
        owner: Person responsible for implementing the action.
        proposal_id: Local proposal UUID.
        proposal_title: Human-readable proposal title.
        solicitation_number: RFP solicitation number.
        outcome: Proposal outcome ('WIN', 'LOSS', 'NO_AWARD', 'PENDING').
        conducted_date: ISO date the hotwash was conducted.
        score: Relevance score (higher = more relevant; keyword-based).
    """
    lesson_id: str
    lesson_text: str
    recommended_action: str
    category: str
    impact: str
    source: str
    owner: str
    proposal_id: str
    proposal_title: str
    solicitation_number: str
    outcome: str
    conducted_date: str
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Return as a plain dict for JSON serialization."""
        return {
            "lesson_id": self.lesson_id,
            "lesson_text": self.lesson_text,
            "recommended_action": self.recommended_action,
            "category": self.category,
            "impact": self.impact,
            "source": self.source,
            "owner": self.owner,
            "proposal_id": self.proposal_id,
            "proposal_title": self.proposal_title,
            "solicitation_number": self.solicitation_number,
            "outcome": self.outcome,
            "conducted_date": self.conducted_date,
            "score": self.score,
        }


# ---------------------------------------------------------------------------
# Search index
# ---------------------------------------------------------------------------

class LessonsSearchIndex:
    """
    Full-text search index over lessons learned from hotwash reports.

    Uses SQLite FTS5 for keyword search. Optionally uses Ollama
    nomic-embed-text for semantic similarity scoring when available.

    Example:
        idx = LessonsSearchIndex()
        idx.build_index()
        results = idx.search("management approach weaknesses")
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ollama_base_url: Optional[str] = None,
        embed_model: Optional[str] = None,
    ):
        """
        Initialize the search index.

        Args:
            db_path: Path to the SQLite database. Defaults to DEFAULT_DB_PATH.
            ollama_base_url: Override OLLAMA_BASE_URL env var.
            embed_model: Override OLLAMA_EMBED_MODEL env var.
        """
        self._db_path = db_path or DEFAULT_DB_PATH
        self._ollama_url = (
            ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self._embed_model = embed_model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create index table and FTS virtual table if not present."""
        with get_conn(self._db_path) as conn:
            conn.execute(_INDEX_TABLE_DDL)
            conn.execute(_FTS_TABLE_DDL)
            conn.execute(_FTS_INSERT_TRIGGER)
            conn.execute(_FTS_DELETE_TRIGGER)

    # ------------------------------------------------------------------
    # Index building
    # ------------------------------------------------------------------

    def build_index(self) -> int:
        """
        Rebuild the lessons index from all hotwash_events records.

        Clears and repopulates the lessons_index table. Safe to call
        repeatedly — idempotent.

        Returns:
            int: Number of lesson records indexed.
        """
        with get_conn(self._db_path) as conn:
            # Reason: deleting lessons_index fires the AD trigger which removes FTS rows;
            # then 'rebuild' syncs the FTS index from the (now empty) content table.
            # Explicitly deleting lessons_fts before the trigger fires corrupts the DB.
            conn.execute("DELETE FROM lessons_index")
            conn.execute("INSERT INTO lessons_fts(lessons_fts) VALUES('rebuild')")

            rows = conn.execute(
                "SELECT h.id AS hotwash_id, h.proposal_id, h.outcome, "
                "h.event_date AS conducted_date, h.lessons_learned, "
                "p.title AS proposal_title, p.solicitation_number "
                "FROM hotwash_events h "
                "LEFT JOIN proposals p ON h.proposal_id = p.id"
            ).fetchall()

        count = 0
        for row in rows:
            row_dict = dict(row)
            raw_lessons = row_dict.get("lessons_learned", "[]")
            try:
                lessons = json.loads(raw_lessons) if isinstance(raw_lessons, str) else raw_lessons
            except json.JSONDecodeError:
                lessons = []

            if not isinstance(lessons, list):
                continue

            for lesson in lessons:
                if not isinstance(lesson, dict):
                    continue
                if self._index_lesson(lesson, row_dict):
                    count += 1

        logger.info("Built lessons index: %d records from %d hotwash events", count, len(rows))
        return count

    def _index_lesson(self, lesson: Dict[str, Any], hotwash_ctx: Dict[str, Any]) -> bool:
        """
        Insert one lesson into the index table.

        Args:
            lesson: Lesson dict (id, lesson/lesson_text, category, impact, etc.).
            hotwash_ctx: Row context from the JOIN query.

        Returns:
            bool: True if the lesson was indexed, False if skipped.
        """
        # Reason: Lesson text may be stored under 'lesson' or 'lesson_text' key
        lesson_text = str(lesson.get("lesson") or lesson.get("lesson_text") or "").strip()
        if not lesson_text:
            return False

        category = str(lesson.get("category", "other")).lower()
        if category not in LESSON_CATEGORIES:
            category = "other"

        impact = str(lesson.get("impact", "medium")).lower()
        if impact not in IMPACT_LEVELS:
            impact = "medium"

        with get_conn(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO lessons_index (
                    lesson_id, lesson_text, recommended_action, category, impact,
                    source, owner, proposal_id, proposal_title, solicitation_number,
                    outcome, conducted_date, hotwash_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(lesson.get("id", "")),
                    lesson_text,
                    str(lesson.get("recommended_action", "")),
                    category,
                    impact,
                    str(lesson.get("source", "internal")),
                    str(lesson.get("owner", "TBD")),
                    str(hotwash_ctx.get("proposal_id", "")),
                    str(hotwash_ctx.get("proposal_title", "")),
                    str(hotwash_ctx.get("solicitation_number", "")),
                    str(hotwash_ctx.get("outcome", "")),
                    str(hotwash_ctx.get("conducted_date", "")),
                    str(hotwash_ctx.get("hotwash_id", "")),
                ),
            )
        return True

    # ------------------------------------------------------------------
    # Keyword search (FTS5)
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        impact: Optional[str] = None,
        outcome: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[LessonSearchResult]:
        """
        Full-text keyword search over indexed lessons.

        Args:
            query: Search terms. FTS5 syntax supported (e.g., '"past performance"').
            limit: Maximum number of results to return.
            category: Optional filter by lesson category.
            impact: Optional filter by impact level.
            outcome: Optional filter by proposal outcome ('WIN', 'LOSS', etc.).
            min_score: Minimum relevance score threshold (0.0 = no threshold).

        Returns:
            List[LessonSearchResult]: Ranked results, most relevant first.
        """
        if not query.strip():
            return self._list_all(limit, category, impact, outcome)

        # Build WHERE clause for metadata filters (prefixed with li. for JOIN query)
        raw_filters, params = self._build_filters(category, impact, outcome)
        # Reason: 'category' exists in both lessons_fts and lessons_index; must qualify
        join_filters = [f"li.{f}" for f in raw_filters]

        # Reason: FTS5 bm25() returns negative scores; negate for ascending sort
        sql = f"""
            SELECT
                li.lesson_id, li.lesson_text, li.recommended_action,
                li.category, li.impact, li.source, li.owner,
                li.proposal_id, li.proposal_title, li.solicitation_number,
                li.outcome, li.conducted_date,
                -bm25(lessons_fts) AS score
            FROM lessons_fts
            JOIN lessons_index li ON lessons_fts.rowid = li.rowid
            WHERE lessons_fts MATCH ?
            {"AND " + " AND ".join(join_filters) if join_filters else ""}
            {"AND score >= ?" if min_score > 0 else ""}
            ORDER BY score DESC
            LIMIT ?
        """
        match_params = [query] + params
        if min_score > 0:
            match_params.append(min_score)
        match_params.append(limit)

        try:
            with get_conn(self._db_path) as conn:
                rows = conn.execute(sql, match_params).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning("FTS search failed ('%s'): %s — falling back to LIKE", query, exc)
            return self._fallback_search(query, limit, category, impact, outcome)

        return [self._row_to_result(row) for row in rows]

    def _list_all(
        self,
        limit: int,
        category: Optional[str],
        impact: Optional[str],
        outcome: Optional[str],
    ) -> List[LessonSearchResult]:
        """Return all indexed lessons matching the given filters, no text query."""
        filters, params = self._build_filters(category, impact, outcome)
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        sql = f"SELECT * FROM lessons_index {where} ORDER BY rowid DESC LIMIT ?"
        with get_conn(self._db_path) as conn:
            rows = conn.execute(sql, params + [limit]).fetchall()
        return [self._row_to_result(row, score=0.0) for row in rows]

    def _fallback_search(
        self,
        query: str,
        limit: int,
        category: Optional[str],
        impact: Optional[str],
        outcome: Optional[str],
    ) -> List[LessonSearchResult]:
        """LIKE-based fallback when FTS5 fails (e.g., special chars in query)."""
        filters, params = self._build_filters(category, impact, outcome)
        term = f"%{query}%"
        # Reason: LIKE filter appended last so params order matches filter order
        filters.append("(lesson_text LIKE ? OR recommended_action LIKE ?)")
        params = params + [term, term]
        where = "WHERE " + " AND ".join(filters)
        sql = f"SELECT * FROM lessons_index {where} LIMIT ?"
        with get_conn(self._db_path) as conn:
            rows = conn.execute(sql, params + [limit]).fetchall()
        return [self._row_to_result(row, score=1.0) for row in rows]

    def _build_filters(
        self,
        category: Optional[str],
        impact: Optional[str],
        outcome: Optional[str],
    ) -> tuple:
        """
        Build SQL WHERE conditions and param list from optional filters.

        Args:
            category: Lesson category filter.
            impact: Impact level filter.
            outcome: Proposal outcome filter.

        Returns:
            Tuple of (list[str] conditions, list params).
        """
        filters: List[str] = []
        params: List[Any] = []
        if category:
            filters.append("category = ?")
            params.append(category.lower())
        if impact:
            filters.append("impact = ?")
            params.append(impact.lower())
        if outcome:
            filters.append("outcome = ?")
            params.append(outcome.upper())
        return filters, params

    def _row_to_result(self, row: sqlite3.Row, score: Optional[float] = None) -> LessonSearchResult:
        """
        Convert a database row to a LessonSearchResult.

        Args:
            row: Row from lessons_index or FTS query.
            score: Override relevance score (uses row['score'] if None).

        Returns:
            LessonSearchResult: Populated result object.
        """
        d = dict(row)
        return LessonSearchResult(
            lesson_id=d.get("lesson_id", ""),
            lesson_text=d.get("lesson_text", ""),
            recommended_action=d.get("recommended_action", ""),
            category=d.get("category", "other"),
            impact=d.get("impact", "medium"),
            source=d.get("source", "internal"),
            owner=d.get("owner", "TBD"),
            proposal_id=d.get("proposal_id", ""),
            proposal_title=d.get("proposal_title", ""),
            solicitation_number=d.get("solicitation_number", ""),
            outcome=d.get("outcome", ""),
            conducted_date=d.get("conducted_date", ""),
            score=score if score is not None else float(d.get("score", 0.0)),
        )

    # ------------------------------------------------------------------
    # Semantic search (Ollama embeddings — optional)
    # ------------------------------------------------------------------

    def search_semantic(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        impact: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> List[LessonSearchResult]:
        """
        Semantic similarity search using Ollama embeddings.

        Embeds the query and all candidate lessons, then ranks by cosine
        similarity. Falls back to keyword search if Ollama is unavailable.

        Args:
            query: Natural language query.
            limit: Maximum number of results.
            category: Optional category filter.
            impact: Optional impact filter.
            outcome: Optional outcome filter.

        Returns:
            List[LessonSearchResult]: Results ranked by semantic similarity.
        """
        query_embedding = self._embed(query)
        if query_embedding is None:
            logger.info("Ollama unavailable — falling back to FTS keyword search")
            return self.search(query, limit, category, impact, outcome)

        # Fetch candidate lessons (apply filters before embedding)
        candidates = self._list_all(500, category, impact, outcome)
        if not candidates:
            return []

        # Score each candidate by cosine similarity
        scored: List[tuple] = []
        for candidate in candidates:
            text = f"{candidate.lesson_text} {candidate.recommended_action}"
            emb = self._embed(text)
            if emb is None:
                continue
            sim = self._cosine_similarity(query_embedding, emb)
            scored.append((sim, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, candidate in scored[:limit]:
            candidate.score = sim
            results.append(candidate)
        return results

    def _embed(self, text: str) -> Optional[List[float]]:
        """
        Get an embedding vector from Ollama for the given text.

        Args:
            text: Input text to embed.

        Returns:
            List[float] embedding or None if Ollama is unavailable.
        """
        try:
            resp = requests.post(
                f"{self._ollama_url}/api/embeddings",
                json={"model": self._embed_model, "prompt": text[:2000]},
                timeout=10,
            )
            if resp.ok:
                return resp.json().get("embedding")
        except requests.RequestException as exc:
            logger.debug("Ollama embedding unavailable: %s", exc)
        return None

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            float: Similarity score in [-1, 1].
        """
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def count(self) -> int:
        """
        Return the number of indexed lesson records.

        Returns:
            int: Total lessons in the index.
        """
        with get_conn(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM lessons_index").fetchone()
        return row[0] if row else 0

    def get_categories(self) -> List[str]:
        """
        Return all lesson categories present in the index.

        Returns:
            List[str]: Distinct category values.
        """
        with get_conn(self._db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM lessons_index ORDER BY category"
            ).fetchall()
        return [r[0] for r in rows]

    def get_outcomes(self) -> List[str]:
        """
        Return all proposal outcomes present in the index.

        Returns:
            List[str]: Distinct outcome values.
        """
        with get_conn(self._db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT outcome FROM lessons_index WHERE outcome != '' ORDER BY outcome"
            ).fetchall()
        return [r[0] for r in rows]
