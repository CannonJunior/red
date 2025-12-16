"""Route handlers for TODO list API endpoints."""

from debug_logger import debug_log, error_log

try:
    from todos import get_todo_manager
    TODOS_AVAILABLE = True
except ImportError:
    TODOS_AVAILABLE = False


# User routes
def handle_users_list_api(handler):
    """Handle GET /api/todos/users - List all users."""
    try:
        manager = get_todo_manager()
        users = manager.list_users()

        debug_log(f"Users list: {len(users)} users", "👥")
        handler.send_json_response({
            'status': 'success',
            'users': users,
            'count': len(users)
        })

    except Exception as e:
        error_log(f"Users list API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_users_create_api(handler):
    """Handle POST /api/todos/users - Create new user."""
    try:
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

    except Exception as e:
        error_log(f"User create API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_users_detail_api(handler, user_id):
    """Handle GET /api/todos/users/{id} - Get user details."""
    try:
        manager = get_todo_manager()
        user = manager.get_user(user_id)

        if user:
            handler.send_json_response({'status': 'success', 'user': user})
        else:
            handler.send_json_response({'status': 'error', 'message': 'User not found'}, 404)

    except Exception as e:
        error_log(f"User detail API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# Todo List routes
def handle_lists_list_api(handler):
    """Handle GET /api/todos/lists - List user's todo lists."""
    try:
        # Get query parameters from URL
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

    except Exception as e:
        error_log(f"Lists list API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_lists_create_api(handler):
    """Handle POST /api/todos/lists - Create new list."""
    try:
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

    except Exception as e:
        error_log(f"List create API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_lists_detail_api(handler, list_id):
    """Handle GET /api/todos/lists/{id} - Get list details."""
    try:
        manager = get_todo_manager()
        todo_list = manager.get_list(list_id)

        if todo_list:
            handler.send_json_response({'status': 'success', 'list': todo_list})
        else:
            handler.send_json_response({'status': 'error', 'message': 'List not found'}, 404)

    except Exception as e:
        error_log(f"List detail API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# Todo routes
def handle_todos_list_api(handler):
    """Handle GET /api/todos - List todos."""
    try:
        # Get query parameters from URL
        query_params = handler.get_query_params()
        user_id = query_params.get('user_id')

        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        # Extract filters from query parameters
        filters = {}
        if query_params.get('list_id'):
            filters['list_id'] = query_params['list_id']
        if query_params.get('status'):
            filters['status'] = query_params['status']
        if query_params.get('bucket'):
            filters['bucket'] = query_params['bucket']
        if query_params.get('assigned_to'):
            filters['assigned_to'] = query_params['assigned_to']

        manager = get_todo_manager()
        result = manager.list_todos(user_id, filters if filters else None)

        debug_log(f"Todos list: {result['count']} todos for user {user_id}", "📝")
        handler.send_json_response(result)

    except Exception as e:
        error_log(f"Todos list API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_create_api(handler):
    """Handle POST /api/todos - Create new todo.

    Supports two input modes:
    1. Natural Language: {"user_id": "...", "input": "Call mom tomorrow @high #personal"}
    2. Structured: {"user_id": "...", "title": "Call mom", "priority": "high", ...}

    The natural language mode uses the NLP parser to extract structured data.
    """
    try:
        from todos.nlp_parser import parse_natural_language

        request_data = handler.get_request_body()
        if not request_data:
            handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
            return

        user_id = request_data.get('user_id')
        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        # Check if natural language input is provided
        natural_input = request_data.get('input')

        if natural_input:
            # Mode 1: Natural Language Processing
            debug_log(f"Creating todo from NLP input: '{natural_input}'", "🧠")

            # Parse the natural language input
            parsed_data = parse_natural_language(natural_input, user_id)

            # Use parsed data as the base, allow overrides from request
            title = parsed_data.get('title')
            if not title:
                handler.send_json_response({
                    'status': 'error',
                    'message': 'Could not extract a title from input'
                }, 400)
                return

            kwargs = {
                'priority': parsed_data.get('priority', 'medium'),
                'due_date': parsed_data.get('due_date'),
                'due_time': parsed_data.get('due_time'),
                'bucket': parsed_data.get('bucket', 'inbox'),
                'tags': parsed_data.get('tags', []),
                'description': parsed_data.get('description')
            }

            # Allow explicit overrides from request data
            override_fields = [
                'list_id', 'status', 'priority', 'due_date', 'due_time',
                'reminder_date', 'reminder_time', 'bucket', 'tags',
                'subtasks', 'parent_id', 'assigned_to', 'recurrence',
                'position', 'metadata', 'description'
            ]
            for field in override_fields:
                if field in request_data and field != 'input':
                    kwargs[field] = request_data[field]

        else:
            # Mode 2: Traditional Structured Input
            title = request_data.get('title')
            if not title:
                handler.send_json_response({
                    'status': 'error',
                    'message': 'title or input is required'
                }, 400)
                return

            # Extract optional fields
            kwargs = {}
            optional_fields = [
                'list_id', 'description', 'status', 'priority', 'due_date',
                'due_time', 'reminder_date', 'reminder_time', 'bucket',
                'tags', 'subtasks', 'parent_id', 'assigned_to', 'recurrence',
                'position', 'metadata'
            ]

            for field in optional_fields:
                if field in request_data:
                    kwargs[field] = request_data[field]

        manager = get_todo_manager()
        result = manager.create_todo(user_id, title, **kwargs)

        if result['status'] == 'success':
            debug_log(f"Created todo: {title}", "✅")
            handler.send_json_response(result, 201)
        else:
            handler.send_json_response(result, 400)

    except Exception as e:
        error_log(f"Todo create API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_detail_api(handler, todo_id):
    """Handle GET /api/todos/{id} - Get todo details."""
    try:
        manager = get_todo_manager()
        todo = manager.get_todo(todo_id)

        if todo:
            handler.send_json_response({'status': 'success', 'todo': todo})
        else:
            handler.send_json_response({'status': 'error', 'message': 'Todo not found'}, 404)

    except Exception as e:
        error_log(f"Todo detail API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_update_api(handler, todo_id):
    """Handle PUT /api/todos/{id} - Update todo."""
    try:
        request_data = handler.get_request_body()
        if not request_data:
            handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
            return

        user_id = request_data.get('user_id')
        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        # Extract updates (exclude user_id from updates)
        updates = {k: v for k, v in request_data.items() if k != 'user_id'}

        manager = get_todo_manager()
        result = manager.update_todo(todo_id, user_id, updates)

        if result['status'] == 'success':
            debug_log(f"Updated todo: {todo_id}", "✅")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 400 if 'not found' not in result.get('message', '') else 404)

    except Exception as e:
        error_log(f"Todo update API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_delete_api(handler, todo_id):
    """Handle DELETE /api/todos/{id} - Delete todo."""
    try:
        request_data = handler.get_request_body()
        user_id = request_data.get('user_id') if request_data else None

        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        manager = get_todo_manager()
        result = manager.delete_todo(todo_id, user_id)

        if result['status'] == 'success':
            debug_log(f"Deleted todo: {todo_id}", "🗑️")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        error_log(f"Todo delete API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_complete_api(handler, todo_id):
    """Handle POST /api/todos/{id}/complete - Mark todo as complete."""
    try:
        request_data = handler.get_request_body()
        user_id = request_data.get('user_id') if request_data else None

        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        manager = get_todo_manager()
        result = manager.complete_todo(todo_id, user_id)

        if result['status'] == 'success':
            debug_log(f"Completed todo: {todo_id}", "✅")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 400)

    except Exception as e:
        error_log(f"Todo complete API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_archive_api(handler, todo_id):
    """Handle POST /api/todos/{id}/archive - Archive todo."""
    try:
        request_data = handler.get_request_body()
        user_id = request_data.get('user_id') if request_data else None

        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        manager = get_todo_manager()
        result = manager.archive_todo(todo_id, user_id)

        if result['status'] == 'success':
            debug_log(f"Archived todo: {todo_id}", "📦")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 400)

    except Exception as e:
        error_log(f"Todo archive API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# Smart query routes
def handle_todos_today_api(handler):
    """Handle GET /api/todos/today - Get today's todos."""
    try:
        request_data = handler.get_request_body()
        user_id = request_data.get('user_id') if request_data else None

        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        manager = get_todo_manager()
        result = manager.get_today_todos(user_id)

        debug_log(f"Today's todos: {result['count']} todos", "📅")
        handler.send_json_response(result)

    except Exception as e:
        error_log(f"Today todos API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_upcoming_api(handler):
    """Handle GET /api/todos/upcoming - Get upcoming todos."""
    try:
        request_data = handler.get_request_body()
        user_id = request_data.get('user_id') if request_data else None

        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        manager = get_todo_manager()
        result = manager.get_upcoming_todos(user_id)

        debug_log(f"Upcoming todos: {result['count']} todos", "📆")
        handler.send_json_response(result)

    except Exception as e:
        error_log(f"Upcoming todos API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_todos_search_api(handler):
    """Handle GET /api/todos/search - Search todos."""
    try:
        request_data = handler.get_request_body()
        if not request_data:
            handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
            return

        user_id = request_data.get('user_id')
        query = request_data.get('query', '')

        if not user_id:
            handler.send_json_response({
                'status': 'error',
                'message': 'user_id is required'
            }, 400)
            return

        manager = get_todo_manager()
        result = manager.search_todos(user_id, query)

        debug_log(f"Search todos: {result['count']} results for '{query}'", "🔍")
        handler.send_json_response(result)

    except Exception as e:
        error_log(f"Search todos API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# Tag routes
def handle_tags_list_api(handler):
    """Handle GET /api/todos/tags - List user's tags."""
    try:
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

    except Exception as e:
        error_log(f"Tags list API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_tags_create_api(handler):
    """Handle POST /api/todos/tags - Create new tag."""
    try:
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

    except Exception as e:
        error_log(f"Tag create API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# User update and delete
def handle_users_update_api(handler, user_id):
    """Handle PUT /api/todos/users/{id} - Update user."""
    try:
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

    except Exception as e:
        error_log(f"User update API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_users_delete_api(handler, user_id):
    """Handle DELETE /api/todos/users/{id} - Delete user."""
    try:
        manager = get_todo_manager()
        result = manager.delete_user(user_id)

        if result['status'] == 'success':
            debug_log(f"Deleted user: {user_id}", "🗑️")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        error_log(f"User delete API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# List update and delete
def handle_lists_update_api(handler, list_id):
    """Handle PUT /api/todos/lists/{id} - Update list."""
    try:
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

    except Exception as e:
        error_log(f"List update API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_lists_delete_api(handler, list_id):
    """Handle DELETE /api/todos/lists/{id} - Delete list."""
    try:
        manager = get_todo_manager()
        result = manager.delete_list(list_id)

        if result['status'] == 'success':
            debug_log(f"Deleted list: {list_id}", "🗑️")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        error_log(f"List delete API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# Tag update and delete
def handle_tags_detail_api(handler, tag_id):
    """Handle GET /api/todos/tags/{id} - Get tag details."""
    try:
        manager = get_todo_manager()
        tag = manager.get_tag(tag_id)

        if tag:
            handler.send_json_response({'status': 'success', 'tag': tag})
        else:
            handler.send_json_response({'status': 'error', 'message': 'Tag not found'}, 404)

    except Exception as e:
        error_log(f"Tag detail API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_tags_update_api(handler, tag_id):
    """Handle PUT /api/todos/tags/{id} - Update tag."""
    try:
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

    except Exception as e:
        error_log(f"Tag update API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_tags_delete_api(handler, tag_id):
    """Handle DELETE /api/todos/tags/{id} - Delete tag."""
    try:
        manager = get_todo_manager()
        result = manager.delete_tag(tag_id)

        if result['status'] == 'success':
            debug_log(f"Deleted tag: {tag_id}", "🗑️")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        error_log(f"Tag delete API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# List sharing routes
def handle_lists_share_api(handler, list_id):
    """Handle POST /api/todos/lists/{id}/share - Share list with user."""
    try:
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

    except Exception as e:
        error_log(f"List share API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_lists_unshare_api(handler, list_id):
    """Handle DELETE /api/todos/lists/{id}/share - Unshare list."""
    try:
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

    except Exception as e:
        error_log(f"List unshare API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_lists_shares_api(handler, list_id):
    """Handle GET /api/todos/lists/{id}/shares - Get list shares."""
    try:
        manager = get_todo_manager()
        result = manager.get_list_shares(list_id)

        debug_log(f"List shares: {result['count']} users", "👥")
        handler.send_json_response(result)

    except Exception as e:
        error_log(f"List shares API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


def handle_shared_lists_api(handler):
    """Handle GET /api/todos/shared - Get lists shared with user."""
    try:
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

    except Exception as e:
        error_log(f"Shared lists API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# History route
def handle_todos_history_api(handler, todo_id):
    """Handle GET /api/todos/{id}/history - Get todo history."""
    try:
        manager = get_todo_manager()
        result = manager.get_todo_history(todo_id)

        debug_log(f"Todo history: {result['count']} entries", "📜")
        handler.send_json_response(result)

    except Exception as e:
        error_log(f"Todo history API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)


# Natural Language Processing endpoints

def handle_todos_parse_api(handler):
    """Handle POST /api/todos/parse - Parse natural language input.

    This endpoint allows testing the NLP parser without creating a todo.
    It returns the parsed structure that would be used to create a todo.

    Request body:
        {
            "input": "Submit report by Friday 3pm @high #work",
            "user_id": "optional-user-id"
        }

    Response:
        {
            "status": "success",
            "parsed": {
                "title": "Submit report",
                "tags": ["work"],
                "priority": "high",
                "due_date": "2025-12-20",
                "due_time": "15:00",
                "bucket": "upcoming"
            },
            "original_input": "Submit report by Friday 3pm @high #work"
        }
    """
    try:
        from todos.nlp_parser import parse_natural_language

        request_data = handler.get_request_body()
        if not request_data:
            handler.send_json_response({'status': 'error', 'message': 'Invalid JSON'}, 400)
            return

        input_text = request_data.get('input')
        if not input_text:
            handler.send_json_response({
                'status': 'error',
                'message': 'input field is required'
            }, 400)
            return

        user_id = request_data.get('user_id')

        # Parse the natural language input
        parsed_data = parse_natural_language(input_text, user_id)

        debug_log(f"Parsed NLP input: '{input_text}' -> {parsed_data['title']}", "🧠")
        handler.send_json_response({
            'status': 'success',
            'parsed': parsed_data,
            'original_input': input_text
        })

    except Exception as e:
        error_log(f"Parse API error: {e}")
        handler.send_json_response({'status': 'error', 'message': str(e)}, 500)
