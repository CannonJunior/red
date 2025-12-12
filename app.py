#!/usr/bin/env python3
"""
Modular HTTP Server Entry Point

This is the new entry point for the modular server architecture.
It initializes all systems and starts the HTTP server using the
ModularHTTPHandler composed from route mixins.

Usage:
    python3 app.py              # Start on default port 9090
    PORT=8080 python3 app.py   # Start on custom port
"""

import os
import sys
from http.server import HTTPServer

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modular handler
from server.base import ModularHTTPHandler

# Import system initialization
from server.utils.system import initialize_systems

# Import logger
from debug_logger import info_log, success_log, error_log


def create_server(port: int = 9090, host: str = '0.0.0.0'):
    """
    Create and configure HTTP server.

    Args:
        port: Port number to listen on (default: 9090)
        host: Host address to bind to (default: 0.0.0.0)

    Returns:
        HTTPServer: Configured HTTP server instance
    """
    server_address = (host, port)
    httpd = HTTPServer(server_address, ModularHTTPHandler)

    info_log(f"Server configured at http://{host}:{port}")
    return httpd


def main():
    """Main entry point."""
    print("=" * 60)
    print("Robobrain Modular HTTP Server")
    print("=" * 60)
    print()

    # Get port from environment or use default
    port = int(os.environ.get('PORT', 9090))
    host = os.environ.get('HOST', '0.0.0.0')

    # Initialize optional systems (RAG, CAG, Agent, etc.)
    info_log("Initializing systems...")
    results = initialize_systems()

    # Show initialization results
    success_count = sum(1 for v in results.values() if v == 'success')
    total_count = len(results)

    print()
    info_log(f"Systems initialized: {success_count}/{total_count} successful")
    print()

    # Create server
    try:
        httpd = create_server(port, host)

        # Start server
        success_log(f"Server started on http://{host}:{port}")
        print()
        info_log("Press Ctrl+C to stop the server")
        print("=" * 60)
        print()

        httpd.serve_forever()

    except KeyboardInterrupt:
        print()
        info_log("Shutting down server...")
        httpd.server_close()
        success_log("Server stopped")

    except Exception as e:
        error_log(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
