"""Route handlers for TODO list management API endpoints."""

from debug_logger import debug_log, error_log
from server.utils.error_handler import error_handler

try:
    from todos import get_todo_manager
    TODOS_AVAILABLE = True
except ImportError:
    TODOS_AVAILABLE = False


@error_handler
def handle_lists_list_api(handler):
    """Handle GET /api/todos/lists - List user's todo lists."""
    query_params = handler.get_query_params()
    user_id = query_params.get('user_id')

    if not user_id:
        handler.send_json_response({
            'status': 'error',
            'message': 'user_id is required'
        }, 400)
        return

    manager = get_todo_manager()
    lists = manager.list_lists(user_id)

    debug_log(f"Todo lists: {len(lists)} lists for user {user_id}", "📋")
    handler.send_json_response({
        'status': 'success',
        'lists': lists,
        'count': len(lists)
    })


@error_handler
def handle_lists_create_api(handler):
    """Handle POST /api/todos/lists - Create new list."""
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
    result = manager.create_list(
        user_id=user_id,
        name=name,
        description=request_data.get('description'),
        color=request_data.get('color', '#3B82F6'),
        icon=request_data.get('icon', 'list')
    )

    if result['status'] == 'success':
        debug_log(f"Created list: {name}", "✅")
        handler.send_json_response(result, 201)
    else:
        handler.send_json_response(result, 400)


@error_handler
def handle_lists_detail_api(handler, list_id):
    """Handle GET /api/todos/lists/{id} - Get list details."""
    manager = get_todo_manager()
    todo_list = manager.get_list(list_id)

    if todo_list:
        handler.send_json_response({'status': 'success', 'list': todo_list})
    else:
        handler.send_json_response({'status': 'error', 'message': 'List not found'}, 404)


@error_handler
def handle_lists_update_api(handler, list_id):
    """Handle PUT /api/todos/lists/{id} - Update list."""
    request_data = handler.get_request_body()
    if not request_data:
        handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
        return

    manager = get_todo_manager()
    result = manager.update_list(list_id, request_data)

    if result['status'] == 'success':
        debug_log(f"Updated list: {list_id}", "✅")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 400)


@error_handler
def handle_lists_delete_api(handler, list_id):
    """Handle DELETE /api/todos/lists/{id} - Delete list."""
    manager = get_todo_manager()
    result = manager.delete_list(list_id)

    if result['status'] == 'success':
        debug_log(f"Deleted list: {list_id}", "🗑️")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


@error_handler
def handle_lists_share_api(handler, list_id):
    """Handle POST /api/todos/lists/{id}/share - Share list with user."""
    request_data = handler.get_request_body()
    if not request_data:
        handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
        return

    user_id = request_data.get('user_id')
    permission = request_data.get('permission', 'view')

    if not user_id:
        handler.send_json_response({
            'status': 'error',
            'message': 'user_id is required'
        }, 400)
        return

    manager = get_todo_manager()
    result = manager.share_list(list_id, user_id, permission)

    if result['status'] == 'success':
        debug_log(f"Shared list {list_id} with user {user_id}", "🔗")
        handler.send_json_response(result, 201)
    else:
        handler.send_json_response(result, 400)


@error_handler
def handle_lists_unshare_api(handler, list_id):
    """Handle DELETE /api/todos/lists/{id}/share - Unshare list."""
    request_data = handler.get_request_body()
    user_id = request_data.get('user_id') if request_data else None

    if not user_id:
        handler.send_json_response({
            'status': 'error',
            'message': 'user_id is required'
        }, 400)
        return

    manager = get_todo_manager()
    result = manager.unshare_list(list_id, user_id)

    if result['status'] == 'success':
        debug_log(f"Unshared list {list_id} from user {user_id}", "🔓")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)


@error_handler
def handle_lists_shares_api(handler, list_id):
    """Handle GET /api/todos/lists/{id}/shares - Get list shares."""
    manager = get_todo_manager()
    result = manager.get_list_shares(list_id)

    debug_log(f"List shares: {result['count']} users", "👥")
    handler.send_json_response(result)


@error_handler
def handle_shared_lists_api(handler):
    """Handle GET /api/todos/shared - Get lists shared with user."""
    request_data = handler.get_request_body()
    user_id = request_data.get('user_id') if request_data else None

    if not user_id:
        handler.send_json_response({
            'status': 'error',
            'message': 'user_id is required'
        }, 400)
        return

    manager = get_todo_manager()
    result = manager.get_shared_lists(user_id)

    debug_log(f"Shared lists: {result['count']} lists", "🔗")
    handler.send_json_response(result)
