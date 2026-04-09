#!/usr/bin/env python3
"""
HTTP server startup for the Robobrain UI web application on port 9090.

Responsibilities:
  - Initialize any system-level singletons that must be ready at startup
  - Build the application router
  - Start the HTTPServer
"""

import atexit
import os
import sys
from http.server import HTTPServer

# Import debug logger
from debug_logger import debug_log, error_log

# Import Ollama configuration (ensures config is loaded before routes)
from ollama_config import ollama_config  # noqa: F401

# Import server decorators (side-effects only at startup)
from server_decorators import require_system  # noqa: F401

# ---------------------------------------------------------------------------
# Add project root to sys.path so agent_system and other local packages resolve
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Initialize agent system managers (start background processes if needed)
# ---------------------------------------------------------------------------
try:
    from agent_system.mcp.server_manager import initialize_default_servers
    from agent_system.agents.agent_config import MojoOptimizedAgentManager
    from agent_system.security.local_security import ZeroCostLocalSecurity

    mcp_manager = initialize_default_servers()
    agent_manager = MojoOptimizedAgentManager()
    security_manager = ZeroCostLocalSecurity()
    print("✅ Agent managers initialized")
except ImportError as e:
    mcp_manager = None
    agent_manager = None
    security_manager = None
    print(f"⚠️  Agent system not available: {e}")

# ---------------------------------------------------------------------------
# Build router and inject into request handler
# ---------------------------------------------------------------------------
from server.routes_builder import build_router
import server.request_handler as _handler_mod

_handler_mod._router = build_router()

from server.request_handler import CustomHTTPRequestHandler

# Ensure pooled DB connections are released cleanly on server shutdown
from server.db_pool import close_all
atexit.register(close_all)


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

_PORT = int(os.getenv('PORT', '9090'))


def main():
    """Start the HTTP server on the configured port (default 9090, override with PORT env var)."""
    server_address = ('', _PORT)
    httpd = HTTPServer(server_address, CustomHTTPRequestHandler)
    print(f'🚀 Server running on http://localhost:{_PORT}')
    print(f'📂 Serving files from: {os.getcwd()}')
    httpd.serve_forever()


if __name__ == '__main__':
    main()
