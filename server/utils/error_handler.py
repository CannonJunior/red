"""
server/utils/error_handler.py — Route handler error decorator.

Centralizes the try/except boilerplate that every route handler repeats.
Apply @error_handler to any handler whose first argument is the HTTP
request handler instance (which exposes send_json_response).

Usage:
    from server.utils.error_handler import error_handler

    @error_handler
    def handle_foo_api(handler):
        result = do_something()
        handler.send_json_response(result)

    @error_handler
    def handle_bar_api(handler, item_id):
        result = get_item(item_id)
        handler.send_json_response(result)
"""

import functools

from debug_logger import error_log


def error_handler(fn):
    """
    Decorator that wraps a route handler in a standard try/except block.

    On exception: logs via error_log and sends a 500 JSON response.
    The first positional argument must be the HTTP request handler
    instance (has send_json_response).

    Args:
        fn: Route handler with signature fn(handler, *args, **kwargs).

    Returns:
        Callable: Wrapped function with automatic error handling.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            handler = args[0]
            error_log(f"{fn.__name__} error: {e}", exception=e)
            handler.send_json_response({'error': str(e)}, 500)
    return wrapper
