"""Route handlers for TODO tag management API endpoints."""

from debug_logger import debug_log
from server.utils.error_handler import error_handler

try:
    from todos import get_todo_manager
    TODOS_AVAILABLE = True
except ImportError:
    TODOS_AVAILABLE = False


@error_handler
def handle_tags_list_api(handler):
    """Handle GET /api/todos/tags - List user's tags."""
    request_data = handler.get_request_body()
    user_id = request_data.get('user_id') if request_data else None

    if not user_id:
        handler.send_json_response({
            'status': 'error',
            'message': 'user_id is required'
        }, 400)
        return

    manager = get_todo_manager()
    result = manager.list_tags(user_id)

    debug_log(f"Tags list: {result['count']} tags", "🏷️")
    handler.send_json_response(result)


@error_handler
def handle_tags_create_api(handler):
    """Handle POST /api/todos/tags - Create new tag."""
    request_data = handler.get_request_body()
    if not request_data:
        handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
        return

    user_id = request_data.get('user_id')
    name = request_data.get('name')

    if not user_id or not name:
        handler.send_json_response({
            'status': 'error',
            'message': 'user_id and name are required'
        }, 400)
        return

    manager = get_todo_manager()
    result = manager.create_tag(
        user_id=user_id,
        name=name,
        color=request_data.get('color', '#6B7280')
    )

    if result['status'] == 'success':
        debug_log(f"Created tag: {name}", "✅")
        handler.send_json_response(result, 201)
    else:
        handler.send_json_response(result, 400)


@error_handler
def handle_tags_detail_api(handler, tag_id):
    """Handle GET /api/todos/tags/{id} - Get tag details."""
    manager = get_todo_manager()
    tag = manager.get_tag(tag_id)

    if tag:
        handler.send_json_response({'status': 'success', 'tag': tag})
    else:
        handler.send_json_response({'status': 'error', 'message': 'Tag not found'}, 404)


@error_handler
def handle_tags_update_api(handler, tag_id):
    """Handle PUT /api/todos/tags/{id} - Update tag."""
    request_data = handler.get_request_body()
    if not request_data:
        handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
        return

    manager = get_todo_manager()
    result = manager.update_tag(tag_id, request_data)

    if result['status'] == 'success':
        debug_log(f"Updated tag: {tag_id}", "✅")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 400)


@error_handler
def handle_tags_delete_api(handler, tag_id):
    """Handle DELETE /api/todos/tags/{id} - Delete tag."""
    manager = get_todo_manager()
    result = manager.delete_tag(tag_id)

    if result['status'] == 'success':
        debug_log(f"Deleted tag: {tag_id}", "🗑️")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)
