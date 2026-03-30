"""
Opportunity Scorer — Core logic for the opportunity-curator skill.

Scores government contracting opportunities against company capabilities
using NAICS alignment, competitive positioning, past performance relevance,
and strategic factors. Returns a 0-100 score with pursue/monitor/pass recommendation.

Configuration via environment variables (see .env.example):
    COMPANY_NAICS_CODES      — comma-separated primary NAICS codes
    COMPANY_CAPABILITY_KEYWORDS — comma-separated capability keywords
    BID_THRESHOLD            — score ≥ this → PURSUE (default 70)
    MONITOR_THRESHOLD        — score ≥ this → MONITOR (default 50)
"""

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Score weights (total = 100 points)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "naics":          30,   # NAICS alignment — hardest technical filter
    "competitive":    25,   # Set-aside type + our eligibility
    "past_perf":      25,   # Relevant past contracts with this agency/domain
    "strategic":      20,   # Customer relationship, incumbent status, timing
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class OpportunityInput:
    """
    Raw opportunity data for scoring — minimal required fields.
    Additional fields improve scoring accuracy.
    """
    title: str
    agency: str = ""
    naics_code: str = ""                   # Primary NAICS from solicitation
    set_aside_type: str = "unknown"        # SetAsideType value
    estimated_value: float = 0.0
    source: str = ""                       # SAM.gov, eBuy, PTAC, etc.
    description: str = ""                  # Full opportunity description
    solicitation_number: str = ""
    proposal_due_date: Optional[str] = None
    is_recompete: bool = False
    incumbent: str = ""                    # Known incumbent (if any)

    # Company-context fields (for scoring accuracy)
    is_prime: bool = True                  # True = we're bidding as prime
    potential_teammates: List[str] = field(default_factory=list)

    # Scoring context overrides (if known from capture intel)
    has_customer_relationship: bool = False
    is_we_incumbent: bool = False
    relevant_past_performance_count: int = 0  # # of relevant PP refs we have


@dataclass
class ScoreBreakdown:
    """Detailed scoring breakdown by category."""
    naics_score: float = 0.0
    competitive_score: float = 0.0
    past_perf_score: float = 0.0
    strategic_score: float = 0.0
    total: float = 0.0

    naics_notes: str = ""
    competitive_notes: str = ""
    past_perf_notes: str = ""
    strategic_notes: str = ""


@dataclass
class ScoringResult:
    """Complete scoring result returned to the opportunity-curator skill."""
    solicitation_number: str
    title: str
    agency: str
    score: float                       # 0–100
    recommendation: str                # PURSUE / MONITOR / PASS
    breakdown: ScoreBreakdown
    rationale: str
    next_action: str
    warnings: List[str] = field(default_factory=list)
    scored_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

def _load_company_naics() -> List[str]:
    """Load company NAICS codes from environment."""
    raw = os.getenv("COMPANY_NAICS_CODES", "")
    return [n.strip() for n in raw.split(",") if n.strip()] if raw else []


def _load_capability_keywords() -> List[str]:
    """Load company capability keywords from environment."""
    raw = os.getenv("COMPANY_CAPABILITY_KEYWORDS", "")
    return [k.strip().lower() for k in raw.split(",") if k.strip()] if raw else []


def _load_company_set_asides() -> List[str]:
    """Load set-aside certifications the company holds from environment."""
    raw = os.getenv("COMPANY_SET_ASIDES", "")
    return [s.strip().lower() for s in raw.split(",") if s.strip()] if raw else []


def _thresholds() -> Tuple[int, int]:
    """Return (bid_threshold, monitor_threshold) from environment."""
    bid = int(os.getenv("BID_THRESHOLD", "70"))
    monitor = int(os.getenv("MONITOR_THRESHOLD", "50"))
    return bid, monitor


# ---------------------------------------------------------------------------
# Scoring functions (one per weight category)
# ---------------------------------------------------------------------------

def _score_naics(opp: OpportunityInput, company_naics: List[str]) -> Tuple[float, str]:
    """
    Score NAICS code alignment.

    Args:
        opp: Opportunity input data.
        company_naics: List of company NAICS codes from environment.

    Returns:
        Tuple[float, str]: (points earned out of 30, explanation note).
    """
    if not opp.naics_code:
        return 15.0, "NAICS not specified — neutral score applied"

    if not company_naics:
        logger.warning("COMPANY_NAICS_CODES not configured — defaulting to neutral NAICS score")
        return 15.0, "Company NAICS not configured in .env (COMPANY_NAICS_CODES)"

    opp_naics = opp.naics_code.strip()

    # Exact 6-digit match
    if opp_naics in company_naics:
        return 30.0, f"Exact NAICS match: {opp_naics}"

    # 4-digit subsector match (first 4 digits)
    opp_sub = opp_naics[:4]
    for cn in company_naics:
        if cn[:4] == opp_sub:
            return 20.0, f"Subsector NAICS match: {opp_sub}xx"

    # 3-digit industry group match
    opp_grp = opp_naics[:3]
    for cn in company_naics:
        if cn[:3] == opp_grp:
            return 12.0, f"Industry group NAICS match: {opp_grp}xxx"

    # 2-digit sector match (very broad)
    opp_sec = opp_naics[:2]
    for cn in company_naics:
        if cn[:2] == opp_sec:
            return 6.0, f"Sector-level NAICS match only: {opp_sec}xxxx — verify fit"

    return 0.0, f"No NAICS match: {opp_naics} not in {company_naics}"


def _score_competitive(
    opp: OpportunityInput,
    company_set_asides: List[str],
    capability_keywords: List[str],
) -> Tuple[float, str]:
    """
    Score competitive positioning based on set-aside type and description match.

    Args:
        opp: Opportunity input data.
        company_set_asides: Set-aside certs the company holds.
        capability_keywords: Company capability keywords.

    Returns:
        Tuple[float, str]: (points earned out of 25, explanation note).
    """
    set_aside = opp.set_aside_type.lower()
    score = 0.0
    notes = []

    # Set-aside alignment scoring
    if set_aside in ("full_and_open", "unknown", "other"):
        score += 8.0
        notes.append("Full & open — competitive but possible")
    elif set_aside == "small_business":
        score += 15.0 if "small_business" in company_set_asides else 5.0
        notes.append("Small business set-aside")
    elif set_aside == "sdvosb":
        score += 25.0 if "sdvosb" in company_set_asides else 0.0
        notes.append("SDVOSB set-aside" + (" — we qualify" if "sdvosb" in company_set_asides else " — we do NOT qualify"))
    elif set_aside == "8a":
        score += 25.0 if "8a" in company_set_asides else 0.0
        notes.append("8(a) set-aside" + (" — we qualify" if "8a" in company_set_asides else " — we do NOT qualify"))
    elif set_aside == "wosb":
        score += 25.0 if "wosb" in company_set_asides else 0.0
        notes.append("WOSB set-aside" + (" — we qualify" if "wosb" in company_set_asides else " — we do NOT qualify"))
    elif set_aside == "hubzone":
        score += 25.0 if "hubzone" in company_set_asides else 0.0
        notes.append("HUBZone set-aside" + (" — we qualify" if "hubzone" in company_set_asides else " — we do NOT qualify"))
    elif set_aside == "vosb":
        score += 20.0 if "vosb" in company_set_asides else 0.0
        notes.append("VOSB set-aside")
    else:
        score += 5.0
        notes.append(f"Set-aside type: {set_aside}")

    # Keyword match bonus (max +5 on top of set-aside)
    if capability_keywords and opp.description:
        desc_lower = opp.description.lower()
        matched = [kw for kw in capability_keywords if kw in desc_lower]
        if matched:
            kw_bonus = min(5.0, len(matched) * 1.5)
            score = min(25.0, score + kw_bonus)
            notes.append(f"Keyword matches: {', '.join(matched[:5])}")

    return score, " | ".join(notes)


def _score_past_performance(opp: OpportunityInput) -> Tuple[float, str]:
    """
    Score past performance relevance.

    Uses explicit count if provided; otherwise estimates from agency/NAICS match.

    Args:
        opp: Opportunity input data.

    Returns:
        Tuple[float, str]: (points earned out of 25, explanation note).
    """
    pp_count = opp.relevant_past_performance_count
    notes = []

    if pp_count >= 3:
        score = 25.0
        notes.append(f"{pp_count} relevant PP refs — strong")
    elif pp_count == 2:
        score = 18.0
        notes.append("2 relevant PP refs — adequate")
    elif pp_count == 1:
        score = 10.0
        notes.append("1 relevant PP ref — thin; consider teaming for additional refs")
    else:
        # Estimate from agency match (better than nothing)
        score = 5.0
        notes.append("No PP count provided — run opportunity-curator with PP data for accurate score")

    return score, " | ".join(notes)


def _score_strategic(opp: OpportunityInput) -> Tuple[float, str]:
    """
    Score strategic factors: customer relationship, incumbent status, timing.

    Args:
        opp: Opportunity input data.

    Returns:
        Tuple[float, str]: (points earned out of 20, explanation note).
    """
    score = 10.0  # Neutral baseline
    notes = []

    # Customer relationship
    if opp.has_customer_relationship:
        score += 5.0
        notes.append("Existing customer relationship — strong intel advantage")
    else:
        notes.append("No known customer relationship — cold pursuit")

    # Incumbent status
    if opp.is_we_incumbent:
        score += 5.0
        notes.append("We ARE the incumbent — significant competitive advantage")
    elif opp.incumbent and not opp.is_we_incumbent:
        score -= 5.0
        notes.append(f"Known incumbent: {opp.incumbent} — must overcome incumbent advantage")
    elif opp.is_recompete and not opp.incumbent:
        notes.append("Recompete — incumbent unknown; research required")

    # Proposal due date feasibility
    if opp.proposal_due_date:
        due = datetime.fromisoformat(opp.proposal_due_date[:10])
        days_until_due = (due - datetime.now()).days
        if days_until_due < 15:
            score -= 5.0
            notes.append(f"⚠ Only {days_until_due} days until due — very tight timeline")
        elif days_until_due < 30:
            score -= 2.0
            notes.append(f"{days_until_due} days until due — compressed schedule")
        else:
            notes.append(f"{days_until_due} days until due — workable timeline")

    # Contract value sizing
    if opp.estimated_value > 0:
        company_size = os.getenv("COMPANY_SIZE", "small")
        if company_size == "small":
            if opp.estimated_value > 50_000_000:
                score -= 3.0
                notes.append(f"${opp.estimated_value/1e6:.0f}M — large contract; teaming likely required")
            elif opp.estimated_value < 500_000:
                score -= 2.0
                notes.append(f"${opp.estimated_value:,.0f} — very small; verify ROI on proposal effort")

    return min(20.0, max(0.0, score)), " | ".join(notes)


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_opportunity(opp: OpportunityInput) -> ScoringResult:
    """
    Score a government contracting opportunity against company capabilities.

    Args:
        opp: OpportunityInput with opportunity details.

    Returns:
        ScoringResult: Score, recommendation, breakdown, and rationale.
    """
    company_naics = _load_company_naics()
    capability_keywords = _load_capability_keywords()
    company_set_asides = _load_company_set_asides()
    bid_threshold, monitor_threshold = _thresholds()

    # Score each category
    naics_pts, naics_notes = _score_naics(opp, company_naics)
    comp_pts, comp_notes = _score_competitive(opp, company_set_asides, capability_keywords)
    pp_pts, pp_notes = _score_past_performance(opp)
    strat_pts, strat_notes = _score_strategic(opp)

    total = round(naics_pts + comp_pts + pp_pts + strat_pts, 1)

    breakdown = ScoreBreakdown(
        naics_score=naics_pts,
        competitive_score=comp_pts,
        past_perf_score=pp_pts,
        strategic_score=strat_pts,
        total=total,
        naics_notes=naics_notes,
        competitive_notes=comp_notes,
        past_perf_notes=pp_notes,
        strategic_notes=strat_notes,
    )

    # Determine recommendation
    warnings: List[str] = []
    if total >= bid_threshold:
        recommendation = "PURSUE"
        next_action = "Run /bid-no-bid for full Shipley assessment"
    elif total >= monitor_threshold:
        recommendation = "MONITOR"
        next_action = "Watch for amendments; revisit in 30 days or if scope changes"
    else:
        recommendation = "PASS"
        next_action = "Document rationale; archive in opportunities.db"

    # Check for disqualifying conditions
    disqualifiers: List[str] = []
    if opp.set_aside_type.lower() == "sdvosb" and "sdvosb" not in company_set_asides:
        disqualifiers.append("SDVOSB set-aside — we do not qualify unless teaming with certified SDVOSB prime")
        recommendation = "PASS"
        next_action = "Cannot bid as prime; identify SDVOSB prime to team with"
    if opp.set_aside_type.lower() == "8a" and "8a" not in company_set_asides:
        disqualifiers.append("8(a) set-aside — we do not qualify")
        recommendation = "PASS"
    if opp.proposal_due_date:
        days_left = (datetime.fromisoformat(opp.proposal_due_date[:10]) - datetime.now()).days
        if days_left < 7:
            warnings.append(f"CRITICAL: Only {days_left} days remaining — immediate decision required")

    if disqualifiers:
        warnings.extend(disqualifiers)

    # Build rationale
    rationale_parts = []
    rationale_parts.append(f"Score {total}/100 → {recommendation}.")
    if naics_pts >= 25:
        rationale_parts.append(f"Strong NAICS alignment ({opp.naics_code}).")
    elif naics_pts < 10:
        rationale_parts.append(f"Weak NAICS alignment ({opp.naics_code} vs {company_naics}).")
    rationale_parts.append(comp_notes.split("|")[0].strip() + ".")
    if pp_pts >= 20:
        rationale_parts.append("Strong past performance coverage.")
    elif pp_pts < 10:
        rationale_parts.append("Past performance is a gap — gather refs before bidding.")
    if strat_pts >= 15:
        rationale_parts.append("Favorable strategic position.")
    rationale = " ".join(rationale_parts)

    return ScoringResult(
        solicitation_number=opp.solicitation_number or "TBD",
        title=opp.title,
        agency=opp.agency,
        score=total,
        recommendation=recommendation,
        breakdown=breakdown,
        rationale=rationale,
        next_action=next_action,
        warnings=warnings,
    )


def score_opportunities_batch(opps: List[OpportunityInput]) -> List[ScoringResult]:
    """
    Score multiple opportunities and return sorted by score descending.

    Args:
        opps: List of OpportunityInput objects.

    Returns:
        List[ScoringResult]: Scored results, highest score first.
    """
    results = [score_opportunity(opp) for opp in opps]
    return sorted(results, key=lambda r: r.score, reverse=True)


def result_to_dict(result: ScoringResult) -> Dict:
    """Serialize a ScoringResult to a plain dict for JSON output."""
    return {
        "solicitation_number": result.solicitation_number,
        "title": result.title,
        "agency": result.agency,
        "score": result.score,
        "recommendation": result.recommendation,
        "breakdown": {
            "naics": result.breakdown.naics_score,
            "competitive": result.breakdown.competitive_score,
            "past_performance": result.breakdown.past_perf_score,
            "strategic": result.breakdown.strategic_score,
        },
        "notes": {
            "naics": result.breakdown.naics_notes,
            "competitive": result.breakdown.competitive_notes,
            "past_performance": result.breakdown.past_perf_notes,
            "strategic": result.breakdown.strategic_notes,
        },
        "rationale": result.rationale,
        "next_action": result.next_action,
        "warnings": result.warnings,
        "scored_at": result.scored_at,
    }
