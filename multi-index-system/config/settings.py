"""
Configuration settings for the multi-index knowledge base system.

Following the project's zero-cost, local-first philosophy with environment variable support.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class IndexConfig:
    """Configuration for individual indices."""
    enabled: bool = True
    priority: int = 1
    cache_size: int = 1000
    timeout_seconds: float = 5.0

@dataclass
class MultiIndexConfig:
    """
    Centralized configuration for the multi-index system.

    Follows the project's pattern of using environment variables with sensible defaults
    and zero-cost, locally-running architecture.
    """

    # Base paths
    base_data_dir: Path = field(default_factory=lambda: Path(os.getenv('MULTI_INDEX_DATA_DIR', './multi_index_data')))

    # Vector database (ChromaDB)
    vector_config: IndexConfig = field(default_factory=lambda: IndexConfig(
        enabled=True,
        priority=1,
        cache_size=int(os.getenv('VECTOR_CACHE_SIZE', '2000')),
        timeout_seconds=float(os.getenv('VECTOR_TIMEOUT', '5.0'))
    ))

    # Graph database (Kùzu)
    graph_config: IndexConfig = field(default_factory=lambda: IndexConfig(
        enabled=bool(os.getenv('GRAPH_ENABLED', 'true').lower() == 'true'),
        priority=2,
        cache_size=int(os.getenv('GRAPH_CACHE_SIZE', '1000')),
        timeout_seconds=float(os.getenv('GRAPH_TIMEOUT', '10.0'))
    ))

    # Metadata database (DuckDB)
    metadata_config: IndexConfig = field(default_factory=lambda: IndexConfig(
        enabled=True,
        priority=3,
        cache_size=int(os.getenv('METADATA_CACHE_SIZE', '500')),
        timeout_seconds=float(os.getenv('METADATA_TIMEOUT', '3.0'))
    ))

    # Full-text search
    fts_config: IndexConfig = field(default_factory=lambda: IndexConfig(
        enabled=bool(os.getenv('FTS_ENABLED', 'true').lower() == 'true'),
        priority=4,
        cache_size=int(os.getenv('FTS_CACHE_SIZE', '800')),
        timeout_seconds=float(os.getenv('FTS_TIMEOUT', '2.0'))
    ))

    # Temporal/versioning index
    temporal_config: IndexConfig = field(default_factory=lambda: IndexConfig(
        enabled=bool(os.getenv('TEMPORAL_ENABLED', 'true').lower() == 'true'),
        priority=5,
        cache_size=int(os.getenv('TEMPORAL_CACHE_SIZE', '300')),
        timeout_seconds=float(os.getenv('TEMPORAL_TIMEOUT', '5.0'))
    ))

    # Query routing configuration
    max_concurrent_queries: int = int(os.getenv('MAX_CONCURRENT_QUERIES', '10'))
    query_timeout_seconds: float = float(os.getenv('QUERY_TIMEOUT', '30.0'))
    enable_query_caching: bool = bool(os.getenv('ENABLE_QUERY_CACHING', 'true').lower() == 'true')
    cache_ttl_seconds: int = int(os.getenv('CACHE_TTL_SECONDS', '300'))

    # Health monitoring
    health_check_interval: float = float(os.getenv('HEALTH_CHECK_INTERVAL', '60.0'))
    metrics_retention_hours: int = int(os.getenv('METRICS_RETENTION_HOURS', '24'))
    enable_performance_tracking: bool = bool(os.getenv('ENABLE_PERFORMANCE_TRACKING', 'true').lower() == 'true')

    # Redis configuration for event streaming
    redis_host: str = os.getenv('REDIS_HOST', 'localhost')
    redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
    redis_timeout: float = float(os.getenv('REDIS_TIMEOUT', '5.0'))

    # Conflict resolution
    enable_conflict_resolution: bool = bool(os.getenv('ENABLE_CONFLICT_RESOLUTION', 'true').lower() == 'true')
    max_conflict_resolution_attempts: int = int(os.getenv('MAX_CONFLICT_ATTEMPTS', '3'))

    def __post_init__(self):
        """Create data directories if they don't exist."""
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for each index type
        (self.base_data_dir / 'vector').mkdir(exist_ok=True)
        (self.base_data_dir / 'graph').mkdir(exist_ok=True)
        (self.base_data_dir / 'metadata').mkdir(exist_ok=True)
        (self.base_data_dir / 'fts').mkdir(exist_ok=True)
        (self.base_data_dir / 'temporal').mkdir(exist_ok=True)
        (self.base_data_dir / 'cache').mkdir(exist_ok=True)
        (self.base_data_dir / 'logs').mkdir(exist_ok=True)

    def get_index_path(self, index_type: str) -> Path:
        """Get the data path for a specific index type."""
        return self.base_data_dir / index_type

    def get_enabled_indices(self) -> Dict[str, IndexConfig]:
        """Get all enabled index configurations."""
        indices = {
            'vector': self.vector_config,
            'graph': self.graph_config,
            'metadata': self.metadata_config,
            'fts': self.fts_config,
            'temporal': self.temporal_config
        }
        return {name: config for name, config in indices.items() if config.enabled}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key with optional default."""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging."""
        return {
            'base_data_dir': str(self.base_data_dir),
            'enabled_indices': list(self.get_enabled_indices().keys()),
            'max_concurrent_queries': self.max_concurrent_queries,
            'query_timeout': self.query_timeout_seconds,
            'caching_enabled': self.enable_query_caching,
            'health_monitoring': self.enable_performance_tracking
        }

# Global configuration instance
config = MultiIndexConfig()

# Convenience functions
def get_config() -> MultiIndexConfig:
    """Get the global configuration instance."""
    return config

def reload_config() -> MultiIndexConfig:
    """Reload configuration from environment variables."""
    global config
    config = MultiIndexConfig()
    return config