"""Opportunities route handlers for business opportunity tracking."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from debug_logger import debug_log
from server.utils.error_handler import error_handler
from server.request_models import (
    OpportunityCreateRequest,
    OpportunityUpdateRequest,
    validate_or_error,
)

_TEMPLATES_PATH = Path(__file__).parent.parent.parent / 'config' / 'tracking_task_templates.json'

try:
    from opportunities_api import (
        handle_opportunities_list_request,
        handle_opportunities_create_request,
        handle_opportunities_get_request,
        handle_opportunities_update_request,
        handle_opportunities_delete_request,
        handle_tasks_list_request,
        handle_tasks_create_request,
        handle_task_get_request,
        handle_tasks_update_request,
        handle_tasks_delete_request,
        handle_task_history_request,
        handle_pipeline_stats_request,
    )
    OPPORTUNITIES_AVAILABLE = True
except ImportError:
    OPPORTUNITIES_AVAILABLE = False

try:
    from opportunities_import_export import (
        handle_opportunities_delete_all_request,
        handle_opportunities_parse_csv_request,
        handle_opportunities_import_confirm_request,
        handle_opportunities_export_request,
    )
    IMPORT_EXPORT_AVAILABLE = True
except ImportError:
    IMPORT_EXPORT_AVAILABLE = False

try:
    from proposal_tracking_api import get_tracking_manager as _get_tm
    _TRACKING_AVAILABLE = True
except ImportError:
    _TRACKING_AVAILABLE = False


_HOTWASH_STAGES = {'negotiating', 'awarded', 'lost', 'no_bid'}


def _get_task_template(trigger: str) -> dict | None:
    """
    Load the task template for a given trigger type from config.

    Args:
        trigger (str): One of 'proposal', 'bnb', 'hotwash'.

    Returns:
        dict: Template dict if enabled, else None.
    """
    try:
        data = json.loads(_TEMPLATES_PATH.read_text()) if _TEMPLATES_PATH.exists() else {}
        templates = data.get('templates', [])
        return next(
            (t for t in templates if t.get('trigger') == trigger and t.get('enabled', True)),
            None,
        )
    except Exception:
        return None


def _create_tracking_task(opportunity_id: str, trigger: str) -> None:
    """
    Create an auto-task for an opportunity based on a tracking event template.

    Args:
        opportunity_id (str): The opportunity to attach the task to.
        trigger (str): Template trigger key ('proposal', 'bnb', 'hotwash').
    """
    if not OPPORTUNITIES_AVAILABLE:
        return
    template = _get_task_template(trigger)
    if not template:
        return
    try:
        today = datetime.now()
        data = {
            'name': template['task_name'],
            'description': template.get('task_description', ''),
            'start_date': today.strftime('%Y-%m-%d'),
            'end_date': (today + timedelta(days=14)).strftime('%Y-%m-%d'),
        }
        result = handle_tasks_create_request(opportunity_id, data)
        if result.get('status') == 'success':
            print(f"✅ Auto-task created: '{template['task_name']}' for {opportunity_id}")
    except Exception as e:
        print(f"⚠️  Failed to create tracking task for {opportunity_id}: {e}")


def _trigger_tracking(opportunity_id: str, result: dict) -> None:
    """Auto-create Proposal, BNB, or Hotwash item on stage change."""
    if not _TRACKING_AVAILABLE:
        return
    opp = result.get('opportunity', {})
    stage = opp.get('pipeline_stage', '')
    name = opp.get('name', opportunity_id)
    try:
        if stage == 'active':
            tracking_result = _get_tm().ensure_proposal_item(opportunity_id, name)
            if tracking_result.get('status') == 'success':
                _create_tracking_task(opportunity_id, 'proposal')
        elif stage == 'bid_decision':
            tracking_result = _get_tm().ensure_bnb_item(opportunity_id, name)
            if tracking_result.get('status') == 'success':
                _create_tracking_task(opportunity_id, 'bnb')
        elif stage in _HOTWASH_STAGES:
            tracking_result = _get_tm().ensure_hotwash_item(opportunity_id, name, trigger_stage=stage)
            if tracking_result.get('status') == 'success':
                _create_tracking_task(opportunity_id, 'hotwash')
    except Exception as e:
        print(f"⚠️  Tracking trigger failed for {opportunity_id}: {e}")


@error_handler
def handle_opportunities_list_api(handler):
    """Handle GET /api/opportunities - List all opportunities."""
    request_data = handler.get_request_body()
    filters = request_data if request_data else {}

    result = handle_opportunities_list_request(filters)

    debug_log(f"Opportunities list: {result.get('count', 0)} opportunities", "📋")
    handler.send_json_response(result)


@error_handler
def handle_opportunities_create_api(handler):
    """Handle POST /api/opportunities - Create new opportunity."""
    raw = handler.get_request_body()
    if raw is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    validated, err = validate_or_error(OpportunityCreateRequest, raw)
    if err:
        handler.send_json_response({'error': f'Validation error: {err}'}, 400)
        return

    # Use the validated dict so defaults + coercions are applied
    request_data = validated.model_dump() if hasattr(validated, 'model_dump') else validated
    result = handle_opportunities_create_request(request_data)

    if result.get('status') == 'success':
        debug_log(f"Created opportunity: {request_data.get('name', 'Unknown')}", "✅")
        handler.send_json_response(result, 201)
    else:
        print(f"❌ Failed to create opportunity: {result.get('message', 'Unknown error')}")
        handler.send_json_response(result, 400)


@error_handler
def handle_opportunities_detail_api(handler):
    """Handle GET /api/opportunities/{opportunity_id} - Get opportunity by ID."""
    # Extract opportunity ID from path
    opportunity_id = handler.path.split('/')[-1]

    result = handle_opportunities_get_request(opportunity_id)

    if result.get('status') == 'success':
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


@error_handler
def handle_opportunities_update_api(handler):
    """Handle PUT/PATCH /api/opportunities/{opportunity_id} - Update opportunity."""
    # Extract opportunity ID from path
    opportunity_id = handler.path.split('/')[-1]

    raw = handler.get_request_body()
    if raw is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    validated, err = validate_or_error(OpportunityUpdateRequest, raw)
    if err:
        handler.send_json_response({'error': f'Validation error: {err}'}, 400)
        return

    request_data = validated.model_dump(exclude_none=True) if hasattr(validated, 'model_dump') else validated
    result = handle_opportunities_update_request(opportunity_id, request_data)

    if result.get('status') == 'success':
        debug_log(f"Updated opportunity: {opportunity_id}", "✅")
        _trigger_tracking(opportunity_id, result)
        handler.send_json_response(result)
    else:
        print(f"❌ Failed to update opportunity: {result.get('message', 'Unknown error')}")
        handler.send_json_response(result, 400)


@error_handler
def handle_opportunities_delete_api(handler, opportunity_id):
    """Handle DELETE /api/opportunities/{opportunity_id} - Delete opportunity."""
    result = handle_opportunities_delete_request(opportunity_id)

    if result.get('status') == 'success':
        debug_log(f"Deleted opportunity: {opportunity_id}", "🗑️")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


@error_handler
def handle_tasks_list_api(handler, opportunity_id):
    """Handle GET /api/opportunities/{opportunity_id}/tasks - List tasks for opportunity."""
    result = handle_tasks_list_request(opportunity_id)

    if result.get('status') == 'success':
        debug_log(f"Tasks list for opportunity {opportunity_id}: {len(result.get('tasks', []))} tasks", "📋")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


@error_handler
def handle_tasks_create_api(handler, opportunity_id):
    """Handle POST /api/opportunities/{opportunity_id}/tasks - Create new task."""
    request_data = handler.get_request_body()
    if request_data is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    result = handle_tasks_create_request(opportunity_id, request_data)

    if result.get('status') == 'success':
        debug_log(f"Created task for opportunity {opportunity_id}: {request_data.get('name', 'Unknown')}", "✅")
        handler.send_json_response(result, 201)
    else:
        print(f"❌ Failed to create task: {result.get('message', 'Unknown error')}")
        handler.send_json_response(result, 400)


@error_handler
def handle_task_get_api(handler, task_id):
    """Handle GET /api/tasks/{task_id} - Get task by ID."""
    result = handle_task_get_request(task_id)

    if result.get('status') == 'success':
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


@error_handler
def handle_task_update_api(handler, task_id):
    """Handle POST /api/tasks/{task_id} - Update task."""
    request_data = handler.get_request_body()
    if request_data is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    result = handle_tasks_update_request(task_id, request_data)

    if result.get('status') == 'success':
        debug_log(f"Updated task: {task_id}", "✅")
        handler.send_json_response(result)
    else:
        print(f"❌ Failed to update task: {result.get('message', 'Unknown error')}")
        handler.send_json_response(result, 400)


@error_handler
def handle_task_delete_api(handler, task_id):
    """Handle DELETE /api/tasks/{task_id} - Delete task."""
    result = handle_tasks_delete_request(task_id)

    if result.get('status') == 'success':
        debug_log(f"Deleted task: {task_id}", "🗑️")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


@error_handler
def handle_task_history_api(handler, task_id):
    """Handle GET /api/tasks/{task_id}/history - Get task history."""
    result = handle_task_history_request(task_id)

    if result.get('status') == 'success':
        debug_log(f"Task history for {task_id}: {len(result.get('history', []))} entries", "📜")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


# ---------------------------------------------------------------------------
# Import / Export / Delete-all handlers
# ---------------------------------------------------------------------------

@error_handler
def handle_opportunities_delete_all_api(handler):
    """Handle DELETE /api/opportunities - Delete all opportunities."""
    if not IMPORT_EXPORT_AVAILABLE:
        handler.send_json_response({'error': 'Import/export module not available'}, 503)
        return
    result = handle_opportunities_delete_all_request()
    if result.get('status') == 'success':
        debug_log(f"Deleted all opportunities: {result.get('deleted_count', 0)}", "🗑️")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 500)


@error_handler
def handle_opportunities_import_parse_api(handler):
    """Handle POST /api/opportunities/import/parse - Parse CSV headers & preview."""
    if not IMPORT_EXPORT_AVAILABLE:
        handler.send_json_response({'error': 'Import/export module not available'}, 503)
        return
    body = handler.get_request_body()
    if body is None or 'csv_content' not in body:
        handler.send_json_response({'error': 'Missing csv_content field'}, 400)
        return
    result = handle_opportunities_parse_csv_request(body['csv_content'])
    handler.send_json_response(result)


@error_handler
def handle_opportunities_import_confirm_api(handler):
    """Handle POST /api/opportunities/import/confirm - Finalize CSV import."""
    if not IMPORT_EXPORT_AVAILABLE:
        handler.send_json_response({'error': 'Import/export module not available'}, 503)
        return
    body = handler.get_request_body()
    if body is None or 'csv_content' not in body or 'field_map' not in body:
        handler.send_json_response({'error': 'Missing csv_content or field_map'}, 400)
        return
    result = handle_opportunities_import_confirm_request(
        body['csv_content'], body['field_map']
    )
    debug_log(f"CSV import: {result.get('imported', 0)} imported, "
              f"{result.get('skipped', 0)} skipped", "📥")
    handler.send_json_response(result)


@error_handler
def handle_pipeline_stats_api(handler):
    """Handle GET /api/pipeline/stats - Pipeline health metrics."""
    result = handle_pipeline_stats_request()
    if result.get('status') == 'success':
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 500)


@error_handler
def handle_opportunities_export_api(handler):
    """Handle GET /api/opportunities/export?format=csv|json - Download export."""
    if not IMPORT_EXPORT_AVAILABLE:
        handler.send_json_response({'error': 'Import/export module not available'}, 503)
        return
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(handler.path)
    params = parse_qs(parsed.query)
    fmt = params.get('format', ['csv'])[0]

    result = handle_opportunities_export_request(fmt)
    if result.get('status') != 'success':
        handler.send_json_response(result, 500)
        return

    content = result['content']
    handler.send_response(200)
    handler.send_header('Content-Type', result['content_type'])
    handler.send_header('Content-Disposition',
                        f'attachment; filename="{result["filename"]}"')
    handler.send_header('Content-Length', str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)
    debug_log(f"Exported opportunities as {fmt}: {len(content)} bytes", "📤")
