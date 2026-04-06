"""HTTP route handlers for Shipley capture intelligence endpoints.

Routes:
  GET/POST  /api/opportunities/{id}/contacts
  PUT/DELETE /api/opportunities/{id}/contacts/{cid}
  GET/POST  /api/opportunities/{id}/competitors
  PUT/DELETE /api/opportunities/{id}/competitors/{cid}
  GET/POST  /api/opportunities/{id}/activities
  DELETE    /api/opportunities/{id}/activities/{aid}
  GET/PUT   /api/opportunities/{id}/win-strategy
  GET/PUT   /api/opportunities/{id}/ptw
"""

from debug_logger import debug_log
from server.utils.error_handler import error_handler

try:
    from capture_api import get_capture_manager
    CAPTURE_AVAILABLE = True
except ImportError:
    CAPTURE_AVAILABLE = False


def _opp_id(path: str) -> str:
    """Extract opportunity_id from path /api/opportunities/{id}/..."""
    return path.split('?')[0].split('/')[3]


def _sub_id(path: str) -> str:
    """Extract sub-resource id from path /api/opportunities/{id}/{res}/{sub_id}"""
    return path.split('?')[0].split('/')[5]


def _unavailable(handler):
    handler.send_json_response({'error': 'Capture module not available'}, 503)


# ---- Customer Contacts -------------------------------------------------------

@error_handler
def handle_contacts_list_api(handler):
    """GET /api/opportunities/{id}/contacts"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().list_contacts(_opp_id(handler.path))
    handler.send_json_response(result)


@error_handler
def handle_contacts_create_api(handler):
    """POST /api/opportunities/{id}/contacts"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_capture_manager().create_contact(_opp_id(handler.path), data)
    status = 201 if result.get('status') == 'success' else 400
    handler.send_json_response(result, status)


@error_handler
def handle_contact_update_api(handler):
    """PUT /api/opportunities/{id}/contacts/{cid}"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_capture_manager().update_contact(_sub_id(handler.path), data)
    handler.send_json_response(result)


@error_handler
def handle_contact_delete_api(handler):
    """DELETE /api/opportunities/{id}/contacts/{cid}"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().delete_contact(_sub_id(handler.path))
    handler.send_json_response(result)


# ---- Competitive Intelligence ------------------------------------------------

@error_handler
def handle_competitors_list_api(handler):
    """GET /api/opportunities/{id}/competitors"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().list_competitors(_opp_id(handler.path))
    handler.send_json_response(result)


@error_handler
def handle_competitors_create_api(handler):
    """POST /api/opportunities/{id}/competitors"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_capture_manager().create_competitor(_opp_id(handler.path), data)
    status = 201 if result.get('status') == 'success' else 400
    handler.send_json_response(result, status)


@error_handler
def handle_competitor_update_api(handler):
    """PUT /api/opportunities/{id}/competitors/{cid}"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_capture_manager().update_competitor(_sub_id(handler.path), data)
    handler.send_json_response(result)


@error_handler
def handle_competitor_delete_api(handler):
    """DELETE /api/opportunities/{id}/competitors/{cid}"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().delete_competitor(_sub_id(handler.path))
    handler.send_json_response(result)


# ---- Engagement Activities ---------------------------------------------------

@error_handler
def handle_activities_list_api(handler):
    """GET /api/opportunities/{id}/activities"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().list_activities(_opp_id(handler.path))
    handler.send_json_response(result)


@error_handler
def handle_activities_create_api(handler):
    """POST /api/opportunities/{id}/activities"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_capture_manager().create_activity(_opp_id(handler.path), data)
    status = 201 if result.get('status') == 'success' else 400
    handler.send_json_response(result, status)


@error_handler
def handle_activity_delete_api(handler):
    """DELETE /api/opportunities/{id}/activities/{aid}"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().delete_activity(_sub_id(handler.path))
    handler.send_json_response(result)


# ---- Win Strategy ------------------------------------------------------------

@error_handler
def handle_win_strategy_get_api(handler):
    """GET /api/opportunities/{id}/win-strategy"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().get_win_strategy(_opp_id(handler.path))
    handler.send_json_response(result)


@error_handler
def handle_win_strategy_put_api(handler):
    """PUT /api/opportunities/{id}/win-strategy"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_capture_manager().upsert_win_strategy(_opp_id(handler.path), data)
    handler.send_json_response(result)


# ---- Price-to-Win ------------------------------------------------------------

@error_handler
def handle_ptw_get_api(handler):
    """GET /api/opportunities/{id}/ptw"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    result = get_capture_manager().get_ptw(_opp_id(handler.path))
    handler.send_json_response(result)


@error_handler
def handle_ptw_put_api(handler):
    """PUT /api/opportunities/{id}/ptw"""
    if not CAPTURE_AVAILABLE:
        return _unavailable(handler)
    data = handler.get_request_body() or {}
    result = get_capture_manager().upsert_ptw(_opp_id(handler.path), data)
    handler.send_json_response(result)
