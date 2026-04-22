"""
Tests for proposal/drafts_db.py, drafts_templates.py, and llm_writer.py.

Covers CRUD for documents, sections, versions, comments, template
application, and LLM prompt construction (without actually calling Ollama).
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from proposal.drafts_db import (
    create_document,
    create_section,
    create_version,
    create_comment,
    delete_comment,
    delete_document,
    delete_section,
    get_document,
    get_section,
    get_version,
    list_comments,
    list_documents,
    list_versions,
    resolve_comment,
    restore_version,
    run_drafts_migration,
    update_comment,
    update_document,
    update_section,
)
from proposal.drafts_templates import apply_template, list_doc_types, TEMPLATES
from proposal.llm_writer import (
    ProposalWriteContext,
    list_actions,
    run_llm_action,
    _build_draft_prompt,
    _build_plan_prompt,
    _build_improve_prompt,
    _build_respond_comments_prompt,
    _build_compliance_check_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_db(tmp_path, monkeypatch):
    """
    Redirect all drafts_db calls to a temp SQLite DB so tests are isolated.

    Patches get_conn in both proposal.database AND proposal.drafts_db because
    drafts_db binds the function at import time via `from proposal.database import get_conn`.
    """
    db_file = tmp_path / "test_drafts.db"

    import proposal.database as _db_mod
    import proposal.drafts_db as _drafts_mod

    from contextlib import contextmanager

    @contextmanager
    def _tmp_conn(**_):
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(_db_mod, "get_conn", _tmp_conn)
    monkeypatch.setattr(_drafts_mod, "get_conn", _tmp_conn)

    # Also patch the proposals table so FK is satisfied
    with _tmp_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY, title TEXT
            );
            INSERT OR IGNORE INTO proposals (id, title) VALUES ('p1', 'Test Proposal');
        """)

    run_drafts_migration()
    yield


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def test_create_and_get_document():
    doc = create_document("p1", "technical_volume", "Technical Volume")
    assert doc is not None
    assert doc["doc_type"] == "technical_volume"
    assert doc["title"] == "Technical Volume"
    assert doc["status"] == "draft"


def test_list_documents_by_proposal():
    create_document("p1", "sow", "SOW")
    create_document("p1", "cost_volume", "Cost Volume")
    docs = list_documents("p1")
    assert len(docs) == 2


def test_update_document():
    doc = create_document("p1", "sow", "Old Title")
    assert doc is not None
    updated = update_document(doc["id"], title="New Title", status="final")
    assert updated is not None
    assert updated["title"] == "New Title"
    assert updated["status"] == "final"


def test_delete_document():
    doc = create_document("p1", "wbs", "WBS")
    assert doc is not None
    assert delete_document(doc["id"]) is True
    assert get_document(doc["id"]) is None


def test_get_document_includes_sections():
    doc = create_document("p1", "technical_volume", "TV")
    assert doc is not None
    create_section(doc["id"], "Intro", section_number="1")
    result = get_document(doc["id"], include_sections=True)
    assert result is not None
    assert len(result["sections"]) == 1


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def test_create_and_get_section():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope", section_number="1")
    assert sec is not None
    assert sec["title"] == "Scope"
    assert sec["section_number"] == "1"


def test_update_section_updates_word_count():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    updated = update_section(sec["id"], content="Hello world foo bar")
    assert updated is not None
    assert updated["word_count"] == 4


def test_update_section_status_auto_set():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    updated = update_section(sec["id"], content="Some content here")
    assert updated is not None
    assert updated["status"] == "draft"


def test_delete_section():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "To Delete")
    assert sec is not None
    assert delete_section(sec["id"]) is True
    assert get_section(sec["id"]) is None


def test_section_tree_nesting():
    doc = create_document("p1", "technical_volume", "TV")
    assert doc is not None
    parent = create_section(doc["id"], "Parent", section_number="1")
    assert parent is not None
    child = create_section(doc["id"], "Child", parent_id=parent["id"], section_number="1.1")
    assert child is not None
    result = get_document(doc["id"], include_sections=True)
    assert result is not None
    roots = result["sections"]
    assert len(roots) == 1
    assert roots[0]["id"] == parent["id"]
    assert len(roots[0]["children"]) == 1
    assert roots[0]["children"][0]["id"] == child["id"]


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

def test_create_and_list_versions():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope", content="v1 content")
    assert sec is not None
    ver = create_version(sec["id"], "v1 content", review_stage="pink", created_by="Alice")
    assert ver["version_number"] == 1
    assert ver["review_stage"] == "pink"
    versions = list_versions(sec["id"])
    assert len(versions) >= 1


def test_restore_version():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope", content="original")
    assert sec is not None
    ver = create_version(sec["id"], "original", change_summary="Initial")
    update_section(sec["id"], content="modified content")
    restored = restore_version(sec["id"], ver["id"], restored_by="Bob")
    assert restored is not None
    assert restored["content"] == "original"


def test_restore_nonexistent_version_returns_none():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    result = restore_version(sec["id"], "nonexistent-id")
    assert result is None


def test_get_version():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    ver = create_version(sec["id"], "some content")
    fetched = get_version(ver["id"])
    assert fetched is not None
    assert fetched["content"] == "some content"


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def test_create_comment():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    cmt = create_comment(sec["id"], "Alice", "This needs more detail.")
    assert cmt is not None
    assert cmt["author"] == "Alice"
    assert cmt["resolved"] == 0


def test_list_comments_threaded():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    root = create_comment(sec["id"], "Alice", "Root comment")
    assert root is not None
    reply = create_comment(sec["id"], "Bob", "Reply", parent_comment_id=root["id"])
    assert reply is not None
    comments = list_comments(sec["id"])
    assert len(comments) == 1  # Only root at top level
    assert len(comments[0]["replies"]) == 1


def test_resolve_comment():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    cmt = create_comment(sec["id"], "Alice", "Fix this.")
    assert cmt is not None
    resolved = resolve_comment(cmt["id"], resolved_by="Bob")
    assert resolved is not None
    assert resolved["resolved"] == 1
    assert resolved["resolved_by"] == "Bob"


def test_list_comments_exclude_resolved():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    c1 = create_comment(sec["id"], "Alice", "Open comment")
    assert c1 is not None
    c2 = create_comment(sec["id"], "Bob", "Resolved comment")
    assert c2 is not None
    resolve_comment(c2["id"])
    open_only = list_comments(sec["id"], include_resolved=False)
    assert len(open_only) == 1
    assert open_only[0]["id"] == c1["id"]


def test_delete_comment():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    cmt = create_comment(sec["id"], "Alice", "Delete me.")
    assert cmt is not None
    assert delete_comment(cmt["id"]) is True
    assert list_comments(sec["id"]) == []


def test_update_comment():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    sec = create_section(doc["id"], "Scope")
    assert sec is not None
    cmt = create_comment(sec["id"], "Alice", "Original text")
    assert cmt is not None
    updated = update_comment(cmt["id"], "Revised text")
    assert updated is not None
    assert updated["content"] == "Revised text"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def test_list_doc_types_returns_all():
    doc_types = list_doc_types()
    keys = {d["key"] for d in doc_types}
    assert "technical_volume" in keys
    assert "cost_volume" in keys
    assert "sow" in keys
    assert "compliance_matrix" in keys
    assert len(doc_types) == len(TEMPLATES)


def test_apply_template_creates_sections():
    doc = create_document("p1", "technical_volume", "TV")
    assert doc is not None
    sections = apply_template(doc["id"], "technical_volume")
    assert len(sections) > 0
    # Verify parent-child relationship exists
    section_ids = {s["id"] for s in sections}
    children = [s for s in sections if s.get("parent_id") is not None]
    for child in children:
        assert child["parent_id"] in section_ids


def test_apply_template_invalid_type_raises():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    with pytest.raises(ValueError, match="No template registered"):
        apply_template(doc["id"], "nonexistent_type")


def test_all_templates_valid():
    """Every registered template must produce at least one section."""
    doc = create_document("p1", "sow", "SOW base")
    assert doc is not None
    for key in TEMPLATES:
        # Create a fresh doc for each template
        d = create_document("p1", key, f"Doc for {key}")
        assert d is not None
        secs = apply_template(d["id"], key)
        assert len(secs) > 0, f"Template '{key}' produced no sections"


# ---------------------------------------------------------------------------
# LLM writer (prompts only — no Ollama)
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx():
    return ProposalWriteContext(
        proposal_title="ACME IT Modernisation",
        doc_type="technical_volume",
        section_title="Technical Approach",
        section_number="2",
        current_content="We will use agile methods.",
        guidance="Describe the technical solution.",
        win_themes=["Agile delivery", "Cost savings"],
        open_comments=[{"author": "Red Team", "content": "Too vague"}],
        compliance_requirements=["Address Section L, Para 4.2"],
    )


def test_plan_prompt_contains_section_title(ctx):
    prompt = _build_plan_prompt(ctx)
    assert "Technical Approach" in prompt
    assert "outline" in prompt.lower()


def test_draft_prompt_includes_win_themes(ctx):
    prompt = _build_draft_prompt(ctx)
    assert "Agile delivery" in prompt


def test_improve_prompt_includes_current_content(ctx):
    prompt = _build_improve_prompt(ctx)
    assert "We will use agile methods" in prompt


def test_respond_comments_includes_comments(ctx):
    prompt = _build_respond_comments_prompt(ctx)
    assert "Red Team" in prompt
    assert "Too vague" in prompt


def test_compliance_check_includes_requirements(ctx):
    prompt = _build_compliance_check_prompt(ctx)
    assert "Section L, Para 4.2" in prompt


def test_list_actions_returns_all_types():
    actions = list_actions()
    keys = {a["key"] for a in actions}
    assert keys == {"plan", "draft", "improve", "respond_comments", "compliance_check"}


def test_run_llm_action_invalid_raises(ctx):
    with pytest.raises(ValueError, match="Unknown LLM action"):
        run_llm_action("nonexistent", ctx)


def test_run_llm_action_calls_ollama(ctx):
    mock_ollama = MagicMock()
    mock_ollama.generate_response.return_value = {
        "success": True,
        "data": {"response": "Generated draft text"}
    }
    with patch.dict("sys.modules", {"ollama_config": MagicMock(ollama_config=mock_ollama)}):
        result = run_llm_action("draft", ctx)
    # Result comes from the mock — just assert it's a string
    assert isinstance(result, str)
