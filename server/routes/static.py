"""
Static file serving routes.

Handles GET requests for static assets (HTML, JS, CSS, images, etc.)
with compression, caching, and proper MIME types.
"""

import os
from pathlib import Path
import hashlib
import mimetypes

from debug_logger import debug_log
from compression_handler import get_compression_handler
from static_cache import get_static_cache
from cors_config import apply_cors_headers
from server.utils.response import send_error_response


class StaticFileRoutes:
    """Mixin providing static file serving functionality."""

    def handle_static_file(self, file_path: str):
        """
        Serve a static file with compression and caching support.

        Args:
            file_path: Relative path to the file

        Features:
            - Gzip compression (if client supports it)
            - ETag-based caching
            - Proper MIME type detection
            - 304 Not Modified responses
        """
        # Resolve full path
        full_path = os.path.join(os.getcwd(), file_path)

        # Security: Ensure file is within the working directory
        try:
            full_path = os.path.realpath(full_path)
            cwd = os.path.realpath(os.getcwd())
            if not full_path.startswith(cwd):
                send_error_response(self, "Access denied", 403)
                return
        except Exception as e:
            send_error_response(self, f"Invalid path: {e}", 400)
            return

        # Check if file exists
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            send_error_response(self, f"File not found: {file_path}", 404)
            return

        # Determine content type
        content_type = self.get_content_type(file_path)

        # Check if client accepts gzip encoding
        accepts_gzip = 'gzip' in self.headers.get('Accept-Encoding', '').lower()

        # Try compression first if supported
        compression_handler = get_compression_handler()
        content, is_compressed = compression_handler.get_compressed_content(
            full_path,
            accepts_gzip
        )

        # Generate ETag for cache validation
        etag = f'"{hashlib.md5(content).hexdigest()}"'

        # Check client's ETag for 304 Not Modified
        client_etag = self.headers.get('If-None-Match')
        if client_etag == etag:
            self.send_response(304)
            apply_cors_headers(self, self.headers.get('Origin'))
            self.end_headers()
            return

        # Send successful response
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('ETag', etag)
        self.send_header('Cache-Control', 'no-cache')  # Validate with ETag

        if is_compressed:
            self.send_header('Content-Encoding', 'gzip')

        apply_cors_headers(self, self.headers.get('Origin'))
        self.end_headers()

        # Write content
        self.wfile.write(content)

        debug_log(f"Served: {file_path} ({len(content)} bytes, compressed={is_compressed})")

    def get_content_type(self, file_path: str) -> str:
        """
        Determine MIME type for a file.

        Args:
            file_path: Path to the file

        Returns:
            str: MIME type string
        """
        # Get extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # Custom MIME types for common web files
        custom_types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.svg': 'image/svg+xml',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.md': 'text/markdown; charset=utf-8'
        }

        if ext in custom_types:
            return custom_types[ext]

        # Fall back to mimetypes module
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

    def serve_index_html(self):
        """Serve index.html as the default page."""
        self.handle_static_file('index.html')
