"""
Tests for proposal/hotwash.py

Covers:
    - Expected use: lesson creation, hotwash build, DOCX export
    - Edge cases: unknown categories, all-pending outcomes, empty debrief
    - Failure cases: Ollama unavailable, missing fields
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from proposal.hotwash import (
    IMPACT_LEVELS,
    LESSON_CATEGORIES,
    DebriefNotes,
    HotwashRecord,
    Lesson,
    build_hotwash_from_dict,
    create_lessons,
    export_hotwash_docx,
    generate_improvement_insights,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_lessons():
    return [
        Lesson("LL-001", "technical_approach",
               "Didn't address the SIEM requirement clearly.",
               impact="critical",
               recommended_action="Add a SIEM section to standard tech volume template."),
        Lesson("LL-002", "schedule_management",
               "Pink Team scheduled too late — insufficient time to incorporate changes.",
               impact="high",
               recommended_action="Schedule Pink Team no later than D-30."),
        Lesson("LL-003", "teaming",
               "Sub's past performance was weaker than expected.",
               impact="medium",
               recommended_action="Pre-qualify subs earlier in capture phase."),
    ]


@pytest.fixture
def sample_debrief():
    return DebriefNotes(
        received=True,
        date="2026-03-15",
        overall_score="82/100",
        ranking="2nd of 4",
        strengths=["Strong management approach", "Well-qualified key personnel"],
        weaknesses=["Technical solution lacked detail on SIEM implementation"],
        price_position="$2M above awardee",
    )


@pytest.fixture
def complete_record(sample_lessons, sample_debrief):
    return HotwashRecord(
        solicitation_number="FA8612-26-R-0001",
        proposal_title="Cloud Infrastructure Support",
        outcome="LOSS",
        submitted_date="2026-02-28",
        conducted_date="2026-03-30",
        facilitator="Alice",
        attendees=["Alice", "Bob", "Charlie"],
        debrief=sample_debrief,
        lessons=sample_lessons,
        process_improvements=[
            "Move Pink Team to D-30 on all future proposals",
            "Add SIEM capability to standard template library",
        ],
        action_items=[
            {"action": "Update tech volume template", "owner": "Alice", "due_date": "2026-04-30"},
        ],
        summary="We lost primarily on price and a gap in SIEM technical detail.",
    )


# ---------------------------------------------------------------------------
# Lesson
# ---------------------------------------------------------------------------

class TestLesson:
    def test_to_dict_has_all_fields(self):
        l = Lesson("LL-001", "technical_approach", "Test lesson", impact="high")
        d = l.to_dict()
        assert set(d.keys()) == {"id", "category", "lesson", "impact", "recommended_action",
                                  "owner", "due_date", "source"}

    def test_default_impact_is_medium(self):
        l = Lesson("LL-001", "other", "Lesson text")
        assert l.impact == "medium"

    def test_default_owner_is_tbd(self):
        l = Lesson("LL-001", "other", "Lesson text")
        assert l.owner == "TBD"


# ---------------------------------------------------------------------------
# create_lessons
# ---------------------------------------------------------------------------

class TestCreateLessons:
    def test_creates_correct_count(self):
        raw = [
            {"lesson": "Lesson 1", "category": "technical_approach", "impact": "high"},
            {"lesson": "Lesson 2", "category": "teaming", "impact": "medium"},
        ]
        lessons = create_lessons(raw)
        assert len(lessons) == 2

    def test_auto_generates_ids(self):
        raw = [{"lesson": "L1", "category": "other"}]
        lessons = create_lessons(raw, id_prefix="LL")
        assert lessons[0].id == "LL-001"

    def test_preserves_explicit_id(self):
        raw = [{"id": "MY-42", "lesson": "L1", "category": "other"}]
        lessons = create_lessons(raw)
        assert lessons[0].id == "MY-42"

    def test_unknown_category_defaults_to_other(self):
        raw = [{"lesson": "Weird lesson", "category": "alien_technology"}]
        lessons = create_lessons(raw)
        assert lessons[0].category == "other"

    def test_unknown_impact_defaults_to_medium(self):
        raw = [{"lesson": "L1", "category": "other", "impact": "extreme"}]
        lessons = create_lessons(raw)
        assert lessons[0].impact == "medium"

    def test_all_valid_categories_accepted(self):
        for cat in LESSON_CATEGORIES:
            raw = [{"lesson": "Test", "category": cat}]
            lessons = create_lessons(raw)
            assert lessons[0].category == cat

    def test_empty_input_returns_empty(self):
        assert create_lessons([]) == []


# ---------------------------------------------------------------------------
# HotwashRecord
# ---------------------------------------------------------------------------

class TestHotwashRecord:
    def test_lessons_by_category(self, complete_record):
        grouped = complete_record.lessons_by_category()
        assert "technical_approach" in grouped
        assert "schedule_management" in grouped

    def test_lessons_by_impact(self, complete_record):
        grouped = complete_record.lessons_by_impact()
        assert "critical" in grouped
        assert "high" in grouped
        # medium lessons present
        assert "medium" in grouped

    def test_critical_lessons_filter(self, complete_record):
        critical = complete_record.critical_lessons()
        assert len(critical) == 1
        assert critical[0].id == "LL-001"

    def test_to_dict_has_required_keys(self, complete_record):
        d = complete_record.to_dict()
        expected = {
            "solicitation_number", "proposal_title", "outcome", "submitted_date",
            "conducted_date", "facilitator", "attendees", "debrief", "lessons",
            "process_improvements", "action_items", "summary",
        }
        assert expected <= set(d.keys())

    def test_debrief_in_dict(self, complete_record):
        d = complete_record.to_dict()
        assert d["debrief"]["received"] is True
        assert d["debrief"]["ranking"] == "2nd of 4"

    def test_no_lessons_critical_returns_empty(self):
        record = HotwashRecord("FA001", "Test", outcome="WIN")
        assert record.critical_lessons() == []


# ---------------------------------------------------------------------------
# build_hotwash_from_dict
# ---------------------------------------------------------------------------

class TestBuildHotwashFromDict:
    def test_builds_from_complete_dict(self):
        data = {
            "solicitation_number": "TEST-001",
            "proposal_title": "My Proposal",
            "outcome": "win",   # should be uppercased
            "submitted_date": "2026-02-01",
            "debrief": {
                "received": True,
                "strengths": ["Strong technical"],
                "weaknesses": ["Weak management"],
                "price_position": "On target",
            },
            "lessons": [
                {"lesson": "Better pink team", "category": "proposal_process", "impact": "high"}
            ],
            "process_improvements": ["Improve schedule"],
            "action_items": [{"action": "Update template", "owner": "Alice", "due_date": "2026-04-01"}],
        }
        record = build_hotwash_from_dict(data)
        assert record.solicitation_number == "TEST-001"
        assert record.outcome == "WIN"
        assert record.debrief.received is True
        assert len(record.lessons) == 1
        assert record.debrief.strengths == ["Strong technical"]

    def test_empty_dict_builds_defaults(self):
        record = build_hotwash_from_dict({})
        assert record.outcome == "PENDING"
        assert record.lessons == []
        assert record.debrief.received is False

    def test_conducted_date_defaults_to_today(self):
        record = build_hotwash_from_dict({"solicitation_number": "X"})
        assert record.conducted_date == date.today().isoformat()


# ---------------------------------------------------------------------------
# generate_improvement_insights
# ---------------------------------------------------------------------------

class TestGenerateImprovementInsights:
    def test_returns_ollama_response(self, complete_record):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "1. Improve schedule\n2. Better subs"}
        mock_resp.raise_for_status.return_value = None
        with patch("requests.post", return_value=mock_resp):
            result = generate_improvement_insights(complete_record)
        assert "Improve schedule" in result

    def test_fallback_when_ollama_down_with_critical(self, complete_record):
        with patch("requests.post", side_effect=requests.ConnectionError("down")):
            result = generate_improvement_insights(complete_record)
        assert "Critical" in result or "SIEM" in result

    def test_fallback_when_no_lessons(self):
        record = HotwashRecord("FA001", "Test", outcome="WIN")
        with patch("requests.post", side_effect=requests.ConnectionError("down")):
            result = generate_improvement_insights(record)
        assert result is not None
        assert len(result) > 0


# ---------------------------------------------------------------------------
# export_hotwash_docx
# ---------------------------------------------------------------------------

class TestExportHotwashDocx:
    def test_creates_docx_file(self, complete_record, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        out = export_hotwash_docx(complete_record)
        assert out.is_file()
        assert out.suffix == ".docx"

    def test_filename_contains_solicitation(self, complete_record, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        out = export_hotwash_docx(complete_record)
        assert "FA8612" in out.name
        assert "hotwash" in out.name

    def test_explicit_output_path(self, complete_record, tmp_path):
        out_path = tmp_path / "hotwash.docx"
        result = export_hotwash_docx(complete_record, output_path=out_path)
        assert result == out_path
        assert out_path.is_file()

    def test_no_debrief_still_writes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        record = HotwashRecord("FA001", "Test Proposal", outcome="WIN")
        out = export_hotwash_docx(record)
        assert out.is_file()

    def test_win_outcome_writes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        record = HotwashRecord("FA002", "Win Proposal", outcome="WIN")
        out = export_hotwash_docx(record)
        assert out.is_file()

    def test_no_lessons_no_crash(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        record = HotwashRecord("FA003", "Empty Proposal", outcome="PENDING",
                               lessons=[], action_items=[])
        out = export_hotwash_docx(record)
        assert out.is_file()
