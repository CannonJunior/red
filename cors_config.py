"""
CORS Configuration Module

Provides environment-based CORS configuration for production security.
"""

import os
from typing import Optional


class CORSConfig:
    """Singleton CORS configuration manager."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize CORS configuration from environment."""
        if self._initialized:
            return

        # Get allowed origins from environment (comma-separated list)
        allowed_origins_env = os.getenv('ALLOWED_ORIGINS', '*')

        if allowed_origins_env == '*':
            # Development mode - allow all origins
            self.allowed_origins = ['*']
            self.dev_mode = True
        else:
            # Production mode - parse comma-separated list
            self.allowed_origins = [
                origin.strip()
                for origin in allowed_origins_env.split(',')
                if origin.strip()
            ]
            self.dev_mode = False

        # Default methods and headers
        self.allowed_methods = ['GET', 'HEAD', 'POST', 'OPTIONS', 'PUT', 'DELETE']
        self.allowed_headers = ['Content-Type', 'Authorization', 'X-Requested-With']

        self._initialized = True

    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """
        Check if an origin is allowed.

        Args:
            origin: The Origin header value from the request

        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            return True  # No origin header means same-origin or local request

        if self.dev_mode:
            return True  # Allow all in dev mode

        # Check if origin is in allowed list
        return origin in self.allowed_origins

    def get_cors_headers(self, origin: Optional[str] = None) -> dict:
        """
        Get CORS headers for response.

        Args:
            origin: The Origin header value from the request

        Returns:
            Dictionary of CORS headers to send
        """
        headers = {}

        if self.dev_mode:
            # Development mode - allow all
            headers['Access-Control-Allow-Origin'] = '*'
        elif origin and self.is_origin_allowed(origin):
            # Production mode - echo back the allowed origin
            headers['Access-Control-Allow-Origin'] = origin
            headers['Access-Control-Allow-Credentials'] = 'true'
        else:
            # Origin not allowed - don't send CORS headers
            return {}

        # Always include methods and headers
        headers['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
        headers['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)

        return headers

    def get_allowed_methods_string(self) -> str:
        """Get comma-separated string of allowed methods."""
        return ', '.join(self.allowed_methods)

    def get_allowed_headers_string(self) -> str:
        """Get comma-separated string of allowed headers."""
        return ', '.join(self.allowed_headers)


# Singleton instance
_cors_config = None


def get_cors_config() -> CORSConfig:
    """
    Get the singleton CORS configuration instance.

    Returns:
        CORSConfig instance
    """
    global _cors_config
    if _cors_config is None:
        _cors_config = CORSConfig()
    return _cors_config


# Convenience function for handlers
def apply_cors_headers(handler, origin: Optional[str] = None):
    """
    Apply CORS headers to a request handler.

    Args:
        handler: HTTP request handler instance
        origin: The Origin header value from the request
    """
    cors_config = get_cors_config()
    headers = cors_config.get_cors_headers(origin)

    for header_name, header_value in headers.items():
        handler.send_header(header_name, header_value)
