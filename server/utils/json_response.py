"""JSON response utilities for the server."""

import json


def send_json_response(handler, data, status_code=200):
    """
    Send a JSON response with proper headers.

    Args:
        handler: The HTTP request handler instance
        data (dict): Data to send as JSON
        status_code (int): HTTP status code (default: 200)
    """
    response_json = json.dumps(data)
    response_bytes = response_json.encode('utf-8')

    handler.send_response(status_code)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(response_bytes)))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type')
    handler.end_headers()

    handler.wfile.write(response_bytes)
