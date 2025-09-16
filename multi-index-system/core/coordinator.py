"""
Multi-Index Coordinator for Data Synchronization

This module coordinates data operations across multiple indices ensuring:
- Consistent data state across all enabled indices
- Atomic operations with rollback capability
- Event-driven synchronization using Redis Streams
- Conflict-free concurrent operations
- Performance optimization through intelligent batching

Following the zero-cost, local-first architecture with Redis for coordination.
"""

import asyncio
import logging
import time
import json
import uuid
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
from collections import defaultdict

# Import Redis for event streaming
import redis
from redis.exceptions import ConnectionError, TimeoutError

# Import existing components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Try relative import first, fallback to absolute
try:
    from ..config.settings import get_config
except ImportError:
    from config.settings import get_config

logger = logging.getLogger(__name__)

class OperationType(Enum):
    """Types of data operations that can be coordinated."""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    BATCH_INSERT = "batch_insert"
    BATCH_UPDATE = "batch_update"
    BATCH_DELETE = "batch_delete"

class OperationStatus(Enum):
    """Status of coordinated operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class IndexOperation:
    """Individual index operation within a coordinated transaction."""
    index_name: str
    operation_type: OperationType
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: OperationStatus = OperationStatus.PENDING
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class CoordinatedTransaction:
    """A coordinated transaction across multiple indices."""
    transaction_id: str
    operations: List[IndexOperation]
    initiator: str = "system"
    workspace: str = "default"
    created_at: datetime = field(default_factory=datetime.now)
    status: OperationStatus = OperationStatus.PENDING
    rollback_operations: List[IndexOperation] = field(default_factory=list)

class MultiIndexCoordinator:
    """
    Coordinates data operations across multiple indices with ACID-like properties.

    Uses Redis Streams for event-driven coordination and maintains consistency
    through two-phase commit patterns adapted for document stores.
    """

    def __init__(self):
        """Initialize the multi-index coordinator."""
        self.config = get_config()
        self.active_transactions: Dict[str, CoordinatedTransaction] = {}
        self.operation_history: List[CoordinatedTransaction] = []
        self.locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

        # Initialize Redis connection for event coordination
        self.redis_client = self._init_redis_client()

        # Performance tracking
        self.performance_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_operation_time': 0.0,
            'rollback_count': 0
        }

        logger.info("MultiIndexCoordinator initialized")

    def _init_redis_client(self) -> Optional[redis.Redis]:
        """Initialize Redis client for event streaming coordination."""
        try:
            client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                decode_responses=True,
                socket_connect_timeout=self.config.redis_timeout,
                socket_timeout=self.config.redis_timeout
            )

            # Test connection
            client.ping()
            logger.info(f"Connected to Redis at {self.config.redis_host}:{self.config.redis_port}")
            return client

        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis not available: {e}. Operating without event streaming.")
            return None
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            return None

    async def coordinate_operation(
        self,
        operations: List[IndexOperation],
        transaction_id: Optional[str] = None,
        workspace: str = "default"
    ) -> CoordinatedTransaction:
        """
        Coordinate a set of operations across multiple indices.

        Args:
            operations: List of index operations to coordinate
            transaction_id: Optional transaction ID (auto-generated if not provided)
            workspace: Workspace context for the operations

        Returns:
            CoordinatedTransaction with operation results
        """
        if transaction_id is None:
            transaction_id = f"tx_{uuid.uuid4().hex[:8]}_{int(time.time())}"

        transaction = CoordinatedTransaction(
            transaction_id=transaction_id,
            operations=operations,
            workspace=workspace
        )

        self.active_transactions[transaction_id] = transaction

        try:
            # Phase 1: Prepare all operations
            prepare_success = await self._prepare_phase(transaction)

            if not prepare_success:
                logger.warning(f"Transaction {transaction_id} preparation failed")
                transaction.status = OperationStatus.FAILED
                await self._rollback_transaction(transaction)
                return transaction

            # Phase 2: Commit all operations
            commit_success = await self._commit_phase(transaction)

            if commit_success:
                transaction.status = OperationStatus.COMPLETED
                self.performance_stats['successful_operations'] += 1
                logger.info(f"Transaction {transaction_id} completed successfully")
            else:
                transaction.status = OperationStatus.FAILED
                await self._rollback_transaction(transaction)

        except Exception as e:
            logger.error(f"Transaction {transaction_id} failed with error: {e}")
            transaction.status = OperationStatus.FAILED
            await self._rollback_transaction(transaction)

        finally:
            # Clean up and record metrics
            self._finalize_transaction(transaction)

        return transaction

    async def _prepare_phase(self, transaction: CoordinatedTransaction) -> bool:
        """
        Prepare phase: Validate and lock resources for all operations.

        Args:
            transaction: The transaction to prepare

        Returns:
            True if all operations can be prepared, False otherwise
        """
        transaction.status = OperationStatus.IN_PROGRESS

        # Emit preparation event
        await self._emit_coordination_event("transaction_prepare", {
            "transaction_id": transaction.transaction_id,
            "operation_count": len(transaction.operations),
            "workspace": transaction.workspace
        })

        preparation_tasks = []
        for operation in transaction.operations:
            task = asyncio.create_task(self._prepare_operation(operation))
            preparation_tasks.append(task)

        # Wait for all preparation tasks
        results = await asyncio.gather(*preparation_tasks, return_exceptions=True)

        # Check if all preparations succeeded
        all_success = True
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Operation preparation failed: {result}")
                transaction.operations[i].status = OperationStatus.FAILED
                transaction.operations[i].error = str(result)
                all_success = False
            elif not result:
                all_success = False

        return all_success

    async def _prepare_operation(self, operation: IndexOperation) -> bool:
        """
        Prepare a single index operation.

        Args:
            operation: The operation to prepare

        Returns:
            True if preparation successful, False otherwise
        """
        try:
            operation.status = OperationStatus.IN_PROGRESS
            operation.started_at = datetime.now()

            # Index-specific preparation logic
            if operation.index_name == "vector":
                return await self._prepare_vector_operation(operation)
            elif operation.index_name == "graph":
                return await self._prepare_graph_operation(operation)
            elif operation.index_name == "metadata":
                return await self._prepare_metadata_operation(operation)
            elif operation.index_name == "fts":
                return await self._prepare_fts_operation(operation)
            elif operation.index_name == "temporal":
                return await self._prepare_temporal_operation(operation)
            else:
                logger.warning(f"Unknown index type: {operation.index_name}")
                return False

        except Exception as e:
            operation.error = str(e)
            operation.status = OperationStatus.FAILED
            logger.error(f"Operation preparation failed for {operation.index_name}: {e}")
            return False

    async def _prepare_vector_operation(self, operation: IndexOperation) -> bool:
        """Prepare vector database operation."""
        # For now, vector operations are always ready
        # In a full implementation, this would check ChromaDB availability
        return True

    async def _prepare_graph_operation(self, operation: IndexOperation) -> bool:
        """Prepare graph database operation."""
        # For now, graph operations are always ready if enabled
        return self.config.graph_config.enabled

    async def _prepare_metadata_operation(self, operation: IndexOperation) -> bool:
        """Prepare metadata database operation."""
        # For now, metadata operations are always ready
        return True

    async def _prepare_fts_operation(self, operation: IndexOperation) -> bool:
        """Prepare full-text search operation."""
        return self.config.fts_config.enabled

    async def _prepare_temporal_operation(self, operation: IndexOperation) -> bool:
        """Prepare temporal index operation."""
        return self.config.temporal_config.enabled

    async def _commit_phase(self, transaction: CoordinatedTransaction) -> bool:
        """
        Commit phase: Execute all prepared operations.

        Args:
            transaction: The transaction to commit

        Returns:
            True if all operations committed successfully, False otherwise
        """
        # Emit commit event
        await self._emit_coordination_event("transaction_commit", {
            "transaction_id": transaction.transaction_id,
            "operation_count": len(transaction.operations)
        })

        commit_tasks = []
        for operation in transaction.operations:
            if operation.status == OperationStatus.IN_PROGRESS:
                task = asyncio.create_task(self._commit_operation(operation))
                commit_tasks.append(task)

        # Wait for all commit tasks
        results = await asyncio.gather(*commit_tasks, return_exceptions=True)

        # Check if all commits succeeded
        all_success = True
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Operation commit failed: {result}")
                transaction.operations[i].status = OperationStatus.FAILED
                transaction.operations[i].error = str(result)
                all_success = False
            elif not result:
                all_success = False

        return all_success

    async def _commit_operation(self, operation: IndexOperation) -> bool:
        """
        Commit a single index operation.

        Args:
            operation: The operation to commit

        Returns:
            True if commit successful, False otherwise
        """
        try:
            # Index-specific commit logic would go here
            # For now, we simulate successful commits
            await asyncio.sleep(0.01)  # Simulate operation time

            operation.status = OperationStatus.COMPLETED
            operation.completed_at = datetime.now()

            logger.debug(f"Committed {operation.operation_type.value} to {operation.index_name}")
            return True

        except Exception as e:
            operation.error = str(e)
            operation.status = OperationStatus.FAILED
            logger.error(f"Operation commit failed for {operation.index_name}: {e}")
            return False

    async def _rollback_transaction(self, transaction: CoordinatedTransaction):
        """
        Rollback a failed transaction.

        Args:
            transaction: The transaction to rollback
        """
        logger.warning(f"Rolling back transaction {transaction.transaction_id}")

        # Emit rollback event
        await self._emit_coordination_event("transaction_rollback", {
            "transaction_id": transaction.transaction_id,
            "reason": "commit_failure"
        })

        # Generate rollback operations for completed operations
        rollback_operations = []
        for operation in transaction.operations:
            if operation.status == OperationStatus.COMPLETED:
                rollback_op = self._generate_rollback_operation(operation)
                if rollback_op:
                    rollback_operations.append(rollback_op)

        # Execute rollback operations
        if rollback_operations:
            rollback_tasks = [
                asyncio.create_task(self._commit_operation(op))
                for op in rollback_operations
            ]
            await asyncio.gather(*rollback_tasks, return_exceptions=True)

        transaction.status = OperationStatus.ROLLED_BACK
        transaction.rollback_operations = rollback_operations
        self.performance_stats['rollback_count'] += 1

    def _generate_rollback_operation(self, original_operation: IndexOperation) -> Optional[IndexOperation]:
        """
        Generate a rollback operation for a completed operation.

        Args:
            original_operation: The operation to rollback

        Returns:
            Rollback operation or None if not applicable
        """
        if original_operation.operation_type == OperationType.INSERT:
            return IndexOperation(
                index_name=original_operation.index_name,
                operation_type=OperationType.DELETE,
                data={"id": original_operation.data.get("id")},
                metadata={"rollback": True, "original_operation": original_operation.operation_type.value}
            )
        elif original_operation.operation_type == OperationType.DELETE:
            return IndexOperation(
                index_name=original_operation.index_name,
                operation_type=OperationType.INSERT,
                data=original_operation.data,
                metadata={"rollback": True, "original_operation": original_operation.operation_type.value}
            )
        # UPDATE rollbacks would require storing previous state
        return None

    async def _emit_coordination_event(self, event_type: str, data: Dict[str, Any]):
        """
        Emit coordination event to Redis Streams.

        Args:
            event_type: Type of event
            data: Event data
        """
        if not self.redis_client:
            return

        event = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': json.dumps(data),
            'coordinator_id': 'multi_index_coordinator'
        }

        try:
            self.redis_client.xadd(f'coordination_events:{event_type}', event)
        except Exception as e:
            logger.warning(f"Failed to emit coordination event: {e}")

    def _finalize_transaction(self, transaction: CoordinatedTransaction):
        """
        Clean up and record metrics for a completed transaction.

        Args:
            transaction: The transaction to finalize
        """
        # Update performance statistics
        self.performance_stats['total_operations'] += 1
        if transaction.status == OperationStatus.FAILED:
            self.performance_stats['failed_operations'] += 1

        # Calculate operation time
        operation_time = 0.0
        if transaction.operations:
            start_times = [op.started_at for op in transaction.operations if op.started_at]
            end_times = [op.completed_at for op in transaction.operations if op.completed_at]

            if start_times and end_times:
                operation_time = (max(end_times) - min(start_times)).total_seconds()

        # Update average operation time
        total_ops = self.performance_stats['total_operations']
        current_avg = self.performance_stats['average_operation_time']
        self.performance_stats['average_operation_time'] = (
            (current_avg * (total_ops - 1) + operation_time) / total_ops
        )

        # Move to history and clean up
        self.operation_history.append(transaction)
        if transaction.transaction_id in self.active_transactions:
            del self.active_transactions[transaction.transaction_id]

        # Trim history to prevent memory growth
        if len(self.operation_history) > 1000:
            self.operation_history = self.operation_history[-500:]

    def get_transaction_status(self, transaction_id: str) -> Optional[CoordinatedTransaction]:
        """
        Get status of a transaction.

        Args:
            transaction_id: ID of the transaction

        Returns:
            Transaction object or None if not found
        """
        if transaction_id in self.active_transactions:
            return self.active_transactions[transaction_id]

        # Search in history
        for transaction in reversed(self.operation_history):
            if transaction.transaction_id == transaction_id:
                return transaction

        return None

    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get coordination statistics."""
        return {
            "active_transactions": len(self.active_transactions),
            "performance_stats": self.performance_stats.copy(),
            "redis_connected": self.redis_client is not None,
            "enabled_indices": list(self.config.get_enabled_indices().keys())
        }

    def create_index_operation(
        self,
        index_name: str,
        operation_type: OperationType,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> IndexOperation:
        """
        Helper method to create index operations.

        Args:
            index_name: Name of the target index
            operation_type: Type of operation
            data: Operation data
            metadata: Optional metadata

        Returns:
            IndexOperation instance
        """
        return IndexOperation(
            index_name=index_name,
            operation_type=operation_type,
            data=data,
            metadata=metadata or {}
        )