"""
Database configuration.

The database path defaults to 'search_system.db' in the current working
directory but can be overridden via the SEARCH_DB_PATH environment variable
without modifying any code.
"""

import os

DEFAULT_DB: str = os.getenv("SEARCH_DB_PATH", "search_system.db")
