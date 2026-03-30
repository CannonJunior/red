"""
Proposals API route handlers.

Exposes the GovCon proposal lifecycle via HTTP REST endpoints:

    GET    /api/proposals                  — list proposals (with optional filters)
    POST   /api/proposals                  — create proposal
    GET    /api/proposals/{id}             — get proposal by ID
    PUT    /api/proposals/{id}             — update proposal fields
    DELETE /api/proposals/{id}             — delete proposal
    POST   /api/proposals/{id}/advance     — advance pipeline stage
    GET    /api/proposals/{id}/schedule    — get generated schedule
    POST   /api/proposals/{id}/folders     — create local folder structure
    GET    /api/proposals/{id}/bid-no-bid  — get B/NB assessment
    POST   /api/proposals/{id}/bid-no-bid  — run/save B/NB assessment

All handlers follow the existing server pattern: accept a handler object,
call handler.send_json_response(data, status_code).
"""

import json
import logging
import urllib.parse
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from proposal.database import (
        create_proposal,
        delete_proposal,
        get_proposal,
        get_bid_no_bid,
        list_proposals,
        run_migration,
        save_bid_no_bid,
        update_proposal,
    )
    from proposal.models import BidDecision, PipelineStage, Proposal
    from proposal.pipeline import (
        TransitionError,
        advance_stage,
        get_valid_next_stages,
        validate_transition,
    )
    from proposal.bid_no_bid import run_assessment, assessment_to_dict
    from proposal.folder_manager import create_proposal_folders, folder_summary
    from proposal.schedule_generator import generate_schedule, schedule_to_text

    # Ensure tables exist on import
    run_migration()
    PROPOSALS_AVAILABLE = True
except ImportError as _exc:
    logger.warning("proposal package not available: %s", _exc)
    PROPOSALS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unavailable(handler) -> None:
    """Return 503 when the proposal package cannot be imported."""
    handler.send_json_response({"error": "Proposal module not available"}, 503)


def _parse_path_id(path: str, prefix: str) -> str:
    """
    Extract the proposal ID from a URL path.

    Args:
        path: Full request path (e.g., "/api/proposals/abc-123/advance").
        prefix: Prefix to strip (e.g., "/api/proposals/").

    Returns:
        str: The proposal ID segment.
    """
    stripped = path[len(prefix):]
    return stripped.split("/")[0]


def _get_body(handler) -> Dict[str, Any]:
    """
    Read and parse the JSON request body.

    Args:
        handler: HTTP request handler with get_request_body() method.

    Returns:
        Dict: Parsed JSON body, or empty dict on failure.
    """
    try:
        body = handler.get_request_body()
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# GET /api/proposals
# ---------------------------------------------------------------------------

def handle_proposals_list_api(handler) -> None:
    """
    Handle GET /api/proposals — list proposals with optional filters.

    Query params: stage, agency, limit (default 100)
    """
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        parsed = urllib.parse.urlparse(handler.path)
        params = urllib.parse.parse_qs(parsed.query)

        stage_str = params.get("stage", [None])[0]
        agency = params.get("agency", [None])[0]
        limit = int(params.get("limit", ["100"])[0])

        stage = None
        if stage_str:
            try:
                stage = PipelineStage(stage_str)
            except ValueError:
                handler.send_json_response({"error": f"Invalid stage: {stage_str}"}, 400)
                return

        proposals = list_proposals(stage=stage, agency=agency, limit=limit)
        handler.send_json_response({
            "proposals": [p.model_dump() for p in proposals],
            "count": len(proposals),
        })
    except Exception as exc:
        logger.error("proposals list error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# POST /api/proposals
# ---------------------------------------------------------------------------

def handle_proposals_create_api(handler) -> None:
    """Handle POST /api/proposals — create a new proposal record."""
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        body = _get_body(handler)
        if not body.get("title"):
            handler.send_json_response({"error": "title is required"}, 400)
            return

        proposal = Proposal(**body)
        create_proposal(proposal)
        handler.send_json_response(proposal.model_dump(), 201)
    except Exception as exc:
        logger.error("proposals create error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 400)


# ---------------------------------------------------------------------------
# GET /api/proposals/{id}
# ---------------------------------------------------------------------------

def handle_proposals_detail_api(handler) -> None:
    """Handle GET /api/proposals/{id} — get a single proposal."""
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        proposal = get_proposal(proposal_id)
        if not proposal:
            handler.send_json_response({"error": "Proposal not found"}, 404)
            return

        data = proposal.model_dump()
        data["valid_next_stages"] = [s.value for s in get_valid_next_stages(proposal.pipeline_stage)]
        handler.send_json_response(data)
    except Exception as exc:
        logger.error("proposals detail error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# PUT /api/proposals/{id}
# ---------------------------------------------------------------------------

def handle_proposals_update_api(handler) -> None:
    """Handle PUT /api/proposals/{id} — update proposal fields."""
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        existing = get_proposal(proposal_id)
        if not existing:
            handler.send_json_response({"error": "Proposal not found"}, 404)
            return

        body = _get_body(handler)
        body.pop("id", None)  # Reason: never allow ID overwrite via PUT
        updated = existing.model_copy(update=body)
        update_proposal(updated)
        handler.send_json_response(updated.model_dump())
    except Exception as exc:
        logger.error("proposals update error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 400)


# ---------------------------------------------------------------------------
# DELETE /api/proposals/{id}
# ---------------------------------------------------------------------------

def handle_proposals_delete_api(handler) -> None:
    """Handle DELETE /api/proposals/{id} — delete a proposal record."""
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        deleted = delete_proposal(proposal_id)
        if not deleted:
            handler.send_json_response({"error": "Proposal not found"}, 404)
            return
        handler.send_json_response({"status": "deleted", "id": proposal_id})
    except Exception as exc:
        logger.error("proposals delete error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# POST /api/proposals/{id}/advance
# ---------------------------------------------------------------------------

def handle_proposals_advance_api(handler) -> None:
    """
    Handle POST /api/proposals/{id}/advance — advance pipeline stage.

    Body: { "stage": "active", "notes": "...", "force": false }
    """
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        proposal = get_proposal(proposal_id)
        if not proposal:
            handler.send_json_response({"error": "Proposal not found"}, 404)
            return

        body = _get_body(handler)
        stage_str = body.get("stage")
        if not stage_str:
            handler.send_json_response({"error": "stage is required"}, 400)
            return

        try:
            target_stage = PipelineStage(stage_str)
        except ValueError:
            handler.send_json_response({"error": f"Invalid stage: {stage_str}"}, 400)
            return

        notes = body.get("notes", "")
        force = bool(body.get("force", False))

        # Validate before advancing (unless force)
        if not force:
            missing = validate_transition(proposal, target_stage)
            if missing:
                handler.send_json_response({
                    "error": "Missing required fields for transition",
                    "missing_fields": missing,
                }, 422)
                return

        advanced = advance_stage(proposal, target_stage, notes=notes, force=force)
        update_proposal(advanced)
        handler.send_json_response({
            "status": "advanced",
            "previous_stage": proposal.pipeline_stage.value,
            "new_stage": advanced.pipeline_stage.value,
            "proposal": advanced.model_dump(),
        })
    except TransitionError as exc:
        handler.send_json_response({"error": str(exc)}, 422)
    except Exception as exc:
        logger.error("proposals advance error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# GET /api/proposals/{id}/schedule
# ---------------------------------------------------------------------------

def handle_proposals_schedule_api(handler) -> None:
    """Handle GET /api/proposals/{id}/schedule — return generated milestone schedule."""
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        proposal = get_proposal(proposal_id)
        if not proposal:
            handler.send_json_response({"error": "Proposal not found"}, 404)
            return

        if not proposal.proposal_due_date:
            handler.send_json_response({"error": "proposal_due_date not set"}, 422)
            return

        milestones = generate_schedule(proposal)
        text = schedule_to_text(milestones, proposal)
        handler.send_json_response({
            "solicitation_number": proposal.solicitation_number,
            "proposal_due_date": proposal.proposal_due_date,
            "milestones": [
                {
                    "name": m.name,
                    "date": m.date,
                    "days_before_due": m.days_before_due,
                    "owner": m.owner,
                    "notes": m.notes,
                }
                for m in milestones
            ],
            "text_summary": text,
        })
    except Exception as exc:
        logger.error("proposals schedule error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# POST /api/proposals/{id}/folders
# ---------------------------------------------------------------------------

def handle_proposals_folders_api(handler) -> None:
    """Handle POST /api/proposals/{id}/folders — create local folder structure."""
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        proposal = get_proposal(proposal_id)
        if not proposal:
            handler.send_json_response({"error": "Proposal not found"}, 404)
            return

        folders = create_proposal_folders(proposal)
        summary = folder_summary(proposal)
        handler.send_json_response({
            "status": "created",
            "root": str(folders["root"]),
            "folders": {k: str(v) for k, v in folders.items()},
            "summary": summary,
        }, 201)
    except Exception as exc:
        logger.error("proposals folders error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# GET/POST /api/proposals/{id}/bid-no-bid
# ---------------------------------------------------------------------------

def handle_proposals_bid_no_bid_get_api(handler) -> None:
    """Handle GET /api/proposals/{id}/bid-no-bid — retrieve existing assessment."""
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        assessment = get_bid_no_bid(proposal_id)
        if not assessment:
            handler.send_json_response({"error": "No B/NB assessment found"}, 404)
            return
        handler.send_json_response(assessment_to_dict(assessment))
    except Exception as exc:
        logger.error("proposals b/nb get error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 500)


def handle_proposals_bid_no_bid_post_api(handler) -> None:
    """
    Handle POST /api/proposals/{id}/bid-no-bid — run and save a B/NB assessment.

    Body:
        scores: {criterion_name: score, ...}    (optional — uses Claude if omitted)
        win_themes, discriminators, risks, mitigations: list[str]
        assessor: str
        final_decision: "bid"|"no_bid"|"conditional"
        decision_made_by: str
        rationale: str
        use_claude: bool  (default false — avoid accidental API charges)
    """
    if not PROPOSALS_AVAILABLE:
        return _unavailable(handler)
    try:
        proposal_id = _parse_path_id(handler.path, "/api/proposals/")
        proposal = get_proposal(proposal_id)
        if not proposal:
            handler.send_json_response({"error": "Proposal not found"}, 404)
            return

        body = _get_body(handler)
        final_dec_str = body.get("final_decision")
        final_decision = BidDecision(final_dec_str) if final_dec_str else None

        assessment = run_assessment(
            proposal,
            scores=body.get("scores"),
            win_themes=body.get("win_themes"),
            discriminators=body.get("discriminators"),
            risks=body.get("risks"),
            mitigations=body.get("mitigations"),
            assessor=body.get("assessor", ""),
            final_decision=final_decision,
            decision_made_by=body.get("decision_made_by", ""),
            rationale=body.get("rationale", ""),
            use_claude=bool(body.get("use_claude", False)),
            additional_context=body.get("additional_context", ""),
        )
        save_bid_no_bid(assessment)

        result = assessment_to_dict(assessment)
        handler.send_json_response(result, 201)
    except Exception as exc:
        logger.error("proposals b/nb post error: %s", exc)
        handler.send_json_response({"error": str(exc)}, 400)
