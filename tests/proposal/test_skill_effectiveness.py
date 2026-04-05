"""
Tests for proposal/skill_effectiveness.py

Uses a temporary SQLite database for isolation.
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from proposal.skill_effectiveness import SkillRating, SkillStats, SkillTracker, WinLossReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_db(tmp_path: Path) -> Path:
    """Create minimal proposals + hotwash_events schema."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE proposals (
            id TEXT PRIMARY KEY,
            title TEXT DEFAULT '',
            solicitation_number TEXT DEFAULT '',
            pipeline_stage TEXT DEFAULT 'active',
            agency TEXT DEFAULT '',
            estimated_value REAL DEFAULT 0.0,
            pwin_score REAL
        )
    """)
    conn.execute("""
        CREATE TABLE hotwash_events (
            id TEXT PRIMARY KEY,
            proposal_id TEXT,
            outcome TEXT DEFAULT '',
            event_date TEXT DEFAULT '',
            lessons_learned TEXT DEFAULT '[]'
        )
    """)
    conn.commit()
    conn.close()
    return db


def _add_proposal(db: Path, pid: str, stage: str, agency: str = "DoD",
                  value: float = 1e6, pwin: float = 0.5) -> None:
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO proposals (id, pipeline_stage, agency, estimated_value, pwin_score) "
        "VALUES (?, ?, ?, ?, ?)",
        (pid, stage, agency, value, pwin),
    )
    conn.commit()
    conn.close()


def _tracker(tmp_path: Path) -> SkillTracker:
    db = _setup_db(tmp_path)
    return SkillTracker(db_path=db)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    def test_creates_skill_ratings_table(self, tmp_path):
        db = _setup_db(tmp_path)
        SkillTracker(db_path=db)
        conn = sqlite3.connect(str(db))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        conn.close()
        assert "skill_ratings" in tables

    def test_idempotent_schema_creation(self, tmp_path):
        db = _setup_db(tmp_path)
        # Call twice — should not raise
        SkillTracker(db_path=db)
        SkillTracker(db_path=db)


# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------

class TestRating:
    def test_rate_returns_skill_rating(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "P1", "awarded")
        r = t.rate("bid-no-bid", "P1", "WIN", 4)
        assert isinstance(r, SkillRating)
        assert r.rating == 4
        assert r.skill_name == "bid-no-bid"
        assert r.outcome == "WIN"

    def test_rate_stores_record_in_db(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "P1", "awarded")
        t.rate("shredding", "P1", "WIN", 5, notes="Excellent extraction")
        ratings = t.get_ratings(skill="shredding")
        assert len(ratings) == 1
        assert ratings[0].notes == "Excellent extraction"

    def test_rate_rejects_out_of_range(self, tmp_path):
        t = _tracker(tmp_path)
        with pytest.raises(ValueError, match="Rating must be 1"):
            t.rate("bid-no-bid", "P1", "WIN", 0)

    def test_rate_rejects_above_5(self, tmp_path):
        t = _tracker(tmp_path)
        with pytest.raises(ValueError):
            t.rate("bid-no-bid", "P1", "WIN", 6)

    def test_rate_normalizes_outcome_to_upper(self, tmp_path):
        t = _tracker(tmp_path)
        r = t.rate("shredding", "P1", "loss", 2)
        assert r.outcome == "LOSS"

    def test_rate_assigns_id(self, tmp_path):
        t = _tracker(tmp_path)
        r = t.rate("cost-estimator", "P1", "WIN", 3)
        assert r.id is not None

    def test_multiple_ratings_same_skill(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("document-drafter", "P1", "WIN", 4)
        t.rate("document-drafter", "P2", "LOSS", 2)
        ratings = t.get_ratings(skill="document-drafter")
        assert len(ratings) == 2


# ---------------------------------------------------------------------------
# Get ratings + filtering
# ---------------------------------------------------------------------------

class TestGetRatings:
    def test_filter_by_skill(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("bid-no-bid", "P1", "WIN", 5)
        t.rate("shredding", "P2", "LOSS", 2)
        results = t.get_ratings(skill="bid-no-bid")
        assert len(results) == 1
        assert results[0].skill_name == "bid-no-bid"

    def test_filter_by_proposal(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("bid-no-bid", "P1", "WIN", 4)
        t.rate("shredding", "P1", "WIN", 3)
        t.rate("bid-no-bid", "P2", "LOSS", 1)
        results = t.get_ratings(proposal_id="P1")
        assert len(results) == 2

    def test_filter_by_outcome(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("bid-no-bid", "P1", "WIN", 5)
        t.rate("bid-no-bid", "P2", "LOSS", 2)
        wins = t.get_ratings(outcome="WIN")
        assert len(wins) == 1
        assert wins[0].outcome == "WIN"

    def test_returns_empty_list_when_no_match(self, tmp_path):
        t = _tracker(tmp_path)
        assert t.get_ratings(skill="nonexistent-skill") == []

    def test_to_dict_serializable(self, tmp_path):
        t = _tracker(tmp_path)
        r = t.rate("bid-no-bid", "P1", "WIN", 4)
        d = r.to_dict()
        assert "skill_name" in d
        assert "rating" in d


# ---------------------------------------------------------------------------
# Skill stats
# ---------------------------------------------------------------------------

class TestSkillStats:
    def test_stats_returns_none_with_no_ratings(self, tmp_path):
        t = _tracker(tmp_path)
        assert t.skill_stats("unknown") is None

    def test_stats_avg_rating(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("shredding", "P1", "WIN", 4)
        t.rate("shredding", "P2", "LOSS", 2)
        stats = t.skill_stats("shredding")
        assert stats is not None
        assert abs(stats.avg_rating - 3.0) < 0.01

    def test_stats_win_loss_averages(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("bid-no-bid", "P1", "WIN", 5)
        t.rate("bid-no-bid", "P2", "WIN", 3)
        t.rate("bid-no-bid", "P3", "LOSS", 1)
        stats = t.skill_stats("bid-no-bid")
        assert stats is not None
        assert abs(stats.win_avg - 4.0) < 0.01
        assert stats.loss_avg == 1.0

    def test_stats_win_avg_none_when_no_wins(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("shredding", "P1", "LOSS", 3)
        stats = t.skill_stats("shredding")
        assert stats.win_avg is None

    def test_all_skill_stats_sorted_descending(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("bid-no-bid", "P1", "WIN", 5)
        t.rate("shredding", "P2", "WIN", 2)
        all_stats = t.all_skill_stats()
        assert all_stats[0].avg_rating >= all_stats[-1].avg_rating

    def test_stats_to_dict(self, tmp_path):
        t = _tracker(tmp_path)
        t.rate("bid-no-bid", "P1", "WIN", 4)
        stats = t.skill_stats("bid-no-bid")
        d = stats.to_dict()
        assert "avg_rating" in d
        assert "win_avg" in d


# ---------------------------------------------------------------------------
# Lesson injection
# ---------------------------------------------------------------------------

class TestLessonInjection:
    def test_inject_returns_list(self, tmp_path):
        t = _tracker(tmp_path)
        # No lessons indexed — should return empty list gracefully
        results = t.inject_lessons("bid-no-bid", "competitive analysis")
        assert isinstance(results, list)

    def test_inject_uses_skill_categories(self, tmp_path):
        t = _tracker(tmp_path)
        # Verify the category mapping exists for known skills
        cats = SkillTracker._SKILL_LESSON_CATEGORIES.get("document-drafter", [])
        assert "technical_approach" in cats

    def test_inject_unknown_skill_falls_back(self, tmp_path):
        t = _tracker(tmp_path)
        # Unknown skill should not raise — searches all categories
        results = t.inject_lessons("some-unknown-skill", "some query")
        assert isinstance(results, list)

    def test_format_lessons_returns_empty_when_no_lessons(self, tmp_path):
        t = _tracker(tmp_path)
        context = t.format_lessons_as_context("bid-no-bid")
        assert context == ""

    def test_format_lessons_returns_string(self, tmp_path):
        t = _tracker(tmp_path)
        # Patch inject_lessons to return a fake lesson
        t.inject_lessons = MagicMock(return_value=[{
            "lesson_text": "Past performance was weak",
            "category": "past_performance",
            "outcome": "LOSS",
            "recommended_action": "Use PP library",
            "lesson_id": "LL-001",
        }])
        context = t.format_lessons_as_context("document-drafter")
        assert "Past performance was weak" in context
        assert "PP library" in context

    def test_inject_deduplicates_by_lesson_id(self, tmp_path):
        t = _tracker(tmp_path)
        # Simulate duplicate results from category search
        fake_lesson = {
            "lesson_text": "Dup lesson",
            "category": "technical_approach",
            "outcome": "WIN",
            "recommended_action": "",
            "lesson_id": "LL-SAME",
            "score": 1.0,
        }
        from proposal.lessons_search import LessonSearchResult
        mock_result = MagicMock(spec=LessonSearchResult)
        mock_result.lesson_id = "LL-SAME"
        mock_result.lesson_text = "Dup lesson"
        mock_result.score = 1.0
        mock_result.to_dict.return_value = fake_lesson
        t._lessons.search = MagicMock(return_value=[mock_result, mock_result])
        results = t.inject_lessons("document-drafter", "technical", limit=10)
        assert len(results) <= 1  # deduplication applied


# ---------------------------------------------------------------------------
# Win/Loss analysis
# ---------------------------------------------------------------------------

class TestWinLossAnalysis:
    def test_empty_db_returns_zero_counts(self, tmp_path):
        t = _tracker(tmp_path)
        report = t.win_loss_analysis()
        assert report.total_proposals == 0
        assert report.win_rate == 0.0
        assert len(report.patterns) >= 1  # "no data" pattern

    def test_win_rate_calculated(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "P1", "awarded", pwin=0.8)
        _add_proposal(t._db_path, "P2", "awarded", pwin=0.7)
        _add_proposal(t._db_path, "P3", "lost", pwin=0.4)
        report = t.win_loss_analysis()
        assert report.wins == 2
        assert report.losses == 1
        assert abs(report.win_rate - 2 / 3) < 0.01

    def test_avg_pwin_computed_for_wins_and_losses(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "W1", "awarded", pwin=0.8)
        _add_proposal(t._db_path, "W2", "awarded", pwin=0.6)
        _add_proposal(t._db_path, "L1", "lost", pwin=0.3)
        report = t.win_loss_analysis()
        assert abs(report.avg_pwin_wins - 0.7) < 0.01
        assert abs(report.avg_pwin_losses - 0.3) < 0.01

    def test_top_win_agencies(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "W1", "awarded", agency="AFRL")
        _add_proposal(t._db_path, "W2", "awarded", agency="AFRL")
        _add_proposal(t._db_path, "W3", "awarded", agency="DARPA")
        report = t.win_loss_analysis()
        agencies = [a for a, _ in report.top_win_agencies]
        assert "AFRL" in agencies
        assert agencies[0] == "AFRL"  # most wins

    def test_report_to_dict_serializable(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "P1", "awarded")
        report = t.win_loss_analysis()
        d = report.to_dict()
        assert "win_rate" in d
        assert "patterns" in d
        assert isinstance(d["patterns"], list)

    def test_pwin_pattern_detected(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "W1", "awarded", pwin=0.9)
        _add_proposal(t._db_path, "W2", "awarded", pwin=0.8)
        _add_proposal(t._db_path, "L1", "lost", pwin=0.3)
        _add_proposal(t._db_path, "L2", "lost", pwin=0.2)
        report = t.win_loss_analysis()
        # Should detect the pWin difference
        pwin_patterns = [p for p in report.patterns if "pWin" in p]
        assert len(pwin_patterns) >= 1

    def test_proposals_in_other_stages_excluded(self, tmp_path):
        t = _tracker(tmp_path)
        _add_proposal(t._db_path, "P1", "active")   # not won/lost
        _add_proposal(t._db_path, "P2", "submitted")  # not won/lost
        report = t.win_loss_analysis()
        assert report.total_proposals == 0
