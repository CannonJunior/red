"""HTTP route handlers for Proposal and BNB tracking lists.

Routes:
  GET    /api/proposal-items              list all proposal items
  POST   /api/proposal-items              create a proposal item manually
  PUT    /api/proposal-items/{id}         update a proposal item
  DELETE /api/proposal-items/{id}         delete a proposal item
  GET    /api/bnb-items                   list all BNB items
  POST   /api/bnb-items                   create a BNB item manually
  PUT    /api/bnb-items/{id}              update a BNB item
  DELETE /api/bnb-items/{id}             delete a BNB item
  GET    /api/all-tasks                   list all tasks across all opportunities
"""

from server.utils.error_handler import error_handler

try:
    from proposal_tracking_api import get_tracking_manager
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False


def _item_id(path: str) -> str:
    """Extract trailing item ID from path."""
    return path.split('?')[0].split('/')[-1]


def _unavailable(handler):
    handler.send_json_response({'error': 'Tracking module not available'}, 503)


# ---- Proposal Items ----------------------------------------------------------

@error_handler
def handle_proposal_items_list_api(handler):
    """GET /api/proposal-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response(get_tracking_manager().list_proposal_items())


@error_handler
def handle_proposal_items_create_api(handler):
    """POST /api/proposal-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_tracking_manager().create_proposal_item(data)
    status = 201 if result.get('status') == 'success' else 400
    handler.send_json_response(result, status)


@error_handler
def handle_proposal_item_update_api(handler):
    """PUT /api/proposal-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_tracking_manager().update_proposal_item(_item_id(handler.path), data)
    handler.send_json_response(result)


@error_handler
def handle_proposal_item_delete_api(handler):
    """DELETE /api/proposal-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response(
        get_tracking_manager().delete_proposal_item(_item_id(handler.path)))


# ---- BNB Items ---------------------------------------------------------------

@error_handler
def handle_bnb_items_list_api(handler):
    """GET /api/bnb-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response(get_tracking_manager().list_bnb_items())


@error_handler
def handle_bnb_items_create_api(handler):
    """POST /api/bnb-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_tracking_manager().create_bnb_item(data)
    status = 201 if result.get('status') == 'success' else 400
    handler.send_json_response(result, status)


@error_handler
def handle_bnb_item_update_api(handler):
    """PUT /api/bnb-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_tracking_manager().update_bnb_item(_item_id(handler.path), data)
    handler.send_json_response(result)


@error_handler
def handle_bnb_item_delete_api(handler):
    """DELETE /api/bnb-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response(
        get_tracking_manager().delete_bnb_item(_item_id(handler.path)))


# ---- Hotwash Items -----------------------------------------------------------

@error_handler
def handle_hotwash_items_list_api(handler):
    """GET /api/hotwash-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response(get_tracking_manager().list_hotwash_items())


@error_handler
def handle_hotwash_items_create_api(handler):
    """POST /api/hotwash-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_tracking_manager().create_hotwash_item(data)
    status = 201 if result.get('status') == 'success' else 400
    handler.send_json_response(result, status)


@error_handler
def handle_hotwash_item_update_api(handler):
    """PUT /api/hotwash-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_tracking_manager().update_hotwash_item(_item_id(handler.path), data)
    handler.send_json_response(result)


@error_handler
def handle_hotwash_item_delete_api(handler):
    """DELETE /api/hotwash-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    handler.send_json_response(
        get_tracking_manager().delete_hotwash_item(_item_id(handler.path)))


# ---- All Tasks (cross-opportunity) -------------------------------------------

@error_handler
def handle_all_tasks_list_api(handler):
    """
    GET /api/all-tasks — list all tasks across all opportunities.

    Queries search_system.db directly to avoid extending the 993-line
    opportunities_api.py beyond maintainable size.

    Args:
        handler: HTTP request handler instance.
    """
    from config.database import DEFAULT_DB
    from server.db_pool import get_db
    with get_db(DEFAULT_DB) as conn:
        cursor = conn.execute("""
            SELECT t.id, t.opportunity_id, t.name, t.description,
                   t.start_date, t.end_date, t.status, t.progress,
                   t.assigned_to, t.created_at, t.updated_at,
                   o.name AS opportunity_name
            FROM tasks t
            LEFT JOIN opportunities o ON t.opportunity_id = o.id
            ORDER BY t.created_at DESC
        """)
        tasks = [dict(row) for row in cursor.fetchall()]
    handler.send_json_response({'status': 'success', 'tasks': tasks, 'count': len(tasks)})
