"""Opportunities route handlers for business opportunity tracking."""

from debug_logger import debug_log

try:
    from opportunities_api import (
        handle_opportunities_list_request,
        handle_opportunities_create_request,
        handle_opportunities_get_request,
        handle_opportunities_update_request,
        handle_opportunities_delete_request
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
