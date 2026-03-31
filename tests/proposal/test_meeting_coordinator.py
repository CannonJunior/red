"""
Tests for proposal/meeting_coordinator.py

Covers:
    - Expected use: agenda generation, action item creation, DOCX export
    - Edge cases: empty lists, all-done action items, boundary due dates
    - Failure cases: invalid meeting type, Ollama unavailable
"""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from proposal.meeting_coordinator import (
    AGENDA_TEMPLATES,
    MEETING_TYPES,
    ActionItem,
    MeetingRecord,
    action_items_by_owner,
    create_action_items,
    export_meeting_summary,
    generate_agenda,
    get_overdue_items,
    get_upcoming_items,
    summarize_notes,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def kickoff_meeting():
    return MeetingRecord(
        meeting_type="kickoff",
        title="Proposal Kickoff",
        date="2026-03-30",
        solicitation_number="FA8612-26-R-0001",
        attendees=["Alice", "Bob", "Charlie"],
        agenda_items=["Welcome", "Win strategy", "Assignments"],
        notes="Discussed win themes and schedule.",
        decisions=["Alice leads technical volume"],
        action_items=[
            ActionItem("AI-001", "Draft outline", "Alice",
                       (date.today() + timedelta(days=7)).isoformat()),
            ActionItem("AI-002", "Schedule pink team", "Bob",
                       (date.today() + timedelta(days=14)).isoformat()),
        ],
        facilitator="Alice",
        recorder="Charlie",
    )


@pytest.fixture
def mixed_action_items():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow  = (date.today() + timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=8)).isoformat()
    return [
        ActionItem("AI-001", "Overdue task", "Alice", yesterday, status="open"),
        ActionItem("AI-002", "Done task", "Bob", yesterday, status="done"),
        ActionItem("AI-003", "Due tomorrow", "Charlie", tomorrow, status="open"),
        ActionItem("AI-004", "Due next week", "Alice", next_week, status="open"),
    ]


# ---------------------------------------------------------------------------
# generate_agenda
# ---------------------------------------------------------------------------

class TestGenerateAgenda:
    def test_valid_type_returns_agenda(self):
        agenda = generate_agenda("kickoff", "FA001", "My Proposal")
        assert agenda["meeting_type"] == "kickoff"
        assert agenda["title"] == "Proposal Kickoff"
        assert len(agenda["agenda_items"]) > 0

    def test_all_meeting_types_have_templates(self):
        for mt in MEETING_TYPES:
            agenda = generate_agenda(mt, "FA001")
            assert agenda["item_count"] > 0, f"No agenda items for {mt}"

    def test_custom_items_appended(self):
        agenda = generate_agenda("weekly_sync", "FA001", custom_items=["Special topic"])
        assert "Special topic" in agenda["agenda_items"]

    def test_defaults_to_today(self):
        agenda = generate_agenda("kickoff", "FA001")
        assert agenda["date"] == date.today().isoformat()

    def test_custom_date_used(self):
        agenda = generate_agenda("kickoff", "FA001", meeting_date="2026-04-15")
        assert agenda["date"] == "2026-04-15"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unknown meeting_type"):
            generate_agenda("unicorn", "FA001")

    def test_solicitation_number_in_result(self):
        agenda = generate_agenda("pink_team", "FA8612-26-R-0001")
        assert agenda["solicitation_number"] == "FA8612-26-R-0001"

    def test_agenda_items_not_mutated_across_calls(self):
        a1 = generate_agenda("kickoff", "FA001", custom_items=["X"])
        a2 = generate_agenda("kickoff", "FA001", custom_items=["Y"])
        assert "X" not in a2["agenda_items"]
        assert "Y" not in a1["agenda_items"]


# ---------------------------------------------------------------------------
# ActionItem
# ---------------------------------------------------------------------------

class TestActionItem:
    def test_overdue_open_item(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        ai = ActionItem("AI-1", "Task", "Alice", yesterday, status="open")
        assert ai.is_overdue() is True

    def test_done_item_not_overdue(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        ai = ActionItem("AI-1", "Task", "Alice", yesterday, status="done")
        assert ai.is_overdue() is False

    def test_future_item_not_overdue(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        ai = ActionItem("AI-1", "Task", "Alice", tomorrow)
        assert ai.is_overdue() is False

    def test_days_until_due_negative_when_overdue(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        ai = ActionItem("AI-1", "Task", "Alice", yesterday)
        assert ai.days_until_due() == -1

    def test_days_until_due_positive_when_future(self):
        in_5_days = (date.today() + timedelta(days=5)).isoformat()
        ai = ActionItem("AI-1", "Task", "Alice", in_5_days)
        assert ai.days_until_due() == 5

    def test_invalid_date_not_overdue(self):
        ai = ActionItem("AI-1", "Task", "Alice", "not-a-date")
        assert ai.is_overdue() is False
        assert ai.days_until_due() is None


# ---------------------------------------------------------------------------
# create_action_items
# ---------------------------------------------------------------------------

class TestCreateActionItems:
    def test_creates_correct_count(self):
        raw = [
            {"action": "Draft section 2", "owner": "Alice", "due_date": "2026-04-10"},
            {"action": "Review cost", "owner": "Bob", "due_date": "2026-04-15"},
        ]
        items = create_action_items(raw, "Kickoff Meeting")
        assert len(items) == 2

    def test_auto_generates_ids(self):
        raw = [{"action": "Do something", "owner": "Alice", "due_date": "2026-04-10"}]
        items = create_action_items(raw, "Kickoff", id_prefix="KO")
        assert items[0].id == "KO-001"

    def test_preserves_explicit_id(self):
        raw = [{"id": "MYID-42", "action": "Something", "owner": "Alice", "due_date": "2026-04-10"}]
        items = create_action_items(raw, "Meeting")
        assert items[0].id == "MYID-42"

    def test_meeting_title_assigned(self):
        raw = [{"action": "Task", "owner": "Bob", "due_date": "2026-04-10"}]
        items = create_action_items(raw, "Pink Team Review")
        assert items[0].meeting_title == "Pink Team Review"

    def test_defaults_owner_to_tbd(self):
        raw = [{"action": "Task", "due_date": "2026-04-10"}]
        items = create_action_items(raw, "Meeting")
        assert items[0].owner == "TBD"

    def test_empty_list_returns_empty(self):
        assert create_action_items([], "Meeting") == []

    def test_start_index_applied(self):
        raw = [{"action": "Task", "owner": "Alice", "due_date": "2026-04-10"}]
        items = create_action_items(raw, "Meeting", start_index=5)
        assert items[0].id == "AI-005"


# ---------------------------------------------------------------------------
# get_overdue_items / get_upcoming_items
# ---------------------------------------------------------------------------

class TestOverdueAndUpcoming:
    def test_overdue_excludes_done(self, mixed_action_items):
        overdue = get_overdue_items(mixed_action_items)
        ids = [ai.id for ai in overdue]
        assert "AI-001" in ids
        assert "AI-002" not in ids  # done

    def test_upcoming_within_7_days(self, mixed_action_items):
        upcoming = get_upcoming_items(mixed_action_items, days_ahead=7)
        ids = [ai.id for ai in upcoming]
        assert "AI-003" in ids        # due tomorrow
        assert "AI-004" not in ids    # next week > 7 days

    def test_upcoming_within_14_days(self, mixed_action_items):
        upcoming = get_upcoming_items(mixed_action_items, days_ahead=14)
        ids = [ai.id for ai in upcoming]
        assert "AI-003" in ids
        assert "AI-004" in ids

    def test_overdue_sorted_by_date(self):
        two_days_ago = (date.today() - timedelta(days=2)).isoformat()
        one_day_ago  = (date.today() - timedelta(days=1)).isoformat()
        items = [
            ActionItem("AI-B", "B", "Bob", one_day_ago),
            ActionItem("AI-A", "A", "Alice", two_days_ago),
        ]
        overdue = get_overdue_items(items)
        assert overdue[0].id == "AI-A"

    def test_no_overdue_returns_empty(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        items = [ActionItem("AI-1", "Task", "Alice", tomorrow)]
        assert get_overdue_items(items) == []


# ---------------------------------------------------------------------------
# action_items_by_owner
# ---------------------------------------------------------------------------

class TestActionItemsByOwner:
    def test_groups_by_owner(self, mixed_action_items):
        grouped = action_items_by_owner(mixed_action_items)
        assert "Alice" in grouped
        assert "Charlie" in grouped

    def test_excludes_done_items(self, mixed_action_items):
        grouped = action_items_by_owner(mixed_action_items)
        # AI-002 is done and owned by Bob
        assert "Bob" not in grouped

    def test_empty_list_returns_empty_dict(self):
        assert action_items_by_owner([]) == {}

    def test_all_done_returns_empty_dict(self):
        items = [ActionItem("AI-1", "T", "Alice", "2026-04-01", status="done")]
        assert action_items_by_owner(items) == {}


# ---------------------------------------------------------------------------
# MeetingRecord.to_dict
# ---------------------------------------------------------------------------

class TestMeetingRecordToDict:
    def test_serializes_all_fields(self, kickoff_meeting):
        d = kickoff_meeting.to_dict()
        assert d["solicitation_number"] == "FA8612-26-R-0001"
        assert d["meeting_type"] == "kickoff"
        assert len(d["action_items"]) == 2
        assert d["action_items"][0]["id"] == "AI-001"

    def test_no_action_items_is_empty_list(self):
        record = MeetingRecord("weekly_sync", "Weekly", "2026-03-30", "FA001")
        d = record.to_dict()
        assert d["action_items"] == []


# ---------------------------------------------------------------------------
# export_meeting_summary
# ---------------------------------------------------------------------------

class TestExportMeetingSummary:
    def test_creates_docx_file(self, kickoff_meeting, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        out = export_meeting_summary(kickoff_meeting)
        assert out.is_file()
        assert out.suffix == ".docx"

    def test_filename_contains_type_and_date(self, kickoff_meeting, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        out = export_meeting_summary(kickoff_meeting)
        assert "kickoff" in out.name
        assert "20260330" in out.name

    def test_explicit_output_path(self, kickoff_meeting, tmp_path):
        out_path = tmp_path / "meeting.docx"
        result = export_meeting_summary(kickoff_meeting, output_path=out_path)
        assert result == out_path
        assert out_path.is_file()

    def test_empty_action_items_still_writes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path))
        record = MeetingRecord("weekly_sync", "Weekly Sync", "2026-03-30", "FA001",
                               attendees=["Alice"], agenda_items=["Status"])
        out = export_meeting_summary(record)
        assert out.is_file()


# ---------------------------------------------------------------------------
# summarize_notes
# ---------------------------------------------------------------------------

class TestSummarizeNotes:
    def test_returns_ollama_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "• Key point 1\n• Action: Alice by Friday"}
        mock_resp.raise_for_status.return_value = None
        with patch("requests.post", return_value=mock_resp):
            result = summarize_notes("Long raw notes here...", "kickoff")
        assert "Key point 1" in result

    def test_returns_raw_when_ollama_down(self):
        with patch("requests.post", side_effect=requests.ConnectionError("down")):
            result = summarize_notes("My raw notes", "pink_team")
        assert result == "My raw notes"

    def test_empty_notes_handled(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "No significant notes."}
        mock_resp.raise_for_status.return_value = None
        with patch("requests.post", return_value=mock_resp):
            result = summarize_notes("")
        assert result is not None
