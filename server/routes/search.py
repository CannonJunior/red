"""Search route handlers for universal search API."""

from debug_logger import debug_log
from server.utils.error_handler import error_handler

try:
    from search_api import (
        handle_search_request,
        handle_folders_request,
        handle_create_folder_request,
        handle_tags_request,
        handle_add_object_request
    )
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False


@error_handler
def handle_search_api(handler):
    """Handle universal search API requests."""
    request_data = handler.get_request_body()
    if request_data is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    search_result = handle_search_request(request_data)
    debug_log(f"Search: '{request_data.get('query', '')}' -> {search_result.get('data', {}).get('total_count', 0)} results", "🔍")
    handler.send_json_response(search_result)


@error_handler
def handle_search_folders_api(handler):
    """Handle folders listing API requests."""
    folders_result = handle_folders_request()
    debug_log(f"Folders: {len(folders_result.get('folders', []))} folders", "📁")
    handler.send_json_response(folders_result)


@error_handler
def handle_search_create_folder_api(handler):
    """Handle folder creation API requests."""
    request_data = handler.get_request_body()
    if request_data is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    create_result = handle_create_folder_request(request_data)
    debug_log(f"Created folder: {request_data.get('name', 'Unknown')}", "✅")
    handler.send_json_response(create_result)


@error_handler
def handle_search_tags_api(handler):
    """Handle tags listing API requests."""
    tags_result = handle_tags_request()
    debug_log(f"Tags: {len(tags_result.get('tags', []))} tags", "🏷️")
    handler.send_json_response(tags_result)


@error_handler
def handle_search_add_object_api(handler):
    """Handle add object API requests."""
    request_data = handler.get_request_body()
    if request_data is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    add_result = handle_add_object_request(request_data)
    debug_log(f"Added object: {request_data.get('object_type', 'unknown')}", "➕")
    handler.send_json_response(add_result)
