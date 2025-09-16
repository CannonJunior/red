"""
Adaptive Index Manager

Implements machine learning-based index optimization and usage pattern learning.
Automatically adjusts index priorities and configurations based on query patterns.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
import sqlite3
from pathlib import Path
from collections import defaultdict, deque
import math

try:
    from ..config.settings import get_config
    from .base import IndexInterface, IndexCapabilities, QueryResult, IndexStats
except ImportError:
    from config.settings import get_config
    from indices.base import IndexInterface, IndexCapabilities, QueryResult, IndexStats

logger = logging.getLogger(__name__)

class QueryPattern:
    """Represents a learned query pattern."""

    def __init__(self, pattern_id: str, query_type: str, features: Dict[str, Any]):
        self.pattern_id = pattern_id
        self.query_type = query_type
        self.features = features
        self.frequency = 0
        self.avg_execution_time = 0.0
        self.preferred_indices = []
        self.last_seen = datetime.now()

    def update(self, execution_time: float, used_indices: List[str]):
        """Update pattern statistics."""
        self.frequency += 1
        self.avg_execution_time = (self.avg_execution_time * (self.frequency - 1) + execution_time) / self.frequency
        self.preferred_indices = used_indices
        self.last_seen = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'pattern_id': self.pattern_id,
            'query_type': self.query_type,
            'features': self.features,
            'frequency': self.frequency,
            'avg_execution_time': self.avg_execution_time,
            'preferred_indices': self.preferred_indices,
            'last_seen': self.last_seen.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryPattern':
        """Create from dictionary."""
        pattern = cls(data['pattern_id'], data['query_type'], data['features'])
        pattern.frequency = data['frequency']
        pattern.avg_execution_time = data['avg_execution_time']
        pattern.preferred_indices = data['preferred_indices']
        pattern.last_seen = datetime.fromisoformat(data['last_seen'])
        return pattern

class AdaptiveIndexManager(IndexInterface):
    """
    Adaptive index manager for learning and optimizing query patterns.

    Features:
    - Query pattern learning and recognition
    - Index performance monitoring
    - Adaptive cache management
    - Query routing optimization
    - Usage-based index tuning
    """

    def __init__(self, index_name: str, data_path: str, config: Dict[str, Any]):
        super().__init__(index_name, data_path, config)

        self.connection = None
        self.db_path = self.data_path / f"{index_name}_adaptive.db"

        # Pattern learning configuration
        self.pattern_window_size = config.get('pattern_window_size', 1000)
        self.min_pattern_frequency = config.get('min_pattern_frequency', 5)
        self.cache_size = config.get('cache_size', 1000)
        self.learning_rate = config.get('learning_rate', 0.1)

        # In-memory data structures
        self.query_patterns: Dict[str, QueryPattern] = {}
        self.recent_queries = deque(maxlen=self.pattern_window_size)
        self.index_performance: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.cache: Dict[str, Tuple[Any, datetime]] = {}

        # Statistics
        self.total_queries_analyzed = 0
        self.patterns_learned = 0
        self.cache_hits = 0
        self.cache_misses = 0

    async def initialize(self) -> bool:
        """Initialize adaptive index manager."""
        try:
            # Create data directory
            self.data_path.mkdir(parents=True, exist_ok=True)

            # Connect to SQLite for persistent storage
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row

            # Create tables for pattern storage
            await self._create_tables()

            # Load existing patterns
            await self._load_patterns()

            self.logger.info(f"Adaptive index manager initialized with {len(self.query_patterns)} patterns")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize adaptive index manager: {e}")
            return False

    async def shutdown(self):
        """Gracefully shutdown the adaptive index manager."""
        try:
            # Save current patterns
            await self._save_patterns()

            if self.connection:
                self.connection.close()
                self.connection = None

            self.logger.info("Adaptive index manager shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during adaptive index manager shutdown: {e}")

    async def insert(self, documents: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Adaptive manager doesn't store documents directly."""
        return {
            "status": "success",
            "message": "Adaptive manager tracks patterns, not documents",
            "documents_inserted": 0
        }

    async def update(self, document_updates: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """Adaptive manager doesn't update documents directly."""
        return {
            "status": "success",
            "message": "Adaptive manager tracks patterns, not documents",
            "documents_updated": 0
        }

    async def delete(self, document_ids: List[str], workspace: str = "default") -> Dict[str, Any]:
        """Adaptive manager doesn't delete documents directly."""
        return {
            "status": "success",
            "message": "Adaptive manager tracks patterns, not documents",
            "documents_deleted": 0
        }

    async def query(self, query_params: Dict[str, Any], workspace: str = "default") -> QueryResult:
        """Analyze query patterns and provide optimization recommendations."""
        start_time = datetime.now()

        try:
            query_type = query_params.get('analysis_type', 'pattern_analysis')

            if query_type == 'pattern_analysis':
                return await self._analyze_patterns(query_params)
            elif query_type == 'index_recommendations':
                return await self._get_index_recommendations(query_params)
            elif query_type == 'performance_insights':
                return await self._get_performance_insights(query_params)
            elif query_type == 'cache_statistics':
                return await self._get_cache_statistics(query_params)
            else:
                raise ValueError(f"Unknown analysis type: {query_type}")

        except Exception as e:
            self.logger.error(f"Adaptive query failed: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check adaptive index manager health."""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        try:
            # Check database connection
            if self.connection:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                health_data["checks"]["database_connection"] = "healthy"
            else:
                health_data["checks"]["database_connection"] = "disconnected"
                health_data["status"] = "unhealthy"

            # Check pattern learning status
            health_data["checks"]["patterns_learned"] = f"{len(self.query_patterns)} patterns"
            health_data["checks"]["recent_queries"] = f"{len(self.recent_queries)} tracked"

            # Check cache performance
            total_requests = self.cache_hits + self.cache_misses
            if total_requests > 0:
                hit_rate = self.cache_hits / total_requests
                health_data["checks"]["cache_hit_rate"] = f"{hit_rate:.2%}"
            else:
                health_data["checks"]["cache_hit_rate"] = "no_data"

        except Exception as e:
            health_data["checks"]["error"] = str(e)
            health_data["status"] = "unhealthy"

        return health_data

    def get_capabilities(self) -> Set[IndexCapabilities]:
        """Return supported capabilities."""
        return {
            IndexCapabilities.AGGREGATION  # Provides analytics and aggregations
        }

    async def optimize(self) -> Dict[str, Any]:
        """Optimize adaptive learning algorithms."""
        try:
            optimization_results = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "optimizations": []
            }

            # Clean up old patterns
            cutoff_time = datetime.now() - timedelta(days=30)
            removed_patterns = 0

            patterns_to_remove = []
            for pattern_id, pattern in self.query_patterns.items():
                if pattern.last_seen < cutoff_time and pattern.frequency < self.min_pattern_frequency:
                    patterns_to_remove.append(pattern_id)

            for pattern_id in patterns_to_remove:
                del self.query_patterns[pattern_id]
                removed_patterns += 1

            optimization_results["optimizations"].append({
                "action": "cleaned_old_patterns",
                "patterns_removed": removed_patterns
            })

            # Optimize cache
            cache_cleaned = await self._optimize_cache()
            optimization_results["optimizations"].append({
                "action": "optimized_cache",
                "entries_cleaned": cache_cleaned
            })

            # Save patterns
            await self._save_patterns()
            optimization_results["optimizations"].append({
                "action": "saved_patterns",
                "patterns_saved": len(self.query_patterns)
            })

            return optimization_results

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def get_stats(self) -> IndexStats:
        """Get adaptive index manager statistics."""
        try:
            # Calculate storage size
            storage_size = 0
            if self.db_path.exists():
                storage_size = self.db_path.stat().st_size

            return IndexStats(
                document_count=len(self.query_patterns),  # Number of patterns learned
                storage_size_bytes=storage_size,
                avg_query_time=self.get_avg_query_time(),
                total_queries=self.total_queries_analyzed,
                last_updated=datetime.now(),
                health_status="healthy",
                capabilities=self.get_capabilities()
            )

        except Exception as e:
            self.logger.error(f"Failed to get adaptive index stats: {e}")
            return IndexStats(
                document_count=0,
                storage_size_bytes=0,
                avg_query_time=0.0,
                total_queries=0,
                last_updated=datetime.now(),
                health_status="error",
                capabilities=set()
            )

    # Core adaptive functionality

    async def learn_from_query(self, query_text: str, query_params: Dict[str, Any],
                              execution_time: float, used_indices: List[str],
                              result_count: int) -> Dict[str, Any]:
        """Learn from a query execution for pattern recognition."""
        try:
            # Extract features from query
            features = self._extract_query_features(query_text, query_params, result_count)

            # Generate pattern ID
            pattern_id = self._generate_pattern_id(features)

            # Update or create pattern
            if pattern_id in self.query_patterns:
                self.query_patterns[pattern_id].update(execution_time, used_indices)
            else:
                pattern = QueryPattern(pattern_id, features['query_type'], features)
                pattern.update(execution_time, used_indices)
                self.query_patterns[pattern_id] = pattern
                self.patterns_learned += 1

            # Track recent query
            self.recent_queries.append({
                'timestamp': datetime.now(),
                'pattern_id': pattern_id,
                'execution_time': execution_time,
                'used_indices': used_indices
            })

            self.total_queries_analyzed += 1

            return {
                'pattern_id': pattern_id,
                'is_new_pattern': pattern_id not in self.query_patterns,
                'pattern_frequency': self.query_patterns[pattern_id].frequency
            }

        except Exception as e:
            self.logger.error(f"Failed to learn from query: {e}")
            return {'error': str(e)}

    async def get_optimization_recommendations(self, query_text: str,
                                            query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimization recommendations for a query."""
        try:
            features = self._extract_query_features(query_text, query_params, 0)
            pattern_id = self._generate_pattern_id(features)

            recommendations = {
                'recommended_indices': [],
                'estimated_execution_time': 0.0,
                'confidence': 0.0,
                'caching_recommended': False,
                'optimization_notes': []
            }

            # Check if we have learned this pattern
            if pattern_id in self.query_patterns:
                pattern = self.query_patterns[pattern_id]
                recommendations['recommended_indices'] = pattern.preferred_indices
                recommendations['estimated_execution_time'] = pattern.avg_execution_time
                recommendations['confidence'] = min(pattern.frequency / 100.0, 1.0)

                # Recommend caching for frequent patterns
                if pattern.frequency >= self.min_pattern_frequency:
                    recommendations['caching_recommended'] = True
                    recommendations['optimization_notes'].append(f"Frequent pattern (seen {pattern.frequency} times)")

            else:
                # Find similar patterns
                similar_patterns = self._find_similar_patterns(features)
                if similar_patterns:
                    best_pattern = similar_patterns[0]
                    recommendations['recommended_indices'] = best_pattern.preferred_indices
                    recommendations['estimated_execution_time'] = best_pattern.avg_execution_time
                    recommendations['confidence'] = 0.5  # Lower confidence for similar patterns
                    recommendations['optimization_notes'].append("Based on similar query patterns")

            return recommendations

        except Exception as e:
            self.logger.error(f"Failed to get optimization recommendations: {e}")
            return {'error': str(e)}

    async def should_cache_result(self, query_text: str, query_params: Dict[str, Any],
                                result_size: int) -> bool:
        """Determine if query result should be cached."""
        try:
            features = self._extract_query_features(query_text, query_params, result_size)
            pattern_id = self._generate_pattern_id(features)

            # Cache if pattern is frequent
            if pattern_id in self.query_patterns:
                pattern = self.query_patterns[pattern_id]
                return pattern.frequency >= self.min_pattern_frequency

            # Cache large result sets from expensive queries
            if result_size > 100 or features.get('complexity_score', 0) > 0.7:
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to determine caching: {e}")
            return False

    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and not expired."""
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]

            # Check if cache entry is still valid (1 hour TTL)
            if datetime.now() - timestamp < timedelta(hours=1):
                self.cache_hits += 1
                return result
            else:
                # Remove expired entry
                del self.cache[cache_key]

        self.cache_misses += 1
        return None

    async def cache_result(self, cache_key: str, result: Any):
        """Cache a query result."""
        # Implement LRU eviction if cache is full
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[cache_key] = (result, datetime.now())

    # Helper methods

    def _extract_query_features(self, query_text: str, query_params: Dict[str, Any],
                               result_count: int) -> Dict[str, Any]:
        """Extract features from query for pattern recognition."""
        features = {
            'query_length': len(query_text),
            'has_aggregation': any(keyword in query_text.lower()
                                 for keyword in ['count', 'sum', 'avg', 'group by']),
            'has_filter': any(keyword in query_text.lower()
                            for keyword in ['where', 'filter', '=']),
            'has_sort': any(keyword in query_text.lower()
                          for keyword in ['order by', 'sort']),
            'has_limit': 'limit' in query_params or 'limit' in query_text.lower(),
            'result_count': result_count,
            'param_count': len(query_params),
            'complexity_score': self._calculate_query_complexity(query_text, query_params)
        }

        # Determine query type
        if features['has_aggregation']:
            features['query_type'] = 'aggregation'
        elif 'search' in query_text.lower() or 'find' in query_text.lower():
            features['query_type'] = 'search'
        elif features['has_filter']:
            features['query_type'] = 'filter'
        else:
            features['query_type'] = 'browse'

        return features

    def _calculate_query_complexity(self, query_text: str, query_params: Dict[str, Any]) -> float:
        """Calculate query complexity score (0-1)."""
        complexity = 0.0

        # Text-based complexity
        complexity += min(len(query_text) / 1000.0, 0.3)

        # Parameter complexity
        complexity += min(len(query_params) / 20.0, 0.2)

        # Keyword-based complexity
        complex_keywords = ['join', 'union', 'group by', 'having', 'subquery', 'nested']
        for keyword in complex_keywords:
            if keyword in query_text.lower():
                complexity += 0.1

        return min(complexity, 1.0)

    def _generate_pattern_id(self, features: Dict[str, Any]) -> str:
        """Generate unique pattern ID from features."""
        # Create a simplified feature signature for pattern matching
        signature = {
            'query_type': features['query_type'],
            'has_aggregation': features['has_aggregation'],
            'has_filter': features['has_filter'],
            'has_sort': features['has_sort'],
            'complexity_bucket': int(features['complexity_score'] * 10)  # 0-10 scale
        }

        signature_str = json.dumps(signature, sort_keys=True)
        import hashlib
        return hashlib.md5(signature_str.encode()).hexdigest()[:12]

    def _find_similar_patterns(self, features: Dict[str, Any]) -> List[QueryPattern]:
        """Find similar query patterns."""
        similar_patterns = []

        for pattern in self.query_patterns.values():
            similarity = self._calculate_pattern_similarity(features, pattern.features)
            if similarity > 0.7:  # 70% similarity threshold
                similar_patterns.append((pattern, similarity))

        # Sort by similarity and frequency
        similar_patterns.sort(key=lambda x: (x[1], x[0].frequency), reverse=True)
        return [pattern for pattern, _ in similar_patterns[:5]]

    def _calculate_pattern_similarity(self, features1: Dict[str, Any],
                                    features2: Dict[str, Any]) -> float:
        """Calculate similarity between two feature sets."""
        # Simple similarity based on matching boolean features
        bool_features = ['has_aggregation', 'has_filter', 'has_sort']
        matches = 0
        total = len(bool_features)

        for feature in bool_features:
            if features1.get(feature) == features2.get(feature):
                matches += 1

        # Add query type similarity
        if features1.get('query_type') == features2.get('query_type'):
            matches += 1
        total += 1

        return matches / total

    async def _optimize_cache(self) -> int:
        """Optimize cache by removing stale entries."""
        cutoff_time = datetime.now() - timedelta(hours=1)
        keys_to_remove = []

        for key, (_, timestamp) in self.cache.items():
            if timestamp < cutoff_time:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        return len(keys_to_remove)

    # Database operations

    async def _create_tables(self):
        """Create database tables for pattern storage."""
        cursor = self.connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_patterns (
                pattern_id TEXT PRIMARY KEY,
                query_type TEXT,
                features TEXT,
                frequency INTEGER,
                avg_execution_time REAL,
                preferred_indices TEXT,
                last_seen TEXT,
                created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT,
                execution_time REAL,
                used_indices TEXT,
                timestamp TEXT,
                FOREIGN KEY (pattern_id) REFERENCES query_patterns (pattern_id)
            )
        """)

        self.connection.commit()

    async def _save_patterns(self):
        """Save patterns to database."""
        cursor = self.connection.cursor()

        for pattern in self.query_patterns.values():
            cursor.execute("""
                INSERT OR REPLACE INTO query_patterns
                (pattern_id, query_type, features, frequency, avg_execution_time,
                 preferred_indices, last_seen, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                pattern.query_type,
                json.dumps(pattern.features),
                pattern.frequency,
                pattern.avg_execution_time,
                json.dumps(pattern.preferred_indices),
                pattern.last_seen.isoformat(),
                datetime.now().isoformat()
            ))

        self.connection.commit()

    async def _load_patterns(self):
        """Load patterns from database."""
        cursor = self.connection.cursor()

        cursor.execute("SELECT * FROM query_patterns")
        rows = cursor.fetchall()

        for row in rows:
            pattern_data = {
                'pattern_id': row['pattern_id'],
                'query_type': row['query_type'],
                'features': json.loads(row['features']),
                'frequency': row['frequency'],
                'avg_execution_time': row['avg_execution_time'],
                'preferred_indices': json.loads(row['preferred_indices']),
                'last_seen': row['last_seen']
            }

            pattern = QueryPattern.from_dict(pattern_data)
            self.query_patterns[pattern.pattern_id] = pattern

    # Query analysis methods

    async def _analyze_patterns(self, query_params: Dict[str, Any]) -> QueryResult:
        """Analyze learned query patterns."""
        documents = []

        for pattern in self.query_patterns.values():
            doc = pattern.to_dict()
            doc['performance_category'] = self._categorize_performance(pattern.avg_execution_time)
            documents.append(doc)

        # Sort by frequency
        documents.sort(key=lambda x: x['frequency'], reverse=True)

        return QueryResult(
            documents=documents,
            metadata={
                "analysis_type": "pattern_analysis",
                "total_patterns": len(documents)
            },
            total_found=len(documents),
            execution_time=0.1,
            index_used=self.index_name
        )

    async def _get_index_recommendations(self, query_params: Dict[str, Any]) -> QueryResult:
        """Get index performance recommendations."""
        # Analyze index performance patterns
        index_performance = defaultdict(lambda: {'total_queries': 0, 'avg_time': 0.0, 'success_rate': 1.0})

        for pattern in self.query_patterns.values():
            for index_name in pattern.preferred_indices:
                perf = index_performance[index_name]
                perf['total_queries'] += pattern.frequency
                perf['avg_time'] = (perf['avg_time'] * (perf['total_queries'] - pattern.frequency) +
                                   pattern.avg_execution_time * pattern.frequency) / perf['total_queries']

        documents = []
        for index_name, stats in index_performance.items():
            doc = {
                'index_name': index_name,
                'total_queries': stats['total_queries'],
                'avg_execution_time': stats['avg_time'],
                'performance_rating': self._rate_performance(stats['avg_time']),
                'recommendation': self._generate_index_recommendation(stats)
            }
            documents.append(doc)

        return QueryResult(
            documents=documents,
            metadata={"analysis_type": "index_recommendations"},
            total_found=len(documents),
            execution_time=0.1,
            index_used=self.index_name
        )

    async def _get_performance_insights(self, query_params: Dict[str, Any]) -> QueryResult:
        """Get performance insights and trends."""
        insights = {
            'total_patterns_learned': len(self.query_patterns),
            'total_queries_analyzed': self.total_queries_analyzed,
            'avg_pattern_frequency': sum(p.frequency for p in self.query_patterns.values()) / max(len(self.query_patterns), 1),
            'most_common_query_type': self._get_most_common_query_type(),
            'performance_trends': self._analyze_performance_trends(),
            'cache_efficiency': {
                'hit_rate': self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
                'total_hits': self.cache_hits,
                'total_misses': self.cache_misses
            }
        }

        return QueryResult(
            documents=[insights],
            metadata={"analysis_type": "performance_insights"},
            total_found=1,
            execution_time=0.1,
            index_used=self.index_name
        )

    async def _get_cache_statistics(self, query_params: Dict[str, Any]) -> QueryResult:
        """Get detailed cache statistics."""
        cache_stats = {
            'cache_size': len(self.cache),
            'max_cache_size': self.cache_size,
            'hit_rate': self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
            'total_hits': self.cache_hits,
            'total_misses': self.cache_misses,
            'cache_entries': []
        }

        # Add cache entry details
        for key, (result, timestamp) in self.cache.items():
            age_minutes = (datetime.now() - timestamp).total_seconds() / 60
            cache_stats['cache_entries'].append({
                'cache_key': key[:20] + '...' if len(key) > 20 else key,
                'age_minutes': age_minutes,
                'result_size': len(str(result)) if result else 0
            })

        return QueryResult(
            documents=[cache_stats],
            metadata={"analysis_type": "cache_statistics"},
            total_found=1,
            execution_time=0.1,
            index_used=self.index_name
        )

    def _categorize_performance(self, execution_time: float) -> str:
        """Categorize query performance."""
        if execution_time < 0.1:
            return "excellent"
        elif execution_time < 0.5:
            return "good"
        elif execution_time < 2.0:
            return "acceptable"
        else:
            return "slow"

    def _rate_performance(self, avg_time: float) -> float:
        """Rate performance on 0-10 scale."""
        if avg_time < 0.1:
            return 10.0
        elif avg_time < 0.5:
            return 8.0
        elif avg_time < 2.0:
            return 6.0
        elif avg_time < 5.0:
            return 4.0
        else:
            return 2.0

    def _generate_index_recommendation(self, stats: Dict[str, Any]) -> str:
        """Generate recommendation text for index."""
        avg_time = stats['avg_time']
        total_queries = stats['total_queries']

        if avg_time < 0.1:
            return f"Excellent performance ({total_queries} queries)"
        elif avg_time < 0.5:
            return f"Good performance ({total_queries} queries)"
        elif avg_time < 2.0:
            return f"Consider optimization ({total_queries} queries)"
        else:
            return f"Needs optimization - high latency ({total_queries} queries)"

    def _get_most_common_query_type(self) -> str:
        """Get the most common query type."""
        type_counts = defaultdict(int)
        for pattern in self.query_patterns.values():
            type_counts[pattern.query_type] += pattern.frequency

        if not type_counts:
            return "unknown"

        return max(type_counts.items(), key=lambda x: x[1])[0]

    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        recent_window = list(self.recent_queries)[-100:]  # Last 100 queries

        if not recent_window:
            return {"trend": "no_data"}

        avg_time = sum(q['execution_time'] for q in recent_window) / len(recent_window)

        # Simple trend analysis
        if len(recent_window) >= 20:
            first_half = recent_window[:len(recent_window)//2]
            second_half = recent_window[len(recent_window)//2:]

            first_avg = sum(q['execution_time'] for q in first_half) / len(first_half)
            second_avg = sum(q['execution_time'] for q in second_half) / len(second_half)

            if second_avg < first_avg * 0.9:
                trend = "improving"
            elif second_avg > first_avg * 1.1:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "avg_execution_time": avg_time,
            "recent_queries_analyzed": len(recent_window)
        }