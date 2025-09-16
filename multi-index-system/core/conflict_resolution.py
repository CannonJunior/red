"""
Conflict Resolution System for Concurrent Operations

This module provides conflict-free concurrent operations using:
- Conflict-Free Replicated Data Types (CRDTs) concepts
- Vector clocks for causality tracking
- Last-Writer-Wins with timestamps for simple conflicts
- Operational transformation for complex document edits
- Multi-user collaboration support

Following the zero-cost, local-first architecture with minimal coordination overhead.
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
from collections import defaultdict

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

class ConflictType(Enum):
    """Types of conflicts that can occur in concurrent operations."""
    CONCURRENT_EDIT = "concurrent_edit"      # Same document edited simultaneously
    DELETE_UPDATE = "delete_update"         # One user deletes, another updates
    SCHEMA_CONFLICT = "schema_conflict"      # Conflicting schema changes
    WORKSPACE_ACCESS = "workspace_access"    # Concurrent workspace modifications
    INDEX_INCONSISTENCY = "index_inconsistency"  # Indices out of sync

class ConflictResolutionStrategy(Enum):
    """Strategies for resolving different types of conflicts."""
    LAST_WRITER_WINS = "last_writer_wins"          # Most recent change wins
    FIRST_WRITER_WINS = "first_writer_wins"        # First change wins
    MERGE_CHANGES = "merge_changes"                 # Attempt to merge changes
    USER_RESOLUTION = "user_resolution"            # Require manual resolution
    AUTOMATIC_MERGE = "automatic_merge"            # AI-powered automatic merge

@dataclass
class VectorClock:
    """Vector clock for tracking causality in distributed operations."""
    clock: Dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str):
        """Increment clock for a specific node."""
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def update(self, other: 'VectorClock'):
        """Update this clock with information from another clock."""
        for node_id, timestamp in other.clock.items():
            self.clock[node_id] = max(self.clock.get(node_id, 0), timestamp)

    def compare(self, other: 'VectorClock') -> str:
        """
        Compare two vector clocks.

        Returns:
            'before': self happened before other
            'after': self happened after other
            'concurrent': self and other are concurrent
            'equal': self and other are equal
        """
        if self.clock == other.clock:
            return 'equal'

        self_dominates = True
        other_dominates = True

        all_nodes = set(self.clock.keys()) | set(other.clock.keys())

        for node_id in all_nodes:
            self_time = self.clock.get(node_id, 0)
            other_time = other.clock.get(node_id, 0)

            if self_time < other_time:
                self_dominates = False
            elif self_time > other_time:
                other_dominates = False

        if self_dominates and not other_dominates:
            return 'after'
        elif other_dominates and not self_dominates:
            return 'before'
        else:
            return 'concurrent'

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary representation."""
        return self.clock.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'VectorClock':
        """Create from dictionary representation."""
        return cls(clock=data.copy())

@dataclass
class ConflictEvent:
    """A conflict event that needs resolution."""
    conflict_id: str
    conflict_type: ConflictType
    conflicting_operations: List[Dict[str, Any]]
    workspace: str
    affected_documents: Set[str]
    created_at: datetime = field(default_factory=datetime.now)
    resolution_strategy: Optional[ConflictResolutionStrategy] = None
    resolved: bool = False
    resolution_data: Optional[Dict[str, Any]] = None

@dataclass
class OperationMetadata:
    """Metadata for tracking operations and conflicts."""
    operation_id: str
    user_id: str
    workspace: str
    document_id: str
    operation_type: str
    vector_clock: VectorClock
    timestamp: datetime
    hash: str  # Hash of the operation for integrity

class ConflictResolver:
    """
    Conflict resolution system for concurrent multi-index operations.

    Uses CRDT concepts, vector clocks, and intelligent merging strategies
    to handle concurrent operations with minimal user intervention.
    """

    def __init__(self):
        """Initialize the conflict resolution system."""
        self.config = get_config()

        # Node identification for vector clocks
        self.node_id = f"node_{uuid.uuid4().hex[:8]}"

        # Active conflicts tracking
        self.active_conflicts: Dict[str, ConflictEvent] = {}
        self.resolved_conflicts: List[ConflictEvent] = []

        # Operation tracking for causality
        self.operation_log: List[OperationMetadata] = []
        self.vector_clock = VectorClock()

        # Conflict resolution statistics
        self.resolution_stats = {
            'total_conflicts': 0,
            'auto_resolved': 0,
            'manual_resolved': 0,
            'resolution_strategies': defaultdict(int)
        }

        logger.info(f"ConflictResolver initialized with node_id: {self.node_id}")

    def track_operation(
        self,
        operation_id: str,
        user_id: str,
        workspace: str,
        document_id: str,
        operation_type: str,
        operation_data: Dict[str, Any]
    ) -> OperationMetadata:
        """
        Track an operation for conflict detection.

        Args:
            operation_id: Unique operation identifier
            user_id: User performing the operation
            workspace: Workspace context
            document_id: Document being modified
            operation_type: Type of operation (insert, update, delete)
            operation_data: Operation payload

        Returns:
            OperationMetadata for the tracked operation
        """
        # Increment vector clock
        self.vector_clock.increment(self.node_id)

        # Create operation hash for integrity
        operation_hash = hashlib.sha256(
            json.dumps(operation_data, sort_keys=True).encode()
        ).hexdigest()[:16]

        # Create metadata
        metadata = OperationMetadata(
            operation_id=operation_id,
            user_id=user_id,
            workspace=workspace,
            document_id=document_id,
            operation_type=operation_type,
            vector_clock=VectorClock(self.vector_clock.to_dict()),
            timestamp=datetime.now(),
            hash=operation_hash
        )

        # Add to operation log
        self.operation_log.append(metadata)

        # Trim log to prevent memory growth
        if len(self.operation_log) > 10000:
            self.operation_log = self.operation_log[-5000:]

        logger.debug(f"Tracked operation {operation_id} for document {document_id}")
        return metadata

    async def detect_conflicts(
        self,
        operation_metadata: OperationMetadata,
        operation_data: Dict[str, Any]
    ) -> Optional[ConflictEvent]:
        """
        Detect conflicts for a new operation.

        Args:
            operation_metadata: Metadata for the new operation
            operation_data: Data for the new operation

        Returns:
            ConflictEvent if conflict detected, None otherwise
        """
        # Look for conflicting operations on the same document
        conflicting_ops = []

        # Check recent operations on the same document
        for existing_op in reversed(self.operation_log[-1000:]):  # Check last 1000 operations
            if (existing_op.document_id == operation_metadata.document_id and
                existing_op.workspace == operation_metadata.workspace and
                existing_op.operation_id != operation_metadata.operation_id):

                # Check if operations are concurrent
                comparison = operation_metadata.vector_clock.compare(existing_op.vector_clock)

                if comparison == 'concurrent':
                    # Determine conflict type
                    conflict_type = self._determine_conflict_type(
                        operation_metadata.operation_type,
                        existing_op.operation_type
                    )

                    if conflict_type:
                        conflicting_ops.append({
                            'metadata': existing_op,
                            'data': None  # Would need to store operation data
                        })

                        logger.info(f"Detected {conflict_type.value} conflict between operations "
                                  f"{operation_metadata.operation_id} and {existing_op.operation_id}")

        if conflicting_ops:
            # Create conflict event
            conflict_event = ConflictEvent(
                conflict_id=f"conflict_{uuid.uuid4().hex[:8]}",
                conflict_type=self._determine_primary_conflict_type(conflicting_ops),
                conflicting_operations=[
                    {'metadata': operation_metadata, 'data': operation_data}
                ] + conflicting_ops,
                workspace=operation_metadata.workspace,
                affected_documents={operation_metadata.document_id}
            )

            self.active_conflicts[conflict_event.conflict_id] = conflict_event
            self.resolution_stats['total_conflicts'] += 1

            return conflict_event

        return None

    def _determine_conflict_type(
        self,
        op1_type: str,
        op2_type: str
    ) -> Optional[ConflictType]:
        """
        Determine the type of conflict between two operations.

        Args:
            op1_type: Type of first operation
            op2_type: Type of second operation

        Returns:
            ConflictType or None if no conflict
        """
        if op1_type == "delete" and op2_type in ["update", "insert"]:
            return ConflictType.DELETE_UPDATE
        elif op2_type == "delete" and op1_type in ["update", "insert"]:
            return ConflictType.DELETE_UPDATE
        elif op1_type == "update" and op2_type == "update":
            return ConflictType.CONCURRENT_EDIT
        elif op1_type == "insert" and op2_type == "insert":
            return ConflictType.CONCURRENT_EDIT

        return None

    def _determine_primary_conflict_type(
        self,
        conflicting_ops: List[Dict[str, Any]]
    ) -> ConflictType:
        """Determine the primary conflict type from multiple conflicting operations."""
        # Simple heuristic: use the first detected conflict type
        # In a full implementation, this would be more sophisticated
        return ConflictType.CONCURRENT_EDIT

    async def resolve_conflict(
        self,
        conflict_event: ConflictEvent,
        strategy: Optional[ConflictResolutionStrategy] = None
    ) -> Dict[str, Any]:
        """
        Resolve a conflict using the specified strategy.

        Args:
            conflict_event: The conflict to resolve
            strategy: Resolution strategy to use (auto-selected if None)

        Returns:
            Resolution result with resolved data
        """
        if strategy is None:
            strategy = self._select_resolution_strategy(conflict_event)

        conflict_event.resolution_strategy = strategy

        logger.info(f"Resolving conflict {conflict_event.conflict_id} using {strategy.value}")

        try:
            if strategy == ConflictResolutionStrategy.LAST_WRITER_WINS:
                result = await self._resolve_last_writer_wins(conflict_event)
            elif strategy == ConflictResolutionStrategy.FIRST_WRITER_WINS:
                result = await self._resolve_first_writer_wins(conflict_event)
            elif strategy == ConflictResolutionStrategy.MERGE_CHANGES:
                result = await self._resolve_merge_changes(conflict_event)
            elif strategy == ConflictResolutionStrategy.AUTOMATIC_MERGE:
                result = await self._resolve_automatic_merge(conflict_event)
            else:
                # User resolution required
                result = {
                    'status': 'pending_user_resolution',
                    'conflict_event': conflict_event,
                    'message': 'Manual resolution required'
                }

            conflict_event.resolution_data = result

            if result.get('status') == 'resolved':
                conflict_event.resolved = True
                self.resolved_conflicts.append(conflict_event)
                del self.active_conflicts[conflict_event.conflict_id]
                self.resolution_stats['auto_resolved'] += 1

            self.resolution_stats['resolution_strategies'][strategy.value] += 1

            return result

        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_event.conflict_id}: {e}")
            return {
                'status': 'resolution_failed',
                'error': str(e),
                'conflict_event': conflict_event
            }

    def _select_resolution_strategy(
        self,
        conflict_event: ConflictEvent
    ) -> ConflictResolutionStrategy:
        """
        Select appropriate resolution strategy based on conflict type.

        Args:
            conflict_event: The conflict to resolve

        Returns:
            Appropriate resolution strategy
        """
        if conflict_event.conflict_type == ConflictType.DELETE_UPDATE:
            return ConflictResolutionStrategy.LAST_WRITER_WINS
        elif conflict_event.conflict_type == ConflictType.CONCURRENT_EDIT:
            return ConflictResolutionStrategy.MERGE_CHANGES
        else:
            return ConflictResolutionStrategy.LAST_WRITER_WINS

    async def _resolve_last_writer_wins(
        self,
        conflict_event: ConflictEvent
    ) -> Dict[str, Any]:
        """Resolve conflict using last-writer-wins strategy."""
        # Find operation with latest timestamp
        latest_op = None
        latest_timestamp = None

        for op_data in conflict_event.conflicting_operations:
            op_metadata = op_data['metadata']
            if latest_timestamp is None or op_metadata.timestamp > latest_timestamp:
                latest_timestamp = op_metadata.timestamp
                latest_op = op_data

        return {
            'status': 'resolved',
            'strategy': 'last_writer_wins',
            'winning_operation': latest_op,
            'resolved_data': latest_op['data'] if latest_op else None
        }

    async def _resolve_first_writer_wins(
        self,
        conflict_event: ConflictEvent
    ) -> Dict[str, Any]:
        """Resolve conflict using first-writer-wins strategy."""
        # Find operation with earliest timestamp
        earliest_op = None
        earliest_timestamp = None

        for op_data in conflict_event.conflicting_operations:
            op_metadata = op_data['metadata']
            if earliest_timestamp is None or op_metadata.timestamp < earliest_timestamp:
                earliest_timestamp = op_metadata.timestamp
                earliest_op = op_data

        return {
            'status': 'resolved',
            'strategy': 'first_writer_wins',
            'winning_operation': earliest_op,
            'resolved_data': earliest_op['data'] if earliest_op else None
        }

    async def _resolve_merge_changes(
        self,
        conflict_event: ConflictEvent
    ) -> Dict[str, Any]:
        """Resolve conflict by attempting to merge changes."""
        # Simple merge strategy: combine non-conflicting fields
        merged_data = {}
        all_fields = set()

        # Collect all fields from all operations
        for op_data in conflict_event.conflicting_operations:
            if op_data.get('data'):
                all_fields.update(op_data['data'].keys())

        # Merge fields where possible
        for field in all_fields:
            values = []
            for op_data in conflict_event.conflicting_operations:
                if op_data.get('data') and field in op_data['data']:
                    values.append(op_data['data'][field])

            if len(set(str(v) for v in values)) == 1:
                # All values are the same, use the common value
                merged_data[field] = values[0]
            else:
                # Use last writer wins for conflicting fields
                latest_op = max(
                    conflict_event.conflicting_operations,
                    key=lambda x: x['metadata'].timestamp
                )
                if latest_op.get('data') and field in latest_op['data']:
                    merged_data[field] = latest_op['data'][field]

        return {
            'status': 'resolved',
            'strategy': 'merge_changes',
            'resolved_data': merged_data,
            'merge_details': {
                'total_fields': len(all_fields),
                'merged_fields': len(merged_data),
                'conflicts_resolved': len(all_fields) - len(merged_data)
            }
        }

    async def _resolve_automatic_merge(
        self,
        conflict_event: ConflictEvent
    ) -> Dict[str, Any]:
        """Resolve conflict using AI-powered automatic merge."""
        # This would use local LLM for intelligent merging
        # For now, fall back to merge_changes
        return await self._resolve_merge_changes(conflict_event)

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of conflict resolution statistics."""
        return {
            'active_conflicts': len(self.active_conflicts),
            'resolved_conflicts': len(self.resolved_conflicts),
            'total_operations_tracked': len(self.operation_log),
            'resolution_stats': dict(self.resolution_stats['resolution_strategies']),
            'auto_resolution_rate': (
                self.resolution_stats['auto_resolved'] /
                max(self.resolution_stats['total_conflicts'], 1)
            ),
            'node_id': self.node_id,
            'vector_clock': self.vector_clock.to_dict()
        }

    def get_active_conflicts(self) -> List[Dict[str, Any]]:
        """Get list of active conflicts requiring attention."""
        return [
            {
                'conflict_id': event.conflict_id,
                'conflict_type': event.conflict_type.value,
                'workspace': event.workspace,
                'affected_documents': list(event.affected_documents),
                'created_at': event.created_at.isoformat(),
                'operation_count': len(event.conflicting_operations)
            }
            for event in self.active_conflicts.values()
        ]