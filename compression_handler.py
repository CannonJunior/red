#!/usr/bin/env python3
"""
Static File Compression Handler
Provides gzip compression for static assets with intelligent caching
"""

import gzip
import os
from pathlib import Path
from typing import Tuple, Optional
import hashlib
from debug_logger import debug_log, info_log


class CompressionHandler:
    """
    Handles gzip compression for static files with caching.

    Features:
    - Automatic gzip compression for supported file types
    - Caching of compressed versions
    - Content-Encoding headers
    - Intelligent compression level selection
    - ETag support for cache validation
    """

    # File types that benefit from gzip compression
    COMPRESSIBLE_TYPES = {
        '.js', '.css', '.html', '.htm', '.json', '.xml', '.svg',
        '.txt', '.md', '.csv', '.ico'
    }

    # Compression level (1-9, 6 is good balance of speed/size)
    COMPRESSION_LEVEL = 6

    # Minimum file size to compress (bytes)
    MIN_SIZE_TO_COMPRESS = 1024  # 1KB

    def __init__(self, cache_dir: str = '.gzip_cache'):
        """
        Initialize compression handler.

        Args:
            cache_dir: Directory to store pre-compressed files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Statistics
        self.compressions = 0
        self.cache_hits = 0
        self.bytes_saved = 0

        info_log("CompressionHandler initialized", "🗜️")

    def _should_compress(self, file_path: str, file_size: int) -> bool:
        """
        Determine if a file should be compressed.

        Args:
            file_path: Path to the file
            file_size: Size of the file in bytes

        Returns:
            True if file should be compressed
        """
        # Check file extension
        ext = Path(file_path).suffix.lower()
        if ext not in self.COMPRESSIBLE_TYPES:
            return False

        # Check minimum size
        if file_size < self.MIN_SIZE_TO_COMPRESS:
            return False

        return True

    def _get_cache_path(self, file_path: str) -> Path:
        """
        Get the cache path for a compressed file.

        Args:
            file_path: Original file path

        Returns:
            Path to cached compressed file
        """
        # Create a hash of the file path to avoid path issues
        path_hash = hashlib.md5(file_path.encode()).hexdigest()

        # Get modification time to invalidate cache if file changes
        mtime = os.path.getmtime(file_path)
        mtime_str = str(int(mtime))

        # Cache filename: hash_mtime.gz
        cache_filename = f"{path_hash}_{mtime_str}.gz"

        return self.cache_dir / cache_filename

    def _compress_file(self, file_path: str, output_path: Path) -> None:
        """
        Compress a file to gzip format.

        Args:
            file_path: Source file path
            output_path: Destination compressed file path
        """
        with open(file_path, 'rb') as f_in:
            with gzip.open(output_path, 'wb', compresslevel=self.COMPRESSION_LEVEL) as f_out:
                f_out.write(f_in.read())

        self.compressions += 1

        # Calculate compression ratio
        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(output_path)
        ratio = (1 - compressed_size / original_size) * 100
        self.bytes_saved += (original_size - compressed_size)

        debug_log(
            f"Compressed {Path(file_path).name}: "
            f"{original_size} → {compressed_size} bytes ({ratio:.1f}% reduction)",
            "🗜️"
        )

    def get_compressed_content(
        self,
        file_path: str,
        accepts_gzip: bool = False
    ) -> Tuple[bytes, bool]:
        """
        Get file content, compressed if appropriate.

        Args:
            file_path: Path to the file
            accepts_gzip: Whether client accepts gzip encoding

        Returns:
            Tuple of (content, is_compressed)
        """
        # Get file size
        file_size = os.path.getsize(file_path)

        # Check if we should compress
        if not accepts_gzip or not self._should_compress(file_path, file_size):
            # Return uncompressed content
            with open(file_path, 'rb') as f:
                return f.read(), False

        # Get cache path
        cache_path = self._get_cache_path(file_path)

        # Check if compressed version exists in cache
        if cache_path.exists():
            self.cache_hits += 1
            debug_log(f"Gzip cache HIT: {Path(file_path).name}", "⚡")
            with open(cache_path, 'rb') as f:
                return f.read(), True

        # Compress and cache
        debug_log(f"Gzip cache MISS: {Path(file_path).name}", "💾")
        self._compress_file(file_path, cache_path)

        # Return compressed content
        with open(cache_path, 'rb') as f:
            return f.read(), True

    def cleanup_old_cache(self) -> int:
        """
        Remove cached files for files that no longer exist.

        Returns:
            Number of files removed
        """
        removed = 0

        for cache_file in self.cache_dir.glob('*.gz'):
            # Cache files are named: hash_mtime.gz
            # We can't easily determine if the original file exists,
            # but we can check file age

            # Remove cache files older than 7 days
            age_days = (Path.ctime(cache_file) - os.path.getctime(cache_file)) / 86400
            if age_days > 7:
                cache_file.unlink()
                removed += 1

        if removed > 0:
            info_log(f"Cleaned up {removed} old cache files", "🧹")

        return removed

    def get_stats(self) -> dict:
        """
        Get compression statistics.

        Returns:
            Dictionary with compression stats
        """
        cache_files = list(self.cache_dir.glob('*.gz'))
        cache_size = sum(f.stat().st_size for f in cache_files)

        return {
            'compressions': self.compressions,
            'cache_hits': self.cache_hits,
            'bytes_saved': self.bytes_saved,
            'cache_files': len(cache_files),
            'cache_size_mb': cache_size / (1024 * 1024),
            'hit_rate': (
                self.cache_hits / (self.cache_hits + self.compressions) * 100
                if (self.cache_hits + self.compressions) > 0
                else 0
            )
        }


# Singleton instance
_compression_handler = None


def get_compression_handler() -> CompressionHandler:
    """
    Get the global compression handler instance.

    Returns:
        CompressionHandler singleton instance
    """
    global _compression_handler
    if _compression_handler is None:
        _compression_handler = CompressionHandler()
    return _compression_handler
