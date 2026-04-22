"""
server/routes/proposal_drafts.py — REST handlers for the proposal writing module.

URL layout:
  GET/POST   /api/proposal-docs                              list / create documents
  GET/PUT/DELETE /api/proposal-docs/{doc_id}                 get / update / delete document
  GET        /api/proposal-docs/{doc_id}/sections            section tree
  POST       /api/proposal-docs/{doc_id}/sections            create section
  POST       /api/proposal-docs/{doc_id}/apply-template      apply built-in template
  GET/PUT/DELETE /api/proposal-sections/{sec_id}             get / update / delete section
  GET        /api/proposal-sections/{sec_id}/versions        list versions
  POST       /api/proposal-sections/{sec_id}/versions        create manual version
  POST       /api/proposal-sections/{sec_id}/restore/{ver_id} restore version
  GET        /api/proposal-sections/{sec_id}/comments        list comments
  POST       /api/proposal-sections/{sec_id}/comments        add comment
  PUT/DELETE /api/proposal-comments/{cmt_id}                 update / delete comment
  POST       /api/proposal-comments/{cmt_id}/resolve         resolve comment
  POST       /api/proposal-sections/{sec_id}/llm             run LLM action
  GET        /api/proposal-doc-types                         list doc types
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from server.utils.error_handler import error_handler

logger = logging.getLogger(__name__)

try:
    from proposal.drafts_db import (
        create_document, get_document, list_documents, update_document, delete_document,
        create_section, get_section, update_section, delete_section,
        create_version, list_versions, get_version, restore_version,
        create_comment, get_comment, list_comments, resolve_comment,
        delete_comment, update_comment,
        run_drafts_migration,
    )
    from proposal.drafts_templates import apply_template, list_doc_types
    from proposal.llm_writer import run_llm_action, list_actions, ProposalWriteContext
    run_drafts_migration()
    DRAFTS_AVAILABLE = True
except ImportError as _exc:
    logger.warning("proposal.drafts package not available: %s", _exc)
    DRAFTS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unavailable(handler) -> None:
    """Return 503 when the drafts module is unavailable."""
    handler.send_json_response({"error": "Proposal drafts module not available"}, 503)


def _body(handler) -> Dict[str, Any]:
    """Parse JSON request body, returning empty dict on failure."""
    try:
        b = handler.get_request_body()
        return b if isinstance(b, dict) else {}
    except Exception:
        return {}


def _last(path: str) -> str:
    """Return the last non-empty path segment (strips query string first)."""
    return path.split("?")[0].rstrip("/").rsplit("/", 1)[-1]


def _second_last(path: str) -> str:
    """Return the second-to-last path segment."""
    parts = path.split("?")[0].rstrip("/").rsplit("/", 2)
    return parts[-2] if len(parts) >= 2 else ""


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_docs_list(handler) -> None:
    """GET /api/proposal-docs  — list documents for a proposal."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    import urllib.parse
    params = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    proposal_id = params.get("proposal_id", [None])[0]
    if not proposal_id:
        handler.send_json_response({"error": "proposal_id query param required"}, 400)
        return
    docs = list_documents(proposal_id)
    handler.send_json_response({"documents": docs, "count": len(docs)})


@error_handler
def handle_proposal_docs_create(handler) -> None:
    """POST /api/proposal-docs  — create a new proposal document."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    data = _body(handler)
    proposal_id = data.get("proposal_id", "").strip()
    doc_type = data.get("doc_type", "").strip()
    title = data.get("title", "").strip()
    if not proposal_id or not doc_type or not title:
        handler.send_json_response(
            {"error": "proposal_id, doc_type, and title are required"}, 400
        )
        return
    doc = create_document(
        proposal_id=proposal_id,
        doc_type=doc_type,
        title=title,
        word_limit=data.get("word_limit"),
        description=data.get("description", ""),
        created_by=data.get("created_by", ""),
    )
    handler.send_json_response({"document": doc}, 201)


@error_handler
def handle_proposal_doc_detail(handler) -> None:
    """GET /api/proposal-docs/{doc_id}  — fetch document with section tree."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _last(handler.path)
    doc = get_document(doc_id)
    if doc is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return
    handler.send_json_response({"document": doc})


@error_handler
def handle_proposal_doc_update(handler) -> None:
    """PUT /api/proposal-docs/{doc_id}  — update document metadata."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _last(handler.path)
    data = _body(handler)
    doc = update_document(doc_id, **data)
    if doc is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return
    handler.send_json_response({"document": doc})


@error_handler
def handle_proposal_doc_delete(handler) -> None:
    """DELETE /api/proposal-docs/{doc_id}  — delete a document."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _last(handler.path)
    deleted = delete_document(doc_id)
    if not deleted:
        handler.send_json_response({"error": "Document not found"}, 404)
        return
    handler.send_json_response({"status": "deleted"})


@error_handler
def handle_proposal_doc_sections(handler) -> None:
    """GET /api/proposal-docs/{doc_id}/sections  — return section tree."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _second_last(handler.path)
    doc = get_document(doc_id, include_sections=True)
    if doc is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return
    handler.send_json_response({"sections": doc.get("sections", [])})


@error_handler
def handle_proposal_doc_section_create(handler) -> None:
    """POST /api/proposal-docs/{doc_id}/sections  — add a section to a document."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _second_last(handler.path)
    data = _body(handler)
    title = data.get("title", "").strip()
    if not title:
        handler.send_json_response({"error": "title is required"}, 400)
        return
    sec = create_section(
        document_id=doc_id,
        title=title,
        parent_id=data.get("parent_id"),
        section_number=data.get("section_number", ""),
        content=data.get("content", ""),
        guidance=data.get("guidance", ""),
        owner=data.get("owner", ""),
        sort_order=int(data.get("sort_order", 0)),
    )
    handler.send_json_response({"section": sec}, 201)


@error_handler
def handle_proposal_doc_apply_template(handler) -> None:
    """POST /api/proposal-docs/{doc_id}/apply-template — stamp a template onto document."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _second_last(handler.path)
    data = _body(handler)
    doc_type = data.get("doc_type", "").strip()
    if not doc_type:
        # Derive from the document record if not provided
        doc = get_document(doc_id, include_sections=False)
        if doc:
            doc_type = doc.get("doc_type", "")
    if not doc_type:
        handler.send_json_response({"error": "doc_type required"}, 400)
        return
    try:
        sections = apply_template(doc_id, doc_type, owner=data.get("owner", ""))
    except ValueError as exc:
        handler.send_json_response({"error": str(exc)}, 400)
        return
    handler.send_json_response({"sections_created": len(sections), "sections": sections})


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_section_detail(handler) -> None:
    """GET /api/proposal-sections/{sec_id}  — fetch a section."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    sec = get_section(_last(handler.path))
    if sec is None:
        handler.send_json_response({"error": "Section not found"}, 404)
        return
    handler.send_json_response({"section": sec})


@error_handler
def handle_proposal_section_update(handler) -> None:
    """PUT /api/proposal-sections/{sec_id}  — update section content / metadata."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    sec_id = _last(handler.path)
    data = _body(handler)
    sec = update_section(sec_id, **data)
    if sec is None:
        handler.send_json_response({"error": "Section not found"}, 404)
        return
    handler.send_json_response({"section": sec})


@error_handler
def handle_proposal_section_delete(handler) -> None:
    """DELETE /api/proposal-sections/{sec_id}  — delete a section."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    deleted = delete_section(_last(handler.path))
    if not deleted:
        handler.send_json_response({"error": "Section not found"}, 404)
        return
    handler.send_json_response({"status": "deleted"})


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_section_versions_list(handler) -> None:
    """GET /api/proposal-sections/{sec_id}/versions"""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    sec_id = _second_last(handler.path)
    handler.send_json_response({"versions": list_versions(sec_id)})


@error_handler
def handle_proposal_section_versions_create(handler) -> None:
    """POST /api/proposal-sections/{sec_id}/versions — manual snapshot."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    sec_id = _second_last(handler.path)
    data = _body(handler)
    sec = get_section(sec_id)
    if sec is None:
        handler.send_json_response({"error": "Section not found"}, 404)
        return
    content = data.get("content", sec.get("content", ""))
    ver = create_version(
        sec_id, content,
        review_stage=data.get("review_stage", "draft"),
        created_by=data.get("created_by", ""),
        change_summary=data.get("change_summary", ""),
    )
    handler.send_json_response({"version": ver}, 201)


@error_handler
def handle_proposal_section_restore(handler) -> None:
    """POST /api/proposal-sections/{sec_id}/restore/{ver_id}"""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    # path: /api/proposal-sections/{sec_id}/restore/{ver_id}
    parts = handler.path.split("?")[0].rstrip("/").rsplit("/", 3)
    # parts[-1] = ver_id, parts[-3] = sec_id
    ver_id = parts[-1]
    sec_id = parts[-3]
    data = _body(handler)
    sec = restore_version(sec_id, ver_id, restored_by=data.get("restored_by", ""))
    if sec is None:
        handler.send_json_response({"error": "Version or section not found"}, 404)
        return
    handler.send_json_response({"section": sec})


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_section_comments_list(handler) -> None:
    """GET /api/proposal-sections/{sec_id}/comments"""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    import urllib.parse
    params = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    include_resolved = params.get("include_resolved", ["true"])[0].lower() != "false"
    sec_id = _second_last(handler.path)
    handler.send_json_response({"comments": list_comments(sec_id, include_resolved)})


@error_handler
def handle_proposal_section_comments_create(handler) -> None:
    """POST /api/proposal-sections/{sec_id}/comments"""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    sec_id = _second_last(handler.path)
    data = _body(handler)
    author = data.get("author", "").strip()
    content = data.get("content", "").strip()
    if not author or not content:
        handler.send_json_response({"error": "author and content are required"}, 400)
        return
    cmt = create_comment(
        section_id=sec_id,
        author=author,
        content=content,
        comment_type=data.get("comment_type", "comment"),
        review_stage=data.get("review_stage", ""),
        parent_comment_id=data.get("parent_comment_id"),
        anchor_start=data.get("anchor_start"),
        anchor_end=data.get("anchor_end"),
        anchor_text=data.get("anchor_text", ""),
        suggested_replacement=data.get("suggested_replacement", ""),
    )
    handler.send_json_response({"comment": cmt}, 201)


@error_handler
def handle_proposal_comment_update(handler) -> None:
    """PUT /api/proposal-comments/{cmt_id}"""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    cmt_id = _last(handler.path)
    data = _body(handler)
    content = data.get("content", "").strip()
    if not content:
        handler.send_json_response({"error": "content is required"}, 400)
        return
    cmt = update_comment(cmt_id, content)
    if cmt is None:
        handler.send_json_response({"error": "Comment not found"}, 404)
        return
    handler.send_json_response({"comment": cmt})


@error_handler
def handle_proposal_comment_delete(handler) -> None:
    """DELETE /api/proposal-comments/{cmt_id}"""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    deleted = delete_comment(_last(handler.path))
    if not deleted:
        handler.send_json_response({"error": "Comment not found"}, 404)
        return
    handler.send_json_response({"status": "deleted"})


@error_handler
def handle_proposal_comment_resolve(handler) -> None:
    """POST /api/proposal-comments/{cmt_id}/resolve"""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    cmt_id = _second_last(handler.path)
    data = _body(handler)
    cmt = resolve_comment(cmt_id, resolved_by=data.get("resolved_by", ""))
    if cmt is None:
        handler.send_json_response({"error": "Comment not found"}, 404)
        return
    handler.send_json_response({"comment": cmt})


# ---------------------------------------------------------------------------
# LLM action
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_section_llm(handler) -> None:
    """
    POST /api/proposal-sections/{sec_id}/llm

    Body:
      action              str   plan | draft | improve | respond_comments | compliance_check
      proposal_title      str
      win_themes          list[str]   optional
      compliance_requirements list[str]  optional (for compliance_check)
      model               str   optional, default 'llama3'
    """
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    sec_id = _second_last(handler.path)
    sec = get_section(sec_id)
    if sec is None:
        handler.send_json_response({"error": "Section not found"}, 404)
        return
    data = _body(handler)
    action = data.get("action", "draft").strip()
    # Fetch open comments if needed
    open_comments: list = []
    if action == "respond_comments":
        open_comments = list_comments(sec_id, include_resolved=False)

    ctx = ProposalWriteContext(
        proposal_title=data.get("proposal_title", ""),
        doc_type=data.get("doc_type", ""),
        section_title=sec["title"],
        section_number=sec.get("section_number", ""),
        current_content=sec.get("content", ""),
        guidance=sec.get("guidance", ""),
        win_themes=data.get("win_themes", []),
        open_comments=open_comments,
        compliance_requirements=data.get("compliance_requirements", []),
        word_limit=data.get("word_limit"),
        model=data.get("model", "llama3"),
    )
    try:
        result_text = run_llm_action(action, ctx)
    except ValueError as exc:
        handler.send_json_response({"error": str(exc)}, 400)
        return
    handler.send_json_response({"action": action, "result": result_text})


# ---------------------------------------------------------------------------
# DOCX export
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_doc_export(handler) -> None:
    """
    GET /api/proposal-docs/{doc_id}/export

    Stream the document as a downloadable .docx file.
    Returns 503 if python-docx is not installed.
    """
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _second_last(handler.path)
    try:
        from proposal.drafts_exporter import export_document_docx
    except ImportError:
        handler.send_json_response(
            {"error": "python-docx is not installed; run: uv add python-docx"}, 503
        )
        return
    docx_bytes = export_document_docx(doc_id)
    if docx_bytes is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return
    # Derive a safe filename from the document title
    doc = get_document(doc_id, include_sections=False)
    safe_title = (doc or {}).get("title", "proposal_document")
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in safe_title).strip()
    filename = f"{safe_title}.docx"
    handler.send_response(200)
    handler.send_header("Content-Type",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(docx_bytes)))
    handler.end_headers()
    handler.wfile.write(docx_bytes)


# ---------------------------------------------------------------------------
# Stage snapshot
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_doc_stage_snapshot(handler) -> None:
    """
    POST /api/proposal-docs/{doc_id}/stage-snapshot

    Snapshot every section in the document at the current review stage.
    Useful at color-team gates (pink, red, gold, final).

    Body:
      review_stage   str   pink | red | gold | final | draft
      created_by     str   optional author label
      change_summary str   optional description
    """
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    doc_id = _second_last(handler.path)
    doc = get_document(doc_id, include_sections=True)
    if doc is None:
        handler.send_json_response({"error": "Document not found"}, 404)
        return
    data = _body(handler)
    review_stage = data.get("review_stage", "draft").strip()
    created_by = data.get("created_by", "").strip()
    change_summary = data.get("change_summary", f"Stage snapshot: {review_stage}").strip()

    # Flatten section tree
    def _flat(sections):
        out = []
        for s in sections:
            out.append(s)
            out.extend(_flat(s.get("children") or []))
        return out

    flat = _flat(doc.get("sections") or [])
    versions = []
    for sec in flat:
        if sec.get("content", "").strip():
            ver = create_version(
                sec["id"],
                sec["content"],
                review_stage=review_stage,
                created_by=created_by,
                change_summary=change_summary,
            )
            versions.append(ver)

    handler.send_json_response({
        "status": "ok",
        "review_stage": review_stage,
        "sections_snapshotted": len(versions),
        "versions": versions,
    }, 201)


# ---------------------------------------------------------------------------
# Doc types catalog
# ---------------------------------------------------------------------------

@error_handler
def handle_proposal_doc_types(handler) -> None:
    """GET /api/proposal-doc-types  — list available document types."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response({"doc_types": list_doc_types()})


@error_handler
def handle_proposal_llm_actions(handler) -> None:
    """GET /api/proposal-llm-actions  — list available LLM actions."""
    if not DRAFTS_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response({"actions": list_actions()})
