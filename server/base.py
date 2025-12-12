"""
Base HTTP request handler combining all route mixins.

This module provides the ModularHTTPHandler class which composes
all route mixins into a single handler class.
"""

import os
import mimetypes
from http.server import BaseHTTPRequestHandler

# Import route mixins
from server.routes.static import StaticFileRoutes
from server.routes.search import SearchRoutes
from server.routes.rag import RAGRoutes
from server.routes.cag import CAGRoutes
from server.routes.chat import ChatRoutes
from server.routes.agents import AgentRoutes
from server.routes.mcp import MCPRoutes

# Import utilities
from server.utils import response as response_utils
from debug_logger import debug_log, info_log
from cors_config import apply_cors_headers
import json


class ModularHTTPHandler(
    ChatRoutes,
    AgentRoutes,
    MCPRoutes,
    StaticFileRoutes,
    SearchRoutes,
    RAGRoutes,
    CAGRoutes,
    BaseHTTPRequestHandler
):
    """
    Modular HTTP request handler composed of route mixins.

    This handler combines all route modules using the mixin pattern:
    - ChatRoutes: Chat API with RAG/CAG/MCP integration
    - AgentRoutes: Agent management endpoints
    - MCPRoutes: MCP server management and tool execution
    - StaticFileRoutes: Static file serving
    - SearchRoutes: Universal search functionality
    - RAGRoutes: RAG system endpoints
    - CAGRoutes: CAG system endpoints

    All mixins have access to standard HTTP handler methods like
    send_response(), send_header(), etc.
    """

    def send_json_response(self, data, status_code=200):
        """Send JSON response with proper headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        apply_cors_headers(self, self.headers.get('Origin'))
        self.end_headers()

        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))

    def send_error_response(self, message, status_code=400):
        """Send error response."""
        self.send_json_response({
            'status': 'error',
            'message': message
        }, status_code)

    def get_request_body(self):
        """Parse JSON request body."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}

            post_data = self.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse request body: {e}")

    def do_GET(self):
        """
        Handle GET requests.

        Routes requests to appropriate handlers based on path.
        """
        try:
            debug_log(f"GET {self.path}", "📥")

            # API routes
            if self.path.startswith('/api/'):
                self._route_api_get()
                return

            # Root path - serve index.html
            if self.path == '/':
                self.serve_index_html()
                return

            # Static files
            file_path = self.path.lstrip('/')
            self.handle_static_file(file_path)

        except Exception as e:
            debug_log(f"GET error: {e}", "❌")
            self.send_error_response(f"Request failed: {str(e)}", 500)

    def do_POST(self):
        """
        Handle POST requests.

        Routes requests to appropriate POST handlers.
        """
        try:
            debug_log(f"POST {self.path}", "📥")

            # API routes
            if self.path.startswith('/api/'):
                self._route_api_post()
                return

            # Not found
            self.send_error_response(f"Endpoint not found: {self.path}", 404)

        except Exception as e:
            debug_log(f"POST error: {e}", "❌")
            self.send_error_response(f"Request failed: {str(e)}", 500)

    def do_DELETE(self):
        """
        Handle DELETE requests.

        Routes requests to appropriate DELETE handlers.
        """
        try:
            debug_log(f"DELETE {self.path}", "📥")

            # API routes
            if self.path.startswith('/api/'):
                self._route_api_delete()
                return

            # Not found
            self.send_error_response(f"Endpoint not found: {self.path}", 404)

        except Exception as e:
            debug_log(f"DELETE error: {e}", "❌")
            self.send_error_response(f"Request failed: {str(e)}", 500)

    def do_HEAD(self):
        """Handle HEAD requests (same as GET but no body)."""
        self.do_GET()

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        apply_cors_headers(self, self.headers.get('Origin'))
        self.end_headers()

    def _route_api_get(self):
        """Route GET API requests to appropriate handlers."""
        path = self.path

        # RAG endpoints
        if path == '/api/rag/status':
            self.handle_rag_status_api()
        elif path == '/api/rag/documents':
            self.handle_rag_documents_api()
        elif path == '/api/rag/analytics':
            self.handle_rag_analytics_api()

        # CAG endpoints
        elif path == '/api/cag/status':
            self.handle_cag_status_api()

        # Search endpoints
        elif path == '/api/search/folders':
            self.handle_search_folders_api()
        elif path == '/api/search/tags':
            self.handle_search_tags_api()

        # Not found
        else:
            self.send_error_response(f"API endpoint not found: {path}", 404)

    def _route_api_post(self):
        """Route POST API requests to appropriate handlers."""
        path = self.path

        # RAG endpoints
        if path == '/api/rag/search':
            self.handle_rag_search_api()
        elif path == '/api/rag/query':
            self.handle_rag_query_api()
        elif path == '/api/rag/ingest':
            self.handle_rag_ingest_api()
        elif path == '/api/rag/upload':
            self.handle_rag_upload_api()

        # CAG endpoints
        elif path == '/api/cag/load':
            self.handle_cag_load_api()
        elif path == '/api/cag/clear':
            self.handle_cag_clear_api()
        elif path == '/api/cag/query':
            self.handle_cag_query_api()

        # Search endpoints
        elif path == '/api/search':
            self.handle_search_api()
        elif path == '/api/search/folders':
            self.handle_search_create_folder_api()
        elif path == '/api/search/objects':
            self.handle_search_add_object_api()

        # Not found
        else:
            self.send_error_response(f"API endpoint not found: {path}", 404)

    def _route_api_delete(self):
        """Route DELETE API requests to appropriate handlers."""
        path = self.path

        # RAG document deletion
        if path.startswith('/api/rag/documents/'):
            document_id = path.split('/')[-1]
            self.handle_rag_document_delete_api(document_id)

        # CAG document deletion
        elif path.startswith('/api/cag/documents/'):
            document_id = path.split('/')[-1]
            self.handle_cag_document_delete_api(document_id)

        # Search object deletion
        elif path.startswith('/api/search/objects/'):
            object_id = path.split('/')[-1]
            self.handle_search_delete_object_api(object_id)

        # Not found
        else:
            self.send_error_response(f"API endpoint not found: {path}", 404)

    def log_message(self, format, *args):
        """
        Override log_message to use our custom logger.

        This prevents default HTTP server logging to stdout.
        """
        debug_log(f"{self.client_address[0]} - {format % args}", "🌐")
