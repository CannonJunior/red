"""Unit tests for capture_api.py — Shipley Capture Intelligence data layer.

Tests cover all CRUD operations for:
  - Customer contacts
  - Competitor intel
  - Engagement activities
  - Win strategy (upsert, one per opportunity)
  - PTW analysis (upsert, one per opportunity)
"""

import os
import sys
import pytest

# Point to repo root so capture_api is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import capture_api
from capture_api import CaptureManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def disable_pool(monkeypatch):
    """Force plain connections so tests run against a clean temp DB.

    db_pool enables PRAGMA foreign_keys=ON which would reject INSERTs into
    tables that have FK references to the `opportunities` table (which is
    created by the main app, not by CaptureManager itself).
    """
    monkeypatch.setattr(capture_api, '_USE_POOL', False)


@pytest.fixture
def mgr(tmp_path):
    """Return a fresh CaptureManager backed by a temp DB for each test."""
    db_path = str(tmp_path / "test_capture.db")
    return CaptureManager(db_path=db_path)


OPP_ID = "opp-001"


# ---------------------------------------------------------------------------
# Customer Contacts
# ---------------------------------------------------------------------------

class TestContacts:
    def test_list_empty(self, mgr):
        """list_contacts returns empty list when no contacts exist."""
        result = mgr.list_contacts(OPP_ID)
        assert result['status'] == 'success'
        assert result['contacts'] == []

    def test_create_and_list(self, mgr):
        """Creating a contact then listing returns it."""
        data = {
            'name': 'Jane Smith',
            'title': 'Program Manager',
            'role': 'decision_maker',
            'relationship_strength': 4,
            'hot_buttons': ['cost', 'schedule'],
        }
        cr = mgr.create_contact(OPP_ID, data)
        assert cr['status'] == 'success'
        cid = cr['contact']['id']

        result = mgr.list_contacts(OPP_ID)
        assert len(result['contacts']) == 1
        assert result['contacts'][0]['id'] == cid
        assert result['contacts'][0]['name'] == 'Jane Smith'

    def test_update_contact(self, mgr):
        """update_contact changes stored fields."""
        cr = mgr.create_contact(OPP_ID, {'name': 'Bob', 'role': 'technical_evaluator'})
        cid = cr['contact']['id']

        ur = mgr.update_contact(cid, {'relationship_strength': 5, 'notes': 'Met at AFCEA'})
        assert ur['status'] == 'success'
        assert ur['contact']['relationship_strength'] == 5
        assert ur['contact']['notes'] == 'Met at AFCEA'

    def test_delete_contact(self, mgr):
        """Deleting a contact removes it from list."""
        cr = mgr.create_contact(OPP_ID, {'name': 'Alice'})
        cid = cr['contact']['id']

        dr = mgr.delete_contact(cid)
        assert dr['status'] == 'success'
        assert mgr.list_contacts(OPP_ID)['contacts'] == []

    def test_create_defaults_unknown_name(self, mgr):
        """create_contact with no name defaults to 'Unknown'."""
        cr = mgr.create_contact(OPP_ID, {'role': 'ko'})
        assert cr['status'] == 'success'
        assert cr['contact']['name'] == 'Unknown'

    def test_delete_nonexistent_contact_succeeds(self, mgr):
        """SQLite DELETE on missing row is idempotent — returns success."""
        # SQLite DELETE WHERE id=? on nonexistent row does not error
        dr = mgr.delete_contact('nonexistent-id-999')
        assert dr['status'] == 'success'


# ---------------------------------------------------------------------------
# Competitor Intel
# ---------------------------------------------------------------------------

class TestCompetitors:
    def test_list_empty(self, mgr):
        result = mgr.list_competitors(OPP_ID)
        assert result['status'] == 'success'
        assert result['competitors'] == []

    def test_create_and_list(self, mgr):
        data = {
            'company_name': 'ACME Corp',
            'is_incumbent': True,
            'likely_bid': 'Likely',
            'strengths': ['past performance', 'low overhead'],
            'weaknesses': ['legacy systems'],
        }
        cr = mgr.create_competitor(OPP_ID, data)
        assert cr['status'] == 'success'
        assert cr['competitor']['company_name'] == 'ACME Corp'
        assert cr['competitor']['is_incumbent'] is True

    def test_update_competitor(self, mgr):
        cr = mgr.create_competitor(OPP_ID, {'company_name': 'Rival Inc'})
        cid = cr['competitor']['id']
        ur = mgr.update_competitor(cid, {'likely_bid': 'Unlikely', 'weaknesses': ['dated toolchain']})
        assert ur['status'] == 'success'
        assert ur['competitor']['likely_bid'] == 'Unlikely'

    def test_delete_competitor(self, mgr):
        cr = mgr.create_competitor(OPP_ID, {'company_name': 'Gone Corp'})
        cid = cr['competitor']['id']
        mgr.delete_competitor(cid)
        assert mgr.list_competitors(OPP_ID)['competitors'] == []

    def test_multiple_competitors_scoped_to_opportunity(self, mgr):
        """Competitors for one opportunity don't bleed into another."""
        mgr.create_competitor(OPP_ID, {'company_name': 'Alpha'})
        result_other = mgr.list_competitors('opp-999')
        assert result_other['competitors'] == []


# ---------------------------------------------------------------------------
# Engagement Activities
# ---------------------------------------------------------------------------

class TestActivities:
    def test_list_empty(self, mgr):
        result = mgr.list_activities(OPP_ID)
        assert result['status'] == 'success'
        assert result['activities'] == []

    def test_create_activity(self, mgr):
        data = {
            'activity_type': 'Meeting',
            'activity_date': '2026-03-15',
            'topics_covered': 'Kickoff discussion',
            'customer_attendees': ['Jane Smith'],
            'our_attendees': ['Bob Jones'],
            'intelligence_gathered': 'Customer wants LPTA evaluation.',
        }
        cr = mgr.create_activity(OPP_ID, data)
        assert cr['status'] == 'success'
        assert cr['activity']['activity_type'] == 'Meeting'
        assert cr['activity']['activity_date'] == '2026-03-15'

    def test_delete_activity(self, mgr):
        cr = mgr.create_activity(OPP_ID, {'activity_type': 'Call', 'topics_covered': 'Quick check-in'})
        aid = cr['activity']['id']
        dr = mgr.delete_activity(aid)
        assert dr['status'] == 'success'
        assert mgr.list_activities(OPP_ID)['activities'] == []

    def test_activities_ordered_by_date_desc(self, mgr):
        """Activities are returned newest-first."""
        mgr.create_activity(OPP_ID, {
            'activity_type': 'Email', 'activity_date': '2026-01-01',
            'topics_covered': 'First contact',
        })
        mgr.create_activity(OPP_ID, {
            'activity_type': 'Meeting', 'activity_date': '2026-03-01',
            'intelligence_gathered': 'Later intel',
        })
        activities = mgr.list_activities(OPP_ID)['activities']
        assert activities[0]['activity_date'] == '2026-03-01'
        assert activities[1]['activity_date'] == '2026-01-01'


# ---------------------------------------------------------------------------
# Win Strategy
# ---------------------------------------------------------------------------

class TestWinStrategy:
    def test_get_returns_defaults_when_no_row(self, mgr):
        """get_win_strategy returns a default dict (not 404) for new opportunity."""
        result = mgr.get_win_strategy(OPP_ID)
        assert result['status'] == 'success'
        ws = result['win_strategy']
        assert ws['opportunity_id'] == OPP_ID
        assert isinstance(ws['win_themes'], list)
        assert isinstance(ws['pwin_score'], (int, float))

    def test_upsert_creates_and_retrieves(self, mgr):
        data = {
            'pwin_score': 65,
            'win_themes': ['proven past performance', 'best-in-class team'],
            'discriminators': ['proprietary toolchain'],
            'customer_hot_buttons_summary': 'Customer wants on-time delivery above all.',
        }
        ur = mgr.upsert_win_strategy(OPP_ID, data)
        assert ur['status'] == 'success'

        gr = mgr.get_win_strategy(OPP_ID)
        ws = gr['win_strategy']
        assert ws['pwin_score'] == 65.0
        assert 'proven past performance' in ws['win_themes']
        assert ws['customer_hot_buttons_summary'] == 'Customer wants on-time delivery above all.'

    def test_upsert_is_idempotent(self, mgr):
        """Second upsert with same opportunity_id updates, does not duplicate."""
        mgr.upsert_win_strategy(OPP_ID, {'pwin_score': 40})
        mgr.upsert_win_strategy(OPP_ID, {'pwin_score': 75})
        ws = mgr.get_win_strategy(OPP_ID)['win_strategy']
        assert ws['pwin_score'] == 75.0

    def test_gate_completion_roundtrip(self, mgr):
        """Gate completion flags are persisted correctly."""
        gates = {'gate_0_complete': True, 'gate_1_complete': False, 'gate_2_complete': True}
        mgr.upsert_win_strategy(OPP_ID, gates)
        ws = mgr.get_win_strategy(OPP_ID)['win_strategy']
        assert ws['gate_0_complete'] is True
        assert ws['gate_1_complete'] is False
        assert ws['gate_2_complete'] is True


# ---------------------------------------------------------------------------
# Price-to-Win (PTW)
# ---------------------------------------------------------------------------

class TestPTW:
    def test_get_returns_defaults_when_no_row(self, mgr):
        result = mgr.get_ptw(OPP_ID)
        assert result['status'] == 'success'
        ptw = result['ptw']
        assert ptw['opportunity_id'] == OPP_ID
        assert 'ptw_target' in ptw
        assert ptw['ptw_target'] is None

    def test_upsert_and_retrieve(self, mgr):
        data = {
            'ptw_target': 4_500_000.0,
            'our_estimated_cost': 4_200_000.0,
            'fee_percent': 0.08,
            'unanet_project_id': 'UNA-2026-042',
        }
        ur = mgr.upsert_ptw(OPP_ID, data)
        assert ur['status'] == 'success'

        ptw = mgr.get_ptw(OPP_ID)['ptw']
        assert ptw['ptw_target'] == 4_500_000.0
        assert ptw['unanet_project_id'] == 'UNA-2026-042'
        # our_price computed: 4_200_000 * 1.08 = 4_536_000
        assert abs(ptw['our_price'] - 4_536_000.0) < 0.01
        # cost_gap: 4_500_000 - 4_536_000 = -36_000 (over budget)
        assert abs(ptw['cost_gap'] - (-36_000.0)) < 0.01

    def test_upsert_is_idempotent(self, mgr):
        ur1 = mgr.upsert_ptw(OPP_ID, {'ptw_target': 1_000_000.0})
        assert ur1['status'] == 'success'
        ur2 = mgr.upsert_ptw(OPP_ID, {'ptw_target': 2_000_000.0})
        assert ur2['status'] == 'success'
        ptw = mgr.get_ptw(OPP_ID)['ptw']
        assert ptw['ptw_target'] == 2_000_000.0

    def test_computed_fields_not_stored(self, mgr):
        """our_price and cost_gap are derived — updating cost recalculates them."""
        mgr.upsert_ptw(OPP_ID, {
            'ptw_target': 1_000_000.0, 'our_estimated_cost': 900_000.0, 'fee_percent': 0.10,
        })
        ptw1 = mgr.get_ptw(OPP_ID)['ptw']
        assert abs(ptw1['our_price'] - 990_000.0) < 0.01

        mgr.upsert_ptw(OPP_ID, {'our_estimated_cost': 800_000.0})
        ptw2 = mgr.get_ptw(OPP_ID)['ptw']
        # fee_percent retained from first upsert (0.10)
        assert abs(ptw2['our_price'] - 880_000.0) < 0.01
