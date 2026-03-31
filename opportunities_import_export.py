"""
Opportunities import/export utilities: CSV import, CSV/JSON export, delete-all.

Provides both class methods (consumed by OpportunitiesManager) and
module-level request handlers that server/routes/opportunities.py calls.
"""

import csv
import io
import json
import sqlite3
from datetime import datetime
from typing import Dict, List
import uuid


# ---------------------------------------------------------------------------
# Field definitions (used in field-mapping UI)
# ---------------------------------------------------------------------------

OPPORTUNITY_FIELDS = [
    {'key': 'name',           'label': 'Name',           'required': True},
    {'key': 'description',    'label': 'Description',    'required': False},
    {'key': 'pipeline_stage', 'label': 'Pipeline Stage', 'required': False},
    {'key': 'priority',       'label': 'Priority',       'required': False},
    {'key': 'value',          'label': 'Value ($)',       'required': False},
    {'key': 'tags',           'label': 'Tags (comma-sep)','required': False},
    {'key': 'status',         'label': 'Status (legacy)', 'required': False},
]

DB_PATH = "search_system.db"


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
        'id':             row['id'],
        'name':           row['name'],
        'description':    row['description'] or '',
        'status':         row['status'],
        'pipeline_stage': row['pipeline_stage'] if 'pipeline_stage' in keys else 'identified',
        'priority':       row['priority'],
        'value':          row['value'],
        'tags':           json.loads(row['tags']) if row['tags'] else [],
        'metadata':       json.loads(row['metadata']) if row['metadata'] else {},
        'created_at':     row['created_at'],
        'updated_at':     row['updated_at'],
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

    Args:
        csv_content: Raw CSV text.
        preview_rows: How many data rows to include in the preview.

    Returns:
        dict: {status, headers: [...], preview: [[...], ...], row_count}
    """
    try:
        reader = csv.reader(io.StringIO(csv_content.strip()))
        rows = list(reader)
        if not rows:
            return {'status': 'error', 'message': 'CSV file is empty'}

        headers = [h.strip() for h in rows[0]]
        data_rows = rows[1:]
        preview = [list(r) for r in data_rows[:preview_rows]]

        return {
            'status': 'success',
            'headers': headers,
            'preview': preview,
            'row_count': len(data_rows),
            'opportunity_fields': OPPORTUNITY_FIELDS,
        }
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

    Args:
        csv_content: Raw CSV text.
        field_map: {csv_column_name: opportunity_field_key}
                   e.g. {"Opportunity Name": "name", "Est. Value": "value"}
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

    for i, row in enumerate(rows, start=2):  # start=2: row 1 is headers
        try:
            # Apply field mapping
            mapped: Dict = {}
            for csv_col, opp_field in field_map.items():
                if opp_field and csv_col in row:
                    mapped[opp_field] = row[csv_col].strip()

            name = mapped.get('name', '').strip()
            if not name:
                skipped += 1
                errors.append(f'Row {i}: skipped — no name value')
                continue

            # Coerce types
            try:
                value = float(mapped.get('value', 0) or 0)
            except ValueError:
                value = 0.0

            tags_raw = mapped.get('tags', '')
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []

            pipeline_stage = mapped.get('pipeline_stage', 'identified') or 'identified'
            priority = mapped.get('priority', 'medium') or 'medium'
            status = mapped.get('status', 'open') or 'open'
            description = mapped.get('description', '') or ''

            opp_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO opportunities
                (id, name, description, status, priority, value, tags, metadata,
                 pipeline_stage, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (opp_id, name, description, status, priority, value,
                  json.dumps(tags), json.dumps({}), pipeline_stage, now, now))

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
        cursor.execute("SELECT * FROM opportunities ORDER BY created_at DESC")
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
        fieldnames = ['id', 'name', 'description', 'status', 'pipeline_stage',
                      'priority', 'value', 'tags', 'created_at', 'updated_at']
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
