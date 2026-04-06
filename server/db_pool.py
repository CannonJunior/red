"""
server/db_pool.py — Thread-local SQLite connection pool.

SQLite does not support concurrent writes from multiple threads on a single
connection, but it *does* support one connection per thread.  This module
provides a lightweight thread-local pool that:

  - Opens one connection per thread on first use
  - Enables WAL (Write-Ahead Logging) for better read/write concurrency
  - Enforces foreign key constraints
  - Returns a context-managed connection that stays open between requests
    (avoiding per-request open/close overhead)

Usage:
    from server.db_pool import get_db

    with get_db("search_system.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        conn.commit()           # explicit commit for writes
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator

# Thread-local storage: maps db_path → sqlite3.Connection
_local = threading.local()


def _open_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a new SQLite connection with optimal settings.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Connection: Configured connection.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # WAL mode: readers don't block writers and vice-versa
    conn.execute("PRAGMA journal_mode=WAL")
    # Enforce FK cascade deletes defined in schema
    conn.execute("PRAGMA foreign_keys=ON")
    # Slightly larger cache for read-heavy workloads (~8 MB)
    conn.execute("PRAGMA cache_size=-8000")
    # Wait up to 5 s instead of immediately raising OperationalError on lock
    conn.execute("PRAGMA busy_timeout=5000")

    return conn


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Return the thread-local connection for db_path, opening it if needed.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Connection: Reusable thread-local connection.
    """
    if not hasattr(_local, "connections"):
        _local.connections = {}

    if db_path not in _local.connections:
        _local.connections[db_path] = _open_connection(db_path)

    return _local.connections[db_path]


@contextmanager
def get_db(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for a pooled SQLite connection.

    The connection is NOT closed on exit — it is returned to the thread-local
    pool for reuse.  Call conn.commit() explicitly inside the block for writes.
    On exception the context manager rolls back any pending transaction.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        sqlite3.Connection: Open, configured connection.

    Example:
        with get_db("search_system.db") as conn:
            conn.execute("INSERT INTO ...")
            conn.commit()
    """
    conn = get_connection(db_path)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise


def close_all() -> None:
    """
    Close all thread-local connections for the current thread.

    Call this from worker thread teardown (e.g. server shutdown hooks) to
    release file handles cleanly.
    """
    if hasattr(_local, "connections"):
        for conn in _local.connections.values():
            try:
                conn.close()
            except Exception:
                pass
        _local.connections.clear()
