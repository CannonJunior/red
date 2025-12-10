"""
Static asset caching system for the RED project.

Provides in-memory caching for static files (HTML, CSS, JS, images) with
automatic cache invalidation based on file modification time.
"""

import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any


class StaticCache:
    """
    In-memory cache for static files with TTL and ETag support.

    This cache stores file contents in memory to avoid repeated disk reads,
    which can provide 10x faster serving for frequently accessed files.
    """

    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize the static cache.

        Args:
            ttl_minutes: Time-to-live for cache entries in minutes (default: 60)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.hits = 0
        self.misses = 0

    def get(self, file_path: str) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Get a file from the cache.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (content, etag) or (None, None) if not cached or expired

        Usage:
            content, etag = cache.get('/path/to/file.js')
            if content is None:
                # Cache miss - load from disk
                pass
        """
        if file_path not in self.cache:
            self.misses += 1
            return None, None

        entry = self.cache[file_path]

        # Check if entry has expired
        if datetime.now() > entry['expires']:
            del self.cache[file_path]
            self.misses += 1
            return None, None

        # Check if file has been modified (invalidate cache)
        try:
            current_mtime = Path(file_path).stat().st_mtime
            if current_mtime != entry['mtime']:
                del self.cache[file_path]
                self.misses += 1
                return None, None
        except OSError:
            # File doesn't exist anymore
            del self.cache[file_path]
            self.misses += 1
            return None, None

        # Cache hit!
        self.hits += 1
        return entry['content'], entry['etag']

    def set(self, file_path: str, content: bytes) -> str:
        """
        Store a file in the cache.

        Args:
            file_path: Path to the file
            content: File content as bytes

        Returns:
            The computed ETag for the file

        Usage:
            etag = cache.set('/path/to/file.js', content_bytes)
        """
        # Compute ETag (MD5 hash of content)
        etag = hashlib.md5(content).hexdigest()

        # Get file modification time for cache invalidation
        try:
            mtime = Path(file_path).stat().st_mtime
        except OSError:
            mtime = 0

        # Store in cache
        self.cache[file_path] = {
            'content': content,
            'etag': etag,
            'mtime': mtime,
            'expires': datetime.now() + self.ttl,
            'cached_at': datetime.now()
        }

        return etag

    def invalidate(self, file_path: str) -> bool:
        """
        Remove a specific file from the cache.

        Args:
            file_path: Path to the file to invalidate

        Returns:
            True if the file was in cache, False otherwise

        Usage:
            cache.invalidate('/path/to/file.js')
        """
        if file_path in self.cache:
            del self.cache[file_path]
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cached files.

        Returns:
            Number of files that were cached

        Usage:
            count = cache.clear()
            print(f"Cleared {count} cached files")
        """
        count = len(self.cache)
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics

        Usage:
            stats = cache.get_stats()
            print(f"Hit rate: {stats['hit_rate']}%")
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'cached_files': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total_requests,
            'hit_rate': round(hit_rate, 2),
            'cache_size_bytes': sum(len(entry['content']) for entry in self.cache.values())
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from the cache.

        Returns:
            Number of expired entries removed

        Usage:
            removed = cache.cleanup_expired()
        """
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now > entry['expires']
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)


# Global cache instance
_cache_instance: Optional[StaticCache] = None


def get_static_cache(ttl_minutes: int = 60) -> StaticCache:
    """
    Get the global static cache instance (singleton).

    Args:
        ttl_minutes: TTL for new cache (only used on first call)

    Returns:
        The global StaticCache instance

    Usage:
        cache = get_static_cache()
        content, etag = cache.get('/path/to/file.js')
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = StaticCache(ttl_minutes=ttl_minutes)
    return _cache_instance
