"""
Document caching layer for MCP tools.

Hash-based caching with automatic invalidation on file changes.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Any
from dataclasses import asdict


class DocumentCache:
    """
    Hash-based document cache with TTL and automatic invalidation.

    Caches extracted document text to avoid re-processing.
    Invalidates cache when files are modified.
    """

    def __init__(self, cache_dir: str = ".cache/mcp_tools", enabled: bool = True, ttl_hours: int = 24):
        """
        Initialize document cache.

        Args:
            cache_dir: Cache directory path (relative)
            enabled: Enable caching
            ttl_hours: Time-to-live in hours
        """
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        self.ttl_seconds = ttl_hours * 3600

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, file_path: str) -> str:
        """
        Get hash of file path + modification time.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash string
        """
        path = Path(file_path)
        if not path.exists():
            return ""

        # Hash: file path + modification time + file size
        hash_input = f"{file_path}:{path.stat().st_mtime}:{path.stat().st_size}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path for hash"""
        return self.cache_dir / f"{file_hash}.json"

    def get(self, file_path: str) -> Optional[Any]:
        """
        Get cached document if available and not expired.

        Args:
            file_path: Path to original document

        Returns:
            Cached LoadedDocument or None if cache miss
        """
        if not self.enabled:
            return None

        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return None

        cache_path = self._get_cache_path(file_hash)

        # Check if cache exists
        if not cache_path.exists():
            return None

        # Check if cache expired
        cache_age = time.time() - cache_path.stat().st_mtime
        if cache_age > self.ttl_seconds:
            # Expired, delete it
            cache_path.unlink()
            return None

        # Load from cache
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruct LoadedDocument
            # Note: Will need to import LoadedDocument when using this
            # For now, return the raw data
            return data

        except Exception as e:
            # Cache corrupted, delete it
            print(f"Warning: Cache corrupted for {file_path}: {e}")
            cache_path.unlink()
            return None

    def set(self, file_path: str, document: Any) -> None:
        """
        Save document to cache.

        Args:
            file_path: Path to original document
            document: LoadedDocument to cache
        """
        if not self.enabled:
            return

        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return

        cache_path = self._get_cache_path(file_hash)

        try:
            # Convert dataclass to dict if needed
            if hasattr(document, '__dataclass_fields__'):
                data = asdict(document)
            elif hasattr(document, 'to_dict'):
                data = document.to_dict()
            else:
                data = document

            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            print(f"Warning: Failed to cache {file_path}: {e}")

    def clear(self) -> int:
        """
        Clear all cache files.

        Returns:
            Number of files deleted
        """
        if not self.enabled or not self.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1

        return count

    def clear_expired(self) -> int:
        """
        Clear expired cache files.

        Returns:
            Number of files deleted
        """
        if not self.enabled or not self.cache_dir.exists():
            return 0

        count = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            cache_age = now - cache_file.stat().st_mtime
            if cache_age > self.ttl_seconds:
                cache_file.unlink()
                count += 1

        return count
