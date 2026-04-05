"""
Tests for proposal/lessons_search.py

All tests use an in-memory (tmp_path) SQLite database to avoid
touching the real search_system.db or proposals database.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from proposal.lessons_search import LessonSearchResult, LessonsSearchIndex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_db(tmp_path: Path) -> Path:
    """Create a minimal proposals + hotwash_events schema in a temp DB."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE proposals (
            id TEXT PRIMARY KEY,
            title TEXT,
            solicitation_number TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE hotwash_events (
            id TEXT PRIMARY KEY,
            proposal_id TEXT,
            outcome TEXT,
            event_date TEXT,
            lessons_learned TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db


def _insert_hotwash(
    db: Path,
    proposal_id: str = "P1",
    outcome: str = "LOSS",
    lessons: list = None,
    hotwash_id: str = "HW1",
) -> None:
    """Insert a proposal and matching hotwash_event into the test DB."""
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT OR IGNORE INTO proposals (id, title, solicitation_number) VALUES (?, ?, ?)",
        (proposal_id, f"Proposal {proposal_id}", f"SOL-{proposal_id}"),
    )
    conn.execute(
        "INSERT INTO hotwash_events (id, proposal_id, outcome, event_date, lessons_learned) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            hotwash_id, proposal_id, outcome, "2026-03-01",
            json.dumps(lessons or [
                {
                    "id": "LL-001",
                    "lesson": "Past performance volume lacked relevance examples",
                    "category": "past_performance",
                    "impact": "high",
                    "recommended_action": "Build a reusable past performance library",
                    "owner": "PM",
                    "source": "debrief",
                }
            ]),
        ),
    )
    conn.commit()
    conn.close()


def _make_idx(db: Path) -> LessonsSearchIndex:
    """Build a LessonsSearchIndex pointing at the temp DB."""
    return LessonsSearchIndex(db_path=db)


# ---------------------------------------------------------------------------
# Schema and initialization
# ---------------------------------------------------------------------------

class TestSchemaSetup:
    def test_creates_lessons_index_table(self, tmp_path):
        db = _setup_db(tmp_path)
        _make_idx(db)
        conn = sqlite3.connect(str(db))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        conn.close()
        assert "lessons_index" in tables

    def test_creates_fts_table(self, tmp_path):
        db = _setup_db(tmp_path)
        _make_idx(db)
        conn = sqlite3.connect(str(db))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        conn.close()
        assert "lessons_fts" in tables

    def test_count_zero_before_build(self, tmp_path):
        db = _setup_db(tmp_path)
        idx = _make_idx(db)
        assert idx.count() == 0


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

class TestBuildIndex:
    def test_indexes_lessons_from_hotwash(self, tmp_path):
        db = _setup_db(tmp_path)
        _insert_hotwash(db)
        idx = _make_idx(db)
        count = idx.build_index()
        assert count == 1
        assert idx.count() == 1

    def test_indexes_multiple_lessons(self, tmp_path):
        db = _setup_db(tmp_path)
        lessons = [
            {"id": "LL-001", "lesson": "First lesson", "category": "other", "impact": "low"},
            {"id": "LL-002", "lesson": "Second lesson", "category": "teaming", "impact": "high"},
            {"id": "LL-003", "lesson": "Third lesson", "category": "cost_price", "impact": "medium"},
        ]
        _insert_hotwash(db, lessons=lessons)
        idx = _make_idx(db)
        assert idx.build_index() == 3

    def test_rebuild_clears_previous_index(self, tmp_path):
        db = _setup_db(tmp_path)
        _insert_hotwash(db)
        idx = _make_idx(db)
        idx.build_index()
        assert idx.count() == 1
        # Build again — should still be 1, not 2
        idx.build_index()
        assert idx.count() == 1

    def test_skips_lesson_with_empty_text(self, tmp_path):
        db = _setup_db(tmp_path)
        lessons = [
            {"id": "LL-001", "lesson": "", "category": "other", "impact": "low"},
            {"id": "LL-002", "lesson": "Valid lesson", "category": "other", "impact": "medium"},
        ]
        _insert_hotwash(db, lessons=lessons)
        idx = _make_idx(db)
        assert idx.build_index() == 1

    def test_handles_malformed_lessons_json(self, tmp_path):
        db = _setup_db(tmp_path)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO proposals (id, title, solicitation_number) VALUES ('P2', 'P2', 'S2')"
        )
        conn.execute(
            "INSERT INTO hotwash_events VALUES ('HW2', 'P2', 'WIN', '2026-01-01', 'NOT_JSON')"
        )
        conn.commit()
        conn.close()
        idx = _make_idx(db)
        # Should not raise; just index 0 lessons
        assert idx.build_index() == 0

    def test_unknown_category_falls_back_to_other(self, tmp_path):
        db = _setup_db(tmp_path)
        lessons = [{"id": "LL-X", "lesson": "A lesson", "category": "UNKNOWN_CAT", "impact": "high"}]
        _insert_hotwash(db, lessons=lessons)
        idx = _make_idx(db)
        idx.build_index()
        results = idx.search("lesson")
        assert results[0].category == "other"

    def test_lesson_text_key_variant(self, tmp_path):
        """Lessons stored with 'lesson_text' key instead of 'lesson' should be indexed."""
        db = _setup_db(tmp_path)
        lessons = [{"id": "LL-T", "lesson_text": "Alternative key lesson", "category": "other", "impact": "low"}]
        _insert_hotwash(db, lessons=lessons)
        idx = _make_idx(db)
        idx.build_index()
        assert idx.count() == 1


# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------

class TestKeywordSearch:
    def _populated_idx(self, tmp_path: Path) -> LessonsSearchIndex:
        db = _setup_db(tmp_path)
        lessons = [
            {
                "id": "LL-001",
                "lesson": "Past performance volume lacked relevance examples",
                "category": "past_performance",
                "impact": "high",
                "recommended_action": "Build a reusable past performance library",
                "source": "debrief",
                "owner": "PM",
            },
            {
                "id": "LL-002",
                "lesson": "Management approach section too generic",
                "category": "management_approach",
                "impact": "medium",
                "recommended_action": "Tailor management section to each agency",
                "source": "internal",
                "owner": "PD",
            },
            {
                "id": "LL-003",
                "lesson": "Cost volume submitted with arithmetic errors",
                "category": "cost_price",
                "impact": "critical",
                "recommended_action": "Mandatory cost volume QC checklist",
                "source": "debrief",
                "owner": "Finance",
            },
        ]
        _insert_hotwash(db, lessons=lessons, outcome="LOSS")
        idx = _make_idx(db)
        idx.build_index()
        return idx

    def test_search_returns_relevant_result(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("past performance")
        assert len(results) >= 1
        assert any("past" in r.lesson_text.lower() for r in results)

    def test_search_empty_query_returns_all(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("", limit=10)
        assert len(results) == 3

    def test_search_with_category_filter(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("", category="cost_price")
        assert len(results) == 1
        assert results[0].category == "cost_price"

    def test_search_with_impact_filter(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("", impact="critical")
        assert len(results) == 1
        assert results[0].impact == "critical"

    def test_search_with_outcome_filter(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("", outcome="WIN")
        assert len(results) == 0  # All inserted under LOSS

    def test_search_result_has_context_fields(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("cost volume")
        assert len(results) >= 1
        r = results[0]
        assert r.proposal_id == "P1"
        assert r.outcome == "LOSS"
        assert r.lesson_id != ""

    def test_search_returns_score(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("cost arithmetic errors")
        assert results[0].score > 0

    def test_search_limit_respected(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("", limit=2)
        assert len(results) <= 2

    def test_no_results_for_unrelated_query(self, tmp_path):
        idx = self._populated_idx(tmp_path)
        results = idx.search("quantum entanglement xyzzy")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Utility methods
# ---------------------------------------------------------------------------

class TestUtilityMethods:
    def test_get_categories_returns_distinct(self, tmp_path):
        db = _setup_db(tmp_path)
        lessons = [
            {"id": "LL-1", "lesson": "A", "category": "teaming", "impact": "low"},
            {"id": "LL-2", "lesson": "B", "category": "cost_price", "impact": "medium"},
            {"id": "LL-3", "lesson": "C", "category": "teaming", "impact": "high"},
        ]
        _insert_hotwash(db, lessons=lessons)
        idx = _make_idx(db)
        idx.build_index()
        cats = idx.get_categories()
        assert "teaming" in cats
        assert "cost_price" in cats
        assert cats.count("teaming") == 1  # distinct

    def test_get_outcomes_returns_distinct(self, tmp_path):
        db = _setup_db(tmp_path)
        _insert_hotwash(db, proposal_id="P1", outcome="WIN", hotwash_id="HW1")
        _insert_hotwash(db, proposal_id="P2", outcome="LOSS", hotwash_id="HW2")
        idx = _make_idx(db)
        idx.build_index()
        outcomes = idx.get_outcomes()
        assert "WIN" in outcomes
        assert "LOSS" in outcomes

    def test_to_dict_serializable(self, tmp_path):
        db = _setup_db(tmp_path)
        _insert_hotwash(db)
        idx = _make_idx(db)
        idx.build_index()
        results = idx.search("past performance")
        assert len(results) >= 1
        d = results[0].to_dict()
        assert "lesson_text" in d
        assert "outcome" in d
        assert isinstance(d["score"], float)


# ---------------------------------------------------------------------------
# Semantic search (Ollama mocked)
# ---------------------------------------------------------------------------

class TestSemanticSearch:
    def _vec(self, n: int = 4) -> list:
        """Return a simple unit-like vector."""
        return [float(i) for i in range(1, n + 1)]

    def test_falls_back_to_keyword_when_ollama_unavailable(self, tmp_path):
        db = _setup_db(tmp_path)
        _insert_hotwash(db)
        idx = _make_idx(db)
        idx.build_index()
        idx._embed = MagicMock(return_value=None)
        results = idx.search_semantic("past performance")
        # Should call keyword search and return results without raising
        assert isinstance(results, list)

    def test_semantic_search_uses_cosine_similarity(self, tmp_path):
        db = _setup_db(tmp_path)
        _insert_hotwash(db)
        idx = _make_idx(db)
        idx.build_index()
        # Return a valid embedding for all calls
        idx._embed = MagicMock(return_value=self._vec())
        results = idx.search_semantic("past performance gaps")
        assert isinstance(results, list)

    def test_cosine_similarity_known_values(self, tmp_path):
        db = _setup_db(tmp_path)
        idx = _make_idx(db)
        a = [1.0, 0.0]
        b = [1.0, 0.0]
        assert abs(idx._cosine_similarity(a, b) - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal_vectors(self, tmp_path):
        db = _setup_db(tmp_path)
        idx = _make_idx(db)
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(idx._cosine_similarity(a, b)) < 1e-6

    def test_cosine_similarity_mismatched_lengths(self, tmp_path):
        db = _setup_db(tmp_path)
        idx = _make_idx(db)
        assert idx._cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_cosine_similarity_zero_vector(self, tmp_path):
        db = _setup_db(tmp_path)
        idx = _make_idx(db)
        assert idx._cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
