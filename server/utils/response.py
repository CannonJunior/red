"""
Response utility functions for HTTP handlers.

Provides helper functions for sending JSON responses, setting headers,
and handling common response patterns.
"""

import json
from typing import Any, Dict
from cors_config import apply_cors_headers


def send_json_response(handler, data: Dict[str, Any], status_code: int = 200):
    """
    Send a JSON response with proper headers.

    Args:
        handler: HTTP request handler instance
        data: Dictionary to serialize as JSON
        status_code: HTTP status code (default: 200)
    """
    handler.send_response(status_code)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    apply_cors_headers(handler, handler.headers.get('Origin'))
    handler.end_headers()

    response_json = json.dumps(data, ensure_ascii=False)
    handler.wfile.write(response_json.encode('utf-8'))


def send_error_response(handler, message: str, status_code: int = 400, error_type: str = "error"):
    """
    Send a JSON error response.

    Args:
        handler: HTTP request handler instance
        message: Error message
        status_code: HTTP status code (default: 400)
        error_type: Type of error (default: "error")
    """
    send_json_response(handler, {
        'status': error_type,
        'message': message
    }, status_code)


def get_request_body(handler) -> Dict[str, Any]:
    """
    Parse JSON request body.

    Args:
        handler: HTTP request handler instance

    Returns:
        Parsed JSON data as dictionary

    Raises:
        ValueError: If JSON is invalid
    """
    try:
        content_length = int(handler.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}

        post_data = handler.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ValueError(f"Failed to parse request body: {e}")
