"""CAG (Cache-Augmented Generation) route handlers."""

import json
import uuid
import urllib.request
from pathlib import Path

from debug_logger import debug_log
from ollama_config import ollama_config
from server_decorators import require_system
from server.utils.error_handler import error_handler

try:
    from cag_api import get_cag_manager, calculate_optimal_cag_capacity
    CAG_AVAILABLE = True
    cag_manager = get_cag_manager()
except ImportError:
    CAG_AVAILABLE = False
    cag_manager = None


@error_handler
def handle_cag_status_api(handler):
    """Handle CAG cache status API requests."""
    if cag_manager is None:
        optimal_capacity = calculate_optimal_cag_capacity()
        handler.send_json_response({
            'error': 'CAG system not available',
            'total_tokens': 0,
            'available_tokens': optimal_capacity,
            'max_tokens': optimal_capacity,
            'usage_percent': 0,
            'document_count': 0,
            'documents': []
        }, 503)
        return

    status = cag_manager.get_cache_status()
    handler.send_json_response(status)


@error_handler
def handle_cag_load_api(handler):
    """Handle CAG document loading API requests."""
    if cag_manager is None:
        handler.send_json_response({'error': 'CAG system not available'}, 503)
        return

    content_length = int(handler.headers.get('Content-Length', 0))
    if content_length == 0:
        handler.send_json_response({'error': 'No data received'}, 400)
        return

    content_type = handler.headers.get('Content-Type', '')

    if content_type.startswith('multipart/form-data'):
        import cgi
        import io

        post_data = handler.rfile.read(content_length)

        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': str(content_length),
        }

        fields = cgi.FieldStorage(
            fp=io.BytesIO(post_data),
            environ=environ,
            keep_blank_values=True
        )

        if 'file' not in fields:
            handler.send_json_response({'error': 'No file uploaded'}, 400)
            return

        file_item = fields['file']
        filename = file_item.filename
        file_data = file_item.file.read()

        temp_path = Path(f'/tmp/cag_{uuid.uuid4()}_{filename}')
        temp_path.write_bytes(file_data)

        result = cag_manager.load_document(str(temp_path))
        temp_path.unlink()
        handler.send_json_response(result)

    else:
        request_data = handler.get_request_body()
        if request_data is None:
            handler.send_json_response({'error': 'Invalid JSON'}, 400)
            return
        file_path = request_data.get('file_path')

        if not file_path:
            handler.send_json_response({'error': 'file_path required'}, 400)
            return

        result = cag_manager.load_document(file_path)
        handler.send_json_response(result)


@error_handler
def handle_cag_clear_api(handler):
    """Handle CAG cache clear API requests."""
    if cag_manager is None:
        handler.send_json_response({'error': 'CAG system not available'}, 503)
        return

    result = cag_manager.clear_cache()
    handler.send_json_response(result)


@error_handler
def handle_cag_document_delete_api(handler, document_id):
    """Handle CAG document deletion API requests."""
    if cag_manager is None:
        handler.send_json_response({'error': 'CAG system not available'}, 503)
        return

    result = cag_manager.remove_document(document_id)
    handler.send_json_response(result)


@error_handler
def handle_cag_query_api(handler):
    """Handle CAG-enhanced query API requests."""
    if cag_manager is None:
        handler.send_json_response({'error': 'CAG system not available'}, 503)
        return

    request_data = handler.get_request_body()
    if request_data is None:
        handler.send_json_response({'error': 'Invalid JSON'}, 400)
        return

    query = request_data.get('query', '')
    model = request_data.get('model', 'qwen2.5:3b')

    if not query:
        handler.send_json_response({'error': 'query required'}, 400)
        return

    full_context = cag_manager.get_context_for_query(query)

    ollama_url = f"{ollama_config.base_url}/api/generate"
    payload = {
        'model': model,
        'prompt': full_context,
        'stream': False
    }

    req = urllib.request.Request(
        ollama_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))

    handler.send_json_response({
        'status': 'success',
        'response': result.get('response', ''),
        'model': model,
        'context_tokens': cag_manager.total_tokens,
        'mode': 'cag'
    })
