#!/usr/bin/env python3
"""
Connection Pooling Module

Provides efficient connection pooling for HTTP and SQLite connections
to improve performance and resource utilization.

Features:
- HTTP connection pool for Ollama requests (reuses connections)
- SQLite connection pool with thread-safe access
- Automatic connection lifecycle management
- Connection health checking and validation
- Configurable pool sizes and timeouts
"""

import threading
import time
import sqlite3
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from queue import Queue, Empty
from dataclasses import dataclass
from datetime import datetime, timedelta
from debug_logger import debug_log, error_log, info_log


# ============================================================================
# HTTP CONNECTION POOL (for Ollama and external APIs)
# ============================================================================

@dataclass
class PooledHTTPConnection:
    """Wrapper for HTTP connection with metadata."""
    opener: urllib.request.OpenerDirector
    created_at: datetime
    last_used: datetime
    use_count: int = 0

    def mark_used(self):
        """Mark connection as used."""
        self.last_used = datetime.now()
        self.use_count += 1

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if connection is stale (older than max_age)."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > max_age_seconds

    def is_idle_too_long(self, max_idle_seconds: int = 60) -> bool:
        """Check if connection has been idle too long."""
        idle = (datetime.now() - self.last_used).total_seconds()
        return idle > max_idle_seconds


class HTTPConnectionPool:
    """
    Thread-safe HTTP connection pool for reusing urllib connections.

    Benefits:
    - Reuses connections (avoids TCP handshake overhead)
    - Reduces connection creation latency
    - Thread-safe with lock protection
    - Automatic connection lifecycle management

    Usage:
        pool = HTTPConnectionPool(pool_size=10)
        with pool.get_connection() as opener:
            response = opener.open(request)
    """

    def __init__(self, pool_size: int = 10, max_age_seconds: int = 300, max_idle_seconds: int = 60):
        """
        Initialize HTTP connection pool.

        Args:
            pool_size: Maximum number of connections in pool
            max_age_seconds: Maximum age of connection before recreation
            max_idle_seconds: Maximum idle time before closing connection
        """
        self.pool_size = pool_size
        self.max_age_seconds = max_age_seconds
        self.max_idle_seconds = max_idle_seconds

        # Thread-safe queue for available connections
        self.pool: Queue = Queue(maxsize=pool_size)

        # Statistics
        self.stats = {
            'created': 0,
            'reused': 0,
            'recycled': 0,
            'total_requests': 0
        }

        # Lock for thread safety
        self.lock = threading.Lock()

        info_log(f"HTTPConnectionPool initialized (size={pool_size}, max_age={max_age_seconds}s)", "🌐")

    def _create_connection(self) -> PooledHTTPConnection:
        """Create a new HTTP connection."""
        # Create opener with timeout support
        opener = urllib.request.build_opener(urllib.request.HTTPHandler())

        conn = PooledHTTPConnection(
            opener=opener,
            created_at=datetime.now(),
            last_used=datetime.now()
        )

        with self.lock:
            self.stats['created'] += 1

        debug_log(f"Created new HTTP connection (total created: {self.stats['created']})", "🔗")
        return conn

    def _is_connection_healthy(self, conn: PooledHTTPConnection) -> bool:
        """Check if connection is healthy and should be reused."""
        # Check if connection is too old
        if conn.is_stale(self.max_age_seconds):
            debug_log("Connection is stale, recycling", "♻️")
            return False

        # Check if connection has been idle too long
        if conn.is_idle_too_long(self.max_idle_seconds):
            debug_log("Connection idle too long, recycling", "♻️")
            return False

        return True

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Usage:
            with pool.get_connection() as opener:
                response = opener.open(request)

        Yields:
            urllib.request.OpenerDirector: HTTP opener for making requests
        """
        conn: Optional[PooledHTTPConnection] = None

        try:
            # Try to get existing connection from pool (non-blocking)
            try:
                conn = self.pool.get_nowait()

                # Validate connection health
                if not self._is_connection_healthy(conn):
                    with self.lock:
                        self.stats['recycled'] += 1
                    conn = self._create_connection()
                else:
                    with self.lock:
                        self.stats['reused'] += 1
                    debug_log("Reusing pooled HTTP connection", "♻️")

            except Empty:
                # Pool is empty, create new connection
                conn = self._create_connection()

            # Mark as used
            conn.mark_used()

            with self.lock:
                self.stats['total_requests'] += 1

            # Yield the opener for use
            yield conn.opener

        finally:
            # Return connection to pool if it's still healthy
            if conn is not None:
                if self._is_connection_healthy(conn):
                    try:
                        # Try to return to pool (non-blocking)
                        self.pool.put_nowait(conn)
                    except:
                        # Pool is full, discard connection
                        debug_log("Pool full, discarding connection", "🗑️")
                else:
                    debug_log("Connection unhealthy, discarding", "🗑️")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self.lock:
            return {
                **self.stats,
                'pool_size': self.pool.qsize(),
                'max_pool_size': self.pool_size,
                'reuse_rate': (self.stats['reused'] / max(self.stats['total_requests'], 1)) * 100
            }

    def cleanup(self):
        """Clean up all connections in the pool."""
        while not self.pool.empty():
            try:
                self.pool.get_nowait()
            except Empty:
                break
        info_log("HTTPConnectionPool cleaned up", "🧹")


# ============================================================================
# SQLITE CONNECTION POOL
# ============================================================================

@dataclass
class PooledSQLiteConnection:
    """Wrapper for SQLite connection with metadata."""
    connection: sqlite3.Connection
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    in_use: bool = False

    def mark_used(self):
        """Mark connection as used."""
        self.last_used = datetime.now()
        self.use_count += 1
        self.in_use = True

    def mark_returned(self):
        """Mark connection as returned to pool."""
        self.in_use = False

    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """Check if connection is stale (older than max_age)."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > max_age_seconds


class SQLiteConnectionPool:
    """
    Thread-safe SQLite connection pool for database operations.

    Benefits:
    - Reuses connections (avoids file open overhead)
    - Thread-safe with lock protection
    - Prevents "database is locked" errors
    - Automatic connection validation

    Usage:
        pool = SQLiteConnectionPool('search_system.db', pool_size=5)
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    """

    def __init__(self, database_path: str, pool_size: int = 5, max_age_seconds: int = 3600):
        """
        Initialize SQLite connection pool.

        Args:
            database_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool
            max_age_seconds: Maximum age of connection before recreation
        """
        self.database_path = database_path
        self.pool_size = pool_size
        self.max_age_seconds = max_age_seconds

        # List of all connections (both available and in-use)
        self.connections: List[PooledSQLiteConnection] = []

        # Statistics
        self.stats = {
            'created': 0,
            'reused': 0,
            'recycled': 0,
            'total_checkouts': 0,
            'wait_count': 0
        }

        # Lock for thread safety
        self.lock = threading.Lock()
        self.available = threading.Condition(self.lock)

        info_log(f"SQLiteConnectionPool initialized (db={database_path}, size={pool_size})", "💾")

    def _create_connection(self) -> PooledSQLiteConnection:
        """Create a new SQLite connection."""
        conn = sqlite3.connect(
            self.database_path,
            check_same_thread=False,  # Allow multi-threading
            timeout=30.0  # Wait up to 30 seconds if database is locked
        )

        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Set journal mode to WAL for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")

        # Set synchronous mode for better performance
        conn.execute("PRAGMA synchronous = NORMAL")

        pooled_conn = PooledSQLiteConnection(
            connection=conn,
            created_at=datetime.now(),
            last_used=datetime.now()
        )

        # NOTE: Caller must hold self.lock (via self.available)
        self.stats['created'] += 1
        self.connections.append(pooled_conn)

        debug_log(f"Created new SQLite connection (total created: {self.stats['created']})", "💾")
        return pooled_conn

    def _is_connection_healthy(self, conn: PooledSQLiteConnection) -> bool:
        """Check if connection is healthy and should be reused."""
        # Check if connection is too old
        if conn.is_stale(self.max_age_seconds):
            return False

        # Test if connection is still valid
        try:
            conn.connection.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """
        Get a connection from the pool (context manager).

        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")

        Args:
            timeout: Maximum time to wait for available connection

        Yields:
            sqlite3.Connection: Database connection
        """
        conn_wrapper: Optional[PooledSQLiteConnection] = None
        start_time = time.time()

        try:
            with self.available:
                # Try to find an available healthy connection
                while True:
                    # Check for available connection
                    for conn in self.connections:
                        if not conn.in_use and self._is_connection_healthy(conn):
                            conn.mark_used()
                            conn_wrapper = conn

                            # NOTE: Already holding self.lock via self.available
                            self.stats['reused'] += 1
                            self.stats['total_checkouts'] += 1

                            debug_log("Reusing pooled SQLite connection", "♻️")
                            break

                    # If we found a connection, break out
                    if conn_wrapper is not None:
                        break

                    # Remove unhealthy connections
                    self.connections = [c for c in self.connections if c.in_use or self._is_connection_healthy(c)]

                    # Create new connection if pool not full
                    if len(self.connections) < self.pool_size:
                        conn_wrapper = self._create_connection()
                        conn_wrapper.mark_used()

                        # NOTE: Already holding self.lock via self.available
                        self.stats['total_checkouts'] += 1
                        break

                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise TimeoutError(f"Failed to acquire SQLite connection after {timeout}s")

                    # Wait for connection to become available
                    # NOTE: Already holding self.lock via self.available
                    self.stats['wait_count'] += 1

                    debug_log("Waiting for available SQLite connection...", "⏳")
                    self.available.wait(timeout=min(1.0, timeout - elapsed))

            # Yield the connection for use
            yield conn_wrapper.connection

        finally:
            # Return connection to pool
            if conn_wrapper is not None:
                conn_wrapper.mark_returned()

                # Notify waiting threads
                with self.available:
                    self.available.notify()

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self.lock:
            return {
                **self.stats,
                'pool_size': len(self.connections),
                'max_pool_size': self.pool_size,
                'active_connections': sum(1 for c in self.connections if c.in_use),
                'reuse_rate': (self.stats['reused'] / max(self.stats['total_checkouts'], 1)) * 100
            }

    def cleanup(self):
        """Clean up all connections in the pool."""
        with self.lock:
            for conn in self.connections:
                try:
                    conn.connection.close()
                except:
                    pass
            self.connections.clear()
        info_log("SQLiteConnectionPool cleaned up", "🧹")


# ============================================================================
# GLOBAL CONNECTION POOLS
# ============================================================================

# Global HTTP connection pool for Ollama requests
_http_pool: Optional[HTTPConnectionPool] = None
_http_pool_lock = threading.Lock()

def get_http_pool() -> HTTPConnectionPool:
    """Get the global HTTP connection pool (singleton)."""
    global _http_pool

    if _http_pool is None:
        with _http_pool_lock:
            if _http_pool is None:
                _http_pool = HTTPConnectionPool(pool_size=10)

    return _http_pool


# Global SQLite connection pools (one per database)
_sqlite_pools: Dict[str, SQLiteConnectionPool] = {}
_sqlite_pools_lock = threading.Lock()

def get_sqlite_pool(database_path: str, pool_size: int = 5) -> SQLiteConnectionPool:
    """
    Get a SQLite connection pool for a specific database (singleton per DB).

    Args:
        database_path: Path to SQLite database file
        pool_size: Maximum number of connections in pool

    Returns:
        SQLiteConnectionPool: Connection pool for the database
    """
    global _sqlite_pools

    if database_path not in _sqlite_pools:
        with _sqlite_pools_lock:
            if database_path not in _sqlite_pools:
                _sqlite_pools[database_path] = SQLiteConnectionPool(database_path, pool_size)

    return _sqlite_pools[database_path]


def cleanup_all_pools():
    """Clean up all connection pools."""
    global _http_pool, _sqlite_pools

    if _http_pool is not None:
        _http_pool.cleanup()

    for pool in _sqlite_pools.values():
        pool.cleanup()

    info_log("All connection pools cleaned up", "🧹")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    import tempfile
    import os

    print("Testing Connection Pools...")

    # Test HTTP Connection Pool
    print("\n1. Testing HTTP Connection Pool:")
    http_pool = get_http_pool()

    for i in range(5):
        with http_pool.get_connection() as opener:
            print(f"   Request {i+1}: Using opener {id(opener)}")

    print(f"   Stats: {http_pool.get_stats()}")

    # Test SQLite Connection Pool
    print("\n2. Testing SQLite Connection Pool:")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name

    try:
        sqlite_pool = get_sqlite_pool(db_path, pool_size=3)

        # Create table
        with sqlite_pool.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            conn.commit()

        # Insert data using multiple connections
        for i in range(5):
            with sqlite_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test (value) VALUES (?)", (f"value_{i}",))
                conn.commit()
                print(f"   Inserted value_{i}")

        # Query data
        with sqlite_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            print(f"   Total rows: {count}")

        print(f"   Stats: {sqlite_pool.get_stats()}")

    finally:
        cleanup_all_pools()
        os.unlink(db_path)

    print("\nConnection pool tests completed! ✅")
