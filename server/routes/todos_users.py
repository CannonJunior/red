"""Route handlers for TODO user management API endpoints."""

from debug_logger import debug_log
from server.utils.error_handler import error_handler

try:
    from todos import get_todo_manager
    TODOS_AVAILABLE = True
except ImportError:
    TODOS_AVAILABLE = False


@error_handler
def handle_users_list_api(handler):
    """Handle GET /api/todos/users - List all users."""
    manager = get_todo_manager()
    users = manager.list_users()

    debug_log(f"Users list: {len(users)} users", "👥")
    handler.send_json_response({
        'status': 'success',
        'users': users,
        'count': len(users)
    })


@error_handler
def handle_users_create_api(handler):
    """Handle POST /api/todos/users - Create new user."""
    request_data = handler.get_request_body()
    if not request_data:
        handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
        return

    username = request_data.get('username')
    email = request_data.get('email')
    display_name = request_data.get('display_name')

    if not username or not email:
        handler.send_json_response({
            'status': 'error',
            'message': 'Username and email are required'
        }, 400)
        return

    manager = get_todo_manager()
    result = manager.create_user(username, email, display_name)

    if result['status'] == 'success':
        debug_log(f"Created user: {username}", "✅")
        handler.send_json_response(result, 201)
    else:
        handler.send_json_response(result, 400)


@error_handler
def handle_users_detail_api(handler, user_id):
    """Handle GET /api/todos/users/{id} - Get user details."""
    manager = get_todo_manager()
    user = manager.get_user(user_id)

    if user:
        handler.send_json_response({'status': 'success', 'user': user})
    else:
        handler.send_json_response({'status': 'error', 'message': 'User not found'}, 404)


@error_handler
def handle_users_update_api(handler, user_id):
    """Handle PUT /api/todos/users/{id} - Update user."""
    request_data = handler.get_request_body()
    if not request_data:
        handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
        return

    manager = get_todo_manager()
    result = manager.update_user(user_id, request_data)

    if result['status'] == 'success':
        debug_log(f"Updated user: {user_id}", "✅")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 400)


@error_handler
def handle_users_delete_api(handler, user_id):
    """Handle DELETE /api/todos/users/{id} - Delete user."""
    manager = get_todo_manager()
    result = manager.delete_user(user_id)

    if result['status'] == 'success':
        debug_log(f"Deleted user: {user_id}", "🗑️")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 404)
