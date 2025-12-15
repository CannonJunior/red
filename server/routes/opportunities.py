"""Opportunities route handlers for business opportunity tracking."""

from debug_logger import debug_log

try:
    from opportunities_api import (
        handle_opportunities_list_request,
        handle_opportunities_create_request,
        handle_opportunities_get_request,
        handle_opportunities_update_request,
        handle_opportunities_delete_request,
        handle_tasks_list_request,
        handle_tasks_create_request,
        handle_task_get_request,
        handle_tasks_update_request,
        handle_tasks_delete_request,
        handle_task_history_request
    )
    OPPORTUNITIES_AVAILABLE = True
except ImportError:
    OPPORTUNITIES_AVAILABLE = False


def handle_opportunities_list_api(handler):
    """Handle GET /api/opportunities - List all opportunities."""
    try:
        request_data = handler.get_request_body()
        filters = request_data if request_data else {}

        result = handle_opportunities_list_request(filters)

        debug_log(f"Opportunities list: {result.get('count', 0)} opportunities", "📋")
        handler.send_json_response(result)

    except Exception as e:
        print(f"❌ Opportunities list API error: {e}")
        handler.send_json_response({'error': f'Opportunities list failed: {str(e)}'}, 500)


def handle_opportunities_create_api(handler):
    """Handle POST /api/opportunities - Create new opportunity."""
    try:
        # Read request body
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_opportunities_create_request(request_data)

        if result.get('status') == 'success':
            debug_log(f"Created opportunity: {request_data.get('name', 'Unknown')}", "✅")
            handler.send_json_response(result, 201)
        else:
            print(f"❌ Failed to create opportunity: {result.get('message', 'Unknown error')}")
            handler.send_json_response(result, 400)

    except Exception as e:
        print(f"❌ Opportunities create API error: {e}")
        handler.send_json_response({'error': f'Opportunities create failed: {str(e)}'}, 500)


def handle_opportunities_detail_api(handler):
    """Handle GET /api/opportunities/{opportunity_id} - Get opportunity by ID."""
    try:
        # Extract opportunity ID from path
        opportunity_id = handler.path.split('/')[-1]

        result = handle_opportunities_get_request(opportunity_id)

        if result.get('status') == 'success':
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Opportunities detail API error: {e}")
        handler.send_json_response({'error': f'Opportunities detail failed: {str(e)}'}, 500)


def handle_opportunities_update_api(handler):
    """Handle PUT/PATCH /api/opportunities/{opportunity_id} - Update opportunity."""
    try:
        # Extract opportunity ID from path
        opportunity_id = handler.path.split('/')[-1]

        # Read request body
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_opportunities_update_request(opportunity_id, request_data)

        if result.get('status') == 'success':
            debug_log(f"Updated opportunity: {opportunity_id}", "✅")
            handler.send_json_response(result)
        else:
            print(f"❌ Failed to update opportunity: {result.get('message', 'Unknown error')}")
            handler.send_json_response(result, 400)

    except Exception as e:
        print(f"❌ Opportunities update API error: {e}")
        handler.send_json_response({'error': f'Opportunities update failed: {str(e)}'}, 500)


def handle_opportunities_delete_api(handler, opportunity_id):
    """Handle DELETE /api/opportunities/{opportunity_id} - Delete opportunity."""
    try:
        result = handle_opportunities_delete_request(opportunity_id)

        if result.get('status') == 'success':
            debug_log(f"Deleted opportunity: {opportunity_id}", "🗑️")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Opportunities delete API error: {e}")
        handler.send_json_response({'error': f'Opportunities delete failed: {str(e)}'}, 500)


def handle_tasks_list_api(handler, opportunity_id):
    """Handle GET /api/opportunities/{opportunity_id}/tasks - List tasks for opportunity."""
    try:
        result = handle_tasks_list_request(opportunity_id)

        if result.get('status') == 'success':
            debug_log(f"Tasks list for opportunity {opportunity_id}: {len(result.get('tasks', []))} tasks", "📋")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Tasks list API error: {e}")
        handler.send_json_response({'error': f'Tasks list failed: {str(e)}'}, 500)


def handle_tasks_create_api(handler, opportunity_id):
    """Handle POST /api/opportunities/{opportunity_id}/tasks - Create new task."""
    try:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_tasks_create_request(opportunity_id, request_data)

        if result.get('status') == 'success':
            debug_log(f"Created task for opportunity {opportunity_id}: {request_data.get('name', 'Unknown')}", "✅")
            handler.send_json_response(result, 201)
        else:
            print(f"❌ Failed to create task: {result.get('message', 'Unknown error')}")
            handler.send_json_response(result, 400)

    except Exception as e:
        print(f"❌ Tasks create API error: {e}")
        handler.send_json_response({'error': f'Tasks create failed: {str(e)}'}, 500)


def handle_task_get_api(handler, task_id):
    """Handle GET /api/tasks/{task_id} - Get task by ID."""
    try:
        result = handle_task_get_request(task_id)

        if result.get('status') == 'success':
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Task get API error: {e}")
        handler.send_json_response({'error': f'Task get failed: {str(e)}'}, 500)


def handle_task_update_api(handler, task_id):
    """Handle POST /api/tasks/{task_id} - Update task."""
    try:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return

        result = handle_tasks_update_request(task_id, request_data)

        if result.get('status') == 'success':
            debug_log(f"Updated task: {task_id}", "✅")
            handler.send_json_response(result)
        else:
            print(f"❌ Failed to update task: {result.get('message', 'Unknown error')}")
            handler.send_json_response(result, 400)

    except Exception as e:
        print(f"❌ Task update API error: {e}")
        handler.send_json_response({'error': f'Task update failed: {str(e)}'}, 500)


def handle_task_delete_api(handler, task_id):
    """Handle DELETE /api/tasks/{task_id} - Delete task."""
    try:
        result = handle_tasks_delete_request(task_id)

        if result.get('status') == 'success':
            debug_log(f"Deleted task: {task_id}", "🗑️")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Task delete API error: {e}")
        handler.send_json_response({'error': f'Task delete failed: {str(e)}'}, 500)


def handle_task_history_api(handler, task_id):
    """Handle GET /api/tasks/{task_id}/history - Get task history."""
    try:
        result = handle_task_history_request(task_id)

        if result.get('status') == 'success':
            debug_log(f"Task history for {task_id}: {len(result.get('history', []))} entries", "📜")
            handler.send_json_response(result)
        else:
            handler.send_json_response(result, 404)

    except Exception as e:
        print(f"❌ Task history API error: {e}")
        handler.send_json_response({'error': f'Task history failed: {str(e)}'}, 500)
