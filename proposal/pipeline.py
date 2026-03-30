"""
Proposal Pipeline State Machine.

Manages valid stage transitions and enforces checklist gates.
Each transition has a required-fields guard and optional side effects.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from proposal.models import BidDecision, PipelineStage, Proposal


# ---------------------------------------------------------------------------
# Transition graph — (from_stage, to_stage) → required_fields
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: Dict[Tuple[PipelineStage, PipelineStage], List[str]] = {
    # ── Unanet 01-Qualification ──────────────────────────────────────────────
    # IDENTIFIED → QUALIFYING: we know who and when
    (PipelineStage.IDENTIFIED, PipelineStage.QUALIFYING): [
        "solicitation_number",
        "agency",
        "proposal_due_date",
    ],
    # IDENTIFIED → LONG_LEAD: tracked early — no RFP yet, but strategic pursuit
    (PipelineStage.IDENTIFIED, PipelineStage.LONG_LEAD): [
        "agency",
        "capture_manager",
    ],

    # ── Unanet 02-Long Lead ──────────────────────────────────────────────────
    # LONG_LEAD → QUALIFYING: RFP drops, move to active qualification
    (PipelineStage.LONG_LEAD, PipelineStage.QUALIFYING): [
        "solicitation_number",
        "proposal_due_date",
    ],
    # LONG_LEAD → BID_DECISION: solicitation came with tight timeline, skip straight to B/NB
    (PipelineStage.LONG_LEAD, PipelineStage.BID_DECISION): [
        "solicitation_number",
        "capture_manager",
        "naics_code",
    ],

    # ── Unanet 03-Bid Decision ───────────────────────────────────────────────
    # QUALIFYING → BID_DECISION: shred analysis done, capture manager set
    (PipelineStage.QUALIFYING, PipelineStage.BID_DECISION): [
        "capture_manager",
        "naics_code",
    ],

    # ── Unanet 04-In Progress ────────────────────────────────────────────────
    # BID_DECISION → ACTIVE: decision is BID, team assembled
    (PipelineStage.BID_DECISION, PipelineStage.ACTIVE): [
        "bid_decision",
        "proposal_manager",
    ],

    # ── Unanet 09-Closed No Bid ──────────────────────────────────────────────
    # BID_DECISION → NO_BID: document rationale before closing
    (PipelineStage.BID_DECISION, PipelineStage.NO_BID): [
        "bid_decision_rationale",
    ],
    # QUALIFYING → NO_BID: decided not to bid before full B/NB (fast pass)
    (PipelineStage.QUALIFYING, PipelineStage.NO_BID): [
        "bid_decision_rationale",
    ],
    # LONG_LEAD → NO_BID: opportunity changed — no longer strategic
    (PipelineStage.LONG_LEAD, PipelineStage.NO_BID): [
        "bid_decision_rationale",
    ],

    # ── Unanet 05-Waiting/Review ─────────────────────────────────────────────
    # ACTIVE → SUBMITTED: package delivered, awaiting government review
    (PipelineStage.ACTIVE, PipelineStage.SUBMITTED): [
        "submission_method",
    ],

    # ── Unanet 06-In Negotiation ─────────────────────────────────────────────
    # SUBMITTED → NEGOTIATING: government selected us, now negotiating terms
    (PipelineStage.SUBMITTED, PipelineStage.NEGOTIATING): [],

    # ── Unanet 07/08-Closed Won/Lost ─────────────────────────────────────────
    # SUBMITTED → AWARDED/LOST: award decision received
    (PipelineStage.SUBMITTED, PipelineStage.AWARDED): [],
    (PipelineStage.SUBMITTED, PipelineStage.LOST): [],
    # NEGOTIATING → AWARDED/LOST: negotiations concluded
    (PipelineStage.NEGOTIATING, PipelineStage.AWARDED): [],
    (PipelineStage.NEGOTIATING, PipelineStage.LOST): [],

    # ── Unanet 98-Awarded-Contract Vehicle ───────────────────────────────────
    # For IDIQ/GWAC vehicle awards — different lifecycle than task orders
    (PipelineStage.SUBMITTED, PipelineStage.CONTRACT_VEHICLE_WON): [],
    (PipelineStage.NEGOTIATING, PipelineStage.CONTRACT_VEHICLE_WON): [],

    # ── Unanet 99-Completed Contract Vehicle ─────────────────────────────────
    (PipelineStage.CONTRACT_VEHICLE_WON, PipelineStage.CONTRACT_VEHICLE_COMPLETE): [],

    # ── Unanet 20-Closed Other Reason ────────────────────────────────────────
    # Any active stage → CANCELLED (solicitation cancelled, scope changed, etc.)
    (PipelineStage.IDENTIFIED, PipelineStage.CANCELLED): [],
    (PipelineStage.QUALIFYING, PipelineStage.CANCELLED): [],
    (PipelineStage.LONG_LEAD, PipelineStage.CANCELLED): [],
    (PipelineStage.BID_DECISION, PipelineStage.CANCELLED): [],
    (PipelineStage.ACTIVE, PipelineStage.CANCELLED): [],
    (PipelineStage.SUBMITTED, PipelineStage.CANCELLED): [],
    (PipelineStage.NEGOTIATING, PipelineStage.CANCELLED): [],
}

# Stages that trigger a hotwash event after transition
HOTWASH_TRIGGER_STAGES = {
    PipelineStage.AWARDED,
    PipelineStage.LOST,
    PipelineStage.NO_BID,
    PipelineStage.CONTRACT_VEHICLE_WON,
}

# Terminal stages — no further transitions expected
TERMINAL_STAGES = {
    PipelineStage.AWARDED,
    PipelineStage.LOST,
    PipelineStage.NO_BID,
    PipelineStage.CANCELLED,
    PipelineStage.CONTRACT_VEHICLE_COMPLETE,
}

# Stages that map to "open / active pursuit" for pipeline health reporting
ACTIVE_PURSUIT_STAGES = {
    PipelineStage.IDENTIFIED,
    PipelineStage.QUALIFYING,
    PipelineStage.LONG_LEAD,
    PipelineStage.BID_DECISION,
    PipelineStage.ACTIVE,
    PipelineStage.SUBMITTED,
    PipelineStage.NEGOTIATING,
}


class TransitionError(ValueError):
    """Raised when a stage transition is invalid or missing required data."""
    pass


def validate_transition(
    proposal: Proposal,
    target_stage: PipelineStage,
) -> List[str]:
    """
    Validate a proposed stage transition.

    Args:
        proposal: Current proposal state.
        target_stage: The stage to transition to.

    Returns:
        List[str]: List of missing required fields (empty = transition valid).
    """
    key = (proposal.pipeline_stage, target_stage)
    if key not in VALID_TRANSITIONS:
        raise TransitionError(
            f"Invalid transition: {proposal.pipeline_stage} → {target_stage}. "
            f"Valid next stages: {get_valid_next_stages(proposal.pipeline_stage)}"
        )

    required = VALID_TRANSITIONS[key]
    missing = []
    for field in required:
        value = getattr(proposal, field, None)
        if not value:
            missing.append(field)
        # Special case: bid_decision must not be PENDING for BID_DECISION → ACTIVE
        if field == "bid_decision" and value == BidDecision.PENDING:
            missing.append("bid_decision (must be 'bid', not 'pending')")

    return missing


def advance_stage(
    proposal: Proposal,
    target_stage: PipelineStage,
    notes: Optional[str] = None,
    force: bool = False,
) -> Proposal:
    """
    Transition a proposal to a new pipeline stage.

    Args:
        proposal: Current proposal state.
        target_stage: The stage to transition to.
        notes: Optional notes to append about this transition.
        force: Skip required-field validation (admin use only).

    Returns:
        Proposal: Updated proposal with new pipeline_stage and updated_at.

    Raises:
        TransitionError: If transition is invalid or required fields missing.
    """
    if not force:
        missing = validate_transition(proposal, target_stage)
        if missing:
            raise TransitionError(
                f"Cannot advance to {target_stage}: missing required fields: "
                f"{', '.join(missing)}"
            )

    now = datetime.now().isoformat()
    updated_notes = proposal.notes
    if notes:
        updated_notes = f"{updated_notes}\n[{now}] Stage {proposal.pipeline_stage} → {target_stage}: {notes}".strip()

    # Return a new Proposal with updated fields (immutable update pattern)
    return proposal.model_copy(update={
        "pipeline_stage": target_stage,
        "updated_at": now,
        "notes": updated_notes,
    })


def get_valid_next_stages(current: PipelineStage) -> List[PipelineStage]:
    """
    Return all valid next stages from the current stage.

    Args:
        current: Current pipeline stage.

    Returns:
        List[PipelineStage]: Valid next stages.
    """
    return [
        to_stage
        for (from_stage, to_stage) in VALID_TRANSITIONS
        if from_stage == current
    ]


def pipeline_summary(proposals: List[Proposal]) -> Dict[str, int]:
    """
    Summarize proposals by pipeline stage.

    Args:
        proposals: List of proposal objects.

    Returns:
        Dict[str, int]: Stage → count mapping.
    """
    summary: Dict[str, int] = {stage.value: 0 for stage in PipelineStage}
    for p in proposals:
        summary[p.pipeline_stage.value] += 1
    return summary


def overdue_proposals(proposals: List[Proposal]) -> List[Proposal]:
    """
    Find proposals whose due date has passed and are not yet submitted.

    Args:
        proposals: List of proposal objects.

    Returns:
        List[Proposal]: Proposals past their due date.
    """
    active_stages = {
        PipelineStage.IDENTIFIED,
        PipelineStage.QUALIFYING,
        PipelineStage.LONG_LEAD,
        PipelineStage.BID_DECISION,
        PipelineStage.ACTIVE,
    }
    now = datetime.now()
    overdue = []
    for p in proposals:
        if p.pipeline_stage not in active_stages:
            continue
        if not p.proposal_due_date:
            continue
        due = datetime.fromisoformat(p.proposal_due_date)
        if due < now:
            overdue.append(p)
    return overdue


def due_soon(proposals: List[Proposal], days: int = 14) -> List[Proposal]:
    """
    Find active proposals with a due date within the next N days.

    Args:
        proposals: List of proposal objects.
        days: Lookahead window in days (default 14).

    Returns:
        List[Proposal]: Proposals due soon, sorted by due date.
    """
    active_stages = {PipelineStage.ACTIVE, PipelineStage.BID_DECISION, PipelineStage.SUBMITTED}
    results = []
    for p in proposals:
        if p.pipeline_stage not in active_stages:
            continue
        days_left = p.days_until_due()
        if days_left is not None and 0 <= days_left <= days:
            results.append(p)
    return sorted(results, key=lambda p: p.proposal_due_date or "")
