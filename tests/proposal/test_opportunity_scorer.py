"""
Tests for proposal/opportunity_scorer.py

Covers:
    - Expected use: scoring a well-specified opportunity
    - Edge cases: missing fields, neutral scores, batch sorting
    - Failure cases: disqualifying set-asides, expired deadlines
"""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from proposal.opportunity_scorer import (
    OpportunityInput,
    ScoreBreakdown,
    ScoringResult,
    _load_capability_keywords,
    _load_company_naics,
    _load_company_set_asides,
    _score_competitive,
    _score_naics,
    _score_past_performance,
    _score_strategic,
    _thresholds,
    result_to_dict,
    score_opportunities_batch,
    score_opportunity,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_env(monkeypatch):
    """Remove scoring-related env vars so tests are deterministic."""
    for key in (
        "COMPANY_NAICS_CODES", "COMPANY_CAPABILITY_KEYWORDS",
        "COMPANY_SET_ASIDES", "BID_THRESHOLD", "MONITOR_THRESHOLD",
        "COMPANY_SIZE",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def it_opp():
    """Typical IT services opportunity — well-specified."""
    return OpportunityInput(
        title="IT Infrastructure Support Services",
        agency="Department of Defense",
        naics_code="541512",
        set_aside_type="small_business",
        estimated_value=5_000_000.0,
        source="SAM.gov",
        description="Python cloud infrastructure DevSecOps support",
        solicitation_number="W91CRB-25-R-0001",
        proposal_due_date=(datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
        has_customer_relationship=True,
        is_we_incumbent=False,
        relevant_past_performance_count=3,
    )


# ---------------------------------------------------------------------------
# _load_company_naics
# ---------------------------------------------------------------------------

class TestLoadCompanyNaics:
    def test_parses_comma_separated(self, monkeypatch):
        monkeypatch.setenv("COMPANY_NAICS_CODES", "541512, 541519, 518210")
        result = _load_company_naics()
        assert result == ["541512", "541519", "518210"]

    def test_empty_env_returns_empty_list(self, clean_env):
        assert _load_company_naics() == []

    def test_single_code(self, monkeypatch):
        monkeypatch.setenv("COMPANY_NAICS_CODES", "541512")
        assert _load_company_naics() == ["541512"]


# ---------------------------------------------------------------------------
# _thresholds
# ---------------------------------------------------------------------------

class TestThresholds:
    def test_defaults(self, clean_env):
        bid, monitor = _thresholds()
        assert bid == 70
        assert monitor == 50

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("BID_THRESHOLD", "75")
        monkeypatch.setenv("MONITOR_THRESHOLD", "55")
        bid, monitor = _thresholds()
        assert bid == 75
        assert monitor == 55


# ---------------------------------------------------------------------------
# _score_naics
# ---------------------------------------------------------------------------

class TestScoreNaics:
    def test_exact_match_full_points(self):
        opp = OpportunityInput(title="Test", naics_code="541512")
        pts, _ = _score_naics(opp, ["541512", "518210"])
        assert pts == 30.0

    def test_subsector_match(self):
        opp = OpportunityInput(title="Test", naics_code="541519")  # 5415xx
        pts, notes = _score_naics(opp, ["541512"])
        assert pts == 20.0
        assert "Subsector" in notes

    def test_industry_group_match(self):
        # 5419xx shares 3-digit subsector prefix (541) with 541512 but not 4-digit
        opp = OpportunityInput(title="Test", naics_code="541990")
        pts, notes = _score_naics(opp, ["541512"])
        assert pts == 12.0
        assert "Industry group" in notes

    def test_sector_match_only(self):
        opp = OpportunityInput(title="Test", naics_code="549999")  # 54xxxx
        pts, notes = _score_naics(opp, ["541512"])
        assert pts == 6.0
        assert "Sector-level" in notes

    def test_no_match(self):
        opp = OpportunityInput(title="Test", naics_code="236110")  # Construction
        pts, _ = _score_naics(opp, ["541512"])
        assert pts == 0.0

    def test_missing_opp_naics_neutral(self):
        opp = OpportunityInput(title="Test", naics_code="")
        pts, notes = _score_naics(opp, ["541512"])
        assert pts == 15.0
        assert "neutral" in notes.lower()

    def test_missing_company_naics_neutral(self):
        opp = OpportunityInput(title="Test", naics_code="541512")
        pts, notes = _score_naics(opp, [])
        assert pts == 15.0
        assert "not configured" in notes.lower()


# ---------------------------------------------------------------------------
# _score_competitive
# ---------------------------------------------------------------------------

class TestScoreCompetitive:
    def test_full_and_open_partial_score(self):
        opp = OpportunityInput(title="T", set_aside_type="full_and_open")
        pts, _ = _score_competitive(opp, [], [])
        assert pts == 8.0

    def test_sdvosb_qualified_full_points(self):
        opp = OpportunityInput(title="T", set_aside_type="sdvosb")
        pts, notes = _score_competitive(opp, ["sdvosb"], [])
        assert pts == 25.0
        assert "we qualify" in notes

    def test_sdvosb_not_qualified_zero(self):
        opp = OpportunityInput(title="T", set_aside_type="sdvosb")
        pts, notes = _score_competitive(opp, [], [])
        assert pts == 0.0
        assert "do NOT qualify" in notes

    def test_8a_qualified(self):
        opp = OpportunityInput(title="T", set_aside_type="8a")
        pts, _ = _score_competitive(opp, ["8a"], [])
        assert pts == 25.0

    def test_keyword_bonus_applied(self):
        opp = OpportunityInput(
            title="T",
            set_aside_type="full_and_open",
            description="Python DevSecOps cloud infrastructure",
        )
        pts, notes = _score_competitive(opp, [], ["python", "devsecops"])
        assert pts > 8.0
        assert "python" in notes.lower()

    def test_keyword_bonus_capped_at_25(self):
        opp = OpportunityInput(
            title="T",
            set_aside_type="sdvosb",
            description="python cloud azure aws gcp devops kubernetes",
        )
        pts, _ = _score_competitive(
            opp, ["sdvosb"], ["python", "cloud", "azure", "aws", "gcp", "devops"]
        )
        assert pts <= 25.0


# ---------------------------------------------------------------------------
# _score_past_performance
# ---------------------------------------------------------------------------

class TestScorePastPerformance:
    def test_three_or_more_refs_full_points(self):
        opp = OpportunityInput(title="T", relevant_past_performance_count=3)
        pts, notes = _score_past_performance(opp)
        assert pts == 25.0
        assert "strong" in notes.lower()

    def test_two_refs(self):
        opp = OpportunityInput(title="T", relevant_past_performance_count=2)
        pts, _ = _score_past_performance(opp)
        assert pts == 18.0

    def test_one_ref(self):
        opp = OpportunityInput(title="T", relevant_past_performance_count=1)
        pts, notes = _score_past_performance(opp)
        assert pts == 10.0
        assert "thin" in notes.lower()

    def test_zero_refs_low_score(self):
        opp = OpportunityInput(title="T", relevant_past_performance_count=0)
        pts, _ = _score_past_performance(opp)
        assert pts == 5.0

    def test_many_refs_capped_at_25(self):
        opp = OpportunityInput(title="T", relevant_past_performance_count=10)
        pts, _ = _score_past_performance(opp)
        assert pts == 25.0


# ---------------------------------------------------------------------------
# _score_strategic
# ---------------------------------------------------------------------------

class TestScoreStrategic:
    def test_baseline_neutral(self, clean_env):
        opp = OpportunityInput(title="T")
        pts, _ = _score_strategic(opp)
        assert 0.0 <= pts <= 20.0

    def test_customer_relationship_bonus(self, clean_env):
        opp_rel = OpportunityInput(title="T", has_customer_relationship=True)
        opp_no  = OpportunityInput(title="T", has_customer_relationship=False)
        pts_rel, _ = _score_strategic(opp_rel)
        pts_no, _  = _score_strategic(opp_no)
        assert pts_rel > pts_no

    def test_incumbent_bonus(self, clean_env):
        opp_inc = OpportunityInput(title="T", is_we_incumbent=True)
        opp_not = OpportunityInput(title="T", is_we_incumbent=False)
        assert _score_strategic(opp_inc)[0] > _score_strategic(opp_not)[0]

    def test_known_competitor_incumbent_penalty(self, clean_env):
        opp_comp = OpportunityInput(title="T", incumbent="Acme Corp", is_we_incumbent=False)
        opp_none = OpportunityInput(title="T", incumbent="", is_we_incumbent=False)
        assert _score_strategic(opp_comp)[0] < _score_strategic(opp_none)[0]

    def test_very_tight_deadline_penalty(self, clean_env):
        tight = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        opp = OpportunityInput(title="T", proposal_due_date=tight)
        pts, notes = _score_strategic(opp)
        assert "tight" in notes.lower() or "Only" in notes

    def test_score_capped_at_20(self, clean_env):
        far_date = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
        opp = OpportunityInput(
            title="T",
            has_customer_relationship=True,
            is_we_incumbent=True,
            proposal_due_date=far_date,
        )
        pts, _ = _score_strategic(opp)
        assert pts <= 20.0


# ---------------------------------------------------------------------------
# score_opportunity (integration)
# ---------------------------------------------------------------------------

class TestScoreOpportunity:
    def test_pursue_recommendation(self, monkeypatch, it_opp):
        monkeypatch.setenv("COMPANY_NAICS_CODES", "541512")
        monkeypatch.setenv("COMPANY_SET_ASIDES", "small_business")
        result = score_opportunity(it_opp)
        assert result.recommendation == "PURSUE"
        assert result.score >= 70

    def test_pass_recommendation_disqualified_8a(self, monkeypatch):
        monkeypatch.delenv("COMPANY_SET_ASIDES", raising=False)
        opp = OpportunityInput(
            title="8(a) Cloud Support",
            naics_code="518210",
            set_aside_type="8a",
            relevant_past_performance_count=3,
        )
        result = score_opportunity(opp)
        assert result.recommendation == "PASS"
        assert any("8(a)" in w for w in result.warnings)

    def test_sdvosb_disqualifier(self, monkeypatch):
        monkeypatch.delenv("COMPANY_SET_ASIDES", raising=False)
        opp = OpportunityInput(title="SDVOSB Opp", set_aside_type="sdvosb")
        result = score_opportunity(opp)
        assert result.recommendation == "PASS"
        assert any("SDVOSB" in w for w in result.warnings)

    def test_critical_deadline_warning(self, monkeypatch, clean_env):
        soon = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        opp = OpportunityInput(title="Urgent Bid", proposal_due_date=soon)
        result = score_opportunity(opp)
        assert any("CRITICAL" in w for w in result.warnings)

    def test_result_has_all_fields(self, clean_env, it_opp):
        result = score_opportunity(it_opp)
        assert isinstance(result, ScoringResult)
        assert result.solicitation_number
        assert result.title
        assert 0.0 <= result.score <= 100.0
        assert result.recommendation in ("PURSUE", "MONITOR", "PASS")
        assert result.rationale
        assert result.next_action

    def test_monitor_recommendation(self, clean_env):
        opp = OpportunityInput(
            title="Marginal Fit",
            naics_code="999999",  # No match
            set_aside_type="full_and_open",
            relevant_past_performance_count=2,
            has_customer_relationship=True,
            is_we_incumbent=True,
            proposal_due_date=(datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
        )
        result = score_opportunity(opp)
        # With no NAICS match but strong strategic, should land somewhere mid-range
        assert result.recommendation in ("MONITOR", "PASS")


# ---------------------------------------------------------------------------
# score_opportunities_batch
# ---------------------------------------------------------------------------

class TestScoreOpportunitiesBatch:
    def test_sorted_descending(self, monkeypatch):
        monkeypatch.setenv("COMPANY_NAICS_CODES", "541512")
        opps = [
            OpportunityInput(title="Low", naics_code="999999"),
            OpportunityInput(title="High", naics_code="541512", relevant_past_performance_count=3,
                             has_customer_relationship=True, is_we_incumbent=True),
        ]
        results = score_opportunities_batch(opps)
        assert results[0].score >= results[1].score

    def test_empty_input(self, clean_env):
        assert score_opportunities_batch([]) == []

    def test_all_results_returned(self, clean_env):
        opps = [OpportunityInput(title=f"Opp {i}") for i in range(5)]
        results = score_opportunities_batch(opps)
        assert len(results) == 5


# ---------------------------------------------------------------------------
# result_to_dict
# ---------------------------------------------------------------------------

class TestResultToDict:
    def test_serializes_all_keys(self, clean_env, it_opp):
        result = score_opportunity(it_opp)
        d = result_to_dict(result)
        expected_keys = {
            "solicitation_number", "title", "agency", "score", "recommendation",
            "breakdown", "notes", "rationale", "next_action", "warnings", "scored_at",
        }
        assert expected_keys <= set(d.keys())

    def test_breakdown_sums_correctly(self, clean_env, it_opp):
        result = score_opportunity(it_opp)
        d = result_to_dict(result)
        breakdown_total = sum(d["breakdown"].values())
        # Allow small floating-point delta; total field is separate
        assert abs(breakdown_total - result.score) < 1.0

    def test_warnings_is_list(self, clean_env, it_opp):
        result = score_opportunity(it_opp)
        d = result_to_dict(result)
        assert isinstance(d["warnings"], list)
