"""
Bid/No-Bid Assessment Engine.

Implements the Shipley Go/No-Go methodology for government proposal decisions.
Scores 8 weighted criteria and derives BID / CONDITIONAL / NO-BID recommendation.

All scoring thresholds are config-driven via environment variables:
    BID_THRESHOLD     — minimum score for BID (default 70)
    COND_THRESHOLD    — minimum score for CONDITIONAL (default 50)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from proposal.models import BidDecision, BidNoBidAssessment, BidNoBidCriterion, Proposal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (env-configurable so they never need code changes)
# ---------------------------------------------------------------------------

def _bid_threshold() -> float:
    """Minimum weighted score to recommend BID."""
    return float(os.getenv("BID_THRESHOLD", "70"))


def _cond_threshold() -> float:
    """Minimum weighted score for CONDITIONAL (below = NO-BID)."""
    return float(os.getenv("COND_THRESHOLD", "50"))


# ---------------------------------------------------------------------------
# Default Shipley criteria (config-driven weights)
# ---------------------------------------------------------------------------

_DEFAULT_CRITERIA_JSON = os.getenv("BID_NO_BID_CRITERIA_FILE", "")

def _load_criteria_config() -> List[Dict[str, Any]]:
    """
    Load criteria definitions from JSON file if configured, else use defaults.

    Returns:
        List[Dict]: Criteria config with name and weight.
    """
    if _DEFAULT_CRITERIA_JSON and os.path.exists(_DEFAULT_CRITERIA_JSON):
        with open(_DEFAULT_CRITERIA_JSON) as f:
            return json.load(f)

    # Reason: Shipley standard weights — heavier on customer/competitive/technical
    return [
        {"name": "Customer Knowledge",       "weight": 1.5},
        {"name": "Competitive Position",     "weight": 1.5},
        {"name": "Incumbent Advantage",      "weight": 1.25},
        {"name": "Technical Capability",     "weight": 1.5},
        {"name": "Past Performance",         "weight": 1.25},
        {"name": "Team Availability",        "weight": 1.0},
        {"name": "Price Competitiveness",    "weight": 1.25},
        {"name": "Risk Assessment",          "weight": 1.0},
    ]


def build_blank_assessment(proposal_id: str, assessor: str = "") -> BidNoBidAssessment:
    """
    Build a blank BidNoBidAssessment with default Shipley criteria.

    Args:
        proposal_id: Proposal UUID the assessment is linked to.
        assessor: Name of the person conducting the assessment.

    Returns:
        BidNoBidAssessment: Assessment with unscored criteria.
    """
    criteria_config = _load_criteria_config()
    criteria = [
        BidNoBidCriterion(name=c["name"], weight=c["weight"])
        for c in criteria_config
    ]
    return BidNoBidAssessment(
        proposal_id=proposal_id,
        assessor=assessor,
        assessment_date=datetime.now().isoformat(),
        criteria=criteria,
    )


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_criterion(assessment: BidNoBidAssessment, criterion_name: str, score: float, notes: str = "") -> BidNoBidAssessment:
    """
    Apply a score to a named criterion in the assessment.

    Args:
        assessment: Current assessment object.
        criterion_name: Exact name of the criterion to score.
        score: Score value (1.0-10.0 scale).
        notes: Optional rationale for this score.

    Returns:
        BidNoBidAssessment: Updated assessment with new score applied.

    Raises:
        ValueError: If criterion_name not found or score out of range.
    """
    if not 1.0 <= score <= 10.0:
        raise ValueError(f"Score must be between 1 and 10, got {score}")

    for criterion in assessment.criteria:
        if criterion.name.lower() == criterion_name.lower():
            updated = criterion.model_copy(update={"score": score, "notes": notes})
            new_criteria = [
                updated if c.name.lower() == criterion_name.lower() else c
                for c in assessment.criteria
            ]
            return assessment.model_copy(update={"criteria": new_criteria})

    raise ValueError(f"Criterion '{criterion_name}' not found in assessment")


def apply_scores_bulk(assessment: BidNoBidAssessment, scores: Dict[str, float]) -> BidNoBidAssessment:
    """
    Apply multiple criterion scores at once.

    Args:
        assessment: Current assessment object.
        scores: Dict of {criterion_name: score_value}.

    Returns:
        BidNoBidAssessment: Updated assessment with all scores applied.
    """
    for name, score in scores.items():
        assessment = score_criterion(assessment, name, score)
    return assessment


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

def get_recommendation(assessment: BidNoBidAssessment) -> BidDecision:
    """
    Derive bid recommendation from the assessment's weighted score.

    Thresholds driven by BID_THRESHOLD and COND_THRESHOLD env vars.

    Args:
        assessment: Assessment with scored criteria.

    Returns:
        BidDecision: BID, CONDITIONAL, or NO_BID.
    """
    score = assessment.weighted_score()
    bid_thresh = _bid_threshold()
    cond_thresh = _cond_threshold()

    if score >= bid_thresh:
        return BidDecision.BID
    elif score >= cond_thresh:
        return BidDecision.CONDITIONAL
    else:
        return BidDecision.NO_BID


def finalize_assessment(
    assessment: BidNoBidAssessment,
    win_themes: Optional[List[str]] = None,
    discriminators: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
    mitigations: Optional[List[str]] = None,
    final_decision: Optional[BidDecision] = None,
    decision_made_by: str = "",
    rationale: str = "",
) -> BidNoBidAssessment:
    """
    Finalize the assessment: set recommendation, record decision, and capture narrative.

    The recommendation is auto-derived from the weighted score. The final_decision
    may differ if leadership overrides (e.g., strategic no-bid on a high scorer).

    Args:
        assessment: Assessment with all criteria scored.
        win_themes: List of win theme strings.
        discriminators: List of discriminator strings.
        risks: List of risk strings.
        mitigations: List of risk mitigation strings.
        final_decision: Leadership override decision (defaults to recommendation).
        decision_made_by: Name of final decision-maker.
        rationale: Narrative rationale for the decision.

    Returns:
        BidNoBidAssessment: Finalized assessment ready for DB persistence.
    """
    recommendation = get_recommendation(assessment)
    decision = final_decision or recommendation
    score = assessment.weighted_score()

    # Reason: Auto-generate rationale if none provided, to ensure DB records are useful
    if not rationale:
        rationale = (
            f"Weighted score: {score:.1f}/100 (threshold: BID≥{_bid_threshold()}, "
            f"COND≥{_cond_threshold()}). "
            f"Auto-recommendation: {recommendation.value.upper()}."
        )
        if decision != recommendation:
            rationale += f" Leadership override to {decision.value.upper()}."

    return assessment.model_copy(update={
        "win_themes":                  win_themes or assessment.win_themes,
        "discriminators":              discriminators or assessment.discriminators,
        "risks":                       risks or assessment.risks,
        "mitigations":                 mitigations or assessment.mitigations,
        "recommendation":              recommendation,
        "recommendation_rationale":    rationale,
        "final_decision":              decision,
        "decision_made_by":            decision_made_by,
        "decision_date":               datetime.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# AI-assisted scoring (Claude analysis)
# ---------------------------------------------------------------------------

def analyze_opportunity_with_claude(
    proposal: Proposal,
    additional_context: str = "",
) -> Dict[str, Any]:
    """
    Use Claude (Sonnet 4.6) to suggest criterion scores based on proposal data.

    This is advisory only — scores can be overridden before finalization.
    Uses extended thinking for deeper competitive analysis.

    Args:
        proposal: Proposal model with all available fields populated.
        additional_context: Additional context (intel, call notes, etc.).

    Returns:
        Dict: Suggested scores and rationale per criterion. Format:
            {
                "scores": {"Customer Knowledge": 7.0, ...},
                "rationale": {"Customer Knowledge": "reason...", ...},
                "pwin_estimate": 0.65,
                "overall_analysis": "...",
            }
    """
    try:
        import anthropic
        from config.model_config import get_model, get_thinking_config, ModelTier
    except ImportError:
        logger.warning("anthropic or config.model_config not available — returning empty analysis")
        return {"scores": {}, "rationale": {}, "pwin_estimate": None, "overall_analysis": ""}

    client = anthropic.Anthropic()
    model = get_model(ModelTier.PRIMARY)
    thinking_cfg = get_thinking_config(budget_tokens=8000)

    proposal_summary = {
        "solicitation_number": proposal.solicitation_number,
        "title":               proposal.title,
        "agency":              proposal.agency,
        "naics_code":          proposal.naics_code,
        "set_aside_type":      proposal.set_aside_type,
        "estimated_value":     proposal.estimated_value,
        "proposal_due_date":   proposal.proposal_due_date,
        "is_recompete":        proposal.is_recompete,
        "incumbent":           proposal.incumbent,
        "capture_manager":     proposal.capture_manager,
        "pwin_score":          proposal.pwin_score,
        "notes":               proposal.notes[:2000] if proposal.notes else "",
    }

    prompt = f"""You are a GovCon Capture Manager conducting a Shipley Bid/No-Bid analysis.

Proposal Data:
{json.dumps(proposal_summary, indent=2, default=str)}

Additional Context:
{additional_context or "(none provided)"}

Score each of the following criteria on a 1-10 scale and provide your reasoning:
1. Customer Knowledge (1.5x weight) — existing relationship, prior interactions, access
2. Competitive Position (1.5x weight) — win probability vs. known competitors
3. Incumbent Advantage (1.25x weight) — prior work with this customer on this effort
4. Technical Capability (1.5x weight) — team can deliver the required scope
5. Past Performance (1.25x weight) — directly relevant, citable contracts
6. Team Availability (1.0x weight) — key personnel available for PoP start date
7. Price Competitiveness (1.25x weight) — can we hit Price-to-Win and still profit?
8. Risk Assessment (1.0x weight) — technical, programmatic, and financial risks (higher score = lower risk)

Also provide:
- Estimated Pwin (0.0-1.0)
- Overall capture analysis

Respond ONLY with valid JSON in this exact format:
{{
  "scores": {{"Customer Knowledge": 7.0, "Competitive Position": 6.0, ...}},
  "rationale": {{"Customer Knowledge": "reason", ...}},
  "pwin_estimate": 0.65,
  "overall_analysis": "..."
}}"""

    try:
        # Reason: Extended thinking gives more rigorous competitive analysis
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            thinking=thinking_cfg,
            messages=[{"role": "user", "content": prompt}],
        )
        # Extract text blocks (thinking blocks are separate)
        text_content = next(
            (b.text for b in resp.content if b.type == "text"), ""
        )
        # Reason: Claude sometimes wraps JSON in markdown fences
        if "```json" in text_content:
            text_content = text_content.split("```json")[1].split("```")[0].strip()
        elif "```" in text_content:
            text_content = text_content.split("```")[1].split("```")[0].strip()

        return json.loads(text_content)
    except Exception as exc:
        logger.error("Claude B/NB analysis failed: %s", exc)
        return {"scores": {}, "rationale": {}, "pwin_estimate": None, "overall_analysis": ""}


# ---------------------------------------------------------------------------
# Convenience: run full assessment from proposal data
# ---------------------------------------------------------------------------

def run_assessment(
    proposal: Proposal,
    scores: Optional[Dict[str, float]] = None,
    win_themes: Optional[List[str]] = None,
    discriminators: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
    mitigations: Optional[List[str]] = None,
    assessor: str = "",
    final_decision: Optional[BidDecision] = None,
    decision_made_by: str = "",
    rationale: str = "",
    use_claude: bool = False,
    additional_context: str = "",
) -> BidNoBidAssessment:
    """
    Run a complete Bid/No-Bid assessment for a proposal.

    If use_claude=True and no scores are provided, Claude will suggest scores.
    Explicit scores always override Claude suggestions.

    Args:
        proposal: Proposal being assessed.
        scores: Dict of {criterion_name: score} for manual scoring.
        win_themes: Win theme strings.
        discriminators: Discriminator strings.
        risks: Risk strings.
        mitigations: Risk mitigation strings.
        assessor: Name of the assessor.
        final_decision: Leadership override decision.
        decision_made_by: Decision-maker name.
        rationale: Decision rationale.
        use_claude: If True, use Claude to suggest scores when none provided.
        additional_context: Extra context for Claude analysis.

    Returns:
        BidNoBidAssessment: Finalized, ready-to-save assessment.
    """
    assessment = build_blank_assessment(proposal.id, assessor=assessor)

    # Optionally get Claude's suggested scores
    ai_result: Dict[str, Any] = {}
    if use_claude and not scores:
        logger.info("Running Claude B/NB analysis for %s", proposal.solicitation_number)
        ai_result = analyze_opportunity_with_claude(proposal, additional_context)
        suggested_scores: Dict[str, float] = ai_result.get("scores", {})
        if suggested_scores:
            assessment = apply_scores_bulk(assessment, suggested_scores)
            # Reason: Inject Claude's per-criterion notes into assessment
            for crit in assessment.criteria:
                rationale_text = ai_result.get("rationale", {}).get(crit.name, "")
                if rationale_text:
                    assessment = score_criterion(
                        assessment, crit.name, crit.score or 5.0, rationale_text
                    )

    # Apply manual scores if provided (always override AI)
    if scores:
        assessment = apply_scores_bulk(assessment, scores)

    # Derive pwin from Claude if proposal doesn't have one
    pwin_from_claude = ai_result.get("pwin_estimate")
    if pwin_from_claude and proposal.pwin_score is None:
        logger.info("Setting pwin from Claude analysis: %.2f", pwin_from_claude)
        # Note: caller should update proposal.pwin_score separately if desired

    overall = ai_result.get("overall_analysis", "") if not rationale else rationale

    return finalize_assessment(
        assessment,
        win_themes=win_themes,
        discriminators=discriminators,
        risks=risks,
        mitigations=mitigations,
        final_decision=final_decision,
        decision_made_by=decision_made_by,
        rationale=overall or rationale,
    )


def assessment_to_dict(assessment: BidNoBidAssessment) -> Dict[str, Any]:
    """
    Serialize a BidNoBidAssessment to a plain dict for display or export.

    Args:
        assessment: Assessment to serialize.

    Returns:
        Dict: Human-readable representation with score included.
    """
    d = assessment.model_dump()
    d["weighted_score"] = round(assessment.weighted_score(), 2)
    d["score_label"] = get_recommendation(assessment).value.upper()
    return d
