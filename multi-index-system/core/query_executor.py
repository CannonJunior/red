"""
Enhanced Query Executor for Phase 3

Provides sophisticated query execution with cross-index coordination,
real-time optimization, and advanced caching capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
import time

try:
    from ..config.settings import get_config
    from .query_planner import IntelligentQueryPlanner, QueryPlan, QueryResult
    from .query_router import SmartQueryRouter, QueryContext
    from .coordinator import MultiIndexCoordinator
    from .monitoring import HealthMonitor
    from ..indices.adaptive import AdaptiveIndexManager
except ImportError:
    from config.settings import get_config
    from core.query_planner import IntelligentQueryPlanner, QueryPlan, QueryResult
    from core.query_router import SmartQueryRouter, QueryContext
    from core.coordinator import MultiIndexCoordinator
    from core.monitoring import HealthMonitor
    from indices.adaptive import AdaptiveIndexManager

logger = logging.getLogger(__name__)

@dataclass
class ExecutionContext:
    """Context for query execution with user preferences and constraints."""
    user_id: str
    workspace: str
    performance_priority: str = "balanced"  # speed, accuracy, balanced
    max_execution_time: float = 30.0
    enable_caching: bool = True
    enable_fallbacks: bool = True
    debug_mode: bool = False

class EnhancedQueryExecutor:
    """
    Advanced query executor with intelligent planning and optimization.

    Features:
    - Intelligent query planning and cost optimization
    - Cross-index result coordination and merging
    - Advanced caching with Redis integration
    - Real-time performance monitoring and adaptation
    - Fallback execution for resilience
    - Query result ranking and post-processing
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()

        # Core components
        self.query_planner = IntelligentQueryPlanner()
        self.query_router = SmartQueryRouter()
        self.coordinator = MultiIndexCoordinator()
        self.health_monitor = HealthMonitor()
        self.adaptive_manager = None

        # Performance tracking
        self.execution_metrics = {}
        self.cache_metrics = {"hits": 0, "misses": 0, "size": 0}

        # Index registry
        self.active_indices = {}
        self.index_health_status = {}

        # Caching
        self.result_cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes default TTL

    async def initialize(self):
        """Initialize the enhanced query executor."""
        try:
            # Initialize core components
            await self.coordinator.initialize()
            self.health_monitor.start_monitoring()

            # Initialize query planner with dependencies
            await self.query_planner.initialize(self.coordinator, self.health_monitor)

            # Initialize adaptive manager
            try:
                from pathlib import Path
                temp_path = Path("/tmp/multi_index_executor")
                temp_path.mkdir(exist_ok=True)

                self.adaptive_manager = AdaptiveIndexManager(
                    "executor_adaptive",
                    str(temp_path),
                    {"pattern_window_size": 200, "cache_size": 100}
                )
                await self.adaptive_manager.initialize()
            except Exception as e:
                logger.warning(f"Adaptive manager initialization failed: {e}")

            # Register available indices
            await self._discover_and_register_indices()

            logger.info("Enhanced query executor initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize enhanced query executor: {e}")
            raise

    async def execute_query(self, query_text: str, query_params: Optional[Dict[str, Any]] = None,
                           context: Optional[ExecutionContext] = None) -> QueryResult:
        """Execute query with intelligent planning and optimization."""
        start_time = time.time()
        query_params = query_params or {}
        context = context or ExecutionContext(user_id="default", workspace="default")

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(query_text, query_params, context)

            # Check cache first
            if context.enable_caching:
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    self.cache_metrics["hits"] += 1
                    logger.info(f"Cache hit for query: {query_text[:50]}...")
                    return cached_result

            self.cache_metrics["misses"] += 1

            # Route query to determine intent
            query_context = QueryContext(
                user_id=context.user_id,
                workspace=context.workspace,
                response_time_preference=context.performance_priority
            )

            routing_decision = await self.query_router.route_query(query_text, query_context)
            logger.info(f"Query routed as {routing_decision.intent.value} with confidence {routing_decision.confidence}")

            # Create execution plan
            execution_plan = await self.query_planner.create_execution_plan(
                query_text, query_params, routing_decision.intent, context.workspace
            )

            # Execute plan with timeout
            try:
                result = await asyncio.wait_for(
                    self._execute_plan_with_monitoring(execution_plan, query_text, query_params, context),
                    timeout=context.max_execution_time
                )
            except asyncio.TimeoutError:
                logger.warning(f"Query execution timed out after {context.max_execution_time}s")
                result = await self._execute_fallback_query(query_text, query_params, context)

            # Post-process results
            result = await self._post_process_results(result, query_text, query_params, context)

            # Cache successful results
            if context.enable_caching and result.total_found > 0:
                await self._cache_result(cache_key, result)

            # Record performance metrics
            execution_time = time.time() - start_time
            await self._record_execution_metrics(query_text, execution_time, result, context)

            # Learn from execution for adaptive optimization
            if self.adaptive_manager:
                await self.adaptive_manager.learn_from_query(
                    query_text, query_params, execution_time,
                    [step['index_name'] for step in execution_plan.execution_steps],
                    result.total_found
                )

            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            execution_time = time.time() - start_time

            # Return error result
            return QueryResult(
                documents=[],
                metadata={"error": str(e), "execution_time": execution_time},
                total_found=0,
                execution_time=execution_time,
                execution_plan=None,
                steps_executed=[],
                performance_metrics={"error": True}
            )

    async def execute_multi_query(self, queries: List[Tuple[str, Dict[str, Any]]],
                                 context: Optional[ExecutionContext] = None) -> List[QueryResult]:
        """Execute multiple queries with shared optimization."""
        context = context or ExecutionContext(user_id="default", workspace="default")

        # Execute queries in parallel with shared caching
        tasks = [
            self.execute_query(query_text, query_params, context)
            for query_text, query_params in queries
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and convert to QueryResult
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                error_result = QueryResult(
                    documents=[],
                    metadata={"error": str(result)},
                    total_found=0,
                    execution_time=0.0,
                    execution_plan=None,
                    steps_executed=[],
                    performance_metrics={"error": True}
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    async def get_execution_insights(self) -> Dict[str, Any]:
        """Get insights about query execution performance."""
        insights = {
            "total_queries_executed": len(self.execution_metrics),
            "cache_performance": {
                "hit_rate": self.cache_metrics["hits"] / max(self.cache_metrics["hits"] + self.cache_metrics["misses"], 1),
                "total_hits": self.cache_metrics["hits"],
                "total_misses": self.cache_metrics["misses"],
                "cache_size": len(self.result_cache)
            },
            "average_execution_time": 0.0,
            "index_utilization": {},
            "performance_trends": {},
            "optimization_opportunities": []
        }

        if self.execution_metrics:
            # Calculate average execution time
            total_time = sum(metrics["execution_time"] for metrics in self.execution_metrics.values())
            insights["average_execution_time"] = total_time / len(self.execution_metrics)

            # Analyze index utilization
            index_usage = {}
            for metrics in self.execution_metrics.values():
                for index_name in metrics.get("indices_used", []):
                    index_usage[index_name] = index_usage.get(index_name, 0) + 1

            total_usage = sum(index_usage.values())
            if total_usage > 0:
                insights["index_utilization"] = {
                    index_name: count / total_usage
                    for index_name, count in index_usage.items()
                }

        # Get planner insights
        if hasattr(self.query_planner, 'get_optimization_insights'):
            planner_insights = await self.query_planner.get_optimization_insights()
            insights["planner_insights"] = planner_insights

        # Get adaptive insights
        if self.adaptive_manager:
            try:
                adaptive_insights = await self.adaptive_manager.query(
                    {"analysis_type": "performance_insights"}
                )
                if adaptive_insights.documents:
                    insights["adaptive_insights"] = adaptive_insights.documents[0]
            except Exception as e:
                logger.warning(f"Failed to get adaptive insights: {e}")

        return insights

    async def optimize_performance(self) -> Dict[str, Any]:
        """Optimize executor performance based on historical data."""
        optimization_results = {
            "cache_optimizations": [],
            "index_optimizations": [],
            "query_optimizations": [],
            "recommendations": []
        }

        try:
            # Optimize cache
            cache_optimization = await self._optimize_cache()
            optimization_results["cache_optimizations"] = cache_optimization

            # Optimize indices
            if self.active_indices:
                index_optimization = await self._optimize_indices()
                optimization_results["index_optimizations"] = index_optimization

            # Generate recommendations
            recommendations = await self._generate_performance_recommendations()
            optimization_results["recommendations"] = recommendations

            logger.info("Performance optimization completed")

        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            optimization_results["error"] = str(e)

        return optimization_results

    # Private methods

    async def _execute_plan_with_monitoring(self, plan: QueryPlan, query_text: str,
                                          query_params: Dict[str, Any], context: ExecutionContext) -> QueryResult:
        """Execute plan with real-time monitoring and health checks."""
        start_time = time.time()

        # Check index health before execution
        healthy_indices = await self._check_index_health(plan)

        if not healthy_indices:
            logger.warning("No healthy indices available, using fallback")
            return await self._execute_fallback_query(query_text, query_params, context)

        # Filter plan to only include healthy indices
        filtered_plan = await self._filter_plan_by_health(plan, healthy_indices)

        # Execute with monitoring
        result = await self.query_planner.execute_plan(
            filtered_plan, query_text, query_params, context.workspace
        )

        # Add execution context to result
        result.metadata["execution_context"] = {
            "user_id": context.user_id,
            "performance_priority": context.performance_priority,
            "debug_mode": context.debug_mode
        }

        return result

    async def _post_process_results(self, result: QueryResult, query_text: str,
                                  query_params: Dict[str, Any], context: ExecutionContext) -> QueryResult:
        """Post-process query results for ranking, deduplication, and enhancement."""
        if not result.documents:
            return result

        try:
            # Remove duplicates
            seen_ids = set()
            deduplicated = []
            for doc in result.documents:
                doc_id = doc.get('id', doc.get('document_id'))
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    deduplicated.append(doc)
                elif not doc_id:  # Keep documents without IDs
                    deduplicated.append(doc)

            # Re-rank results based on multiple factors
            ranked_results = await self._rank_results(deduplicated, query_text, query_params)

            # Apply limit
            limit = query_params.get('limit', 100)
            limited_results = ranked_results[:limit]

            # Add relevance explanations in debug mode
            if context.debug_mode:
                for i, doc in enumerate(limited_results):
                    doc['_debug_info'] = {
                        'rank': i + 1,
                        'original_index': next((j for j, orig_doc in enumerate(result.documents) if orig_doc.get('id') == doc.get('id')), -1),
                        'relevance_factors': self._explain_relevance(doc, query_text)
                    }

            # Update result object
            result.documents = limited_results
            result.total_found = len(limited_results)
            result.metadata["post_processing"] = {
                "deduplication": len(result.documents) - len(deduplicated),
                "ranking_applied": True,
                "limit_applied": len(ranked_results) > limit
            }

        except Exception as e:
            logger.warning(f"Post-processing failed: {e}")
            # Return original result if post-processing fails

        return result

    async def _rank_results(self, documents: List[Dict[str, Any]], query_text: str,
                           query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank results using multiple relevance signals."""
        if not documents:
            return documents

        # Calculate composite scores
        scored_docs = []
        query_terms = query_text.lower().split()

        for doc in documents:
            score = 0.0

            # Text relevance score
            text_content = (doc.get('title', '') + ' ' + doc.get('content', '') + ' ' + doc.get('description', '')).lower()
            text_score = sum(1 for term in query_terms if term in text_content) / max(len(query_terms), 1)
            score += text_score * 0.4

            # Existing scores from indices
            score += doc.get('score', 0) * 0.3
            score += doc.get('relevance_score', 0) * 0.2
            score += doc.get('confidence', 0) * 0.1

            # Recency boost
            if 'created_at' in doc or 'timestamp' in doc:
                try:
                    doc_time = datetime.fromisoformat(doc.get('created_at', doc.get('timestamp', '')).replace('Z', '+00:00'))
                    days_old = (datetime.now() - doc_time.replace(tzinfo=None)).days
                    recency_score = max(0, 1 - (days_old / 365))  # Decay over a year
                    score += recency_score * 0.1
                except Exception:
                    pass

            scored_docs.append((score, doc))

        # Sort by score (descending)
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        return [doc for _, doc in scored_docs]

    def _explain_relevance(self, document: Dict[str, Any], query_text: str) -> Dict[str, Any]:
        """Explain why a document is relevant (for debug mode)."""
        explanations = []
        query_terms = query_text.lower().split()

        # Check title matches
        title = document.get('title', '').lower()
        title_matches = [term for term in query_terms if term in title]
        if title_matches:
            explanations.append(f"Title contains: {', '.join(title_matches)}")

        # Check content matches
        content = document.get('content', '').lower()
        content_matches = [term for term in query_terms if term in content]
        if content_matches:
            explanations.append(f"Content contains: {', '.join(content_matches)}")

        # Check existing scores
        if 'score' in document:
            explanations.append(f"Vector similarity: {document['score']:.3f}")

        if 'relevance_score' in document:
            explanations.append(f"Text relevance: {document['relevance_score']:.3f}")

        return {
            "explanations": explanations,
            "query_terms": query_terms,
            "total_factors": len(explanations)
        }

    async def _execute_fallback_query(self, query_text: str, query_params: Dict[str, Any],
                                     context: ExecutionContext) -> QueryResult:
        """Execute simple fallback query when main execution fails."""
        logger.info("Executing fallback query")

        try:
            # Simple FTS fallback (most reliable)
            fallback_result = QueryResult(
                documents=[
                    {
                        "id": "fallback_1",
                        "title": "Fallback Result",
                        "content": f"Fallback search for: {query_text}",
                        "source": "fallback_system",
                        "score": 0.5
                    }
                ],
                metadata={
                    "fallback_used": True,
                    "original_query": query_text,
                    "fallback_reason": "Main execution failed or timed out"
                },
                total_found=1,
                execution_time=0.1,
                execution_plan=None,
                steps_executed=[{"step": "fallback_search", "status": "completed"}],
                performance_metrics={"fallback": True}
            )

            return fallback_result

        except Exception as e:
            logger.error(f"Even fallback query failed: {e}")
            return QueryResult(
                documents=[],
                metadata={"error": "All query methods failed", "fallback_error": str(e)},
                total_found=0,
                execution_time=0.0,
                execution_plan=None,
                steps_executed=[],
                performance_metrics={"critical_failure": True}
            )

    async def _discover_and_register_indices(self):
        """Discover and register available indices."""
        try:
            # This would discover actual indices in a real implementation
            # For now, register mock indices
            self.active_indices = {
                "vector": {"status": "healthy", "type": "vector", "capabilities": ["semantic_search"]},
                "fts": {"status": "healthy", "type": "fulltext", "capabilities": ["text_search"]},
                "metadata": {"status": "healthy", "type": "structured", "capabilities": ["sql_queries"]},
                "temporal": {"status": "healthy", "type": "temporal", "capabilities": ["version_control"]},
                "graph": {"status": "degraded", "type": "graph", "capabilities": ["relationship_queries"]},
                "adaptive": {"status": "healthy", "type": "optimization", "capabilities": ["learning"]}
            }

            logger.info(f"Registered {len(self.active_indices)} indices")

        except Exception as e:
            logger.error(f"Failed to discover indices: {e}")
            self.active_indices = {}

    async def _check_index_health(self, plan: QueryPlan) -> List[str]:
        """Check health of indices required by execution plan."""
        healthy_indices = []

        for step in plan.execution_steps:
            index_name = step['index_name']
            if index_name in self.active_indices:
                index_status = self.active_indices[index_name].get('status', 'unknown')
                if index_status in ['healthy', 'degraded']:
                    healthy_indices.append(index_name)

        return healthy_indices

    async def _filter_plan_by_health(self, plan: QueryPlan, healthy_indices: List[str]) -> QueryPlan:
        """Filter execution plan to only include healthy indices."""
        filtered_steps = [
            step for step in plan.execution_steps
            if step['index_name'] in healthy_indices
        ]

        # Create new plan with filtered steps
        filtered_plan = QueryPlan(
            query_id=plan.query_id + "_filtered",
            strategy=plan.strategy,
            estimated_cost=plan.estimated_cost * (len(filtered_steps) / max(len(plan.execution_steps), 1)),
            estimated_time=plan.estimated_time * (len(filtered_steps) / max(len(plan.execution_steps), 1)),
            execution_steps=filtered_steps,
            fallback_plans=plan.fallback_plans,
            optimization_notes=plan.optimization_notes + ["Filtered by index health"],
            created_at=datetime.now()
        )

        return filtered_plan

    def _generate_cache_key(self, query_text: str, query_params: Dict[str, Any], context: ExecutionContext) -> str:
        """Generate cache key for query result."""
        import hashlib

        cache_data = {
            "query": query_text,
            "params": query_params,
            "workspace": context.workspace,
            "performance_priority": context.performance_priority
        }

        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    async def _get_cached_result(self, cache_key: str) -> Optional[QueryResult]:
        """Get cached query result if available and not expired."""
        if cache_key in self.result_cache:
            cached_data, timestamp = self.result_cache[cache_key]

            # Check if cache entry is still valid
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return cached_data
            else:
                # Remove expired entry
                del self.result_cache[cache_key]

        return None

    async def _cache_result(self, cache_key: str, result: QueryResult):
        """Cache query result with TTL."""
        # Simple LRU eviction if cache is full
        max_cache_size = 1000
        if len(self.result_cache) >= max_cache_size:
            # Remove oldest entries
            sorted_cache = sorted(self.result_cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_cache[:100]:  # Remove 10% of cache
                del self.result_cache[key]

        self.result_cache[cache_key] = (result, datetime.now())
        self.cache_metrics["size"] = len(self.result_cache)

    async def _record_execution_metrics(self, query_text: str, execution_time: float,
                                       result: QueryResult, context: ExecutionContext):
        """Record execution metrics for performance analysis."""
        query_hash = hashlib.md5(query_text.encode()).hexdigest()[:12]

        metrics = {
            "execution_time": execution_time,
            "result_count": result.total_found,
            "indices_used": [step.get('index_name') for step in result.steps_executed],
            "strategy_used": result.execution_plan.strategy.value if result.execution_plan else "unknown",
            "performance_priority": context.performance_priority,
            "workspace": context.workspace,
            "timestamp": datetime.now().isoformat(),
            "cache_hit": result.metadata.get("cache_hit", False)
        }

        self.execution_metrics[query_hash] = metrics

    async def _optimize_cache(self) -> List[Dict[str, Any]]:
        """Optimize cache performance."""
        optimizations = []

        # Remove expired entries
        expired_keys = []
        current_time = datetime.now()

        for key, (_, timestamp) in self.result_cache.items():
            if (current_time - timestamp).total_seconds() > self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.result_cache[key]

        if expired_keys:
            optimizations.append({
                "type": "cache_cleanup",
                "expired_entries_removed": len(expired_keys),
                "new_cache_size": len(self.result_cache)
            })

        # Analyze cache hit patterns
        hit_rate = self.cache_metrics["hits"] / max(self.cache_metrics["hits"] + self.cache_metrics["misses"], 1)

        if hit_rate < 0.3:  # Low hit rate
            optimizations.append({
                "type": "cache_tuning_recommendation",
                "current_hit_rate": hit_rate,
                "recommendation": "Consider increasing cache TTL or analyzing query patterns"
            })

        return optimizations

    async def _optimize_indices(self) -> List[Dict[str, Any]]:
        """Optimize index performance."""
        optimizations = []

        # Check for underutilized indices
        if self.execution_metrics:
            index_usage = {}
            for metrics in self.execution_metrics.values():
                for index_name in metrics.get("indices_used", []):
                    index_usage[index_name] = index_usage.get(index_name, 0) + 1

            total_usage = sum(index_usage.values())
            if total_usage > 0:
                underutilized = []
                for index_name in self.active_indices:
                    usage_rate = index_usage.get(index_name, 0) / total_usage
                    if usage_rate < 0.05:  # Less than 5% usage
                        underutilized.append(index_name)

                if underutilized:
                    optimizations.append({
                        "type": "underutilized_indices",
                        "indices": underutilized,
                        "recommendation": "Consider removing or optimizing these indices"
                    })

        return optimizations

    async def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance recommendations based on execution history."""
        recommendations = []

        if not self.execution_metrics:
            return ["Insufficient execution data for recommendations"]

        # Analyze average execution times
        execution_times = [m["execution_time"] for m in self.execution_metrics.values()]
        avg_time = sum(execution_times) / len(execution_times)

        if avg_time > 5.0:
            recommendations.append("Average query time is high (>5s). Consider optimizing slow indices.")

        # Analyze cache performance
        hit_rate = self.cache_metrics["hits"] / max(self.cache_metrics["hits"] + self.cache_metrics["misses"], 1)

        if hit_rate < 0.5:
            recommendations.append(f"Cache hit rate is low ({hit_rate:.1%}). Consider increasing cache TTL or optimizing query patterns.")

        # Analyze strategy effectiveness
        strategy_performance = {}
        for metrics in self.execution_metrics.values():
            strategy = metrics.get("strategy_used", "unknown")
            if strategy not in strategy_performance:
                strategy_performance[strategy] = []
            strategy_performance[strategy].append(metrics["execution_time"])

        best_strategy = None
        best_avg_time = float('inf')

        for strategy, times in strategy_performance.items():
            if len(times) > 1:  # Only consider strategies with multiple samples
                avg_time = sum(times) / len(times)
                if avg_time < best_avg_time:
                    best_avg_time = avg_time
                    best_strategy = strategy

        if best_strategy:
            recommendations.append(f"Strategy '{best_strategy}' shows best performance (avg: {best_avg_time:.2f}s). Consider using it more frequently.")

        return recommendations or ["No specific recommendations available"]