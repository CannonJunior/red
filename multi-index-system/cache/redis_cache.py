"""
Advanced Caching Layer with Redis Integration for Phase 3

Provides intelligent caching with Redis for query results, embeddings,
and real-time data with advanced features like cache warming,
distributed locking, and performance analytics.
"""

import asyncio
import json
import logging
import pickle
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import uuid

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

try:
    from ..config.settings import get_config
    from ..core.query_executor import QueryResult
except ImportError:
    from config.settings import get_config
    # Mock QueryResult for fallback
    class QueryResult:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int
    last_accessed: datetime
    size_bytes: int
    tags: List[str]

@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int
    hits: int
    misses: int
    hit_rate: float
    avg_retrieval_time: float
    total_size_bytes: int
    entry_count: int
    evictions: int

class AdvancedRedisCache:
    """
    Advanced Redis-based caching system with intelligent features.

    Features:
    - Distributed caching with Redis
    - Intelligent cache warming and prefetching
    - Query result and embedding caching
    - Cache invalidation strategies
    - Performance analytics and monitoring
    - Distributed locking for consistency
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()

        # Redis configuration
        self.redis_url = self.config.get('redis_url', 'redis://localhost:6379/0')
        self.redis_pool = None
        self.redis_client = None

        # Cache configuration
        self.default_ttl = self.config.get('cache_ttl', 3600)  # 1 hour
        self.max_memory = self.config.get('cache_max_memory', '100MB')
        self.compression_threshold = self.config.get('compression_threshold', 1024)  # 1KB

        # Performance tracking
        self.stats = CacheStats(
            total_requests=0, hits=0, misses=0, hit_rate=0.0,
            avg_retrieval_time=0.0, total_size_bytes=0,
            entry_count=0, evictions=0
        )

        # Fallback in-memory cache
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.use_redis = REDIS_AVAILABLE

        # Cache prefixes for different data types
        self.prefixes = {
            'query_result': 'qr:',
            'embedding': 'emb:',
            'analytics': 'ana:',
            'visualization': 'viz:',
            'user_session': 'usr:',
            'index_health': 'health:',
            'adaptive_pattern': 'pattern:'
        }

    async def initialize(self):
        """Initialize Redis connection and cache system."""
        if not self.use_redis:
            logger.warning("Redis not available, using in-memory cache fallback")
            return

        try:
            # Create Redis connection pool
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30
            )

            self.redis_client = redis.Redis(connection_pool=self.redis_pool)

            # Test connection
            await self.redis_client.ping()

            # Configure Redis memory policy
            try:
                await self.redis_client.config_set('maxmemory', self.max_memory)
                await self.redis_client.config_set('maxmemory-policy', 'allkeys-lru')
            except Exception as e:
                logger.warning(f"Could not configure Redis memory settings: {e}")

            logger.info(f"Redis cache initialized at {self.redis_url}")

        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            logger.info("Falling back to in-memory cache")
            self.use_redis = False

    async def get(self, key: str, data_type: str = 'query_result') -> Optional[Any]:
        """Get value from cache with performance tracking."""
        start_time = time.time()
        self.stats.total_requests += 1

        try:
            prefixed_key = self._get_prefixed_key(key, data_type)

            if self.use_redis and self.redis_client:
                # Try Redis first
                cached_data = await self.redis_client.get(prefixed_key)
                if cached_data:
                    # Update access tracking
                    await self._update_access_tracking(prefixed_key)

                    value = self._deserialize(cached_data)
                    self.stats.hits += 1
                    self._update_retrieval_time(time.time() - start_time)
                    return value
            else:
                # Use in-memory cache
                if prefixed_key in self.memory_cache:
                    entry = self.memory_cache[prefixed_key]

                    # Check expiration
                    if entry.expires_at and datetime.now() > entry.expires_at:
                        del self.memory_cache[prefixed_key]
                        self.stats.misses += 1
                        return None

                    # Update access tracking
                    entry.access_count += 1
                    entry.last_accessed = datetime.now()

                    self.stats.hits += 1
                    self._update_retrieval_time(time.time() - start_time)
                    return entry.value

            self.stats.misses += 1
            return None

        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            self.stats.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None,
                 data_type: str = 'query_result', tags: Optional[List[str]] = None) -> bool:
        """Set value in cache with optional TTL and tags."""
        try:
            prefixed_key = self._get_prefixed_key(key, data_type)
            ttl = ttl or self.default_ttl
            tags = tags or []

            if self.use_redis and self.redis_client:
                # Serialize and potentially compress
                serialized_value = self._serialize(value)

                # Set with TTL
                await self.redis_client.setex(prefixed_key, ttl, serialized_value)

                # Set metadata
                metadata = {
                    'created_at': datetime.now().isoformat(),
                    'tags': tags,
                    'size_bytes': len(serialized_value),
                    'data_type': data_type
                }
                await self.redis_client.setex(
                    f"{prefixed_key}:meta",
                    ttl,
                    json.dumps(metadata)
                )

                # Add to tag sets for invalidation
                for tag in tags:
                    await self.redis_client.sadd(f"tag:{tag}", prefixed_key)
                    await self.redis_client.expire(f"tag:{tag}", ttl)

            else:
                # Use in-memory cache
                expires_at = datetime.now() + timedelta(seconds=ttl)
                serialized_value = self._serialize(value)

                entry = CacheEntry(
                    key=prefixed_key,
                    value=value,
                    created_at=datetime.now(),
                    expires_at=expires_at,
                    access_count=0,
                    last_accessed=datetime.now(),
                    size_bytes=len(serialized_value),
                    tags=tags
                )

                self.memory_cache[prefixed_key] = entry

                # Implement simple LRU eviction for memory cache
                await self._evict_if_needed()

            self.stats.entry_count += 1
            return True

        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    async def delete(self, key: str, data_type: str = 'query_result') -> bool:
        """Delete value from cache."""
        try:
            prefixed_key = self._get_prefixed_key(key, data_type)

            if self.use_redis and self.redis_client:
                # Delete main key and metadata
                deleted = await self.redis_client.delete(prefixed_key, f"{prefixed_key}:meta")
                return deleted > 0
            else:
                if prefixed_key in self.memory_cache:
                    del self.memory_cache[prefixed_key]
                    return True

            return False

        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate all cache entries with specified tags."""
        invalidated_count = 0

        try:
            if self.use_redis and self.redis_client:
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    keys = await self.redis_client.smembers(tag_key)

                    if keys:
                        # Delete all keys with this tag
                        await self.redis_client.delete(*keys)
                        # Delete metadata keys
                        meta_keys = [f"{key}:meta" for key in keys]
                        await self.redis_client.delete(*meta_keys)
                        # Delete tag set
                        await self.redis_client.delete(tag_key)

                        invalidated_count += len(keys)
            else:
                # In-memory cache tag invalidation
                keys_to_delete = []
                for key, entry in self.memory_cache.items():
                    if any(tag in entry.tags for tag in tags):
                        keys_to_delete.append(key)

                for key in keys_to_delete:
                    del self.memory_cache[key]
                    invalidated_count += 1

            logger.info(f"Invalidated {invalidated_count} cache entries for tags: {tags}")
            return invalidated_count

        except Exception as e:
            logger.error(f"Cache tag invalidation failed: {e}")
            return 0

    async def warm_cache(self, warm_data: List[Tuple[str, Any, str]]) -> int:
        """Warm cache with precomputed data."""
        warmed_count = 0

        try:
            for key, value, data_type in warm_data:
                success = await self.set(key, value, data_type=data_type, tags=['warmed'])
                if success:
                    warmed_count += 1

            logger.info(f"Warmed cache with {warmed_count} entries")
            return warmed_count

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return 0

    async def get_multi(self, keys: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Get multiple values efficiently."""
        results = {}

        try:
            if self.use_redis and self.redis_client:
                # Get all keys in one operation
                prefixed_keys = [self._get_prefixed_key(key, data_type) for key, data_type in keys]
                values = await self.redis_client.mget(prefixed_keys)

                for (original_key, data_type), value in zip(keys, values):
                    if value:
                        results[original_key] = self._deserialize(value)
                        self.stats.hits += 1
                    else:
                        self.stats.misses += 1
            else:
                # In-memory multi-get
                for key, data_type in keys:
                    prefixed_key = self._get_prefixed_key(key, data_type)
                    if prefixed_key in self.memory_cache:
                        entry = self.memory_cache[prefixed_key]
                        if not entry.expires_at or datetime.now() <= entry.expires_at:
                            results[key] = entry.value
                            self.stats.hits += 1
                        else:
                            del self.memory_cache[prefixed_key]
                            self.stats.misses += 1
                    else:
                        self.stats.misses += 1

            self.stats.total_requests += len(keys)
            return results

        except Exception as e:
            logger.error(f"Cache multi-get failed: {e}")
            self.stats.total_requests += len(keys)
            self.stats.misses += len(keys)
            return {}

    async def set_multi(self, items: List[Tuple[str, Any, str, Optional[int]]]) -> int:
        """Set multiple values efficiently."""
        success_count = 0

        try:
            if self.use_redis and self.redis_client:
                # Use pipeline for efficiency
                pipe = self.redis_client.pipeline()

                for key, value, data_type, ttl in items:
                    prefixed_key = self._get_prefixed_key(key, data_type)
                    serialized_value = self._serialize(value)
                    ttl = ttl or self.default_ttl

                    pipe.setex(prefixed_key, ttl, serialized_value)

                await pipe.execute()
                success_count = len(items)
            else:
                # In-memory multi-set
                for key, value, data_type, ttl in items:
                    success = await self.set(key, value, ttl, data_type)
                    if success:
                        success_count += 1

            return success_count

        except Exception as e:
            logger.error(f"Cache multi-set failed: {e}")
            return 0

    async def acquire_lock(self, resource: str, timeout: int = 10) -> Optional[str]:
        """Acquire distributed lock for resource."""
        if not self.use_redis or not self.redis_client:
            # Fallback: always return a mock lock
            return str(uuid.uuid4())

        try:
            lock_key = f"lock:{resource}"
            lock_value = str(uuid.uuid4())

            # Try to acquire lock with timeout
            acquired = await self.redis_client.set(
                lock_key, lock_value, nx=True, ex=timeout
            )

            return lock_value if acquired else None

        except Exception as e:
            logger.error(f"Failed to acquire lock for {resource}: {e}")
            return None

    async def release_lock(self, resource: str, lock_value: str) -> bool:
        """Release distributed lock."""
        if not self.use_redis or not self.redis_client:
            return True  # Always succeed for fallback

        try:
            lock_key = f"lock:{resource}"

            # Lua script for atomic lock release
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """

            result = await self.redis_client.eval(lua_script, 1, lock_key, lock_value)
            return result == 1

        except Exception as e:
            logger.error(f"Failed to release lock for {resource}: {e}")
            return False

    async def get_cache_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        try:
            # Update hit rate
            total_requests = self.stats.hits + self.stats.misses
            self.stats.hit_rate = self.stats.hits / max(total_requests, 1)

            if self.use_redis and self.redis_client:
                # Get Redis-specific stats
                info = await self.redis_client.info('memory')
                self.stats.total_size_bytes = info.get('used_memory', 0)

                # Count keys by prefix
                key_count = 0
                for prefix in self.prefixes.values():
                    keys = await self.redis_client.keys(f"{prefix}*")
                    key_count += len(keys)

                self.stats.entry_count = key_count
            else:
                # In-memory cache stats
                self.stats.entry_count = len(self.memory_cache)
                self.stats.total_size_bytes = sum(
                    entry.size_bytes for entry in self.memory_cache.values()
                )

            return self.stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return self.stats

    async def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache performance."""
        optimization_results = {
            "actions_taken": [],
            "stats_before": await self.get_cache_stats(),
            "recommendations": []
        }

        try:
            if self.use_redis and self.redis_client:
                # Clean up expired keys
                cleaned_keys = await self._cleanup_expired_keys()
                if cleaned_keys > 0:
                    optimization_results["actions_taken"].append({
                        "action": "cleaned_expired_keys",
                        "count": cleaned_keys
                    })

                # Optimize memory usage
                await self._optimize_memory_usage()
                optimization_results["actions_taken"].append({
                    "action": "optimized_memory_usage"
                })

            else:
                # In-memory cache optimization
                evicted = await self._evict_if_needed()
                if evicted > 0:
                    optimization_results["actions_taken"].append({
                        "action": "evicted_lru_entries",
                        "count": evicted
                    })

            # Generate recommendations
            stats_after = await self.get_cache_stats()
            optimization_results["stats_after"] = stats_after

            if stats_after.hit_rate < 0.5:
                optimization_results["recommendations"].append(
                    "Consider increasing cache TTL or implementing cache warming"
                )

            if stats_after.total_size_bytes > 100 * 1024 * 1024:  # 100MB
                optimization_results["recommendations"].append(
                    "Cache size is large, consider implementing more aggressive eviction"
                )

            return optimization_results

        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            optimization_results["error"] = str(e)
            return optimization_results

    async def shutdown(self):
        """Shutdown cache system."""
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.close()
                if self.redis_pool:
                    await self.redis_pool.disconnect()

            self.memory_cache.clear()
            logger.info("Cache system shutdown complete")

        except Exception as e:
            logger.error(f"Error during cache shutdown: {e}")

    # Helper methods

    def _get_prefixed_key(self, key: str, data_type: str) -> str:
        """Get prefixed cache key."""
        prefix = self.prefixes.get(data_type, 'misc:')
        return f"{prefix}{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            # Try JSON first for simple types
            if isinstance(value, (str, int, float, bool, list, dict)):
                serialized = json.dumps(value).encode('utf-8')
            else:
                # Use pickle for complex objects
                serialized = pickle.dumps(value)

            # Compress if large
            if len(serialized) > self.compression_threshold:
                import gzip
                serialized = gzip.compress(serialized)

            return serialized

        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            # Fallback to string representation
            return str(value).encode('utf-8')

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Check if compressed (simple heuristic)
            if data[:2] == b'\x1f\x8b':  # gzip magic number
                import gzip
                data = gzip.decompress(data)

            # Try JSON first
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Try pickle
                return pickle.loads(data)

        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            # Return raw string as fallback
            return data.decode('utf-8', errors='ignore')

    def _update_retrieval_time(self, retrieval_time: float):
        """Update average retrieval time."""
        if self.stats.total_requests > 1:
            self.stats.avg_retrieval_time = (
                (self.stats.avg_retrieval_time * (self.stats.total_requests - 1) + retrieval_time) /
                self.stats.total_requests
            )
        else:
            self.stats.avg_retrieval_time = retrieval_time

    async def _update_access_tracking(self, key: str):
        """Update access tracking for cache entry."""
        if self.use_redis and self.redis_client:
            try:
                # Increment access count
                await self.redis_client.incr(f"{key}:access_count")
                # Update last accessed time
                await self.redis_client.set(
                    f"{key}:last_accessed",
                    datetime.now().isoformat()
                )
            except Exception:
                pass  # Non-critical operation

    async def _cleanup_expired_keys(self) -> int:
        """Clean up expired keys (Redis specific)."""
        if not self.use_redis or not self.redis_client:
            return 0

        try:
            cleaned_count = 0
            for prefix in self.prefixes.values():
                keys = await self.redis_client.keys(f"{prefix}*")
                for key in keys:
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -2:  # Key doesn't exist or expired
                        await self.redis_client.delete(key, f"{key}:meta")
                        cleaned_count += 1

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {e}")
            return 0

    async def _optimize_memory_usage(self):
        """Optimize Redis memory usage."""
        if not self.use_redis or not self.redis_client:
            return

        try:
            # Run Redis memory optimization commands
            await self.redis_client.memory_purge()
        except Exception as e:
            logger.warning(f"Memory optimization failed: {e}")

    async def _evict_if_needed(self) -> int:
        """Evict entries if memory cache is too large."""
        max_entries = 1000  # Configurable limit
        evicted_count = 0

        if len(self.memory_cache) > max_entries:
            # Sort by last accessed time and remove oldest
            sorted_entries = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].last_accessed
            )

            entries_to_remove = len(self.memory_cache) - max_entries
            for i in range(entries_to_remove):
                key_to_remove = sorted_entries[i][0]
                del self.memory_cache[key_to_remove]
                evicted_count += 1

            self.stats.evictions += evicted_count

        return evicted_count

# Specialized cache managers

class QueryResultCache(AdvancedRedisCache):
    """Specialized cache for query results."""

    async def cache_query_result(self, query_hash: str, result: QueryResult,
                                ttl: Optional[int] = None) -> bool:
        """Cache a query result."""
        return await self.set(
            query_hash,
            result,
            ttl=ttl,
            data_type='query_result',
            tags=['query_result', 'searchable']
        )

    async def get_cached_query_result(self, query_hash: str) -> Optional[QueryResult]:
        """Get cached query result."""
        return await self.get(query_hash, 'query_result')

class EmbeddingCache(AdvancedRedisCache):
    """Specialized cache for embeddings."""

    async def cache_embedding(self, text_hash: str, embedding: List[float],
                            model: str, ttl: Optional[int] = None) -> bool:
        """Cache an embedding vector."""
        embedding_data = {
            'embedding': embedding,
            'model': model,
            'dimension': len(embedding),
            'created_at': datetime.now().isoformat()
        }

        return await self.set(
            text_hash,
            embedding_data,
            ttl=ttl,
            data_type='embedding',
            tags=['embedding', model]
        )

    async def get_cached_embedding(self, text_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached embedding."""
        return await self.get(text_hash, 'embedding')

class VisualizationCache(AdvancedRedisCache):
    """Specialized cache for visualizations."""

    async def cache_visualization(self, viz_id: str, viz_data: Dict[str, Any],
                                ttl: Optional[int] = None) -> bool:
        """Cache visualization data."""
        return await self.set(
            viz_id,
            viz_data,
            ttl=ttl,
            data_type='visualization',
            tags=['visualization', viz_data.get('type', 'unknown')]
        )

    async def get_cached_visualization(self, viz_id: str) -> Optional[Dict[str, Any]]:
        """Get cached visualization."""
        return await self.get(viz_id, 'visualization')