"""
RFP Shredding API Routes

Endpoints for RFP shredding, requirement management, and compliance tracking.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any

from shredding.rfp_shredder import RFPShredder
from server.utils.json_response import send_json_response
from server.utils.request_helpers import get_request_body

logger = logging.getLogger(__name__)

# Initialize shredder
shredder = RFPShredder(
    db_path="opportunities.db",
    ollama_url="http://localhost:11434"
)


def handle_shredding_shred_api(handler, path: str, query_params: Dict):
    """
    POST /api/shredding/shred

    Start RFP shredding process.

    Request body:
    {
        "file_path": str,
        "rfp_number": str,
        "opportunity_name": str,
        "due_date": str,  # YYYY-MM-DD
        "agency": str (optional),
        "naics_code": str (optional),
        "set_aside": str (optional),
        "create_tasks": bool (default: true),
        "auto_assign": bool (default: false),
        "output_dir": str (optional)
    }

    Response:
    {
        "status": "success" | "error",
        "opportunity_id": str,
        "total_requirements": int,
        "mandatory_count": int,
        "recommended_count": int,
        "optional_count": int,
        "tasks_created": int,
        "matrix_file": str,
        "sections": {...}
    }
    """
    if handler.command != 'POST':
        send_json_response(handler, {'error': 'Method not allowed'}, 405)
        return

    try:
        # Parse request body
        body = get_request_body(handler)
        data = json.loads(body)

        # Validate required fields
        required_fields = ['file_path', 'rfp_number', 'opportunity_name', 'due_date']
        missing = [f for f in required_fields if f not in data]

        if missing:
            send_json_response(handler, {
                'error': f'Missing required fields: {", ".join(missing)}'
            }, 400)
            return

        # Validate file exists
        if not Path(data['file_path']).exists():
            send_json_response(handler, {
                'error': f'File not found: {data["file_path"]}'
            }, 400)
            return

        # Start shredding
        logger.info(f"Starting RFP shredding: {data['rfp_number']}")

        result = shredder.shred_rfp(
            file_path=data['file_path'],
            rfp_number=data['rfp_number'],
            opportunity_name=data['opportunity_name'],
            due_date=data['due_date'],
            agency=data.get('agency'),
            naics_code=data.get('naics_code'),
            set_aside=data.get('set_aside'),
            create_tasks=data.get('create_tasks', True),
            auto_assign=data.get('auto_assign', False),
            output_dir=data.get('output_dir')
        )

        if result['status'] == 'success':
            send_json_response(handler, result, 200)
        else:
            send_json_response(handler, result, 500)

    except json.JSONDecodeError:
        send_json_response(handler, {'error': 'Invalid JSON'}, 400)
    except Exception as e:
        logger.error(f"Shredding failed: {e}")
        send_json_response(handler, {'error': str(e)}, 500)


def handle_shredding_status_api(handler, path: str, query_params: Dict):
    """
    GET /api/shredding/status/<opportunity_id>

    Get status of shredded RFP opportunity.

    Response:
    {
        "opportunity": {
            "id": str,
            "title": str,
            "status": str,
            "due_date": str,
            "metadata": {...}
        },
        "requirements": {
            "total": int,
            "mandatory": int,
            "compliant": int,
            "partial": int,
            "non_compliant": int,
            "not_started": int,
            "completion_rate": float
        },
        "tasks": {
            "total": int,
            "completed": int,
            "in_progress": int,
            "pending": int
        }
    }
    """
    if handler.command != 'GET':
        send_json_response(handler, {'error': 'Method not allowed'}, 405)
        return

    try:
        # Extract opportunity_id from path
        # Path format: /api/shredding/status/<opportunity_id>
        parts = path.split('/')
        if len(parts) < 5:
            send_json_response(handler, {'error': 'Missing opportunity_id'}, 400)
            return

        opportunity_id = parts[4]

        # Get status
        status = shredder.get_opportunity_status(opportunity_id)

        if 'error' in status:
            send_json_response(handler, status, 404)
        else:
            send_json_response(handler, status, 200)

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        send_json_response(handler, {'error': str(e)}, 500)


def handle_shredding_requirements_api(handler, path: str, query_params: Dict):
    """
    GET /api/shredding/requirements/<opportunity_id>

    List requirements for an opportunity.

    Query params:
    - section: Filter by section (C, L, M)
    - compliance_type: Filter by compliance type
    - category: Filter by category
    - priority: Filter by priority
    - status: Filter by compliance status
    - limit: Max results (default: 100)
    - offset: Offset for pagination (default: 0)

    Response:
    {
        "requirements": [
            {
                "id": str,
                "section": str,
                "page_number": int,
                "paragraph_id": str,
                "source_text": str,
                "compliance_type": str,
                "category": str,
                "priority": str,
                "risk_level": str,
                "compliance_status": str,
                "proposal_section": str,
                "proposal_page": int,
                "assignee_id": str,
                "assignee_type": str,
                "keywords": [str],
                "notes": str,
                "due_date": str
            },
            ...
        ],
        "total": int,
        "limit": int,
        "offset": int
    }
    """
    if handler.command != 'GET':
        send_json_response(handler, {'error': 'Method not allowed'}, 405)
        return

    try:
        # Extract opportunity_id
        parts = path.split('/')
        if len(parts) < 5:
            send_json_response(handler, {'error': 'Missing opportunity_id'}, 400)
            return

        opportunity_id = parts[4]

        # Parse query params
        section = query_params.get('section')
        compliance_type = query_params.get('compliance_type')
        category = query_params.get('category')
        priority = query_params.get('priority')
        status = query_params.get('status')
        limit = int(query_params.get('limit', ['100'])[0]) if 'limit' in query_params else 100
        offset = int(query_params.get('offset', ['0'])[0]) if 'offset' in query_params else 0

        # Build query
        conn = sqlite3.connect(shredder.db_path)
        cursor = conn.cursor()

        # Build WHERE clause
        where_clauses = ['opportunity_id = ?']
        params = [opportunity_id]

        if section:
            where_clauses.append('section = ?')
            params.append(section)
        if compliance_type:
            where_clauses.append('compliance_type = ?')
            params.append(compliance_type)
        if category:
            where_clauses.append('requirement_category = ?')
            params.append(category)
        if priority:
            where_clauses.append('priority = ?')
            params.append(priority)
        if status:
            where_clauses.append('compliance_status = ?')
            params.append(status)

        where_clause = ' AND '.join(where_clauses)

        # Count total
        cursor.execute(f"""
            SELECT COUNT(*) FROM requirements WHERE {where_clause}
        """, params)
        total = cursor.fetchone()[0]

        # Get requirements
        cursor.execute(f"""
            SELECT
                id, section, page_number, paragraph_id, source_text,
                compliance_type, requirement_category, priority, risk_level,
                compliance_status, proposal_section, proposal_page,
                assignee_id, assignee_type, assignee_name,
                keywords, notes, due_date
            FROM requirements
            WHERE {where_clause}
            ORDER BY section, id
            LIMIT ? OFFSET ?
        """, params + [limit, offset])

        rows = cursor.fetchall()
        conn.close()

        # Format requirements
        requirements = []
        for row in rows:
            req = {
                'id': row[0],
                'section': row[1],
                'page_number': row[2],
                'paragraph_id': row[3],
                'source_text': row[4],
                'compliance_type': row[5],
                'category': row[6],
                'priority': row[7],
                'risk_level': row[8],
                'compliance_status': row[9],
                'proposal_section': row[10],
                'proposal_page': row[11],
                'assignee_id': row[12],
                'assignee_type': row[13],
                'assignee_name': row[14],
                'keywords': json.loads(row[15]) if row[15] else [],
                'notes': row[16],
                'due_date': row[17]
            }
            requirements.append(req)

        send_json_response(handler, {
            'requirements': requirements,
            'total': total,
            'limit': limit,
            'offset': offset
        }, 200)

    except Exception as e:
        logger.error(f"Failed to get requirements: {e}")
        send_json_response(handler, {'error': str(e)}, 500)


def handle_shredding_requirement_update_api(handler, path: str, query_params: Dict):
    """
    PUT /api/shredding/requirements/<requirement_id>

    Update a requirement.

    Request body:
    {
        "compliance_status": str (optional),
        "proposal_section": str (optional),
        "proposal_page": int (optional),
        "assignee_id": str (optional),
        "assignee_type": str (optional),
        "assignee_name": str (optional),
        "notes": str (optional)
    }

    Response:
    {
        "status": "success",
        "requirement_id": str
    }
    """
    if handler.command != 'PUT':
        send_json_response(handler, {'error': 'Method not allowed'}, 405)
        return

    try:
        # Extract requirement_id
        parts = path.split('/')
        if len(parts) < 5:
            send_json_response(handler, {'error': 'Missing requirement_id'}, 400)
            return

        requirement_id = parts[4]

        # Parse body
        body = get_request_body(handler)
        data = json.loads(body)

        # Build UPDATE query
        update_fields = []
        params = []

        allowed_fields = {
            'compliance_status': 'compliance_status',
            'proposal_section': 'proposal_section',
            'proposal_page': 'proposal_page',
            'assignee_id': 'assignee_id',
            'assignee_type': 'assignee_type',
            'assignee_name': 'assignee_name',
            'notes': 'notes'
        }

        for field, db_field in allowed_fields.items():
            if field in data:
                update_fields.append(f"{db_field} = ?")
                params.append(data[field])

        if not update_fields:
            send_json_response(handler, {'error': 'No fields to update'}, 400)
            return

        # Always update updated_at
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        # Execute update
        conn = sqlite3.connect(shredder.db_path)
        cursor = conn.cursor()

        query = f"""
            UPDATE requirements
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        params.append(requirement_id)

        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            send_json_response(handler, {'error': 'Requirement not found'}, 404)
            return

        conn.close()

        send_json_response(handler, {
            'status': 'success',
            'requirement_id': requirement_id
        }, 200)

    except json.JSONDecodeError:
        send_json_response(handler, {'error': 'Invalid JSON'}, 400)
    except Exception as e:
        logger.error(f"Failed to update requirement: {e}")
        send_json_response(handler, {'error': str(e)}, 500)


def handle_shredding_matrix_api(handler, path: str, query_params: Dict):
    """
    GET /api/shredding/matrix/<opportunity_id>

    Export compliance matrix as CSV.

    Returns CSV file download.
    """
    if handler.command != 'GET':
        send_json_response(handler, {'error': 'Method not allowed'}, 405)
        return

    try:
        # Extract opportunity_id
        parts = path.split('/')
        if len(parts) < 5:
            send_json_response(handler, {'error': 'Missing opportunity_id'}, 400)
            return

        opportunity_id = parts[4]

        # Generate matrix
        matrix_file = shredder._generate_compliance_matrix(
            opportunity_id=opportunity_id,
            rfp_number=opportunity_id,  # Use ID as fallback
            output_dir='/tmp'
        )

        # Read CSV file
        with open(matrix_file, 'r', encoding='utf-8') as f:
            csv_content = f.read()

        # Send CSV response
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/csv')
        handler.send_header('Content-Disposition', f'attachment; filename="compliance_matrix_{opportunity_id}.csv"')
        handler.end_headers()
        handler.wfile.write(csv_content.encode('utf-8'))

    except Exception as e:
        logger.error(f"Failed to export matrix: {e}")
        send_json_response(handler, {'error': str(e)}, 500)
