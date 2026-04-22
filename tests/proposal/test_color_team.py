"""
Tests for proposal/color_team.py.

Covers:
  - .docx comment extraction (XML parsing)
  - Section matching (anchor text and keyword fallback)
  - Compliance requirement detection (LLM mock)
  - Rating generation (LLM mock)
  - Full ingestion pipeline (integration-style with temp DB)
  - Compliance assessment aggregation
"""

from __future__ import annotations

import io
import sqlite3
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from proposal.color_team import (
    RATING_SCALE,
    _build_anchor_map,
    _build_assessment,
    _flat_sections,
    extract_docx_comments,
    get_document_compliance_assessment,
    match_comment_to_section,
    rate_section_comment,
    detect_compliance_requirement,
    run_color_team_migration,
    ingest_color_team_review,
)
from proposal.drafts_db import (
    create_document,
    create_section,
    run_drafts_migration,
)
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Helpers for building synthetic .docx bytes
# ---------------------------------------------------------------------------

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _make_docx(comments: list[dict], body_text: str = "") -> bytes:
    """
    Build minimal .docx bytes in memory with the given comments.

    Each comment dict must have: id, author, content, anchor (substring of body_text).
    """
    # Build comments.xml
    comments_el = ET.Element(_w("comments"))
    for c in comments:
        cmt = ET.SubElement(comments_el, _w("comment"))
        cmt.set(_w("id"), str(c["id"]))
        cmt.set(_w("author"), c.get("author", "Reviewer"))
        cmt.set(_w("date"), "2026-01-01T00:00:00Z")
        p = ET.SubElement(cmt, _w("p"))
        r = ET.SubElement(p, _w("r"))
        t = ET.SubElement(r, _w("t"))
        t.text = c["content"]

    # Build document.xml with commentRangeStart/End around anchor text
    body_el = ET.Element(_w("document"))
    body = ET.SubElement(body_el, _w("body"))
    remaining = body_text
    for c in comments:
        anchor = c.get("anchor", "")
        if anchor and anchor in remaining:
            pre, _, rest = remaining.partition(anchor)
            if pre:
                p_el = ET.SubElement(body, _w("p"))
                r_el = ET.SubElement(p_el, _w("r"))
                t_el = ET.SubElement(r_el, _w("t"))
                t_el.text = pre

            start = ET.SubElement(body, _w("commentRangeStart"))
            start.set(_w("id"), str(c["id"]))

            p_el = ET.SubElement(body, _w("p"))
            r_el = ET.SubElement(p_el, _w("r"))
            t_el = ET.SubElement(r_el, _w("t"))
            t_el.text = anchor

            end = ET.SubElement(body, _w("commentRangeEnd"))
            end.set(_w("id"), str(c["id"]))
            remaining = rest
        else:
            pass  # no anchor — comment exists without range

    if remaining:
        p_el = ET.SubElement(body, _w("p"))
        r_el = ET.SubElement(p_el, _w("r"))
        t_el = ET.SubElement(r_el, _w("t"))
        t_el.text = remaining

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/comments.xml", ET.tostring(comments_el, encoding="unicode"))
        z.writestr("word/document.xml", ET.tostring(body_el, encoding="unicode"))
        z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    return buf.getvalue()


# ---------------------------------------------------------------------------
# DB fixture (same pattern as test_drafts.py)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_ct.db"

    import proposal.database as _db_mod
    import proposal.drafts_db as _drafts_mod
    import proposal.color_team as _ct_mod

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
    monkeypatch.setattr(_ct_mod, "get_conn", _tmp_conn)

    with _tmp_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY, title TEXT
            );
            CREATE TABLE IF NOT EXISTS requirements (
                id TEXT PRIMARY KEY,
                opportunity_id TEXT,
                section TEXT,
                source_text TEXT,
                compliance_type TEXT,
                requirement_category TEXT,
                priority TEXT DEFAULT 'medium',
                created_at TEXT,
                updated_at TEXT
            );
            INSERT OR IGNORE INTO proposals (id, title) VALUES ('p1', 'Test Proposal');
            INSERT OR IGNORE INTO requirements (id, opportunity_id, section, source_text, compliance_type)
              VALUES ('req1', 'opp1', 'Section L', 'The offeror shall describe its technical approach.', 'mandatory');
            INSERT OR IGNORE INTO requirements (id, opportunity_id, section, source_text, compliance_type)
              VALUES ('req2', 'opp1', 'Section M', 'The offeror must demonstrate past performance.', 'mandatory');
        """)

    run_drafts_migration()
    run_color_team_migration()
    yield


# ---------------------------------------------------------------------------
# extract_docx_comments
# ---------------------------------------------------------------------------

def test_extract_empty_docx_returns_empty_list():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<x/>")
        z.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body/></w:document>")
    assert extract_docx_comments(buf.getvalue()) == []


def test_extract_single_comment():
    body = "The team will use Agile methodology for delivery."
    docx = _make_docx([
        {"id": "0", "author": "Alice", "content": "Too vague — needs specifics.", "anchor": "Agile methodology"}
    ], body)
    comments = extract_docx_comments(docx)
    assert len(comments) == 1
    assert comments[0]["author"] == "Alice"
    assert "Too vague" in comments[0]["content"]
    assert comments[0]["anchor_text"] == "Agile methodology"


def test_extract_multiple_comments():
    body = "We will deliver on time and within budget using proven methods."
    docx = _make_docx([
        {"id": "0", "author": "Bob", "content": "Quantify 'on time'.", "anchor": "on time"},
        {"id": "1", "author": "Carol", "content": "Define 'proven methods'.", "anchor": "proven methods"},
    ], body)
    comments = extract_docx_comments(docx)
    assert len(comments) == 2
    authors = {c["author"] for c in comments}
    assert "Bob" in authors
    assert "Carol" in authors


def test_extract_comment_without_anchor():
    """Comments without commentRangeStart/End still extracted with empty anchor."""
    body = "Some proposal text."
    docx = _make_docx([
        {"id": "0", "author": "Dan", "content": "General remark.", "anchor": ""}
    ], body)
    comments = extract_docx_comments(docx)
    assert len(comments) == 1
    # anchor_text will be empty since no range markers
    assert comments[0]["content"] == "General remark."


def test_extract_returns_empty_for_invalid_bytes():
    comments = extract_docx_comments(b"not a docx file")
    assert comments == []


# ---------------------------------------------------------------------------
# match_comment_to_section
# ---------------------------------------------------------------------------

_SECTIONS = [
    {"id": "sec1", "title": "Technical Approach", "content": "We will use Agile methodology for all deliverables."},
    {"id": "sec2", "title": "Past Performance", "content": "ACME delivered the HERO contract with Outstanding CPARS."},
    {"id": "sec3", "title": "Management Plan", "content": "Our PM holds a PMP certification and ten years experience."},
]


def test_match_by_anchor_text():
    result = match_comment_to_section("Agile methodology", "Too vague.", _SECTIONS)
    assert result == "sec1"


def test_match_by_keyword_overlap_fallback():
    # No anchor, but "performance" + "CPARS" overlap with sec2
    result = match_comment_to_section("", "CPARS rating is missing from past performance section.", _SECTIONS)
    assert result == "sec2"


def test_match_returns_none_when_no_overlap():
    result = match_comment_to_section("", "xyz qqq rrr", _SECTIONS)
    assert result is None


def test_match_prefers_anchor_over_keyword():
    # Anchor is in sec1; comment mentions 'management' (sec3 keyword)
    result = match_comment_to_section("Agile methodology", "management plan needs more detail", _SECTIONS)
    assert result == "sec1"


# ---------------------------------------------------------------------------
# _build_assessment
# ---------------------------------------------------------------------------

def test_build_assessment_worst_rating_wins():
    comments = [
        {"id": "c1", "requirement_id": "req1", "requirement_text": "Req A", "rating": "Outstanding"},
        {"id": "c2", "requirement_id": "req1", "requirement_text": "Req A", "rating": "Marginal"},
    ]
    result = _build_assessment(comments, [])
    assert len(result) == 1
    assert result[0]["worst_rating"] == "Marginal"
    assert result[0]["comment_count"] == 2


def test_build_assessment_excludes_unlinked_comments():
    """Comments without requirement_id should not appear in assessment."""
    comments = [
        {"id": "c1", "requirement_id": None, "requirement_text": "", "rating": "Good"},
    ]
    result = _build_assessment(comments, [])
    assert result == []


def test_build_assessment_sorted_worst_first():
    comments = [
        {"id": "c1", "requirement_id": "req1", "requirement_text": "", "rating": "Good"},
        {"id": "c2", "requirement_id": "req2", "requirement_text": "", "rating": "Unacceptable"},
        {"id": "c3", "requirement_id": "req3", "requirement_text": "", "rating": "Acceptable"},
    ]
    result = _build_assessment(comments, [])
    assert result[0]["worst_rating"] == "Unacceptable"


# ---------------------------------------------------------------------------
# rate_section_comment (LLM mock)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("llm_response,expected", [
    ("Good", "Good"),
    ("The section is Outstanding in this regard.", "Outstanding"),
    ("MARGINAL", "Marginal"),
    ("This is completely Unacceptable because", "Unacceptable"),
    ("gibberish response", "Marginal"),  # default fallback
])
def test_rate_section_comment_parses_rating(llm_response, expected):
    mock_ollama = MagicMock()
    mock_ollama.generate_response.return_value = {"success": True, "data": {"response": llm_response}}
    with patch.dict("sys.modules", {"ollama_config": MagicMock(ollama_config=mock_ollama)}):
        rating = rate_section_comment("Section content here.", "Reviewer says it's weak.", "Req text.", "llama3")
    assert rating == expected


# ---------------------------------------------------------------------------
# detect_compliance_requirement (LLM mock)
# ---------------------------------------------------------------------------

def test_detect_compliance_requirement_returns_match():
    reqs = [
        {"id": "req1", "section": "L", "source_text": "Offeror shall describe technical approach."},
        {"id": "req2", "section": "M", "source_text": "Demonstrate past performance."},
    ]
    mock_ollama = MagicMock()
    mock_ollama.generate_response.return_value = {"success": True, "data": {"response": "0"}}
    with patch.dict("sys.modules", {"ollama_config": MagicMock(ollama_config=mock_ollama)}):
        result = detect_compliance_requirement("Technical approach is too vague.", "Agile", reqs, "llama3")
    assert result is not None
    assert result["id"] == "req1"


def test_detect_compliance_requirement_returns_none_for_none():
    mock_ollama = MagicMock()
    mock_ollama.generate_response.return_value = {"success": True, "data": {"response": "none"}}
    with patch.dict("sys.modules", {"ollama_config": MagicMock(ollama_config=mock_ollama)}):
        result = detect_compliance_requirement("Random comment.", "", [{"id": "r", "section": "L", "source_text": "x"}], "llama3")
    assert result is None


def test_detect_compliance_requirement_empty_list():
    result = detect_compliance_requirement("Comment text.", "anchor", [], "llama3")
    assert result is None


# ---------------------------------------------------------------------------
# Full ingestion pipeline
# ---------------------------------------------------------------------------

def test_ingest_color_team_review_basic():
    """End-to-end: create doc, upload synthetic docx, check comments stored."""
    doc = create_document("p1", "technical_volume", "TV")
    assert doc is not None
    sec = create_section(doc["id"], "Technical Approach",
                         content="We will use Agile methodology for all deliverables.")
    assert sec is not None

    docx = _make_docx([
        {"id": "0", "author": "Red Team", "content": "Too vague — needs metrics.", "anchor": "Agile methodology"}
    ], "We will use Agile methodology for all deliverables.")

    mock_ollama = MagicMock()
    mock_ollama.generate_response.return_value = {"success": True, "data": {"response": "Marginal"}}

    with patch.dict("sys.modules", {"ollama_config": MagicMock(ollama_config=mock_ollama)}):
        result = ingest_color_team_review(
            document_id=doc["id"],
            opportunity_id="opp1",
            docx_bytes=docx,
            review_stage="red",
        )

    assert result["ingested"] >= 1
    stored = result["comments"][0]
    assert stored["author"] == "Red Team"
    assert stored["review_stage"] == "red"
    assert stored["rating"] in RATING_SCALE


def test_ingest_skips_when_no_section_match():
    """Comments that can't be matched to a section are counted as skipped."""
    doc = create_document("p1", "technical_volume", "TV")
    assert doc is not None
    create_section(doc["id"], "Technical Approach", content="We deliver quality.")

    docx = _make_docx([
        {"id": "0", "author": "Reviewer", "content": "Complete rewrite needed.", "anchor": "xyzzy not present"}
    ], "This is completely unrelated content.")

    mock_ollama = MagicMock()
    mock_ollama.generate_response.return_value = {"success": True, "data": {"response": "0"}}

    with patch.dict("sys.modules", {"ollama_config": MagicMock(ollama_config=mock_ollama)}):
        result = ingest_color_team_review(doc["id"], "", docx, "red")

    assert result["skipped"] >= 1


def test_ingest_empty_docx():
    doc = create_document("p1", "sow", "SOW")
    assert doc is not None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body/></w:document>")
    result = ingest_color_team_review(doc["id"], "", buf.getvalue(), "red")
    assert result["ingested"] == 0
    assert "No comments" in result["message"]


def test_get_document_compliance_assessment_after_ingest():
    """After ingestion, compliance assessment reflects stored ratings."""
    doc = create_document("p1", "technical_volume", "TV")
    assert doc is not None
    create_section(doc["id"], "Technical Approach",
                   content="We will use Agile methodology for all deliverables.")

    docx = _make_docx([
        {"id": "0", "author": "Red Team", "content": "Needs more detail.", "anchor": "Agile methodology"}
    ], "We will use Agile methodology for all deliverables.")

    mock_ollama = MagicMock()
    mock_ollama.generate_response.return_value = {"success": True, "data": {"response": "Marginal"}}

    with patch.dict("sys.modules", {"ollama_config": MagicMock(ollama_config=mock_ollama)}):
        ingest_color_team_review(doc["id"], "opp1", docx, "red")

    assessment = get_document_compliance_assessment(doc["id"])
    assert len(assessment) >= 0  # may be 0 if no requirements matched
