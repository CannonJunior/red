"""
Tests for proposal/bid_no_bid.py and proposal/bid_no_bid_slide.py.
"""

import os
import tempfile
from pathlib import Path

import pytest

from proposal.bid_no_bid import (
    apply_scores_bulk,
    assessment_to_dict,
    build_blank_assessment,
    finalize_assessment,
    get_recommendation,
    score_criterion,
)
from proposal.bid_no_bid_slide import generate_bid_no_bid_slide
from proposal.models import BidDecision, Proposal, SetAsideType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def blank_assessment():
    return build_blank_assessment("prop-001", assessor="Test User")


@pytest.fixture
def scored_assessment(blank_assessment):
    """Assessment with all criteria scored at 7.5."""
    scores = {c.name: 7.5 for c in blank_assessment.criteria}
    return apply_scores_bulk(blank_assessment, scores)


@pytest.fixture
def sample_proposal():
    return Proposal(
        id="prop-001",
        title="Cyber Defense Platform",
        solicitation_number="FA8612-26-R-0001",
        agency="AFRL",
        naics_code="541512",
        set_aside_type=SetAsideType.SDVOSB,
        estimated_value=4_500_000,
        proposal_due_date="2026-07-15",
        is_recompete=False,
        capture_manager="Alice",
        pwin_score=0.70,
    )


# ---------------------------------------------------------------------------
# build_blank_assessment
# ---------------------------------------------------------------------------

def test_blank_assessment_has_eight_criteria(blank_assessment):
    """Expected use: blank assessment starts with 8 Shipley criteria."""
    assert len(blank_assessment.criteria) == 8


def test_blank_assessment_no_scores(blank_assessment):
    """Expected use: blank criteria have no scores."""
    assert all(c.score is None for c in blank_assessment.criteria)


def test_blank_assessment_links_proposal_id(blank_assessment):
    """Expected use: proposal_id is correctly stored."""
    assert blank_assessment.proposal_id == "prop-001"


# ---------------------------------------------------------------------------
# score_criterion
# ---------------------------------------------------------------------------

def test_score_criterion_updates_value(blank_assessment):
    """Expected use: scoring a named criterion stores the value."""
    updated = score_criterion(blank_assessment, "Customer Knowledge", 8.0, "Strong relationship")
    ck = next(c for c in updated.criteria if c.name == "Customer Knowledge")
    assert ck.score == 8.0
    assert ck.notes == "Strong relationship"


def test_score_criterion_case_insensitive(blank_assessment):
    """Edge case: criterion name match should be case-insensitive."""
    updated = score_criterion(blank_assessment, "customer knowledge", 6.0)
    ck = next(c for c in updated.criteria if c.name == "Customer Knowledge")
    assert ck.score == 6.0


def test_score_criterion_invalid_range(blank_assessment):
    """Failure case: score outside 1-10 raises ValueError."""
    with pytest.raises(ValueError, match="between 1 and 10"):
        score_criterion(blank_assessment, "Customer Knowledge", 11.0)


def test_score_criterion_unknown_name(blank_assessment):
    """Failure case: unknown criterion name raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        score_criterion(blank_assessment, "Nonexistent Factor", 5.0)


# ---------------------------------------------------------------------------
# apply_scores_bulk
# ---------------------------------------------------------------------------

def test_apply_scores_bulk_all_criteria(blank_assessment):
    """Expected use: bulk scoring updates all named criteria."""
    scores = {c.name: float(i + 1) for i, c in enumerate(blank_assessment.criteria)}
    updated = apply_scores_bulk(blank_assessment, scores)
    scored = [c for c in updated.criteria if c.score is not None]
    assert len(scored) == 8


# ---------------------------------------------------------------------------
# get_recommendation / finalize_assessment
# ---------------------------------------------------------------------------

def test_recommendation_bid_above_threshold(scored_assessment):
    """Expected use: score ≥70 yields BID recommendation."""
    rec = get_recommendation(scored_assessment)
    assert rec == BidDecision.BID


def test_recommendation_no_bid_below_threshold(blank_assessment):
    """Expected use: score <50 yields NO_BID."""
    low_scores = {c.name: 2.0 for c in blank_assessment.criteria}
    low = apply_scores_bulk(blank_assessment, low_scores)
    assert get_recommendation(low) == BidDecision.NO_BID


def test_recommendation_conditional_midrange(blank_assessment):
    """Edge case: score between cond and bid thresholds yields CONDITIONAL."""
    mid_scores = {c.name: 5.5 for c in blank_assessment.criteria}
    mid = apply_scores_bulk(blank_assessment, mid_scores)
    rec = get_recommendation(mid)
    assert rec == BidDecision.CONDITIONAL


def test_finalize_sets_decision_date(scored_assessment):
    """Expected use: finalizing stores a decision_date."""
    final = finalize_assessment(scored_assessment)
    assert final.decision_date is not None


def test_finalize_leadership_override(scored_assessment):
    """Edge case: leadership can override recommendation to NO_BID."""
    final = finalize_assessment(scored_assessment, final_decision=BidDecision.NO_BID, decision_made_by="VP")
    assert final.final_decision == BidDecision.NO_BID
    assert final.recommendation == BidDecision.BID  # recommendation unchanged
    assert "override" in final.recommendation_rationale.lower()


def test_finalize_auto_rationale_generated(scored_assessment):
    """Edge case: rationale auto-populated when not provided."""
    final = finalize_assessment(scored_assessment)
    assert len(final.recommendation_rationale) > 0


# ---------------------------------------------------------------------------
# assessment_to_dict
# ---------------------------------------------------------------------------

def test_assessment_to_dict_includes_score(scored_assessment):
    """Expected use: serialized dict includes weighted_score and score_label."""
    final = finalize_assessment(scored_assessment)
    d = assessment_to_dict(final)
    assert "weighted_score" in d
    assert "score_label" in d
    assert isinstance(d["weighted_score"], float)


# ---------------------------------------------------------------------------
# Threshold env override
# ---------------------------------------------------------------------------

def test_threshold_override_via_env(blank_assessment, monkeypatch):
    """Edge case: BID_THRESHOLD env var changes cutoff."""
    monkeypatch.setenv("BID_THRESHOLD", "90")
    high_scores = {c.name: 8.0 for c in blank_assessment.criteria}
    assessment = apply_scores_bulk(blank_assessment, high_scores)
    # Score ~80 which would normally be BID but now below 90 threshold
    from proposal.bid_no_bid import get_recommendation
    rec = get_recommendation(assessment)
    assert rec == BidDecision.CONDITIONAL


# ---------------------------------------------------------------------------
# Slide generation
# ---------------------------------------------------------------------------

def test_slide_generation_creates_pptx(sample_proposal, scored_assessment):
    """Expected use: generate_bid_no_bid_slide creates a valid PPTX file."""
    final = finalize_assessment(
        scored_assessment,
        win_themes=["SDVOSB set-aside", "AI/ML expertise"],
        risks=["Key personnel availability"],
        mitigations=["Early engagement"],
        decision_made_by="CEO",
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_bid_no_bid_slide(sample_proposal, final, output_dir=tmp)
        assert path.exists()
        assert path.suffix == ".pptx"
        assert path.stat().st_size > 10_000


def test_slide_filename_convention(sample_proposal, scored_assessment):
    """Expected use: filename follows {solicitation}_bid_no_bid_{date}.pptx."""
    final = finalize_assessment(scored_assessment)
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_bid_no_bid_slide(sample_proposal, final, output_dir=tmp)
        assert "FA8612-26-R-0001" in path.name
        assert "bid_no_bid" in path.name
        assert path.name.endswith(".pptx")


def test_slide_six_slides_generated(sample_proposal, scored_assessment):
    """Expected use: deck contains exactly 6 slides."""
    from pptx import Presentation as PRS
    final = finalize_assessment(scored_assessment)
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_bid_no_bid_slide(sample_proposal, final, output_dir=tmp)
        prs = PRS(str(path))
        assert len(prs.slides) == 6


def test_slide_no_bid_proposal(sample_proposal, blank_assessment):
    """Failure case: NO-BID decision still generates valid slide."""
    low_scores = {c.name: 2.0 for c in blank_assessment.criteria}
    low = apply_scores_bulk(blank_assessment, low_scores)
    final = finalize_assessment(low, decision_made_by="Capture Manager")
    assert final.final_decision == BidDecision.NO_BID
    with tempfile.TemporaryDirectory() as tmp:
        path = generate_bid_no_bid_slide(sample_proposal, final, output_dir=tmp)
        assert path.exists()
