"""Request helper utilities for the server."""

import json
import os
from debug_logger import debug_log


def get_content_type(file_path):
    """
    Determine content type based on file extension.

    Args:
        file_path (str): Path to the file

    Returns:
        str: MIME content type
    """
    # Define explicit mappings for web files
    content_types = {
        '.html': 'text/html; charset=utf-8',
        '.htm': 'text/html; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.svg': 'image/svg+xml',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.ico': 'image/x-icon',
    }

    # Get file extension
    _, ext = os.path.splitext(file_path.lower())

    # Return specific type or default
    return content_types.get(ext, 'text/plain')


def get_request_body(handler):
    """
    Parse JSON request body safely.

    Args:
        handler: The HTTP request handler instance

    Returns:
        dict: Parsed JSON data, or None if parsing fails, or {} if no content

    Usage:
        request_data = get_request_body(self)
        if request_data is None:
            send_json_response(self, {'error': 'Invalid JSON'}, 400)
            return
    """
    try:
        content_length = int(handler.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        post_data = handler.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))
    except (ValueError, json.JSONDecodeError) as e:
        debug_log(f"Failed to parse request body: {e}", "⚠️")
        return None
    except Exception as e:
        debug_log(f"Unexpected error parsing request body: {e}", "❌")
        return None
