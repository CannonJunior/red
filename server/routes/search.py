"""Search route handlers for universal search API."""

from debug_logger import debug_log

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


def handle_search_api(handler):
    """Handle universal search API requests."""
    try:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        search_result = handle_search_request(request_data)
        debug_log(f"Search: '{request_data.get('query', '')}' -> {search_result.get('data', {}).get('total_count', 0)} results", "🔍")
        handler.send_json_response(search_result)

    except Exception as e:
        print(f"❌ Search API error: {e}")
        handler.send_json_response({'error': f'Search failed: {str(e)}'}, 500)


def handle_search_folders_api(handler):
    """Handle folders listing API requests."""
    try:
        folders_result = handle_folders_request()
        debug_log(f"Folders: {len(folders_result.get('folders', []))} folders", "📁")
        handler.send_json_response(folders_result)

    except Exception as e:
        print(f"❌ Folders API error: {e}")
        handler.send_json_response({'error': f'Failed to load folders: {str(e)}'}, 500)


def handle_search_create_folder_api(handler):
    """Handle folder creation API requests."""
    try:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        create_result = handle_create_folder_request(request_data)
        debug_log(f"Created folder: {request_data.get('name', 'Unknown')}", "✅")
        handler.send_json_response(create_result)

    except Exception as e:
        print(f"❌ Create folder API error: {e}")
        handler.send_json_response({'error': f'Create folder failed: {str(e)}'}, 500)


def handle_search_tags_api(handler):
    """Handle tags listing API requests."""
    try:
        tags_result = handle_tags_request()
        debug_log(f"Tags: {len(tags_result.get('tags', []))} tags", "🏷️")
        handler.send_json_response(tags_result)

    except Exception as e:
        print(f"❌ Tags API error: {e}")
        handler.send_json_response({'error': f'Failed to load tags: {str(e)}'}, 500)


def handle_search_add_object_api(handler):
    """Handle add object API requests."""
    try:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        add_result = handle_add_object_request(request_data)
        debug_log(f"Added object: {request_data.get('object_type', 'unknown')}", "➕")
        handler.send_json_response(add_result)

    except Exception as e:
        print(f"❌ Add object API error: {e}")
        handler.send_json_response({'error': f'Add object failed: {str(e)}'}, 500)
