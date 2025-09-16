"""
Integration Layer for Multi-Index System

This module provides the main integration layer that coordinates all Phase 1 components:
- Smart Query Router
- Multi-Index Coordinator
- Health Monitoring
- Conflict Resolution

It provides a unified API for the multi-index system and manages component lifecycle.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Import Phase 1 components
from .query_router import SmartQueryRouter, QueryContext, RouteDecision
from .coordinator import MultiIndexCoordinator, IndexOperation, OperationType
from .monitoring import HealthMonitor
from .conflict_resolution import ConflictResolver

from ..config.settings import get_config

logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    """Overall system status including all components."""
    overall_health: str
    query_router_active: bool
    coordinator_active: bool
    monitor_active: bool
    conflict_resolver_active: bool
    enabled_indices: List[str]
    performance_summary: Dict[str, Any]
    last_updated: datetime

class MultiIndexSystem:
    """
    Main integration layer for the multi-index knowledge base system.

    Coordinates all Phase 1 components and provides a unified API for:
    - Query routing and execution
    - Data operations across indices
    - Health monitoring and metrics
    - Conflict resolution
    """

    def __init__(self):
        """Initialize the multi-index system with all components."""
        self.config = get_config()

        # Initialize components
        self.query_router = SmartQueryRouter()
        self.coordinator = MultiIndexCoordinator()
        self.health_monitor = HealthMonitor(check_interval=self.config.health_check_interval)
        self.conflict_resolver = ConflictResolver()

        # System state
        self.system_active = False
        self.startup_time: Optional[datetime] = None

        logger.info("MultiIndexSystem initialized")

    async def startup(self):
        """Start all system components."""
        try:
            logger.info("Starting multi-index system...")

            # Start health monitoring
            self.health_monitor.start_monitoring()

            # Set up alert callbacks
            self.health_monitor.add_alert_callback(self._handle_health_alert)

            self.system_active = True
            self.startup_time = datetime.now()

            logger.info("Multi-index system started successfully")

        except Exception as e:
            logger.error(f"Failed to start multi-index system: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Shutdown all system components."""
        try:
            logger.info("Shutting down multi-index system...")

            # Stop monitoring
            self.health_monitor.stop_monitoring()

            self.system_active = False

            logger.info("Multi-index system shutdown complete")

        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")

    async def query(
        self,
        query_text: str,
        context: Optional[QueryContext] = None,
        workspace: str = "default"
    ) -> Dict[str, Any]:
        """
        Execute a query through the multi-index system.

        Args:
            query_text: The query to execute
            context: Optional query context for routing decisions
            workspace: Workspace context

        Returns:
            Query results with routing information
        """
        if not self.system_active:
            raise RuntimeError("Multi-index system not active. Call startup() first.")

        try:
            # Route the query
            routing_decision = await self.query_router.route_query(query_text, context)

            # Execute query through appropriate indices
            # For now, return routing decision with placeholder results
            # In Phase 2, this would execute actual queries

            return {
                'query': query_text,
                'routing': {
                    'primary_index': routing_decision.primary_index,
                    'secondary_indices': routing_decision.secondary_indices,
                    'intent': routing_decision.intent.value,
                    'confidence': routing_decision.confidence,
                    'reasoning': routing_decision.reasoning,
                    'estimated_time': routing_decision.estimated_time
                },
                'results': {
                    'status': 'routed',
                    'message': f'Query routed to {routing_decision.primary_index} index'
                },
                'workspace': workspace
            }

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                'query': query_text,
                'error': str(e),
                'status': 'failed',
                'workspace': workspace
            }

    async def ingest_data(
        self,
        data: List[Dict[str, Any]],
        workspace: str = "default",
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Ingest data across multiple indices with conflict resolution.

        Args:
            data: List of data items to ingest
            workspace: Target workspace
            user_id: User performing the ingestion

        Returns:
            Ingestion results with conflict information
        """
        if not self.system_active:
            raise RuntimeError("Multi-index system not active. Call startup() first.")

        try:
            # Create coordinated operations for each enabled index
            enabled_indices = self.config.get_enabled_indices()
            operations = []

            for item in data:
                document_id = item.get('id', f"doc_{hash(str(item)) % 100000}")

                # Track operation for conflict detection
                operation_metadata = self.conflict_resolver.track_operation(
                    operation_id=f"ingest_{document_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    workspace=workspace,
                    document_id=document_id,
                    operation_type="insert",
                    operation_data=item
                )

                # Check for conflicts
                conflict_event = await self.conflict_resolver.detect_conflicts(
                    operation_metadata, item
                )

                if conflict_event:
                    logger.warning(f"Conflict detected for document {document_id}")

                # Create operations for each index
                for index_name in enabled_indices:
                    operation = self.coordinator.create_index_operation(
                        index_name=index_name,
                        operation_type=OperationType.INSERT,
                        data=item,
                        metadata={'user_id': user_id, 'workspace': workspace}
                    )
                    operations.append(operation)

            # Execute coordinated transaction
            transaction_result = await self.coordinator.coordinate_operation(
                operations=operations,
                workspace=workspace
            )

            return {
                'status': 'success' if transaction_result.status.value == 'completed' else 'failed',
                'transaction_id': transaction_result.transaction_id,
                'operations_count': len(operations),
                'indices_updated': list(enabled_indices.keys()),
                'workspace': workspace,
                'conflicts_detected': len([event for event in self.conflict_resolver.active_conflicts.values()
                                         if event.workspace == workspace])
            }

        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'workspace': workspace
            }

    def get_system_status(self) -> SystemStatus:
        """Get overall system status."""
        health_summary = self.health_monitor.get_overall_health()
        performance_summary = self.health_monitor.get_performance_summary()

        return SystemStatus(
            overall_health=health_summary.get('status', 'unknown'),
            query_router_active=True,  # Always active if system is active
            coordinator_active=True,
            monitor_active=self.health_monitor.monitoring_active,
            conflict_resolver_active=True,
            enabled_indices=list(self.config.get_enabled_indices().keys()),
            performance_summary=performance_summary,
            last_updated=datetime.now()
        )

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics from all components."""
        return {
            'system': {
                'active': self.system_active,
                'startup_time': self.startup_time.isoformat() if self.startup_time else None,
                'enabled_indices': list(self.config.get_enabled_indices().keys())
            },
            'query_router': self.query_router.get_routing_stats(),
            'coordinator': self.coordinator.get_coordinator_stats(),
            'health_monitor': {
                'overall_health': self.health_monitor.get_overall_health(),
                'performance_summary': self.health_monitor.get_performance_summary(),
                'metrics_summary': self.health_monitor.get_metrics_summary()
            },
            'conflict_resolver': self.conflict_resolver.get_conflict_summary()
        }

    def _handle_health_alert(self, health_check):
        """Handle health alerts from monitoring system."""
        logger.warning(f"Health alert: {health_check.component} - {health_check.status.value} - {health_check.message}")

        # In a full implementation, this would trigger appropriate responses:
        # - Disable problematic indices
        # - Adjust routing decisions
        # - Send notifications
        # - Trigger recovery procedures

    async def resolve_conflicts(self, workspace: str = "default") -> Dict[str, Any]:
        """
        Resolve all active conflicts for a workspace.

        Args:
            workspace: Workspace to resolve conflicts for

        Returns:
            Resolution results
        """
        workspace_conflicts = [
            conflict for conflict in self.conflict_resolver.active_conflicts.values()
            if conflict.workspace == workspace
        ]

        if not workspace_conflicts:
            return {
                'status': 'no_conflicts',
                'workspace': workspace,
                'message': 'No active conflicts to resolve'
            }

        resolution_results = []
        for conflict in workspace_conflicts:
            try:
                result = await self.conflict_resolver.resolve_conflict(conflict)
                resolution_results.append({
                    'conflict_id': conflict.conflict_id,
                    'result': result
                })
            except Exception as e:
                logger.error(f"Failed to resolve conflict {conflict.conflict_id}: {e}")
                resolution_results.append({
                    'conflict_id': conflict.conflict_id,
                    'result': {'status': 'failed', 'error': str(e)}
                })

        successful_resolutions = sum(1 for r in resolution_results if r['result'].get('status') == 'resolved')

        return {
            'status': 'completed',
            'workspace': workspace,
            'total_conflicts': len(workspace_conflicts),
            'resolved_conflicts': successful_resolutions,
            'failed_resolutions': len(workspace_conflicts) - successful_resolutions,
            'results': resolution_results
        }

# Global system instance
_global_system: Optional[MultiIndexSystem] = None

def get_multi_index_system() -> MultiIndexSystem:
    """Get the global multi-index system instance."""
    global _global_system
    if _global_system is None:
        _global_system = MultiIndexSystem()
    return _global_system

async def initialize_system() -> MultiIndexSystem:
    """Initialize and start the global multi-index system."""
    system = get_multi_index_system()
    if not system.system_active:
        await system.startup()
    return system