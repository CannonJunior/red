"""
server/routes/color_team.py — Color team review upload and compliance assessment endpoints.

Endpoints:
  POST /api/proposal-docs/{doc_id}/color-team-upload
      Accepts a multipart .docx upload; runs full ingestion pipeline.
      Form fields:
        file            .docx file (required)
        opportunity_id  str (required, for shredding requirement lookup)
        review_stage    str  pink|red|gold|final  (default: red)
        author_prefix   str  optional label, e.g. "Red Team"
        model           str  ollama model (default: llama3)

  GET /api/proposal-docs/{doc_id}/compliance-assessment
      Returns aggregated per-requirement ratings for all color-team comments.

  GET /api/proposal-docs/{doc_id}/color-team-comments
      Returns all color-team review comments for the document.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from server.utils.error_handler import error_handler
from server.background_jobs import job_store

logger = logging.getLogger(__name__)

try:
    from proposal.color_team import (
        ingest_color_team_review,
        get_document_compliance_assessment,
        run_color_team_migration,
        RATING_SCALE,
    )
    from proposal.drafts_db import get_document
    from proposal.database import get_conn
    run_color_team_migration()
    COLOR_TEAM_AVAILABLE = True
except ImportError as _exc:
    logger.warning("color_team module not available: %s", _exc)
    COLOR_TEAM_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unavailable(handler) -> None:
    handler.send_json_response({"error": "Color team module not available"}, 503)


def _last(path: str) -> str:
    return path.split("?")[0].rstrip("/").rsplit("/", 1)[-1]


def _second_last(path: str) -> str:
    parts = path.split("?")[0].rstrip("/").rsplit("/", 2)
    return parts[-2] if len(parts) >= 2 else ""


def _parse_cd_params(cd: str) -> Dict[str, str]:
    """Parse name= and filename= tokens from a Content-Disposition header value."""
    params: Dict[str, str] = {}
    for part in cd.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            params[k.strip().lower()] = v.strip().strip('"')
    return params


def _read_multipart(handler) -> Dict[str, Any]:
    """
    Parse a multipart/form-data POST using the stdlib email.message module.

    Replaces the deprecated cgi.FieldStorage approach (removed in Python 3.13).

    Returns:
        dict with keys:
          'file_bytes': bytes | None
          'filename': str
          'fields': dict of other text form fields
    """
    import email

    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", 0) or 0)
    body = handler.rfile.read(content_length)

    # email.message_from_bytes needs headers + blank line + body
    raw = f"Content-Type: {content_type}\r\n\r\n".encode() + body
    msg = email.message_from_bytes(raw)

    result: Dict[str, Any] = {"file_bytes": None, "filename": "", "fields": {}}
    if not msg.is_multipart():
        return result

    parts = msg.get_payload()
    if not isinstance(parts, list):
        return result

    for part in parts:
        cd = part.get("Content-Disposition", "")  # type: ignore[union-attr]
        params = _parse_cd_params(cd)
        name = params.get("name", "")
        filename = params.get("filename", "")
        payload: bytes = (part.get_payload(decode=True) or b"")  # type: ignore[union-attr]
        if filename:
            result["file_bytes"] = payload
            result["filename"] = filename
        elif name:
            result["fields"][name] = payload.decode("utf-8", errors="replace")

    return result


# ---------------------------------------------------------------------------
# Background wrapper — called by job_store.submit_with_id
# ---------------------------------------------------------------------------

def _run_ingest_with_job_id(
    job_id: str,
    doc_id: str,
    opportunity_id: str,
    docx_bytes: bytes,
    review_stage: str,
    author_prefix: str,
    model: str,
) -> dict:
    """
    Thin wrapper that forwards the job_id into ingest_color_team_review
    so progress updates are recorded in the job store.

    Imports ingest_color_team_review locally so this function works even
    when called from a background thread after module load.
    """
    from proposal.color_team import ingest_color_team_review as _ingest
    return _ingest(
        document_id=doc_id,
        opportunity_id=opportunity_id,
        docx_bytes=docx_bytes,
        review_stage=review_stage,
        author_prefix=author_prefix,
        model=model,
        job_id=job_id,
    )


# ---------------------------------------------------------------------------
# GET /api/color-team-jobs/{job_id}
# ---------------------------------------------------------------------------

@error_handler
def handle_color_team_job_status(handler) -> None:
    """
    Poll a color-team ingestion job.

    Response when running:
      {"status": "running", "progress": "Processing comment 3/10", ...}

    Response when done:
      {"status": "done", "result": {ingested, skipped, comments, assessment}}

    Response when failed:
      {"status": "error", "error": "..."}
    """
    job_id = _last(handler.path)
    job = job_store.get(job_id)
    if job is None:
        handler.send_json_response({"error": "Job not found"}, 404)
        return
    handler.send_json_response(job)


# ---------------------------------------------------------------------------
# POST /api/proposal-docs/{doc_id}/color-team-upload
# ---------------------------------------------------------------------------

@error_handler
def handle_color_team_upload(handler) -> None:
    """
    Accept a reviewer's marked-up .docx and ingest all comments.

    Expects multipart/form-data with fields:
      file            — the .docx file
      opportunity_id  — for shredding requirement lookup (optional but recommended)
      review_stage    — pink | red | gold | final  (default: red)
      author_prefix   — label prepended to reviewer names (e.g. "Red Team")
      model           — ollama model (default: llama3)
    """
    if not COLOR_TEAM_AVAILABLE:
        return _unavailable(handler)

    doc_id = _second_last(handler.path)
    doc = get_document(doc_id, include_sections=False)
    if doc is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return

    content_type = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        handler.send_json_response(
            {"error": "Expected multipart/form-data upload"}, 400
        )
        return

    parsed = _read_multipart(handler)
    docx_bytes = parsed["file_bytes"]
    if not docx_bytes:
        handler.send_json_response({"error": "No .docx file found in upload"}, 400)
        return
    if not parsed["filename"].endswith(".docx"):
        handler.send_json_response(
            {"error": "Only .docx files are supported"}, 400
        )
        return

    fields = parsed["fields"]
    opportunity_id = fields.get("opportunity_id", "")
    review_stage = fields.get("review_stage", "red").lower()
    author_prefix = fields.get("author_prefix", "")
    model = fields.get("model", "llama3")

    if review_stage not in ("pink", "red", "gold", "final"):
        review_stage = "red"

    # Submit to background thread — returns immediately with a job_id.
    # submit_with_id passes the job_id as the first arg to the wrapper so
    # ingest_color_team_review can report per-comment progress.
    job_id = job_store.submit_with_id(
        _run_ingest_with_job_id,
        doc_id, opportunity_id, docx_bytes, review_stage, author_prefix, model,
    )

    handler.send_json_response({
        "status": "accepted",
        "job_id": job_id,
        "document_id": doc_id,
        "filename": parsed["filename"],
        "review_stage": review_stage,
        "message": "Color team ingestion started. Poll /api/color-team-jobs/{job_id} for results.",
    }, 202)


# ---------------------------------------------------------------------------
# GET /api/proposal-docs/{doc_id}/compliance-assessment
# ---------------------------------------------------------------------------

@error_handler
def handle_compliance_assessment(handler) -> None:
    """
    Return a per-requirement compliance assessment for the document.

    Aggregates all color-team review comments, worst-rating wins per requirement.
    Also includes an overall document rating summary.
    """
    if not COLOR_TEAM_AVAILABLE:
        return _unavailable(handler)

    doc_id = _second_last(handler.path)
    doc = get_document(doc_id, include_sections=False)
    if doc is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return

    assessment = get_document_compliance_assessment(doc_id)
    summary = _summarise_assessment(assessment)

    handler.send_json_response({
        "document_id": doc_id,
        "assessment": assessment,
        "summary": summary,
        "rating_scale": RATING_SCALE,
    })


def _summarise_assessment(assessment: list) -> Dict:
    """Count requirements by worst rating."""
    counts: Dict[str, int] = {r: 0 for r in RATING_SCALE}
    for entry in assessment:
        rating = entry.get("worst_rating", "Acceptable")
        counts[rating] = counts.get(rating, 0) + 1
    total = sum(counts.values())
    return {"total_requirements": total, "by_rating": counts}


# ---------------------------------------------------------------------------
# GET /api/proposal-docs/{doc_id}/color-team-export
# ---------------------------------------------------------------------------

@error_handler
def handle_color_team_export(handler) -> None:
    """
    Export a proposal document with color-team comments embedded inline as .docx.

    Optional query param:
      review_stage  pink | red | gold | final  (default: all stages)
    """
    if not COLOR_TEAM_AVAILABLE:
        return _unavailable(handler)

    import urllib.parse
    params = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    stage_filter = params.get("review_stage", [None])[0]

    doc_id = _second_last(handler.path)
    doc = get_document(doc_id, include_sections=False)
    if doc is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return

    try:
        from proposal.color_team import export_color_team_docx
    except ImportError:
        handler.send_json_response(
            {"error": "python-docx is not installed; run: uv add python-docx"}, 503
        )
        return

    docx_bytes = export_color_team_docx(doc_id, review_stage=stage_filter)
    if docx_bytes is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return

    safe_title = (doc or {}).get("title", "color_team_review")
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in safe_title).strip()
    suffix = f"_{stage_filter}" if stage_filter else ""
    filename = f"{safe_title}{suffix}_review.docx"

    handler.send_response(200)
    handler.send_header("Content-Type",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(docx_bytes)))
    handler.end_headers()
    handler.wfile.write(docx_bytes)


# ---------------------------------------------------------------------------
# GET /api/proposal-docs/{doc_id}/color-team-comments
# ---------------------------------------------------------------------------

@error_handler
def handle_color_team_comments(handler) -> None:
    """
    List all color-team review comments for a document, across all sections.

    Optionally filter by review_stage query param.
    """
    if not COLOR_TEAM_AVAILABLE:
        return _unavailable(handler)

    import urllib.parse
    params = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    stage_filter = params.get("review_stage", [None])[0]

    doc_id = _second_last(handler.path)

    with get_conn() as conn:
        sql = """
            SELECT pc.*
            FROM proposal_comments pc
            JOIN proposal_sections ps ON pc.section_id = ps.id
            WHERE ps.document_id = ?
              AND pc.comment_type = 'color_team_review'
        """
        args: list = [doc_id]
        if stage_filter:
            sql += " AND pc.review_stage = ?"
            args.append(stage_filter)
        sql += " ORDER BY pc.created_at"
        rows = conn.execute(sql, args).fetchall()

    handler.send_json_response({
        "document_id": doc_id,
        "comments": [dict(r) for r in rows],
        "count": len(rows),
    })
