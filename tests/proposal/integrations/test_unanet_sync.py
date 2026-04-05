"""
Tests for proposal/integrations/unanet_sync.py

All database and HTTP calls are mocked — no live instances required.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from proposal.integrations.unanet import UnanetAPIError
from proposal.integrations.unanet_sync import (
    SyncEntry,
    SyncResult,
    UnanetSyncManager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(offset_seconds: int = 0) -> str:
    """Return a UTC ISO timestamp offset by given seconds from now."""
    dt = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return dt.isoformat()


def _make_proposal(pid: str = "P1", updated_at: str = "", crm_id: str = "") -> MagicMock:
    """Build a mock Proposal object."""
    p = MagicMock()
    p.id = pid
    p.updated_at = updated_at or _iso(-3600)  # 1 hour ago
    p.crm_opportunity_id = crm_id
    p.model_dump.return_value = {
        "id": pid,
        "title": "Test Proposal",
        "pipeline_stage": "active",
        "pwin_score": 0.6,
        "agency": "DARPA",
        "solicitation_number": "DARPA-26-001",
        "estimated_value": 1_000_000,
        "notes": "Notes here",
        "updated_at": p.updated_at,
    }
    return p


def _make_manager(
    tmp_path: Path,
    proposals: list = (),
    state: dict = None,
    conflict_strategy: str = "prefer_local",
) -> UnanetSyncManager:
    """
    Build a UnanetSyncManager with mocked client and DB functions,
    and an isolated state file.
    """
    state_file = tmp_path / "sync_state.json"
    if state:
        state_file.write_text(json.dumps(state))

    mock_client = MagicMock()
    mock_client.field_mapping = {
        "title": "name",
        "pipeline_stage": "stage_code",
        "pwin_score": "probability",
        "agency": "client_name",
        "solicitation_number": "external_id",
        "estimated_value": "potential_revenue",
        "notes": "description",
    }
    mock_client.map_stage_from_crm.side_effect = lambda s: {
        "04-In Progress": "active",
        "07-Closed Won": "awarded",
    }.get(s, "qualifying")

    with patch(
        "proposal.integrations.unanet_sync.list_proposals",
        return_value=proposals or [],
    ):
        mgr = UnanetSyncManager(
            client=mock_client,
            state_file=state_file,
            conflict_strategy=conflict_strategy,
        )
    return mgr


# ---------------------------------------------------------------------------
# SyncEntry
# ---------------------------------------------------------------------------

class TestSyncEntry:
    def test_to_dict_contains_expected_keys(self):
        entry = SyncEntry(
            proposal_id="P1",
            crm_id="CRM-99",
            last_pushed_at="2026-04-01T00:00:00+00:00",
            last_pulled_at="2026-04-02T00:00:00+00:00",
        )
        d = entry.to_dict()
        assert d["crm_id"] == "CRM-99"
        assert "last_pushed_at" in d
        assert "last_pulled_at" in d
        assert "proposal_id" not in d  # stored as key, not value

    def test_default_values(self):
        entry = SyncEntry(proposal_id="P2")
        assert entry.crm_id == ""
        assert entry.last_pushed_at == ""
        assert entry.last_pulled_at == ""


# ---------------------------------------------------------------------------
# SyncResult
# ---------------------------------------------------------------------------

class TestSyncResult:
    def test_summary_string(self):
        r = SyncResult(
            pushed_created=["P1"],
            pushed_updated=["P2"],
            pulled_updated=["P3"],
            skipped=["P4", "P5"],
            errors=[("P6", "error")],
        )
        s = r.summary()
        assert "created: 1" in s
        assert "updated→CRM: 1" in s
        assert "pulled←CRM: 1" in s
        assert "skipped: 2" in s
        assert "errors: 1" in s

    def test_has_errors_false_when_clean(self):
        assert SyncResult().has_errors is False

    def test_has_errors_true_when_errors_present(self):
        r = SyncResult(errors=[("P1", "boom")])
        assert r.has_errors is True


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestStatePersistence:
    def test_loads_existing_state_file(self, tmp_path):
        state = {"P1": {"crm_id": "CRM-1", "last_pushed_at": "2026-04-01T00:00:00+00:00", "last_pulled_at": ""}}
        mgr = _make_manager(tmp_path, state=state)
        entry = mgr.get_sync_entry("P1")
        assert entry is not None
        assert entry.crm_id == "CRM-1"

    def test_missing_state_file_starts_empty(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_sync_entry("UNKNOWN") is None

    def test_corrupted_state_file_falls_back_to_empty(self, tmp_path):
        state_file = tmp_path / "sync_state.json"
        state_file.write_text("NOT VALID JSON {{{{")
        mock_client = MagicMock()
        mock_client.field_mapping = {}
        with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[]):
            mgr = UnanetSyncManager(client=mock_client, state_file=state_file)
        assert len(mgr._state) == 0

    def test_save_state_creates_directory_if_missing(self, tmp_path):
        nested = tmp_path / "deep" / "path" / "sync.json"
        mock_client = MagicMock()
        mock_client.field_mapping = {}
        with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[]):
            mgr = UnanetSyncManager(client=mock_client, state_file=nested)
        mgr._save_state()
        assert nested.exists()

    def test_reset_all_clears_state(self, tmp_path):
        state = {"P1": {"crm_id": "CRM-1", "last_pushed_at": "", "last_pulled_at": ""}}
        mgr = _make_manager(tmp_path, state=state)
        mgr.reset_sync_state()
        assert mgr.get_sync_entry("P1") is None

    def test_reset_single_proposal(self, tmp_path):
        state = {
            "P1": {"crm_id": "CRM-1", "last_pushed_at": "", "last_pulled_at": ""},
            "P2": {"crm_id": "CRM-2", "last_pushed_at": "", "last_pulled_at": ""},
        }
        mgr = _make_manager(tmp_path, state=state)
        mgr.reset_sync_state("P1")
        assert mgr.get_sync_entry("P1") is None
        assert mgr.get_sync_entry("P2") is not None


# ---------------------------------------------------------------------------
# Push: local → CRM
# ---------------------------------------------------------------------------

class TestPushAll:
    def test_creates_crm_record_for_new_proposal(self, tmp_path):
        proposal = _make_proposal("P1")
        mgr = _make_manager(tmp_path, proposals=[proposal])
        mgr._client.create_opportunity.return_value = "CRM-100"

        with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[proposal]):
            with patch("proposal.integrations.unanet_sync.update_proposal") as mock_update:
                result = mgr.push_all()

        assert "P1" in result.pushed_created
        assert len(result.pushed_updated) == 0
        mgr._client.create_opportunity.assert_called_once()
        mock_update.assert_called_once_with("P1", {"crm_opportunity_id": "CRM-100"}, db_path=mgr._db_path)

    def test_updates_existing_crm_record_when_local_is_newer(self, tmp_path):
        proposal = _make_proposal("P1", updated_at=_iso(-60))
        state = {
            "P1": {
                "crm_id": "CRM-1",
                "last_pushed_at": _iso(-3600),  # 1 hour ago, local is newer
                "last_pulled_at": "",
            }
        }
        mgr = _make_manager(tmp_path, proposals=[proposal], state=state)
        mgr._client.update_opportunity.return_value = True

        with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[proposal]):
            with patch("proposal.integrations.unanet_sync.update_proposal"):
                result = mgr.push_all()

        assert "P1" in result.pushed_updated
        mgr._client.update_opportunity.assert_called_once_with("CRM-1", proposal.model_dump())

    def test_skips_proposal_when_not_modified(self, tmp_path):
        proposal = _make_proposal("P1", updated_at=_iso(-3600))
        state = {
            "P1": {
                "crm_id": "CRM-1",
                "last_pushed_at": _iso(-60),  # 1 minute ago, CRM already has latest
                "last_pulled_at": "",
            }
        }
        mgr = _make_manager(tmp_path, proposals=[proposal], state=state)

        with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[proposal]):
            with patch("proposal.integrations.unanet_sync.update_proposal"):
                result = mgr.push_all()

        assert "P1" in result.skipped
        mgr._client.update_opportunity.assert_not_called()

    def test_records_error_on_api_failure(self, tmp_path):
        proposal = _make_proposal("P1")
        mgr = _make_manager(tmp_path, proposals=[proposal])
        mgr._client.create_opportunity.side_effect = UnanetAPIError(500, "Server Error")

        with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[proposal]):
            with patch("proposal.integrations.unanet_sync.update_proposal"):
                result = mgr.push_all()

        assert len(result.errors) == 1
        assert result.errors[0][0] == "P1"

    def test_push_saves_crm_id_in_sync_state(self, tmp_path):
        proposal = _make_proposal("P1")
        mgr = _make_manager(tmp_path, proposals=[proposal])
        mgr._client.create_opportunity.return_value = "CRM-777"

        with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[proposal]):
            with patch("proposal.integrations.unanet_sync.update_proposal"):
                mgr.push_all()

        entry = mgr.get_sync_entry("P1")
        assert entry is not None
        assert entry.crm_id == "CRM-777"


# ---------------------------------------------------------------------------
# Pull: CRM → local
# ---------------------------------------------------------------------------

class TestPullAll:
    def _crm_record(self, crm_id: str = "CRM-1", stage: str = "04-In Progress") -> dict:
        return {
            "id": crm_id,
            "stage_code": stage,
            "probability": 75.0,
            "description": "Updated via CRM",
            "updated_date": _iso(-30),  # 30s ago
        }

    def test_skips_pull_when_no_crm_linked_proposals(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._client.list_opportunities.return_value = [self._crm_record()]
        result = mgr.pull_all()
        mgr._client.list_opportunities.assert_not_called()
        assert len(result.pulled_updated) == 0

    def test_pulls_crm_updates_for_linked_proposal(self, tmp_path):
        state = {
            "P1": {
                "crm_id": "CRM-1",
                "last_pushed_at": _iso(-3600),
                "last_pulled_at": _iso(-7200),  # 2 hrs ago, CRM record is 30s old
            }
        }
        mgr = _make_manager(tmp_path, state=state)
        mgr._client.list_opportunities.return_value = [self._crm_record("CRM-1")]

        proposal = _make_proposal("P1", updated_at=_iso(-3600))

        with patch("proposal.integrations.unanet_sync.get_proposal", return_value=proposal):
            with patch("proposal.integrations.unanet_sync.update_proposal") as mock_update:
                result = mgr.pull_all()

        assert "P1" in result.pulled_updated
        mock_update.assert_called_once()

    def test_skips_when_crm_record_id_not_in_state(self, tmp_path):
        state = {"P1": {"crm_id": "CRM-1", "last_pushed_at": "", "last_pulled_at": ""}}
        mgr = _make_manager(tmp_path, state=state)
        mgr._client.list_opportunities.return_value = [{"id": "CRM-999", "stage_code": "04-In Progress"}]

        with patch("proposal.integrations.unanet_sync.get_proposal"):
            with patch("proposal.integrations.unanet_sync.update_proposal") as mock_update:
                mgr.pull_all()

        mock_update.assert_not_called()

    def test_handles_list_opportunities_api_error(self, tmp_path):
        state = {"P1": {"crm_id": "CRM-1", "last_pushed_at": "", "last_pulled_at": ""}}
        mgr = _make_manager(tmp_path, state=state)
        mgr._client.list_opportunities.side_effect = UnanetAPIError(503, "Service Unavailable")

        result = mgr.pull_all()
        assert result.has_errors
        assert result.errors[0][0] == "list_opportunities"

    def test_skips_missing_local_proposal(self, tmp_path):
        state = {"P1": {"crm_id": "CRM-1", "last_pushed_at": "", "last_pulled_at": ""}}
        mgr = _make_manager(tmp_path, state=state)
        mgr._client.list_opportunities.return_value = [self._crm_record("CRM-1")]

        with patch("proposal.integrations.unanet_sync.get_proposal", return_value=None):
            with patch("proposal.integrations.unanet_sync.update_proposal") as mock_update:
                mgr.pull_all()

        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# CRM field extraction
# ---------------------------------------------------------------------------

class TestExtractCRMUpdates:
    def _mgr(self, tmp_path: Path) -> UnanetSyncManager:
        return _make_manager(tmp_path)

    def test_pwin_scaled_from_100_to_decimal(self, tmp_path):
        mgr = self._mgr(tmp_path)
        crm_record = {"probability": 80.0}
        updates = mgr._extract_crm_updates(crm_record)
        assert abs(updates.get("pwin_score", 0) - 0.8) < 0.001

    def test_stage_reverse_mapped(self, tmp_path):
        mgr = self._mgr(tmp_path)
        crm_record = {"stage_code": "04-In Progress"}
        updates = mgr._extract_crm_updates(crm_record)
        assert updates.get("pipeline_stage") == "active"

    def test_unmapped_crm_fields_ignored(self, tmp_path):
        mgr = self._mgr(tmp_path)
        crm_record = {"some_unknown_field": "value", "internal_notes": "private"}
        updates = mgr._extract_crm_updates(crm_record)
        assert len(updates) == 0

    def test_local_only_fields_not_overwritten(self, tmp_path):
        mgr = self._mgr(tmp_path)
        # Manually add a local-only field to the reverse map to test protection
        mgr._client.field_mapping["id"] = "crm_internal_id"
        crm_record = {"crm_internal_id": "SOME-VALUE"}
        updates = mgr._extract_crm_updates(crm_record)
        assert "id" not in updates

    def test_none_values_excluded(self, tmp_path):
        mgr = self._mgr(tmp_path)
        crm_record = {"description": None}
        updates = mgr._extract_crm_updates(crm_record)
        assert "notes" not in updates


# ---------------------------------------------------------------------------
# Conflict strategies
# ---------------------------------------------------------------------------

class TestConflictStrategy:
    def test_invalid_strategy_raises(self, tmp_path):
        mock_client = MagicMock()
        mock_client.field_mapping = {}
        with pytest.raises(ValueError, match="conflict_strategy"):
            with patch("proposal.integrations.unanet_sync.list_proposals", return_value=[]):
                UnanetSyncManager(
                    client=mock_client,
                    state_file=tmp_path / "s.json",
                    conflict_strategy="invalid_mode",
                )

    def test_prefer_newer_pulls_when_crm_is_newer(self, tmp_path):
        mgr = _make_manager(tmp_path, conflict_strategy="prefer_newer")
        crm_record = {"updated_date": _iso(-30)}  # CRM 30s ago
        local_updated_at = _iso(-3600)  # local 1 hr ago — CRM is newer
        assert mgr._needs_pull(crm_record, _iso(-7200), local_updated_at) is True

    def test_prefer_newer_skips_when_local_is_newer(self, tmp_path):
        mgr = _make_manager(tmp_path, conflict_strategy="prefer_newer")
        crm_record = {"updated_date": _iso(-3600)}  # CRM 1 hr ago
        local_updated_at = _iso(-30)  # local 30s ago — local is newer
        assert mgr._needs_pull(crm_record, _iso(-7200), local_updated_at) is False

    def test_prefer_crm_pulls_even_when_local_is_newer(self, tmp_path):
        mgr = _make_manager(tmp_path, conflict_strategy="prefer_crm")
        crm_record = {"updated_date": _iso(-30)}  # CRM 30s ago
        last_pulled_at = _iso(-7200)  # last pull was 2 hrs ago
        local_updated_at = _iso(-10)  # local very recent
        # prefer_crm still pulls if CRM timestamp > last_pulled_at
        assert mgr._needs_pull(crm_record, last_pulled_at, local_updated_at) is True


# ---------------------------------------------------------------------------
# Full bidirectional sync
# ---------------------------------------------------------------------------

class TestBidirectionalSync:
    def test_sync_calls_push_then_pull(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.push_all = MagicMock(return_value=SyncResult(pushed_created=["P1"]))
        mgr.pull_all = MagicMock(return_value=SyncResult(pulled_updated=["P2"]))

        result = mgr.sync()

        mgr.push_all.assert_called_once()
        mgr.pull_all.assert_called_once()
        # pull receives the partial result from push
        pull_call_arg = mgr.pull_all.call_args[0][0]
        assert "P1" in pull_call_arg.pushed_created

    def test_sync_returns_combined_result(self, tmp_path):
        mgr = _make_manager(tmp_path)
        push_result = SyncResult(pushed_created=["P1"])
        pull_result = SyncResult(pushed_created=["P1"], pulled_updated=["P2"])
        mgr.push_all = MagicMock(return_value=push_result)
        mgr.pull_all = MagicMock(return_value=pull_result)

        result = mgr.sync()
        assert "P2" in result.pulled_updated
