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
"""

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

def handle_proposal_items_list_api(handler):
    """GET /api/proposal-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        handler.send_json_response(get_tracking_manager().list_proposal_items())
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)


def handle_proposal_items_create_api(handler):
    """POST /api/proposal-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        data = handler.get_request_body() or {}
        result = get_tracking_manager().create_proposal_item(data)
        status = 201 if result.get('status') == 'success' else 400
        handler.send_json_response(result, status)
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)


def handle_proposal_item_update_api(handler):
    """PUT /api/proposal-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        data = handler.get_request_body() or {}
        result = get_tracking_manager().update_proposal_item(_item_id(handler.path), data)
        handler.send_json_response(result)
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)


def handle_proposal_item_delete_api(handler):
    """DELETE /api/proposal-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        handler.send_json_response(
            get_tracking_manager().delete_proposal_item(_item_id(handler.path)))
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)


# ---- BNB Items ---------------------------------------------------------------

def handle_bnb_items_list_api(handler):
    """GET /api/bnb-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        handler.send_json_response(get_tracking_manager().list_bnb_items())
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)


def handle_bnb_items_create_api(handler):
    """POST /api/bnb-items"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        data = handler.get_request_body() or {}
        result = get_tracking_manager().create_bnb_item(data)
        status = 201 if result.get('status') == 'success' else 400
        handler.send_json_response(result, status)
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)


def handle_bnb_item_update_api(handler):
    """PUT /api/bnb-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        data = handler.get_request_body() or {}
        result = get_tracking_manager().update_bnb_item(_item_id(handler.path), data)
        handler.send_json_response(result)
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)


def handle_bnb_item_delete_api(handler):
    """DELETE /api/bnb-items/{id}"""
    if not TRACKING_AVAILABLE:
        return _unavailable(handler)
    try:
        handler.send_json_response(
            get_tracking_manager().delete_bnb_item(_item_id(handler.path)))
    except Exception as e:
        handler.send_json_response({'error': str(e)}, 500)
