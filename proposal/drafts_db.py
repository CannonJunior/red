"""
proposal/drafts_db.py — Proposal document drafting database layer.

Manages four tables that live alongside the existing proposals table:
  proposal_documents  — one per volume / document type per proposal
  proposal_sections   — hierarchical section tree within a document
  section_versions    — point-in-time snapshots for local version control
  proposal_comments   — inline review comments anchored to sections

All functions follow the project's get_conn() context-manager pattern.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from proposal.database import get_conn

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

DRAFTS_DDL = """
CREATE TABLE IF NOT EXISTS proposal_documents (
    id              TEXT PRIMARY KEY,
    proposal_id     TEXT NOT NULL,
    doc_type        TEXT NOT NULL,
    title           TEXT NOT NULL,
    status          TEXT DEFAULT 'draft',
    word_limit      INTEGER,
    description     TEXT DEFAULT '',
    created_by      TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS proposal_sections (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL,
    parent_id       TEXT,
    section_number  TEXT DEFAULT '',
    title           TEXT NOT NULL,
    content         TEXT DEFAULT '',
    owner           TEXT DEFAULT '',
    guidance        TEXT DEFAULT '',
    word_count      INTEGER DEFAULT 0,
    sort_order      INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'empty',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES proposal_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id)   REFERENCES proposal_sections(id)  ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS section_versions (
    id             TEXT PRIMARY KEY,
    section_id     TEXT NOT NULL,
    content        TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    review_stage   TEXT DEFAULT 'draft',
    created_by     TEXT DEFAULT '',
    change_summary TEXT DEFAULT '',
    word_count     INTEGER DEFAULT 0,
    created_at     TEXT NOT NULL,
    FOREIGN KEY (section_id) REFERENCES proposal_sections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS proposal_comments (
    id                   TEXT PRIMARY KEY,
    section_id           TEXT NOT NULL,
    parent_comment_id    TEXT,
    comment_type         TEXT DEFAULT 'comment',
    review_stage         TEXT DEFAULT '',
    author               TEXT NOT NULL,
    content              TEXT NOT NULL,
    anchor_start         INTEGER,
    anchor_end           INTEGER,
    anchor_text          TEXT DEFAULT '',
    suggested_replacement TEXT DEFAULT '',
    resolved             INTEGER DEFAULT 0,
    resolved_by          TEXT DEFAULT '',
    resolved_at          TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    FOREIGN KEY (section_id) REFERENCES proposal_sections(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_prop_docs_proposal ON proposal_documents(proposal_id);
CREATE INDEX IF NOT EXISTS idx_prop_sections_doc  ON proposal_sections(document_id);
CREATE INDEX IF NOT EXISTS idx_prop_sections_par  ON proposal_sections(parent_id);
CREATE INDEX IF NOT EXISTS idx_section_versions   ON section_versions(section_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_prop_comments_sec  ON proposal_comments(section_id);
"""


def run_drafts_migration() -> None:
    """
    Create drafting tables if they do not already exist.

    Safe to call on every server startup — all statements are idempotent.
    """
    with get_conn() as conn:
        conn.executescript(DRAFTS_DDL)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().isoformat()


def create_document(proposal_id: str, doc_type: str, title: str,
                    word_limit: Optional[int] = None,
                    description: str = "", created_by: str = "") -> Optional[Dict]:
    """
    Insert a new proposal document record.

    Args:
        proposal_id: Parent proposal ID.
        doc_type: Document type slug (technical_volume, cost_volume, sow, etc.).
        title: Human-readable document title.
        word_limit: Optional page/word limit from the RFP.
        description: Optional free-text notes.
        created_by: Author name or user ID.

    Returns:
        dict: The newly created document record.
    """
    doc_id = str(uuid.uuid4())
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO proposal_documents
               (id, proposal_id, doc_type, title, status, word_limit,
                description, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?)""",
            (doc_id, proposal_id, doc_type, title, word_limit,
             description, created_by, now, now),
        )
    return get_document(doc_id)


def get_document(doc_id: str, include_sections: bool = True) -> Optional[Dict]:
    """
    Fetch a document record, optionally including its full section tree.

    Args:
        doc_id: Document UUID.
        include_sections: If True, attach the nested section tree.

    Returns:
        dict or None if not found.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM proposal_documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if not row:
        return None
    doc = dict(row)
    if include_sections:
        doc["sections"] = _build_section_tree(doc_id)
    return doc


def list_documents(proposal_id: str) -> List[Dict]:
    """
    List all documents for a proposal (sections not included).

    Args:
        proposal_id: Parent proposal ID.

    Returns:
        list[dict]: Document records ordered by created_at.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM proposal_documents WHERE proposal_id = ? ORDER BY created_at",
            (proposal_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_document(doc_id: str, **fields) -> Optional[Dict]:
    """
    Update document metadata fields (title, status, word_limit, description).

    Args:
        doc_id: Document UUID.
        **fields: Keyword arguments for fields to update.

    Returns:
        Updated document dict or None.
    """
    allowed = {"title", "status", "word_limit", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_document(doc_id)
    updates["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in updates)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE proposal_documents SET {cols} WHERE id = ?",
            (*updates.values(), doc_id),
        )
    return get_document(doc_id)


def delete_document(doc_id: str) -> bool:
    """
    Delete a document and all its sections (CASCADE handles children).

    Args:
        doc_id: Document UUID.

    Returns:
        bool: True if a row was deleted.
    """
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM proposal_documents WHERE id = ?", (doc_id,)
        )
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _build_section_tree(document_id: str) -> List[Dict]:
    """Build nested section tree from flat table rows."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM proposal_sections
               WHERE document_id = ?
               ORDER BY sort_order, section_number""",
            (document_id,),
        ).fetchall()
    flat = [dict(r) for r in rows]
    by_id = {s["id"]: s for s in flat}
    roots: List[Dict] = []
    for s in flat:
        s["children"] = []
    for s in flat:
        pid = s.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(s)
        else:
            roots.append(s)
    return roots


def create_section(document_id: str, title: str,
                   parent_id: Optional[str] = None,
                   section_number: str = "", content: str = "",
                   guidance: str = "", owner: str = "",
                   sort_order: int = 0) -> Optional[Dict]:
    """
    Create a new section within a document.

    Args:
        document_id: Parent document UUID.
        title: Section heading text.
        parent_id: Parent section UUID for nested sections.
        section_number: e.g. "2.1.3"
        content: Initial markdown content.
        guidance: Template guidance text shown to writers.
        owner: Assigned writer name/ID.
        sort_order: Integer for ordering siblings.

    Returns:
        dict: The newly created section.
    """
    sec_id = str(uuid.uuid4())
    now = _now()
    wc = len(content.split()) if content.strip() else 0
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO proposal_sections
               (id, document_id, parent_id, section_number, title, content,
                guidance, owner, word_count, sort_order, status,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sec_id, document_id, parent_id, section_number, title, content,
             guidance, owner, wc, sort_order,
             "in_progress" if content.strip() else "empty",
             now, now),
        )
    return get_section(sec_id)


def get_section(section_id: str) -> Optional[Dict]:
    """Fetch a single section by ID."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM proposal_sections WHERE id = ?", (section_id,)
        ).fetchone()
    return dict(row) if row else None


def update_section(section_id: str, **fields) -> Optional[Dict]:
    """
    Update a section's content and/or metadata.

    Automatically recalculates word_count when content is updated
    and auto-saves a version snapshot (rate-limited to one per minute).

    Args:
        section_id: Section UUID.
        **fields: Fields to update (content, title, owner, status, sort_order,
                  parent_id, section_number).

    Returns:
        Updated section dict.
    """
    allowed = {"content", "title", "owner", "status", "sort_order",
               "parent_id", "section_number", "guidance"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_section(section_id)
    if "content" in updates:
        # Only recompute word_count when content actually changed.
        # Reason: avoids a redundant split+status update on no-op saves.
        current = get_section(section_id)
        if current is None or updates["content"] != current.get("content"):
            updates["word_count"] = len(updates["content"].split()) if updates["content"].strip() else 0
            if not updates.get("status"):
                updates["status"] = "draft" if updates["word_count"] > 0 else "empty"
        else:
            # Content unchanged — drop it from the update set to avoid a
            # spurious updated_at bump.
            del updates["content"]
            if not updates:
                return current
    updates["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in updates)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE proposal_sections SET {cols} WHERE id = ?",
            (*updates.values(), section_id),
        )
    # Auto-snapshot (rate-limited)
    if "content" in updates:
        _maybe_auto_snapshot(section_id, updates["content"])
    return get_section(section_id)


def delete_section(section_id: str) -> bool:
    """Delete a section and all its descendants."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM proposal_sections WHERE id = ?", (section_id,)
        )
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Version Control
# ---------------------------------------------------------------------------

def _maybe_auto_snapshot(section_id: str, content: str,
                          created_by: str = "auto") -> None:
    """
    Create a snapshot only if none exists in the last 60 seconds.

    Reason: prevents flooding the versions table on every keystroke while
    still capturing meaningful edit history during writing sessions.
    """
    with get_conn() as conn:
        row = conn.execute(
            """SELECT created_at FROM section_versions
               WHERE section_id = ? ORDER BY version_number DESC LIMIT 1""",
            (section_id,),
        ).fetchone()
    if row:
        last_ts = datetime.fromisoformat(row["created_at"])
        if (datetime.now() - last_ts).total_seconds() < 60:
            return
    create_version(section_id, content, created_by=created_by,
                   change_summary="Auto-save")


def create_version(section_id: str, content: str,
                   review_stage: str = "draft", created_by: str = "",
                   change_summary: str = "") -> Dict:
    """
    Manually snapshot a section's current content.

    Args:
        section_id: Section UUID.
        content: Content to snapshot (usually current section.content).
        review_stage: Review gate label (draft/pink/red/gold/final).
        created_by: Author name.
        change_summary: Human-readable description of changes.

    Returns:
        dict: The new version record.
    """
    ver_id = str(uuid.uuid4())
    now = _now()
    wc = len(content.split()) if content.strip() else 0
    with get_conn() as conn:
        row = conn.execute(
            """SELECT COALESCE(MAX(version_number), 0) AS n
               FROM section_versions WHERE section_id = ?""",
            (section_id,),
        ).fetchone()
        next_num = (row["n"] if row else 0) + 1
        conn.execute(
            """INSERT INTO section_versions
               (id, section_id, content, version_number, review_stage,
                created_by, change_summary, word_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ver_id, section_id, content, next_num, review_stage,
             created_by, change_summary, wc, now),
        )
    return {"id": ver_id, "section_id": section_id, "content": content,
            "version_number": next_num, "review_stage": review_stage,
            "created_by": created_by, "change_summary": change_summary,
            "word_count": wc, "created_at": now}


def list_versions(section_id: str) -> List[Dict]:
    """List all versions for a section, newest first (content excluded)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, section_id, version_number, review_stage, created_by,
                      change_summary, word_count, created_at
               FROM section_versions WHERE section_id = ?
               ORDER BY version_number DESC""",
            (section_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_version(version_id: str) -> Optional[Dict]:
    """Fetch a single version including its full content."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM section_versions WHERE id = ?", (version_id,)
        ).fetchone()
    return dict(row) if row else None


def restore_version(section_id: str, version_id: str,
                    restored_by: str = "") -> Optional[Dict]:
    """
    Restore a section to a previous version.

    Creates a new version snapshot of the current content first, then
    replaces section.content with the historical version's content.

    Args:
        section_id: Section UUID.
        version_id: Version UUID to restore.
        restored_by: Author name.

    Returns:
        Updated section dict, or None if version not found.
    """
    ver = get_version(version_id)
    if not ver:
        return None
    # Snapshot current state before overwriting
    current = get_section(section_id)
    if current and current["content"]:
        create_version(section_id, current["content"],
                       created_by=restored_by,
                       change_summary=f"Pre-restore snapshot (restoring v{ver['version_number']})")
    return update_section(section_id, content=ver["content"])


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def create_comment(section_id: str, author: str, content: str,
                   comment_type: str = "comment", review_stage: str = "",
                   parent_comment_id: Optional[str] = None,
                   anchor_start: Optional[int] = None,
                   anchor_end: Optional[int] = None,
                   anchor_text: str = "",
                   suggested_replacement: str = "") -> Optional[Dict]:
    """
    Add a comment to a section.

    Args:
        section_id: Section UUID.
        author: Commenter name or user ID.
        content: Comment text.
        comment_type: 'comment', 'suggestion', 'llm_response', or 'review'.
        review_stage: Color team stage that generated this comment.
        parent_comment_id: For threaded replies.
        anchor_start: Character offset of commented text.
        anchor_end: End of commented text range.
        anchor_text: The text being commented on (for display).
        suggested_replacement: Proposed text (for suggestions).

    Returns:
        dict: The newly created comment.
    """
    c_id = str(uuid.uuid4())
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO proposal_comments
               (id, section_id, parent_comment_id, comment_type, review_stage,
                author, content, anchor_start, anchor_end, anchor_text,
                suggested_replacement, resolved, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (c_id, section_id, parent_comment_id, comment_type, review_stage,
             author, content, anchor_start, anchor_end, anchor_text,
             suggested_replacement, now, now),
        )
    result = get_comment(c_id)
    if result is None:
        raise RuntimeError(f"create_comment: INSERT succeeded but fetch returned None for id={c_id}")
    return result


def get_comment(comment_id: str) -> Optional[Dict]:
    """Fetch a single comment by ID."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM proposal_comments WHERE id = ?", (comment_id,)
        ).fetchone()
    return dict(row) if row else None


def list_comments(section_id: str, include_resolved: bool = True) -> List[Dict]:
    """
    List all comments for a section as a threaded list.

    Args:
        section_id: Section UUID.
        include_resolved: If False, only returns open comments.

    Returns:
        list[dict]: Top-level comments with 'replies' list attached.
    """
    sql = "SELECT * FROM proposal_comments WHERE section_id = ?"
    params: list = [section_id]
    if not include_resolved:
        sql += " AND resolved = 0"
    sql += " ORDER BY created_at"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    flat = [dict(r) for r in rows]
    by_id = {c["id"]: c for c in flat}
    roots: List[Dict] = []
    for c in flat:
        c["replies"] = []
    for c in flat:
        pid = c.get("parent_comment_id")
        if pid and pid in by_id:
            by_id[pid]["replies"].append(c)
        else:
            roots.append(c)
    return roots


def resolve_comment(comment_id: str, resolved_by: str = "") -> Optional[Dict]:
    """Mark a comment as resolved."""
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """UPDATE proposal_comments
               SET resolved = 1, resolved_by = ?, resolved_at = ?, updated_at = ?
               WHERE id = ?""",
            (resolved_by, now, now, comment_id),
        )
    return get_comment(comment_id)


def delete_comment(comment_id: str) -> bool:
    """Delete a comment by ID."""
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM proposal_comments WHERE id = ?", (comment_id,)
        )
    return cur.rowcount > 0


def update_comment(comment_id: str, content: str) -> Optional[Dict]:
    """Edit a comment's text."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE proposal_comments SET content = ?, updated_at = ? WHERE id = ?",
            (content, _now(), comment_id),
        )
    return get_comment(comment_id)
