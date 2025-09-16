"""
Intelligent Query Planner for Phase 3

Provides cost-based optimization, execution planning, and cross-index coordination
for complex hybrid queries across multiple indices.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime
import json
from dataclasses import dataclass
from enum import Enum
import math

try:
    from ..config.settings import get_config
    from .query_router import QueryIntent
    from .monitoring import HealthMonitor
    from .coordinator import MultiIndexCoordinator
except ImportError:
    from config.settings import get_config
    from core.query_router import QueryIntent
    from core.monitoring import HealthMonitor
    from core.coordinator import MultiIndexCoordinator

logger = logging.getLogger(__name__)

class QueryStrategy(Enum):
    """Available query execution strategies."""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    WATERFALL = "waterfall"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"

class IndexPriority(Enum):
    """Index priority levels for query planning."""
    PRIMARY = 1
    SECONDARY = 2
    FALLBACK = 3
    OPTIONAL = 4

@dataclass
class QueryPlan:
    """Represents an optimized query execution plan."""
    query_id: str
    strategy: QueryStrategy
    estimated_cost: float
    estimated_time: float
    execution_steps: List[Dict[str, Any]]
    fallback_plans: List['QueryPlan']
    optimization_notes: List[str]
    created_at: datetime

@dataclass
class ExecutionStep:
    """Individual step in query execution plan."""
    step_id: str
    index_name: str
    operation: str
    parameters: Dict[str, Any]
    dependencies: List[str]
    priority: IndexPriority
    estimated_cost: float
    timeout_seconds: float

@dataclass
class QueryResult:
    """Enhanced query result with execution metadata."""
    documents: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    total_found: int
    execution_time: float
    execution_plan: QueryPlan
    steps_executed: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    confidence_scores: Optional[List[float]] = None

class IntelligentQueryPlanner:
    """
    Cost-based query planner with multi-index optimization.

    Features:
    - Cost estimation and optimization
    - Parallel and sequential execution strategies
    - Adaptive query routing based on performance
    - Fallback planning for resilience
    - Real-time performance feedback
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Performance tracking
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}
        self.index_performance: Dict[str, Dict[str, float]] = {}

        # Cost model parameters
        self.base_costs = {
            'vector': 0.8,      # High cost due to embedding computation
            'graph': 0.6,       # Medium-high cost for traversal
            'metadata': 0.3,    # Low cost for structured queries
            'fts': 0.4,         # Medium cost for text search
            'temporal': 0.5,    # Medium cost for version queries
            'adaptive': 0.1     # Very low cost for recommendations
        }

        # Strategy preferences
        self.strategy_preferences = {
            QueryIntent.SEMANTIC_SEARCH: QueryStrategy.PARALLEL,
            QueryIntent.ANALYTICAL: QueryStrategy.SEQUENTIAL,
            QueryIntent.BROWSE: QueryStrategy.WATERFALL,
            QueryIntent.HYBRID: QueryStrategy.ADAPTIVE
        }

        self.coordinator = None
        self.health_monitor = None

    async def initialize(self, coordinator: MultiIndexCoordinator,
                        health_monitor: HealthMonitor):
        """Initialize planner with system components."""
        self.coordinator = coordinator
        self.health_monitor = health_monitor

        # Load historical performance data
        await self._load_performance_history()

        logger.info("Intelligent query planner initialized")

    async def create_execution_plan(self, query_text: str, query_params: Dict[str, Any],
                                  intent: QueryIntent, workspace: str = "default") -> QueryPlan:
        """Create optimized execution plan for query."""
        query_id = self._generate_query_id(query_text, query_params)

        try:
            # Analyze query requirements
            requirements = await self._analyze_query_requirements(
                query_text, query_params, intent
            )

            # Get available indices and their health
            available_indices = await self._get_available_indices()

            # Generate candidate plans
            candidate_plans = await self._generate_candidate_plans(
                query_id, requirements, available_indices, workspace
            )

            # Select optimal plan
            optimal_plan = await self._select_optimal_plan(
                candidate_plans, requirements
            )

            # Add fallback plans
            optimal_plan.fallback_plans = await self._generate_fallback_plans(
                optimal_plan, requirements, available_indices
            )

            logger.info(f"Created execution plan {query_id} with strategy {optimal_plan.strategy.value}")
            return optimal_plan

        except Exception as e:
            logger.error(f"Failed to create execution plan: {e}")
            # Return simple fallback plan
            return await self._create_fallback_plan(query_id, query_text, query_params)

    async def execute_plan(self, plan: QueryPlan, query_text: str,
                          query_params: Dict[str, Any], workspace: str = "default") -> QueryResult:
        """Execute query plan with performance tracking."""
        start_time = datetime.now()
        steps_executed = []
        all_results = []

        try:
            if plan.strategy == QueryStrategy.PARALLEL:
                results = await self._execute_parallel(plan, query_text, query_params, workspace)
            elif plan.strategy == QueryStrategy.SEQUENTIAL:
                results = await self._execute_sequential(plan, query_text, query_params, workspace)
            elif plan.strategy == QueryStrategy.WATERFALL:
                results = await self._execute_waterfall(plan, query_text, query_params, workspace)
            elif plan.strategy == QueryStrategy.HYBRID:
                results = await self._execute_hybrid(plan, query_text, query_params, workspace)
            else:  # ADAPTIVE
                results = await self._execute_adaptive(plan, query_text, query_params, workspace)

            # Combine and rank results
            combined_results = await self._combine_results(results, plan)

            execution_time = (datetime.now() - start_time).total_seconds()

            # Record performance
            await self._record_execution_performance(plan, execution_time, len(combined_results))

            return QueryResult(
                documents=combined_results,
                metadata={
                    "strategy": plan.strategy.value,
                    "steps_planned": len(plan.execution_steps),
                    "steps_executed": len(steps_executed),
                    "workspace": workspace
                },
                total_found=len(combined_results),
                execution_time=execution_time,
                execution_plan=plan,
                steps_executed=steps_executed,
                performance_metrics=self._calculate_performance_metrics(plan, execution_time)
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}")

            # Try fallback plans
            for fallback_plan in plan.fallback_plans:
                try:
                    logger.info(f"Attempting fallback plan with strategy {fallback_plan.strategy.value}")
                    return await self.execute_plan(fallback_plan, query_text, query_params, workspace)
                except Exception as fallback_error:
                    logger.warning(f"Fallback plan failed: {fallback_error}")
                    continue

            # If all fallbacks fail, return empty result
            execution_time = (datetime.now() - start_time).total_seconds()
            return QueryResult(
                documents=[],
                metadata={"error": str(e), "fallbacks_attempted": len(plan.fallback_plans)},
                total_found=0,
                execution_time=execution_time,
                execution_plan=plan,
                steps_executed=steps_executed,
                performance_metrics={}
            )

    async def get_optimization_insights(self) -> Dict[str, Any]:
        """Get insights about query optimization and performance."""
        insights = {
            "total_queries_planned": sum(len(history) for history in self.execution_history.values()),
            "strategy_distribution": {},
            "index_performance": self.index_performance.copy(),
            "optimization_opportunities": [],
            "recommendations": []
        }

        # Analyze strategy distribution
        strategy_counts = {}
        for history in self.execution_history.values():
            for execution in history:
                strategy = execution.get('strategy', 'unknown')
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        total_executions = sum(strategy_counts.values())
        if total_executions > 0:
            insights["strategy_distribution"] = {
                strategy: count / total_executions
                for strategy, count in strategy_counts.items()
            }

        # Generate recommendations
        insights["recommendations"] = await self._generate_optimization_recommendations()

        return insights

    # Execution strategy implementations

    async def _execute_parallel(self, plan: QueryPlan, query_text: str,
                               query_params: Dict[str, Any], workspace: str) -> List[Dict[str, Any]]:
        """Execute steps in parallel for maximum speed."""
        tasks = []

        for step in plan.execution_steps:
            if step.get('priority', IndexPriority.PRIMARY.value) <= IndexPriority.SECONDARY.value:
                task = self._execute_index_query(
                    step['index_name'], query_text, query_params, workspace, step
                )
                tasks.append(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Parallel execution step failed: {result}")
            elif result:
                successful_results.extend(result)

        return successful_results

    async def _execute_sequential(self, plan: QueryPlan, query_text: str,
                                 query_params: Dict[str, Any], workspace: str) -> List[Dict[str, Any]]:
        """Execute steps sequentially with dependency handling."""
        all_results = []
        step_results = {}

        # Sort steps by dependencies
        sorted_steps = self._sort_steps_by_dependencies(plan.execution_steps)

        for step in sorted_steps:
            # Check dependencies
            if self._dependencies_satisfied(step, step_results):
                try:
                    # Modify parameters based on previous results if needed
                    modified_params = await self._modify_params_for_step(
                        query_params, step, step_results
                    )

                    results = await self._execute_index_query(
                        step['index_name'], query_text, modified_params, workspace, step
                    )

                    if results:
                        all_results.extend(results)
                        step_results[step['step_id']] = results

                except Exception as e:
                    logger.warning(f"Sequential step {step['step_id']} failed: {e}")

        return all_results

    async def _execute_waterfall(self, plan: QueryPlan, query_text: str,
                                query_params: Dict[str, Any], workspace: str) -> List[Dict[str, Any]]:
        """Execute steps in waterfall pattern, stopping when sufficient results found."""
        target_results = query_params.get('limit', 100)
        all_results = []

        # Sort steps by priority
        sorted_steps = sorted(
            plan.execution_steps,
            key=lambda x: x.get('priority', IndexPriority.PRIMARY.value)
        )

        for step in sorted_steps:
            try:
                results = await self._execute_index_query(
                    step['index_name'], query_text, query_params, workspace, step
                )

                if results:
                    all_results.extend(results)

                    # Stop if we have enough results
                    if len(all_results) >= target_results:
                        logger.info(f"Waterfall execution stopped after {step['index_name']} - sufficient results")
                        break

            except Exception as e:
                logger.warning(f"Waterfall step {step['step_id']} failed: {e}")
                continue

        return all_results

    async def _execute_hybrid(self, plan: QueryPlan, query_text: str,
                             query_params: Dict[str, Any], workspace: str) -> List[Dict[str, Any]]:
        """Execute hybrid strategy combining parallel and sequential execution."""
        # Execute primary indices in parallel
        primary_tasks = []
        secondary_steps = []

        for step in plan.execution_steps:
            priority = step.get('priority', IndexPriority.PRIMARY.value)

            if priority == IndexPriority.PRIMARY.value:
                task = self._execute_index_query(
                    step['index_name'], query_text, query_params, workspace, step
                )
                primary_tasks.append(task)
            else:
                secondary_steps.append(step)

        # Execute primary tasks in parallel
        primary_results = []
        if primary_tasks:
            results = await asyncio.gather(*primary_tasks, return_exceptions=True)
            for result in results:
                if not isinstance(result, Exception) and result:
                    primary_results.extend(result)

        # Execute secondary steps sequentially if needed
        if len(primary_results) < query_params.get('limit', 100) and secondary_steps:
            for step in secondary_steps:
                try:
                    results = await self._execute_index_query(
                        step['index_name'], query_text, query_params, workspace, step
                    )
                    if results:
                        primary_results.extend(results)
                except Exception as e:
                    logger.warning(f"Hybrid secondary step failed: {e}")

        return primary_results

    async def _execute_adaptive(self, plan: QueryPlan, query_text: str,
                               query_params: Dict[str, Any], workspace: str) -> List[Dict[str, Any]]:
        """Execute adaptive strategy based on real-time performance."""
        # Start with most performant index based on history
        best_performing_index = await self._get_best_performing_index(query_text, query_params)

        results = []

        # Try best performing index first
        if best_performing_index:
            try:
                step = next(
                    (s for s in plan.execution_steps if s['index_name'] == best_performing_index),
                    None
                )
                if step:
                    results = await self._execute_index_query(
                        best_performing_index, query_text, query_params, workspace, step
                    )
            except Exception as e:
                logger.warning(f"Best performing index {best_performing_index} failed: {e}")

        # If insufficient results, add more indices
        target_results = query_params.get('limit', 100)
        if len(results) < target_results * 0.8:  # 80% of target
            # Execute remaining indices in parallel
            remaining_tasks = []
            for step in plan.execution_steps:
                if step['index_name'] != best_performing_index:
                    task = self._execute_index_query(
                        step['index_name'], query_text, query_params, workspace, step
                    )
                    remaining_tasks.append(task)

            if remaining_tasks:
                additional_results = await asyncio.gather(*remaining_tasks, return_exceptions=True)
                for result in additional_results:
                    if not isinstance(result, Exception) and result:
                        results.extend(result)

        return results

    # Helper methods

    async def _analyze_query_requirements(self, query_text: str, query_params: Dict[str, Any],
                                         intent: QueryIntent) -> Dict[str, Any]:
        """Analyze query to determine requirements and optimal indices."""
        requirements = {
            'intent': intent,
            'complexity': self._calculate_query_complexity(query_text, query_params),
            'required_indices': [],
            'optional_indices': [],
            'estimated_result_size': query_params.get('limit', 100),
            'performance_priority': query_params.get('performance_priority', 'balanced')
        }

        # Determine required indices based on intent
        if intent == QueryIntent.SEMANTIC_SEARCH:
            requirements['required_indices'] = ['vector', 'fts']
            requirements['optional_indices'] = ['metadata']
        elif intent == QueryIntent.ANALYTICAL:
            requirements['required_indices'] = ['metadata']
            requirements['optional_indices'] = ['temporal', 'fts']
        elif intent == QueryIntent.BROWSE:
            requirements['required_indices'] = ['fts', 'metadata']
            requirements['optional_indices'] = ['temporal']
        elif intent == QueryIntent.HYBRID:
            requirements['required_indices'] = ['vector', 'metadata', 'fts']
            requirements['optional_indices'] = ['graph', 'temporal']

        return requirements

    async def _generate_candidate_plans(self, query_id: str, requirements: Dict[str, Any],
                                       available_indices: List[str], workspace: str) -> List[QueryPlan]:
        """Generate multiple candidate execution plans."""
        plans = []

        # Get indices that are actually available
        required_available = [idx for idx in requirements['required_indices'] if idx in available_indices]
        optional_available = [idx for idx in requirements['optional_indices'] if idx in available_indices]

        if not required_available:
            # Fallback to any available index
            required_available = available_indices[:2] if len(available_indices) >= 2 else available_indices

        # Generate plans for different strategies
        strategies_to_try = [QueryStrategy.PARALLEL, QueryStrategy.SEQUENTIAL, QueryStrategy.WATERFALL]

        for strategy in strategies_to_try:
            plan = await self._create_plan_for_strategy(
                query_id, strategy, required_available, optional_available, requirements
            )
            if plan:
                plans.append(plan)

        return plans

    async def _create_plan_for_strategy(self, query_id: str, strategy: QueryStrategy,
                                       required_indices: List[str], optional_indices: List[str],
                                       requirements: Dict[str, Any]) -> Optional[QueryPlan]:
        """Create execution plan for specific strategy."""
        try:
            execution_steps = []
            total_cost = 0.0
            total_time = 0.0

            # Add required indices
            for i, index_name in enumerate(required_indices):
                step = {
                    'step_id': f"{query_id}_{index_name}_{i}",
                    'index_name': index_name,
                    'operation': 'query',
                    'parameters': {},
                    'dependencies': [],
                    'priority': IndexPriority.PRIMARY.value,
                    'estimated_cost': self._estimate_index_cost(index_name, requirements),
                    'timeout_seconds': 30.0
                }
                execution_steps.append(step)
                total_cost += step['estimated_cost']

            # Add optional indices if performance allows
            if requirements.get('performance_priority') != 'speed':
                for i, index_name in enumerate(optional_indices[:2]):  # Limit to 2 optional
                    step = {
                        'step_id': f"{query_id}_{index_name}_opt_{i}",
                        'index_name': index_name,
                        'operation': 'query',
                        'parameters': {},
                        'dependencies': [],
                        'priority': IndexPriority.SECONDARY.value,
                        'estimated_cost': self._estimate_index_cost(index_name, requirements),
                        'timeout_seconds': 15.0
                    }
                    execution_steps.append(step)
                    total_cost += step['estimated_cost'] * 0.5  # Optional indices weighted less

            # Estimate execution time based on strategy
            if strategy == QueryStrategy.PARALLEL:
                total_time = max(step['estimated_cost'] for step in execution_steps) if execution_steps else 0
            else:
                total_time = sum(step['estimated_cost'] for step in execution_steps)

            return QueryPlan(
                query_id=query_id,
                strategy=strategy,
                estimated_cost=total_cost,
                estimated_time=total_time,
                execution_steps=execution_steps,
                fallback_plans=[],
                optimization_notes=[f"Strategy: {strategy.value}", f"Indices: {len(execution_steps)}"],
                created_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Failed to create plan for strategy {strategy}: {e}")
            return None

    async def _execute_index_query(self, index_name: str, query_text: str,
                                  query_params: Dict[str, Any], workspace: str,
                                  step: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute query on specific index."""
        try:
            # This would integrate with the actual index implementations
            # For now, return mock results
            logger.info(f"Executing query on {index_name} index")

            # Mock results based on index type
            if index_name == 'vector':
                return [
                    {"id": f"vec_{i}", "title": f"Vector Result {i}", "score": 0.9 - i*0.1}
                    for i in range(min(5, query_params.get('limit', 10)))
                ]
            elif index_name == 'fts':
                return [
                    {"id": f"fts_{i}", "title": f"FTS Result {i}", "relevance": 0.8 - i*0.1}
                    for i in range(min(3, query_params.get('limit', 10)))
                ]
            elif index_name == 'metadata':
                return [
                    {"id": f"meta_{i}", "title": f"Metadata Result {i}", "category": "test"}
                    for i in range(min(4, query_params.get('limit', 10)))
                ]
            else:
                return []

        except Exception as e:
            logger.error(f"Index query failed for {index_name}: {e}")
            return []

    def _estimate_index_cost(self, index_name: str, requirements: Dict[str, Any]) -> float:
        """Estimate cost for querying specific index."""
        base_cost = self.base_costs.get(index_name, 0.5)

        # Adjust based on complexity
        complexity_multiplier = 1 + (requirements.get('complexity', 0.5) * 0.5)

        # Adjust based on historical performance
        if index_name in self.index_performance:
            perf_data = self.index_performance[index_name]
            avg_time = perf_data.get('avg_execution_time', base_cost)
            base_cost = (base_cost + avg_time) / 2

        return base_cost * complexity_multiplier

    def _calculate_query_complexity(self, query_text: str, query_params: Dict[str, Any]) -> float:
        """Calculate query complexity score (0-1)."""
        complexity = 0.0

        # Text length factor
        complexity += min(len(query_text) / 500.0, 0.3)

        # Parameter count factor
        complexity += min(len(query_params) / 10.0, 0.2)

        # Special operations
        if any(op in query_text.lower() for op in ['aggregation', 'group', 'join']):
            complexity += 0.3

        if 'limit' in query_params and query_params['limit'] > 100:
            complexity += 0.2

        return min(complexity, 1.0)

    def _generate_query_id(self, query_text: str, query_params: Dict[str, Any]) -> str:
        """Generate unique ID for query."""
        import hashlib
        query_str = f"{query_text}_{json.dumps(query_params, sort_keys=True)}"
        return hashlib.md5(query_str.encode()).hexdigest()[:12]

    async def _get_available_indices(self) -> List[str]:
        """Get list of available and healthy indices."""
        # This would check actual index health
        # For now, return mock available indices
        return ['vector', 'fts', 'metadata', 'temporal', 'graph', 'adaptive']

    async def _select_optimal_plan(self, candidate_plans: List[QueryPlan],
                                  requirements: Dict[str, Any]) -> QueryPlan:
        """Select optimal plan based on requirements and performance."""
        if not candidate_plans:
            raise ValueError("No candidate plans available")

        performance_priority = requirements.get('performance_priority', 'balanced')

        if performance_priority == 'speed':
            # Prefer parallel execution with lowest estimated time
            return min(candidate_plans, key=lambda p: p.estimated_time)
        elif performance_priority == 'accuracy':
            # Prefer plans with more indices
            return max(candidate_plans, key=lambda p: len(p.execution_steps))
        else:  # balanced
            # Optimize for cost-effectiveness
            return min(candidate_plans, key=lambda p: p.estimated_cost)

    async def _combine_results(self, results: List[Dict[str, Any]], plan: QueryPlan) -> List[Dict[str, Any]]:
        """Combine and deduplicate results from multiple indices."""
        seen_ids = set()
        combined = []

        for result in results:
            doc_id = result.get('id')
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                combined.append(result)

        # Sort by relevance/score if available
        def get_score(doc):
            return doc.get('score', doc.get('relevance', doc.get('confidence', 0)))

        combined.sort(key=get_score, reverse=True)
        return combined

    def _calculate_performance_metrics(self, plan: QueryPlan, execution_time: float) -> Dict[str, Any]:
        """Calculate performance metrics for executed plan."""
        return {
            'actual_execution_time': execution_time,
            'estimated_execution_time': plan.estimated_time,
            'time_variance': abs(execution_time - plan.estimated_time) / max(plan.estimated_time, 0.001),
            'cost_efficiency': plan.estimated_cost / max(execution_time, 0.001),
            'strategy_used': plan.strategy.value
        }

    async def _record_execution_performance(self, plan: QueryPlan, execution_time: float, result_count: int):
        """Record execution performance for future optimization."""
        if plan.query_id not in self.execution_history:
            self.execution_history[plan.query_id] = []

        self.execution_history[plan.query_id].append({
            'execution_time': execution_time,
            'result_count': result_count,
            'strategy': plan.strategy.value,
            'timestamp': datetime.now().isoformat(),
            'cost': plan.estimated_cost
        })

        # Update index performance metrics
        for step in plan.execution_steps:
            index_name = step['index_name']
            if index_name not in self.index_performance:
                self.index_performance[index_name] = {}

            current_avg = self.index_performance[index_name].get('avg_execution_time', execution_time)
            self.index_performance[index_name]['avg_execution_time'] = (current_avg + execution_time) / 2

    async def _load_performance_history(self):
        """Load historical performance data."""
        # This would load from persistent storage
        # For now, initialize empty
        self.execution_history = {}
        self.index_performance = {}

    async def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on performance history."""
        recommendations = []

        # Analyze strategy performance
        strategy_performance = {}
        for history in self.execution_history.values():
            for execution in history:
                strategy = execution.get('strategy', 'unknown')
                time = execution.get('execution_time', 0)

                if strategy not in strategy_performance:
                    strategy_performance[strategy] = []
                strategy_performance[strategy].append(time)

        # Find best performing strategy
        best_strategy = None
        best_avg_time = float('inf')

        for strategy, times in strategy_performance.items():
            if times:
                avg_time = sum(times) / len(times)
                if avg_time < best_avg_time:
                    best_avg_time = avg_time
                    best_strategy = strategy

        if best_strategy:
            recommendations.append(f"Consider using {best_strategy} strategy more frequently (avg: {best_avg_time:.3f}s)")

        # Analyze index performance
        slow_indices = []
        for index_name, metrics in self.index_performance.items():
            avg_time = metrics.get('avg_execution_time', 0)
            if avg_time > 1.0:  # Slow threshold
                slow_indices.append(index_name)

        if slow_indices:
            recommendations.append(f"Indices needing optimization: {', '.join(slow_indices)}")

        return recommendations

    # Additional helper methods
    def _sort_steps_by_dependencies(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort steps to respect dependencies."""
        # Simple topological sort
        sorted_steps = []
        remaining_steps = steps.copy()

        while remaining_steps:
            # Find steps with no unresolved dependencies
            ready_steps = []
            for step in remaining_steps:
                dependencies = step.get('dependencies', [])
                resolved_deps = [s['step_id'] for s in sorted_steps]
                if all(dep in resolved_deps for dep in dependencies):
                    ready_steps.append(step)

            if not ready_steps:
                # Circular dependency or error - add remaining steps
                sorted_steps.extend(remaining_steps)
                break

            # Add ready steps and remove from remaining
            sorted_steps.extend(ready_steps)
            for step in ready_steps:
                remaining_steps.remove(step)

        return sorted_steps

    def _dependencies_satisfied(self, step: Dict[str, Any], completed_steps: Dict[str, Any]) -> bool:
        """Check if step dependencies are satisfied."""
        dependencies = step.get('dependencies', [])
        return all(dep in completed_steps for dep in dependencies)

    async def _modify_params_for_step(self, original_params: Dict[str, Any],
                                    step: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Modify query parameters based on previous step results."""
        # Default: return original parameters
        # This could be enhanced to filter results, adjust limits, etc.
        return original_params.copy()

    async def _get_best_performing_index(self, query_text: str, query_params: Dict[str, Any]) -> Optional[str]:
        """Get best performing index for similar queries."""
        if not self.index_performance:
            return None

        # Find index with best average performance
        best_index = None
        best_performance = float('inf')

        for index_name, metrics in self.index_performance.items():
            avg_time = metrics.get('avg_execution_time', float('inf'))
            if avg_time < best_performance:
                best_performance = avg_time
                best_index = index_name

        return best_index

    async def _create_fallback_plan(self, query_id: str, query_text: str, query_params: Dict[str, Any]) -> QueryPlan:
        """Create simple fallback plan when optimization fails."""
        return QueryPlan(
            query_id=query_id,
            strategy=QueryStrategy.SEQUENTIAL,
            estimated_cost=1.0,
            estimated_time=2.0,
            execution_steps=[
                {
                    'step_id': f"{query_id}_fallback",
                    'index_name': 'fts',  # Most reliable fallback
                    'operation': 'query',
                    'parameters': query_params,
                    'dependencies': [],
                    'priority': IndexPriority.PRIMARY.value,
                    'estimated_cost': 0.5,
                    'timeout_seconds': 30.0
                }
            ],
            fallback_plans=[],
            optimization_notes=["Fallback plan - optimization failed"],
            created_at=datetime.now()
        )

    async def _generate_fallback_plans(self, main_plan: QueryPlan, requirements: Dict[str, Any],
                                     available_indices: List[str]) -> List[QueryPlan]:
        """Generate fallback plans for resilience."""
        fallback_plans = []

        # Create simple single-index fallbacks
        reliable_indices = ['fts', 'metadata']  # Most reliable indices

        for index_name in reliable_indices:
            if index_name in available_indices and index_name != main_plan.execution_steps[0]['index_name']:
                fallback_plan = QueryPlan(
                    query_id=f"{main_plan.query_id}_fallback_{index_name}",
                    strategy=QueryStrategy.SEQUENTIAL,
                    estimated_cost=0.5,
                    estimated_time=1.0,
                    execution_steps=[
                        {
                            'step_id': f"{main_plan.query_id}_fallback_{index_name}",
                            'index_name': index_name,
                            'operation': 'query',
                            'parameters': {},
                            'dependencies': [],
                            'priority': IndexPriority.PRIMARY.value,
                            'estimated_cost': 0.5,
                            'timeout_seconds': 30.0
                        }
                    ],
                    fallback_plans=[],
                    optimization_notes=[f"Fallback to {index_name} only"],
                    created_at=datetime.now()
                )
                fallback_plans.append(fallback_plan)

        return fallback_plans[:2]  # Limit to 2 fallback plans