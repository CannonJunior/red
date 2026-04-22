"""
Tests for OpportunitiesManager.get_pipeline_stats()

Uses an in-memory SQLite DB so no files are touched.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from opportunities_api import OpportunitiesManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mgr(tmp_path):
    """OpportunitiesManager backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_opps.db")
    m = OpportunitiesManager(db_path=db_path)
    return m


def _insert(mgr, pipeline_stage: str, value: float, priority: str = "medium"):
    """Insert a bare opportunity row directly (bypasses knowledge graph)."""
    conn = sqlite3.connect(mgr.db_path)
    conn.row_factory = sqlite3.Row
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO opportunities
        (id, name, description, status, priority, value, tags, metadata,
         pipeline_stage, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), f"Opp-{pipeline_stage}", "", pipeline_stage,
          priority, value, "[]", "{}", pipeline_stage, now, now))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Empty database
# ---------------------------------------------------------------------------

class TestPipelineStatsEmpty:
    def test_returns_success_on_empty_db(self, mgr):
        result = mgr.get_pipeline_stats()
        assert result['status'] == 'success'

    def test_total_is_zero(self, mgr):
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['total'] == 0

    def test_win_rate_is_none_with_no_closed_opps(self, mgr):
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['win_rate'] is None

    def test_values_are_zero(self, mgr):
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['total_value'] == 0.0
        assert stats['active_value'] == 0.0
        assert stats['won_value'] == 0.0


# ---------------------------------------------------------------------------
# Win rate
# ---------------------------------------------------------------------------

class TestWinRate:
    def test_perfect_win_rate(self, mgr):
        _insert(mgr, 'awarded', 1_000_000)
        _insert(mgr, 'awarded', 500_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['win_rate'] == 1.0

    def test_zero_win_rate(self, mgr):
        _insert(mgr, 'lost', 200_000)
        _insert(mgr, 'no_bid', 100_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['win_rate'] == 0.0

    def test_fifty_percent_win_rate(self, mgr):
        _insert(mgr, 'awarded', 1_000_000)
        _insert(mgr, 'lost', 500_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert abs(stats['win_rate'] - 0.5) < 0.001

    def test_win_rate_excludes_open_stages(self, mgr):
        """Open opportunities should not affect the win rate denominator."""
        _insert(mgr, 'awarded', 1_000_000)
        _insert(mgr, 'lost', 1_000_000)
        _insert(mgr, 'active', 500_000)  # open — not counted
        stats = mgr.get_pipeline_stats()['stats']
        assert abs(stats['win_rate'] - 0.5) < 0.001

    def test_no_bid_counts_as_loss(self, mgr):
        _insert(mgr, 'awarded', 1_000_000)
        _insert(mgr, 'no_bid', 1_000_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert abs(stats['win_rate'] - 0.5) < 0.001

    def test_cancelled_counts_as_loss(self, mgr):
        _insert(mgr, 'awarded', 1_000_000)
        _insert(mgr, 'cancelled', 1_000_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert abs(stats['win_rate'] - 0.5) < 0.001

    def test_contract_vehicle_won_is_a_win(self, mgr):
        _insert(mgr, 'contract_vehicle_won', 2_000_000)
        _insert(mgr, 'lost', 1_000_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert abs(stats['win_rate'] - 0.5) < 0.001


# ---------------------------------------------------------------------------
# Value aggregation
# ---------------------------------------------------------------------------

class TestValueAggregation:
    def test_total_value_sums_all(self, mgr):
        _insert(mgr, 'active', 1_000_000)
        _insert(mgr, 'awarded', 2_000_000)
        _insert(mgr, 'lost', 500_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['total_value'] == 3_500_000.0

    def test_active_value_only_open_stages(self, mgr):
        _insert(mgr, 'active', 1_000_000)
        _insert(mgr, 'submitted', 500_000)
        _insert(mgr, 'awarded', 2_000_000)  # closed — not in active
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['active_value'] == 1_500_000.0

    def test_won_value_includes_all_won_stages(self, mgr):
        _insert(mgr, 'awarded', 1_000_000)
        _insert(mgr, 'contract_vehicle_won', 500_000)
        _insert(mgr, 'contract_vehicle_complete', 250_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['won_value'] == 1_750_000.0

    def test_zero_value_ops_dont_break_anything(self, mgr):
        _insert(mgr, 'active', 0.0)
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['total_value'] == 0.0


# ---------------------------------------------------------------------------
# Stage counts
# ---------------------------------------------------------------------------

class TestStageCounts:
    def test_by_stage_count(self, mgr):
        _insert(mgr, 'active', 100)
        _insert(mgr, 'active', 200)
        _insert(mgr, 'awarded', 300)
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['by_stage']['active']['count'] == 2
        assert stats['by_stage']['awarded']['count'] == 1

    def test_by_stage_value(self, mgr):
        _insert(mgr, 'submitted', 1_000_000)
        _insert(mgr, 'submitted', 500_000)
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['by_stage']['submitted']['value'] == 1_500_000.0

    def test_active_count_field(self, mgr):
        for stage in ('identified', 'qualifying', 'active', 'submitted'):
            _insert(mgr, stage, 100)
        _insert(mgr, 'awarded', 100)  # closed — not active
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['active_count'] == 4


# ---------------------------------------------------------------------------
# Priority breakdown
# ---------------------------------------------------------------------------

class TestPriorityBreakdown:
    def test_priority_counts(self, mgr):
        _insert(mgr, 'active', 100, priority='high')
        _insert(mgr, 'active', 100, priority='high')
        _insert(mgr, 'active', 100, priority='medium')
        stats = mgr.get_pipeline_stats()['stats']
        assert stats['by_priority']['high'] == 2
        assert stats['by_priority']['medium'] == 1

    def test_missing_priority_absent_from_dict(self, mgr):
        _insert(mgr, 'active', 100, priority='high')
        stats = mgr.get_pipeline_stats()['stats']
        assert 'low' not in stats['by_priority']


# ---------------------------------------------------------------------------
# Handler function
# ---------------------------------------------------------------------------

class TestHandlePipelineStatsRequest:
    def test_handler_returns_success(self, mgr):
        with patch('opportunities_handlers._opportunities_manager', mgr):
            from opportunities_handlers import handle_pipeline_stats_request
            result = handle_pipeline_stats_request()
        assert result['status'] == 'success'
        assert 'stats' in result
