"""
Server decorators for common patterns.

This module provides decorators to reduce boilerplate code in server handlers.
"""

from functools import wraps
from typing import Callable, List


def require_system(*systems: str) -> Callable:
    """
    Decorator to check system availability before handler execution.

    Checks if required systems (RAG, CAG, SEARCH, etc.) are available before
    executing the handler. If any system is unavailable, returns a 503 error.

    Args:
        *systems: Variable number of system names to check (e.g., 'rag', 'cag', 'search')

    Usage:
        @require_system('rag')
        def handle_rag_api(self):
            # RAG logic - only executes if RAG_AVAILABLE is True

        @require_system('rag', 'cag')
        def handle_combined_api(self):
            # Logic requiring both RAG and CAG

    Returns:
        Decorated function that performs availability checks before execution.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Import system module to check availability flags
            try:
                from server.utils import system as system_module
            except ImportError:
                # Fallback for original server.py (no modular structure)
                import sys
                calling_module = sys.modules[func.__module__]
                system_module = calling_module

            # Check each required system
            for system_name in systems:
                available_var = f"{system_name.upper()}_AVAILABLE"

                # Get the availability flag from the system module
                is_available = getattr(system_module, available_var, False)

                if not is_available:
                    # Send error response and exit early
                    self.send_json_response({
                        'status': 'error',
                        'message': f'{system_name.upper()} system not available'
                    }, 503)
                    return

            # All systems available - execute the handler
            return func(self, *args, **kwargs)

        return wrapper
    return decorator


def require_authentication(func: Callable) -> Callable:
    """
    Decorator to require authentication before handler execution.

    Currently a placeholder for future authentication implementation.

    Usage:
        @require_authentication
        def handle_protected_api(self):
            # Protected logic
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # TODO: Implement authentication check
        # For now, always allow (maintain current behavior)
        return func(self, *args, **kwargs)

    return wrapper
