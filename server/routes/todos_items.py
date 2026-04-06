"""Route handlers for TODO item CRUD and smart query API endpoints."""

from debug_logger import debug_log, error_log
from server.utils.error_handler import error_handler

try:
    from todos import get_todo_manager
    TODOS_AVAILABLE = True
except ImportError:
    TODOS_AVAILABLE = False


@error_handler
def handle_todos_list_api(handler):
    """Handle GET /api/todos - List todos."""
    query_params = handler.get_query_params()
    user_id = query_params.get('user_id')

    if not user_id:
        handler.send_json_response({
            'status': 'error',
            'message': 'user_id is required'
        }, 400)
        return

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


@error_handler
def handle_todos_create_api(handler):
    """Handle POST /api/todos - Create new todo.

    Supports two input modes:
    1. Natural Language: {"user_id": "...", "input": "Call mom tomorrow @high #personal"}
    2. Structured: {"user_id": "...", "title": "Call mom", "priority": "high", ...}

    The natural language mode uses the NLP parser to extract structured data.
    """
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

    natural_input = request_data.get('input')

    if natural_input:
        # Mode 1: Natural Language Processing
        debug_log(f"Creating todo from NLP input: '{natural_input}'", "🧠")

        parsed_data = parse_natural_language(natural_input, user_id)

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


@error_handler
def handle_todos_detail_api(handler, todo_id):
    """Handle GET /api/todos/{id} - Get todo details."""
    manager = get_todo_manager()
    todo = manager.get_todo(todo_id)

    if todo:
        handler.send_json_response({'status': 'success', 'todo': todo})
    else:
        handler.send_json_response({'status': 'error', 'message': 'Todo not found'}, 404)


@error_handler
def handle_todos_update_api(handler, todo_id):
    """Handle PUT /api/todos/{id} - Update todo."""
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

    updates = {k: v for k, v in request_data.items() if k != 'user_id'}

    manager = get_todo_manager()
    result = manager.update_todo(todo_id, user_id, updates)

    if result['status'] == 'success':
        debug_log(f"Updated todo: {todo_id}", "✅")
        handler.send_json_response(result)
    else:
        handler.send_json_response(result, 400 if 'not found' not in result.get('message', '') else 404)


@error_handler
def handle_todos_delete_api(handler, todo_id):
    """Handle DELETE /api/todos/{id} - Delete todo."""
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


@error_handler
def handle_todos_complete_api(handler, todo_id):
    """Handle POST /api/todos/{id}/complete - Mark todo as complete."""
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


@error_handler
def handle_todos_archive_api(handler, todo_id):
    """Handle POST /api/todos/{id}/archive - Archive todo."""
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


@error_handler
def handle_todos_today_api(handler):
    """Handle GET /api/todos/today - Get today's todos."""
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


@error_handler
def handle_todos_upcoming_api(handler):
    """Handle GET /api/todos/upcoming - Get upcoming todos."""
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


@error_handler
def handle_todos_search_api(handler):
    """Handle GET /api/todos/search - Search todos."""
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


@error_handler
def handle_todos_history_api(handler, todo_id):
    """Handle GET /api/todos/{id}/history - Get todo history."""
    manager = get_todo_manager()
    result = manager.get_todo_history(todo_id)

    debug_log(f"Todo history: {result['count']} entries", "📜")
    handler.send_json_response(result)


@error_handler
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

    parsed_data = parse_natural_language(input_text, user_id)

    debug_log(f"Parsed NLP input: '{input_text}' -> {parsed_data['title']}", "🧠")
    handler.send_json_response({
        'status': 'success',
        'parsed': parsed_data,
        'original_input': input_text
    })
