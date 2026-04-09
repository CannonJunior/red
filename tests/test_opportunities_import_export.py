"""
Tests for opportunities_import_export.py — CSV import, schema detection,
value normalisation, and field mapping.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from opportunities_import_export import (
    _detect_crm_field_map,
    _normalize_stage,
    _parse_currency,
    _normalize_status,
    handle_opportunities_delete_all_request,
    handle_opportunities_import_confirm_request,
    handle_opportunities_parse_csv_request,
    OPPORTUNITY_FIELDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path):
    """Create a SQLite DB with the full opportunities schema including CRM columns."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE opportunities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            value REAL DEFAULT 0.0,
            tags TEXT,
            metadata TEXT,
            pipeline_stage TEXT DEFAULT 'identified',
            probability TEXT,
            proposal_due_date TEXT,
            opp_number TEXT,
            is_iwa TEXT,
            owning_org TEXT,
            proposal_folder TEXT,
            agency TEXT,
            solicitation_link TEXT,
            deal_type TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db_path


CRM_CSV = """\
Opportunity Name,Stage,CCRI's Est. Funded/Award Contract Value,Probability of Win,Proposal Due Date,Opp Number,Status,Client,Description,Solicitation Number,Teaming Role,Contract Type,Portfolio,Divisions
Widget Program,02-Long Lead,"$500,000",25%,12/31/2026,240001,Open,DoD Agency,Some description,N00014-26-R-1234,Prime,CPFF,"DoD,Federal",Charlottesville Office
Closed Opp,07-Closed Won,"$1,000,000",90%,06/30/2025,230099,Open,,,,,,
"""

GENERIC_CSV = """\
Name,Description,Value,Stage,Status
Foo,Bar,100000,identified,open
"""


# ---------------------------------------------------------------------------
# _parse_currency
# ---------------------------------------------------------------------------

def test_parse_currency_dollar_string():
    assert _parse_currency("$250,000") == 250_000.0


def test_parse_currency_plain_number():
    assert _parse_currency("150000") == 150_000.0


def test_parse_currency_empty():
    assert _parse_currency("") == 0.0


def test_parse_currency_percentage():
    # Probability fields also use %; strip and return numeric
    assert _parse_currency("25%") == 25.0


def test_parse_currency_zero_dollar():
    assert _parse_currency("$0") == 0.0


# ---------------------------------------------------------------------------
# _normalize_stage
# ---------------------------------------------------------------------------

def test_normalize_stage_crm_format():
    assert _normalize_stage("02-Long Lead") == "02-lead"


def test_normalize_stage_closed_won():
    assert _normalize_stage("07-Closed Won") == "07-won"


def test_normalize_stage_vehicle():
    assert _normalize_stage("98-Awarded Contract") == "98-vehicle"


def test_normalize_stage_already_slug():
    assert _normalize_stage("04-progress") == "04-progress"


def test_normalize_stage_unknown_fallback():
    assert _normalize_stage("Unknown Stage") == "identified"


# ---------------------------------------------------------------------------
# _normalize_status
# ---------------------------------------------------------------------------

def test_normalize_status_open():
    assert _normalize_status("Open") == "open"


def test_normalize_status_closed():
    assert _normalize_status("Closed") == "closed"


def test_normalize_status_unknown_defaults_open():
    assert _normalize_status("Pursuing") == "open"


# ---------------------------------------------------------------------------
# _detect_crm_field_map
# ---------------------------------------------------------------------------

def test_detect_crm_field_map_recognises_crm_headers():
    headers = [
        "Opportunity Name", "Stage", "CCRI's Est. Funded/Award Contract Value",
        "Proposal Due Date", "Opp Number", "Client", "Status", "Description",
    ]
    result = _detect_crm_field_map(headers)
    assert result is not None
    assert result["Opportunity Name"] == "name"
    assert result["Stage"] == "pipeline_stage"
    assert result["Client"] == "agency"  # now a direct DB column


def test_detect_crm_field_map_returns_none_for_generic():
    headers = ["Name", "Description", "Value"]
    assert _detect_crm_field_map(headers) is None


def test_detect_crm_field_map_missing_signature_col():
    # Missing "Opp Number" — not enough signature columns
    headers = ["Opportunity Name", "Stage", "Proposal Due Date"]
    assert _detect_crm_field_map(headers) is None


# ---------------------------------------------------------------------------
# handle_opportunities_parse_csv_request
# ---------------------------------------------------------------------------

def test_parse_csv_returns_headers_and_preview():
    result = handle_opportunities_parse_csv_request(CRM_CSV)
    assert result["status"] == "success"
    assert "Opportunity Name" in result["headers"]
    assert result["row_count"] == 2
    assert len(result["preview"]) <= 5


def test_parse_csv_detects_crm_schema():
    result = handle_opportunities_parse_csv_request(CRM_CSV)
    assert result.get("schema_detected") == "crm_export"
    assert "auto_field_map" in result
    assert result["auto_field_map"]["Opportunity Name"] == "name"


def test_parse_csv_generic_no_auto_map():
    result = handle_opportunities_parse_csv_request(GENERIC_CSV)
    assert result["status"] == "success"
    assert "auto_field_map" not in result


def test_parse_csv_empty_returns_error():
    result = handle_opportunities_parse_csv_request("   ")
    assert result["status"] == "error"


def test_parse_csv_includes_opportunity_fields():
    result = handle_opportunities_parse_csv_request(CRM_CSV)
    keys = [f["key"] for f in result["opportunity_fields"]]
    assert "name" in keys
    assert "agency" in keys          # direct DB column
    assert "solicitation_link" in keys


# ---------------------------------------------------------------------------
# handle_opportunities_import_confirm_request
# ---------------------------------------------------------------------------

def test_import_confirm_basic(tmp_db):
    field_map = {
        "Opportunity Name": "name",
        "Stage": "pipeline_stage",
        "CCRI's Est. Funded/Award Contract Value": "value",
        "Status": "status",
        "Client": "agency",
        "Portfolio": "meta_portfolio",
    }
    result = handle_opportunities_import_confirm_request(CRM_CSV, field_map, db_path=tmp_db)
    assert result["status"] == "success"
    assert result["imported"] == 2
    assert result["skipped"] == 0


def test_import_confirm_stage_normalised(tmp_db):
    field_map = {"Opportunity Name": "name", "Stage": "pipeline_stage"}
    handle_opportunities_import_confirm_request(CRM_CSV, field_map, db_path=tmp_db)

    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT pipeline_stage FROM opportunities WHERE name = 'Widget Program'").fetchone()
    conn.close()
    assert row[0] == "02-lead"


def test_import_confirm_value_parsed(tmp_db):
    field_map = {
        "Opportunity Name": "name",
        "CCRI's Est. Funded/Award Contract Value": "value",
    }
    handle_opportunities_import_confirm_request(CRM_CSV, field_map, db_path=tmp_db)

    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT value FROM opportunities WHERE name = 'Widget Program'").fetchone()
    conn.close()
    assert row[0] == 500_000.0


def test_import_confirm_direct_columns_stored(tmp_db):
    """Agency and solicitation_link are now direct DB columns, not metadata."""
    field_map = {
        "Opportunity Name": "name",
        "Client": "agency",
        "Solicitation Link": "solicitation_link",
        "Probability of Win": "probability",
        "Opp Number": "opp_number",
    }
    handle_opportunities_import_confirm_request(CRM_CSV, field_map, db_path=tmp_db)

    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        "SELECT agency, solicitation_link, probability, opp_number FROM opportunities WHERE name = 'Widget Program'"
    ).fetchone()
    conn.close()
    assert row[0] == "DoD Agency"
    assert row[2] == "25%"
    assert row[3] == "240001"


def test_import_confirm_portfolio_added_to_tags(tmp_db):
    field_map = {
        "Opportunity Name": "name",
        "Portfolio": "meta_portfolio",
    }
    handle_opportunities_import_confirm_request(CRM_CSV, field_map, db_path=tmp_db)

    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT tags FROM opportunities WHERE name = 'Widget Program'").fetchone()
    conn.close()
    tags = json.loads(row[0])
    assert "DoD" in tags or "Federal" in tags


def test_import_confirm_skips_rows_without_name(tmp_db):
    csv_no_name = "Opportunity Name,Stage\n,02-Long Lead\n"
    field_map = {"Opportunity Name": "name"}
    result = handle_opportunities_import_confirm_request(csv_no_name, field_map, db_path=tmp_db)
    assert result["skipped"] == 1
    assert result["imported"] == 0


# ---------------------------------------------------------------------------
# handle_opportunities_delete_all_request
# ---------------------------------------------------------------------------

def test_delete_all_removes_rows(tmp_db):
    field_map = {"Opportunity Name": "name"}
    handle_opportunities_import_confirm_request(CRM_CSV, field_map, db_path=tmp_db)

    result = handle_opportunities_delete_all_request(db_path=tmp_db)
    assert result["status"] == "success"
    assert result["deleted_count"] == 2

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    conn.close()
    assert count == 0
