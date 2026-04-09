"""
Opportunities import/export utilities: CSV import, CSV/JSON export, delete-all.

Provides both class methods (consumed by OpportunitiesManager) and
module-level request handlers that server/routes/opportunities.py calls.
"""

import csv
import io
import json
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import uuid

from config.database import DEFAULT_DB


# ---------------------------------------------------------------------------
# Field definitions (used in field-mapping UI)
# ---------------------------------------------------------------------------

OPPORTUNITY_FIELDS = [
    {'key': 'name',               'label': 'Name',                    'required': True},
    {'key': 'description',        'label': 'Description',             'required': False},
    {'key': 'pipeline_stage',     'label': 'Pipeline Stage',          'required': False},
    {'key': 'priority',           'label': 'Priority',                'required': False},
    {'key': 'value',              'label': 'Value ($)',                'required': False},
    {'key': 'tags',               'label': 'Tags (comma-sep)',         'required': False},
    {'key': 'status',             'label': 'Status',                  'required': False},
    # Direct DB columns
    {'key': 'agency',             'label': 'Agency / Client',         'required': False},
    {'key': 'probability',        'label': 'Probability of Win',      'required': False},
    {'key': 'proposal_due_date',  'label': 'Proposal Due Date',       'required': False},
    {'key': 'opp_number',         'label': 'Opp Number',              'required': False},
    {'key': 'is_iwa',             'label': 'Is IWA?',                 'required': False},
    {'key': 'owning_org',         'label': 'Owning Org',              'required': False},
    {'key': 'proposal_folder',    'label': 'Proposal Folder Location','required': False},
    {'key': 'solicitation_link',  'label': 'Solicitation Link',       'required': False},
    {'key': 'deal_type',          'label': 'Deal Type',               'required': False},
    # Overflow → metadata
    {'key': 'meta_award_date',    'label': 'Scheduled Award Date',    'required': False},
    {'key': 'meta_solicitation',  'label': 'Solicitation Number',     'required': False},
    {'key': 'meta_teaming_role',  'label': 'Teaming Role',            'required': False},
    {'key': 'meta_contract_type', 'label': 'Contract Type',           'required': False},
    {'key': 'meta_capture_mgr',   'label': 'Capture Manager',         'required': False},
    {'key': 'meta_portfolio',     'label': 'Portfolio',               'required': False},
    {'key': 'meta_divisions',     'label': 'Divisions',               'required': False},
    {'key': 'meta_acq_type',      'label': 'Acquisition Type',        'required': False},
    {'key': 'meta_set_aside',     'label': 'Set Aside Type',          'required': False},
]

DB_PATH = DEFAULT_DB

# ---------------------------------------------------------------------------
# CRM schema auto-detection
# ---------------------------------------------------------------------------

# Maps CRM stage labels (case-insensitive prefix match) → our pipeline_stage slugs.
# Reason: The CRM exports stages as "02-Long Lead"; our app uses "02-lead".
_STAGE_LABEL_TO_SLUG: Dict[str, str] = {
    '01':   '01-qual',
    '02':   '02-lead',
    '03':   '03-bid',
    '04':   '04-progress',
    '05':   '05-review',
    '06':   '06-nego',
    '07':   '07-won',
    '08':   '08-lost',
    '09':   '09-nobid',
    '20':   '20-other',
    '98':   '98-vehicle',
    '99':   '99-complete',
}

# Known CRM column-name → opportunity field key.
# Used by _detect_crm_field_map() to auto-populate the mapping UI.
_CRM_COLUMN_MAP: Dict[str, str] = {
    'opportunity name':                        'name',
    'stage':                                   'pipeline_stage',
    "ccri's est. funded/award contract value": 'value',
    'ccri est. funded/award contract value':   'value',
    'est. funded/award contract value':        'value',
    'description':                             'description',
    'status':                                  'status',
    'client':                                  'agency',
    'probability of win':                      'probability',
    'proposal due date':                       'proposal_due_date',
    'opp number':                              'opp_number',
    'proposal number':                         'opp_number',
    'is iwa?':                                 'is_iwa',
    'owning org':                              'owning_org',
    'proposal folder location':                'proposal_folder',
    'solicitation link':                       'solicitation_link',
    'deal type':                               'deal_type',
    # Remaining fields → metadata blob
    'portfolio':                               'meta_portfolio',
    'divisions':                               'meta_divisions',
    'scheduled award date':                    'meta_award_date',
    'solicitation number':                     'meta_solicitation',
    'teaming role':                            'meta_teaming_role',
    'contract type':                           'meta_contract_type',
    'capture manager':                         'meta_capture_mgr',
    'acquisition type':                        'meta_acq_type',
    'set aside type':                          'meta_set_aside',
}

# Signature columns that identify this as the known CRM export format.
_CRM_SIGNATURE_COLS = {'opportunity name', 'stage', 'proposal due date', 'opp number'}


def _detect_crm_field_map(headers: List[str]) -> Optional[Dict[str, str]]:
    """
    Return an auto field_map if headers match the known CRM export format.

    Args:
        headers: Column names from the CSV.

    Returns:
        dict mapping csv_column → opp_field_key, or None if not recognized.
    """
    lower_headers = {h.lower().strip() for h in headers}
    if not _CRM_SIGNATURE_COLS.issubset(lower_headers):
        return None

    field_map: Dict[str, str] = {}
    for header in headers:
        key = header.lower().strip()
        if key in _CRM_COLUMN_MAP:
            field_map[header] = _CRM_COLUMN_MAP[key]
    return field_map


# ---------------------------------------------------------------------------
# Value normalisation helpers
# ---------------------------------------------------------------------------

def _parse_currency(raw: str) -> float:
    """
    Parse a currency string like "$250,000" or "10%" to a float.

    Args:
        raw: Raw string value from CSV.

    Returns:
        float: Numeric value, 0.0 on failure.
    """
    if not raw:
        return 0.0
    cleaned = re.sub(r'[$,%\s]', '', raw.strip())
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _normalize_stage(raw: str) -> str:
    """
    Normalize a CRM stage label to our pipeline_stage slug.

    Maps "02-Long Lead" → "02-lead", "07-Closed Won" → "07-won", etc.
    Falls back to 'identified' for unrecognised values.

    Args:
        raw: Stage label from the CRM CSV.

    Returns:
        str: Pipeline stage slug.
    """
    raw = raw.strip()
    # Extract leading two-digit prefix
    m = re.match(r'^(\d{2})', raw)
    if m:
        prefix = m.group(1)
        if prefix in _STAGE_LABEL_TO_SLUG:
            return _STAGE_LABEL_TO_SLUG[prefix]
    # Fallback: try exact match against slug values
    if raw in _STAGE_LABEL_TO_SLUG.values():
        return raw
    return 'identified'


def _normalize_status(raw: str) -> str:
    """
    Normalize CRM status strings to our two-value system ('open'/'closed').

    Args:
        raw: Raw status string.

    Returns:
        str: 'open' or 'closed'.
    """
    lower = raw.strip().lower()
    if lower in ('open', 'active', 'in progress', 'pursuing'):
        return 'open'
    if lower in ('closed', 'won', 'lost', 'no bid', 'no-bid', 'complete', 'completed'):
        return 'closed'
    # Keep original if it already matches our values
    return lower if lower in ('open', 'closed') else 'open'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_conn(db_path: str = DB_PATH):
    """Open a SQLite connection with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row) -> Dict:
    """Convert a sqlite3.Row opportunity to a plain dict."""
    keys = row.keys()
    return {
        'id':               row['id'],
        'name':             row['name'],
        'description':      row['description'] or '',
        'status':           row['status'],
        'pipeline_stage':   row['pipeline_stage'] if 'pipeline_stage' in keys else 'identified',
        'priority':         row['priority'],
        'value':            row['value'],
        'tags':             json.loads(row['tags']) if row['tags'] else [],
        'metadata':         json.loads(row['metadata']) if row['metadata'] else {},
        'probability':      row['probability'] if 'probability' in keys else '',
        'proposal_due_date':row['proposal_due_date'] if 'proposal_due_date' in keys else '',
        'opp_number':       row['opp_number'] if 'opp_number' in keys else '',
        'is_iwa':           row['is_iwa'] if 'is_iwa' in keys else '',
        'owning_org':       row['owning_org'] if 'owning_org' in keys else '',
        'proposal_folder':  row['proposal_folder'] if 'proposal_folder' in keys else '',
        'agency':           row['agency'] if 'agency' in keys else '',
        'solicitation_link':row['solicitation_link'] if 'solicitation_link' in keys else '',
        'deal_type':        row['deal_type'] if 'deal_type' in keys else '',
        'created_at':       row['created_at'],
        'updated_at':       row['updated_at'],
    }


# ---------------------------------------------------------------------------
# Delete all
# ---------------------------------------------------------------------------

def handle_opportunities_delete_all_request(db_path: str = DB_PATH) -> Dict:
    """
    Delete every opportunity (and cascade-delete their tasks).

    Returns:
        dict: {status, deleted_count}
    """
    try:
        conn = _get_conn(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM opportunities")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM opportunities")
        conn.commit()
        conn.close()
        return {'status': 'success', 'deleted_count': count,
                'message': f'Deleted {count} opportunities'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ---------------------------------------------------------------------------
# CSV parse (step 1 of import)
# ---------------------------------------------------------------------------

def handle_opportunities_parse_csv_request(csv_content: str,
                                           preview_rows: int = 5) -> Dict:
    """
    Parse a CSV string, returning its headers and a preview of data rows.

    Also performs schema auto-detection: if the headers match the known CRM
    export format, an auto_field_map is included so the UI can pre-populate
    the column-mapping step.

    Args:
        csv_content: Raw CSV text.
        preview_rows: How many data rows to include in the preview.

    Returns:
        dict: {status, headers, preview, row_count, opportunity_fields,
               auto_field_map (if detected)}
    """
    try:
        reader = csv.reader(io.StringIO(csv_content.strip()))
        rows = list(reader)
        if not rows:
            return {'status': 'error', 'message': 'CSV file is empty'}

        headers = [h.strip() for h in rows[0]]
        data_rows = rows[1:]
        preview = [list(r) for r in data_rows[:preview_rows]]

        result: Dict = {
            'status': 'success',
            'headers': headers,
            'preview': preview,
            'row_count': len(data_rows),
            'opportunity_fields': OPPORTUNITY_FIELDS,
        }

        auto_map = _detect_crm_field_map(headers)
        if auto_map:
            result['auto_field_map'] = auto_map
            result['schema_detected'] = 'crm_export'

        return result
    except Exception as e:
        return {'status': 'error', 'message': f'CSV parse error: {e}'}


# ---------------------------------------------------------------------------
# CSV import confirm (step 2 of import)
# ---------------------------------------------------------------------------

def handle_opportunities_import_confirm_request(csv_content: str,
                                                field_map: Dict[str, str],
                                                db_path: str = DB_PATH) -> Dict:
    """
    Import opportunities from CSV using the provided field mapping.

    Handles CRM-specific value normalization:
    - Currency strings ("$250,000") are parsed to floats.
    - Stage labels ("02-Long Lead") are normalized to slugs ("02-lead").
    - Status strings are normalized to 'open'/'closed'.
    - Fields prefixed "meta_" are stored in the metadata JSON blob.
    - Portfolio / Divisions columns are merged into the tags list.

    Args:
        csv_content: Raw CSV text.
        field_map: {csv_column_name: opportunity_field_key}
                   e.g. {"Opportunity Name": "name", "Stage": "pipeline_stage"}
        db_path: SQLite database path.

    Returns:
        dict: {status, imported, skipped, errors: [...]}
    """
    try:
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        rows = list(reader)
    except Exception as e:
        return {'status': 'error', 'message': f'CSV read error: {e}'}

    imported = 0
    skipped = 0
    errors: List[str] = []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for i, row in enumerate(rows, start=2):  # row 1 is headers
        try:
            # Apply field mapping — separate metadata fields from core fields
            mapped: Dict = {}
            meta_mapped: Dict = {}
            for csv_col, opp_field in field_map.items():
                if not opp_field or csv_col not in row:
                    continue
                val = row[csv_col].strip()
                if opp_field.startswith('meta_'):
                    meta_mapped[opp_field[5:]] = val  # strip "meta_" prefix
                else:
                    mapped[opp_field] = val

            name = mapped.get('name', '').strip()
            if not name:
                skipped += 1
                errors.append(f'Row {i}: skipped — no name value')
                continue

            # Normalise core fields
            value = _parse_currency(mapped.get('value', '0'))
            pipeline_stage = _normalize_stage(mapped.get('pipeline_stage', '')) or 'identified'
            status = _normalize_status(mapped.get('status', 'open'))
            priority = mapped.get('priority', 'medium') or 'medium'
            description = mapped.get('description', '') or ''

            # Direct CRM columns
            probability        = mapped.get('probability', '')
            proposal_due_date  = mapped.get('proposal_due_date', '')
            opp_number         = mapped.get('opp_number', '')
            is_iwa             = mapped.get('is_iwa', '')
            owning_org         = mapped.get('owning_org', '')
            proposal_folder    = mapped.get('proposal_folder', '')
            agency             = mapped.get('agency', '')
            solicitation_link  = mapped.get('solicitation_link', '')
            deal_type          = mapped.get('deal_type', '')

            # Tags: explicit tags column + portfolio + divisions (from meta overflow)
            tags_raw = mapped.get('tags', '')
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []
            for tag_source in ('portfolio', 'divisions'):
                extra = meta_mapped.get(tag_source, '')
                for t in extra.split(','):
                    t = t.strip()
                    if t and t not in tags:
                        tags.append(t)

            # Build metadata blob from remaining meta_ fields
            metadata: Dict = {k: v for k, v in meta_mapped.items() if v and k not in ('portfolio', 'divisions')}

            opp_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO opportunities
                (id, name, description, status, priority, value, tags, metadata,
                 pipeline_stage, probability, proposal_due_date, opp_number, is_iwa,
                 owning_org, proposal_folder, agency, solicitation_link, deal_type,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (opp_id, name, description, status, priority, value,
                  json.dumps(tags), json.dumps(metadata), pipeline_stage,
                  probability, proposal_due_date, opp_number, is_iwa,
                  owning_org, proposal_folder, agency, solicitation_link, deal_type,
                  now, now))

            imported += 1

        except Exception as e:
            skipped += 1
            errors.append(f'Row {i}: {e}')

    conn.commit()
    conn.close()

    return {
        'status': 'success',
        'imported': imported,
        'skipped': skipped,
        'errors': errors,
        'message': f'Imported {imported} opportunities ({skipped} skipped)',
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def handle_opportunities_export_request(fmt: str = 'csv',
                                        db_path: str = DB_PATH) -> Dict:
    """
    Export all opportunities as CSV or JSON.

    Args:
        fmt: 'csv' or 'json'
        db_path: SQLite database path.

    Returns:
        dict: {status, content: bytes, content_type, filename}
    """
    try:
        conn = _get_conn(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, description, status, pipeline_stage, priority, value,
                   tags, metadata, probability, proposal_due_date, opp_number, is_iwa,
                   owning_org, proposal_folder, agency, solicitation_link, deal_type,
                   created_at, updated_at
            FROM opportunities ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        opportunities = [_row_to_dict(r) for r in rows]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if fmt == 'json':
            content = json.dumps(opportunities, indent=2).encode('utf-8')
            return {
                'status': 'success',
                'content': content,
                'content_type': 'application/json',
                'filename': f'opportunities_{timestamp}.json',
            }

        # Default: CSV
        fieldnames = [
            'id', 'name', 'opp_number', 'pipeline_stage', 'value', 'probability',
            'agency', 'proposal_due_date', 'deal_type', 'is_iwa', 'owning_org',
            'solicitation_link', 'proposal_folder', 'description', 'status',
            'priority', 'tags', 'created_at', 'updated_at',
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for opp in opportunities:
            row = dict(opp)
            row['tags'] = ', '.join(opp.get('tags', []))
            writer.writerow(row)

        content = buf.getvalue().encode('utf-8')
        return {
            'status': 'success',
            'content': content,
            'content_type': 'text/csv',
            'filename': f'opportunities_{timestamp}.csv',
        }

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
