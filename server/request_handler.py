"""
server/request_handler.py — CustomHTTPRequestHandler for Robobrain UI.

Handles static file serving and delegates API calls to the router.
The `_router` module-level variable must be set by server.py before
the HTTPServer is started.
"""

import gzip
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

_GZIP_TYPES = (
    'text/',
    'application/javascript',
    'application/json',
    'image/svg+xml',
)

from debug_logger import debug_log, error_log
from static_cache import get_static_cache
from server.utils.json_response import send_json_response as send_json_response_util
from server.utils.request_helpers import (
    get_content_type as get_content_type_util,
    get_request_body as get_request_body_util,
)

# Set by server.py after calling build_router(); do not import directly.
_router = None


class CustomHTTPRequestHandler(BaseHTTPRequestHandler):
    """Serve static files and dispatch API requests via the router."""

    def do_GET(self):
        """Handle GET requests — API dispatch then static file fallback."""
        try:
            if self.path.startswith('/api/'):
                if not _router.dispatch('GET', self.path, self):
                    self.send_error(404, f"API endpoint not found: {self.path}")
                return

            # Handle root path
            if self.path == '/':
                self.path = '/index.html'

            # Remove query string and leading slash, then resolve file path
            path_without_query = self.path.split('?')[0]
            file_path = path_without_query.lstrip('/')
            full_path = os.path.join(os.getcwd(), file_path)

            # Quick Win 1: Path traversal protection
            base_dir = os.path.realpath(os.getcwd())
            real_path = os.path.realpath(full_path)
            if not (real_path == base_dir or real_path.startswith(base_dir + os.sep)):
                self.send_error(403, "Forbidden")
                return

            debug_log(f"Request: {self.path} -> {file_path}")

            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                self.send_error(404, f"File not found: {self.path}")
                return

            content_type = self.get_content_type(file_path)

            static_cache = get_static_cache()
            content, etag = static_cache.get(full_path)

            if content is None:
                with open(full_path, 'rb') as f:
                    content = f.read()
                etag = static_cache.set(full_path, content)
                debug_log(f"Cache MISS: {file_path}", "💾")
            else:
                debug_log(f"Cache HIT: {file_path}", "⚡")

            # Determine cache policy: immutable assets (images, fonts, woff) get 1h;
            # mutable source files (JS, CSS, HTML) require revalidation every request.
            _MUTABLE_TYPES = ('text/javascript', 'application/javascript', 'text/css', 'text/html')
            cache_control = (
                'no-cache, must-revalidate'
                if any(content_type.startswith(t) for t in _MUTABLE_TYPES)
                else 'public, max-age=3600'
            )

            # Quick Win 2: If-None-Match → 304 Not Modified
            if self.headers.get('If-None-Match') == etag:
                self.send_response(304)
                self.send_header('ETag', etag)
                self.send_header('Cache-Control', cache_control)
                self.end_headers()
                return

            # Quick Win 4: Gzip compression for text assets
            accepts_gzip = 'gzip' in self.headers.get('Accept-Encoding', '')
            use_gzip = accepts_gzip and any(content_type.startswith(t) for t in _GZIP_TYPES)
            if use_gzip:
                content = gzip.compress(content, compresslevel=6)

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', cache_control)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            if use_gzip:
                self.send_header('Content-Encoding', 'gzip')
                self.send_header('Vary', 'Accept-Encoding')
            self.end_headers()
            self.wfile.write(content)

            debug_log(f"Served {file_path} as {content_type}", "✅")

        except Exception as e:
            print(f"❌ Error serving {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def do_POST(self):
        """Handle POST requests — API dispatch via router."""
        try:
            if not _router.dispatch('POST', self.path, self):
                self.send_error(404, f"API endpoint not found: {self.path}")
        except Exception as e:
            print(f"❌ Error handling POST {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def do_DELETE(self):
        """Handle DELETE requests — API dispatch via router."""
        try:
            if not _router.dispatch('DELETE', self.path, self):
                self.send_error(404, f"API endpoint not found: {self.path}")
        except Exception as e:
            print(f"❌ Error handling DELETE {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def do_PUT(self):
        """Handle PUT requests — API dispatch via router."""
        try:
            if not _router.dispatch('PUT', self.path, self):
                self.send_error(404, f"API endpoint not found: {self.path}")
        except Exception as e:
            print(f"❌ Error handling PUT {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def do_HEAD(self):
        """Handle HEAD requests (like GET but without body)."""
        try:
            if self.path == '/':
                self.path = '/index.html'

            path_without_query = self.path.split('?')[0]
            file_path = path_without_query.lstrip('/')
            full_path = os.path.join(os.getcwd(), file_path)

            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                self.send_error(404, f"File not found: {self.path}")
                return

            file_size = os.path.getsize(full_path)
            content_type = self.get_content_type(file_path)

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        except Exception as e:
            print(f"❌ Error handling HEAD {self.path}: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def send_json_response(self, data, status_code=200):
        """Send a JSON response."""
        send_json_response_util(self, data, status_code)

    def get_content_type(self, file_path):
        """Determine content type based on file extension."""
        return get_content_type_util(file_path)

    def get_request_body(self):
        """Parse JSON request body safely."""
        return get_request_body_util(self)

    def get_query_params(self):
        """Parse URL query parameters."""
        parsed_url = urlparse(self.path)
        return {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

    def log_message(self, format, *args):
        """Override to disable default request logging noise."""
        return
