"""Prompts route handlers for prompt library management."""

from debug_logger import debug_log
from server_decorators import require_system

try:
    from prompts_api import (
        handle_prompts_list_request,
        handle_prompts_create_request,
        handle_prompts_get_request,
        handle_prompts_update_request,
        handle_prompts_delete_request,
        handle_prompts_use_request,
        handle_prompts_search_request
    )
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False


def handle_prompts_list_api(handler):
    """Handle GET /api/prompts - List all prompts."""
    try:
        # Parse query parameters
        query_params = {}
        # For now, just list all prompts
        result = handle_prompts_list_request(query_params)

        debug_log(f"Prompts list: {result.get('count', 0)} prompts", "📋")
        handler.send_json_response(result)

    except Exception as e:
        print(f"❌ Prompts list API error: {e}")
        handler.send_json_response({'error': f'Prompts list failed: {str(e)}'}, 500)


def handle_prompts_create_api(handler):
    """Handle POST /api/prompts - Create new prompt."""
    try:
        # Read request body
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_prompts_create_request(request_data)

        if result.get('status') == 'success':
            debug_log(f"Created prompt: {request_data.get('name', 'Unknown')}", "✅")
            handler.send_json_response(result, 201)
        else:
            print(f"❌ Failed to create prompt: {result.get('message', 'Unknown error')}")
            handler.send_json_response(result, 400)

    except Exception as e:
        print(f"❌ Prompts create API error: {e}")
        handler.send_json_response({'error': f'Prompts create failed: {str(e)}'}, 500)


def handle_prompts_detail_api(handler):
    """Handle GET /api/prompts/{prompt_id} - Get prompt by ID."""
    try:
        # Extract prompt ID from path
        prompt_id = handler.path.split('/')[-1]

        result = handle_prompts_get_request(prompt_id)

        if result.get('status') == 'success':
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Prompts detail API error: {e}")
        handler.send_json_response({'error': f'Prompts detail failed: {str(e)}'}, 500)


def handle_prompts_update_api(handler):
    """Handle PUT/POST /api/prompts/{prompt_id} - Update prompt."""
    try:
        # Extract prompt ID from path
        prompt_id = handler.path.split('/')[-1]

        # Read request body
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_prompts_update_request(prompt_id, request_data)

        if result.get('status') == 'success':
            debug_log(f"Updated prompt: {prompt_id}", "✅")
            handler.send_json_response(result)
        else:
            print(f"❌ Failed to update prompt: {result.get('message', 'Unknown error')}")
            handler.send_json_response(result, 400)

    except Exception as e:
        print(f"❌ Prompts update API error: {e}")
        handler.send_json_response({'error': f'Prompts update failed: {str(e)}'}, 500)


def handle_prompts_delete_api(handler, prompt_id):
    """Handle DELETE /api/prompts/{prompt_id} - Delete prompt."""
    try:
        result = handle_prompts_delete_request(prompt_id)

        if result.get('status') == 'success':
            debug_log(f"Deleted prompt: {prompt_id}", "🗑️")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Prompts delete API error: {e}")
        handler.send_json_response({'error': f'Prompts delete failed: {str(e)}'}, 500)


def handle_prompts_use_api(handler):
    """Handle POST /api/prompts/use - Use a prompt (get content)."""
    try:
        # Read request body
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_prompts_use_request(request_data)

        if result.get('status') == 'success':
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Prompts use API error: {e}")
        handler.send_json_response({'error': f'Prompts use failed: {str(e)}'}, 500)


def handle_prompts_search_api(handler):
    """Handle POST /api/prompts/search - Search prompts."""
    try:
        # Read request body
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_prompts_search_request(request_data)

        debug_log(f"Prompts search: {result.get('count', 0)} results", "🔍")
        handler.send_json_response(result)

    except Exception as e:
        print(f"❌ Prompts search API error: {e}")
        handler.send_json_response({'error': f'Prompts search failed: {str(e)}'}, 500)
