"""
Tests for proposal/integrations/unanet.py

All HTTP calls are mocked — no live Unanet instance required.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from proposal.integrations.unanet import (
    UnanetAPIError,
    UnanetAuthError,
    UnanetClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_body=None, text: str = "") -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = (200 <= status_code < 300)
    resp.text = text or json.dumps(json_body or {})
    resp.json.return_value = json_body if json_body is not None else {}
    return resp


MAPPING_FILE = Path(__file__).parents[3] / "proposal" / "integrations" / "unanet_mapping.json"


@pytest.fixture()
def client():
    """UnanetClient with test credentials; mapping file read from real JSON."""
    with patch("proposal.integrations.unanet.requests.Session") as MockSession:
        mock_session = MagicMock()
        MockSession.return_value = mock_session
        c = UnanetClient(
            base_url="https://test.unanet.biz",
            api_key="test-key-abc",
            mapping_file=MAPPING_FILE,
        )
        c._session = mock_session
        return c


# ---------------------------------------------------------------------------
# Construction & configuration
# ---------------------------------------------------------------------------

class TestUnanetClientInit:
    def test_raises_without_base_url(self):
        """Missing base_url should raise ValueError."""
        with pytest.raises(ValueError, match="UNANET_BASE_URL"):
            UnanetClient(base_url="", api_key="k", mapping_file=MAPPING_FILE)

    def test_raises_without_api_key(self):
        """Missing api_key should raise ValueError."""
        with pytest.raises(ValueError, match="UNANET_API_KEY"):
            UnanetClient(base_url="https://test.unanet.biz", api_key="", mapping_file=MAPPING_FILE)

    def test_loads_field_mapping_from_json(self, client):
        """Field mapping should be loaded from unanet_mapping.json."""
        assert "title" in client.field_mapping
        assert client.field_mapping["title"] == "name"

    def test_loads_stage_map_from_json(self, client):
        """Stage mapping should be loaded from unanet_mapping.json."""
        assert "identified" in client._stage_map
        assert client._stage_map["identified"] == "01-Qualification"

    def test_loads_reverse_stage_map_from_json(self, client):
        """Reverse stage mapping should be loaded from unanet_mapping.json."""
        assert "04-In Progress" in client._reverse_stage_map
        assert client._reverse_stage_map["04-In Progress"] == "active"

    def test_missing_mapping_file_falls_back_to_defaults(self, tmp_path):
        """When mapping file is absent, default mapping is used without error."""
        with patch("proposal.integrations.unanet.requests.Session"):
            c = UnanetClient(
                base_url="https://x.biz",
                api_key="k",
                mapping_file=tmp_path / "nonexistent.json",
            )
        assert "title" in c.field_mapping


# ---------------------------------------------------------------------------
# Stage mapping
# ---------------------------------------------------------------------------

class TestStageMapping:
    def test_local_to_crm_via_json_map(self, client):
        assert client._map_stage("active") == "04-In Progress"

    def test_local_to_crm_fallback_when_not_in_json(self, client):
        """Stages absent from JSON map should fall back to hardcoded mapping."""
        client._stage_map = {}
        assert client._map_stage("awarded") == "07-Closed Won"

    def test_unknown_stage_passthrough(self, client):
        """Unmapped stage values should be returned unchanged."""
        client._stage_map = {}
        assert client._map_stage("weird_stage") == "weird_stage"

    def test_crm_to_local_via_reverse_json(self, client):
        assert client.map_stage_from_crm("07-Closed Won") == "awarded"

    def test_crm_to_local_fallback_when_reverse_map_empty(self, client):
        client._reverse_stage_map = {}
        assert client.map_stage_from_crm("09-Closed No Bid") == "no_bid"

    def test_unknown_crm_stage_defaults_to_qualifying(self, client):
        client._reverse_stage_map = {}
        assert client.map_stage_from_crm("99-Mystery") == "qualifying"

    def test_all_local_stages_have_crm_mapping(self, client):
        """Every local stage used by the Kanban board should map to a CRM code."""
        stages = [
            "identified", "qualifying", "long_lead", "bid_decision", "active",
            "submitted", "negotiating", "awarded", "lost", "no_bid", "cancelled",
            "contract_vehicle_won", "contract_vehicle_complete",
        ]
        for stage in stages:
            result = client._map_stage(stage)
            assert result != stage or stage in client._stage_map, \
                f"Stage '{stage}' not mapped to a CRM code"


# ---------------------------------------------------------------------------
# Proposal → CRM field mapping
# ---------------------------------------------------------------------------

class TestProposalToCRMMapping:
    def test_title_maps_to_name(self, client):
        payload = client._map_proposal_to_crm({"title": "DARPA Widget"})
        assert payload["name"] == "DARPA Widget"

    def test_pwin_scaled_to_100(self, client):
        """pwin_score 0.0–1.0 locally should be sent as 0–100 to Unanet."""
        payload = client._map_proposal_to_crm({"pwin_score": 0.65})
        assert abs(payload["probability"] - 65.0) < 0.001

    def test_pipeline_stage_converted_to_crm_code(self, client):
        payload = client._map_proposal_to_crm({"pipeline_stage": "submitted"})
        assert payload["stage_code"] == "05-Waiting/Review"

    def test_none_values_excluded(self, client):
        """Fields with None values should not appear in the CRM payload."""
        payload = client._map_proposal_to_crm({"title": "Test", "estimated_value": None})
        assert "potential_revenue" not in payload

    def test_agency_maps_to_client_name(self, client):
        payload = client._map_proposal_to_crm({"agency": "AFRL"})
        assert payload["client_name"] == "AFRL"

    def test_full_proposal_mapping(self, client):
        proposal = {
            "solicitation_number": "FA8612-26-R-0001",
            "title": "Widget System",
            "pipeline_stage": "active",
            "estimated_value": 5_000_000,
            "pwin_score": 0.40,
        }
        payload = client._map_proposal_to_crm(proposal)
        assert payload["external_id"] == "FA8612-26-R-0001"
        assert payload["name"] == "Widget System"
        assert payload["stage_code"] == "04-In Progress"
        assert payload["potential_revenue"] == 5_000_000
        assert abs(payload["probability"] - 40.0) < 0.001


# ---------------------------------------------------------------------------
# API methods — happy path
# ---------------------------------------------------------------------------

class TestUnanetClientAPI:
    def test_create_opportunity_returns_id(self, client):
        client._session.post.return_value = _mock_response(
            201, {"id": "CRM-999"}
        )
        crm_id = client.create_opportunity({"title": "New Opp", "pipeline_stage": "identified"})
        assert crm_id == "CRM-999"
        client._session.post.assert_called_once()

    def test_create_opportunity_uses_opportunityId_key(self, client):
        """Some Unanet versions return opportunityId instead of id."""
        client._session.post.return_value = _mock_response(
            201, {"opportunityId": "OPP-42"}
        )
        crm_id = client.create_opportunity({"title": "Alt Opp"})
        assert crm_id == "OPP-42"

    def test_update_opportunity_returns_true(self, client):
        client._session.put.return_value = _mock_response(200, {})
        result = client.update_opportunity("CRM-999", {"pipeline_stage": "awarded"})
        assert result is True
        client._session.put.assert_called_once()

    def test_get_opportunity_returns_dict(self, client):
        expected = {"id": "CRM-1", "name": "Widget"}
        client._session.get.return_value = _mock_response(200, expected)
        result = client.get_opportunity("CRM-1")
        assert result == expected

    def test_get_opportunity_returns_none_on_404(self, client):
        client._session.get.return_value = _mock_response(404)
        result = client.get_opportunity("MISSING")
        assert result is None

    def test_list_opportunities_returns_list(self, client):
        items = [{"id": "A"}, {"id": "B"}]
        client._session.get.return_value = _mock_response(200, items)
        result = client.list_opportunities()
        assert result == items

    def test_list_opportunities_unwraps_items_key(self, client):
        """Unanet may return {"items": [...]} wrapper."""
        items = [{"id": "X"}]
        client._session.get.return_value = _mock_response(200, {"items": items})
        result = client.list_opportunities()
        assert result == items

    def test_list_opportunities_with_stage_filter(self, client):
        client._session.get.return_value = _mock_response(200, [])
        client.list_opportunities(stage_filter="04-In Progress")
        call_kwargs = client._session.get.call_args
        assert call_kwargs.kwargs["params"]["stage"] == "04-In Progress"

    def test_log_activity_returns_true(self, client):
        client._session.post.return_value = _mock_response(200, {})
        result = client.log_activity("CRM-1", "NOTE", "Kickoff call held", "2026-04-01")
        assert result is True
        payload = client._session.post.call_args.kwargs["json"]
        assert payload["type"] == "NOTE"
        assert payload["description"] == "Kickoff call held"
        assert payload["date"] == "2026-04-01"

    def test_log_activity_defaults_to_today(self, client):
        from datetime import date
        client._session.post.return_value = _mock_response(200, {})
        client.log_activity("CRM-1", "CALL", "Check-in")
        payload = client._session.post.call_args.kwargs["json"]
        assert payload["date"] == date.today().isoformat()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestUnanetClientErrors:
    def test_api_error_raised_on_non_2xx(self, client):
        client._session.get.return_value = _mock_response(
            500, {"message": "Internal Server Error"}
        )
        with pytest.raises(UnanetAPIError) as exc_info:
            client.get_opportunity("CRM-1")
        assert exc_info.value.status_code == 500

    def test_api_error_message_extracted_from_json(self, client):
        client._session.get.return_value = _mock_response(
            403, {"message": "Forbidden — insufficient permissions"}
        )
        with pytest.raises(UnanetAPIError, match="Forbidden"):
            client.get_opportunity("CRM-1")

    def test_api_error_falls_back_to_text(self, client):
        resp = _mock_response(400, text="Bad Request")
        resp.json.side_effect = ValueError("not json")
        client._session.get.return_value = resp
        with pytest.raises(UnanetAPIError, match="400"):
            client.get_opportunity("CRM-1")

    def test_test_connection_raises_auth_error_on_401(self, client):
        client._session.get.return_value = _mock_response(401)
        with pytest.raises(UnanetAuthError):
            client.test_connection()

    def test_test_connection_returns_false_on_connection_error(self, client):
        client._session.get.side_effect = requests.ConnectionError("refused")
        result = client.test_connection()
        assert result is False

    def test_test_connection_returns_true_on_200(self, client):
        client._session.get.return_value = _mock_response(200, [])
        result = client.test_connection()
        assert result is True
