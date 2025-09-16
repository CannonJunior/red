"""
Base Interface for All Index Types

Defines the common interface that all indices must implement for
coordinated multi-index operations, health monitoring, and optimization.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class IndexCapabilities(Enum):
    """Capabilities that an index can support."""
    SEMANTIC_SEARCH = "semantic_search"
    EXACT_MATCH = "exact_match"
    RANGE_QUERIES = "range_queries"
    FULL_TEXT_SEARCH = "full_text_search"
    GRAPH_TRAVERSAL = "graph_traversal"
    TEMPORAL_QUERIES = "temporal_queries"
    AGGREGATION = "aggregation"
    FUZZY_MATCHING = "fuzzy_matching"

@dataclass
class QueryResult:
    """Result from an index query operation."""
    documents: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    total_found: int
    execution_time: float
    index_used: str
    confidence_scores: Optional[List[float]] = None

@dataclass
class IndexStats:
    """Statistics about an index's performance and state."""
    document_count: int
    storage_size_bytes: int
    avg_query_time: float
    total_queries: int
    last_updated: datetime
    health_status: str
    capabilities: Set[IndexCapabilities]

class IndexInterface(ABC):
    """
    Abstract base class for all index implementations.

    Provides a common interface for operations across vector, graph,
    metadata, FTS, and temporal indices.
    """

    def __init__(self, index_name: str, data_path: str, config: Dict[str, Any]):
        """
        Initialize the index.

        Args:
            index_name: Unique name for this index
            data_path: Path to store index data
            config: Index-specific configuration
        """
        self.index_name = index_name
        self.data_path = data_path
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{index_name}")

        # Performance tracking
        self.query_count = 0
        self.total_query_time = 0.0
        self.last_query_time: Optional[datetime] = None

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the index and its underlying storage.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """Gracefully shutdown the index."""
        pass

    @abstractmethod
    async def insert(self, documents: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """
        Insert documents into the index.

        Args:
            documents: List of documents to insert
            workspace: Workspace context

        Returns:
            Result dictionary with status and metrics
        """
        pass

    @abstractmethod
    async def update(self, document_updates: List[Dict[str, Any]], workspace: str = "default") -> Dict[str, Any]:
        """
        Update existing documents in the index.

        Args:
            document_updates: List of document updates (must include id)
            workspace: Workspace context

        Returns:
            Result dictionary with status and metrics
        """
        pass

    @abstractmethod
    async def delete(self, document_ids: List[str], workspace: str = "default") -> Dict[str, Any]:
        """
        Delete documents from the index.

        Args:
            document_ids: List of document IDs to delete
            workspace: Workspace context

        Returns:
            Result dictionary with status and metrics
        """
        pass

    @abstractmethod
    async def query(self, query_params: Dict[str, Any], workspace: str = "default") -> QueryResult:
        """
        Execute a query against the index.

        Args:
            query_params: Query parameters (index-specific format)
            workspace: Workspace context

        Returns:
            QueryResult with documents and metadata
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the index.

        Returns:
            Health status and metrics
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Set[IndexCapabilities]:
        """
        Get the capabilities supported by this index.

        Returns:
            Set of supported capabilities
        """
        pass

    @abstractmethod
    async def optimize(self) -> Dict[str, Any]:
        """
        Optimize the index for better performance.

        Returns:
            Optimization results and metrics
        """
        pass

    @abstractmethod
    async def get_stats(self) -> IndexStats:
        """
        Get comprehensive statistics about the index.

        Returns:
            IndexStats with current metrics
        """
        pass

    # Common utility methods

    def _track_query_performance(self, execution_time: float):
        """Track query performance metrics."""
        self.query_count += 1
        self.total_query_time += execution_time
        self.last_query_time = datetime.now()

    def get_avg_query_time(self) -> float:
        """Get average query execution time."""
        if self.query_count == 0:
            return 0.0
        return self.total_query_time / self.query_count

    async def supports_capability(self, capability: IndexCapabilities) -> bool:
        """Check if index supports a specific capability."""
        return capability in self.get_capabilities()

    def _validate_workspace(self, workspace: str) -> str:
        """Validate and normalize workspace name."""
        if not workspace or not workspace.strip():
            return "default"
        return workspace.strip().lower()

    def _prepare_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare documents for insertion (add timestamps, validate)."""
        prepared = []
        for doc in documents:
            if not isinstance(doc, dict):
                self.logger.warning(f"Skipping non-dict document: {type(doc)}")
                continue

            # Ensure document has an ID
            if 'id' not in doc:
                import hashlib
                import json
                doc_str = json.dumps(doc, sort_keys=True)
                doc['id'] = hashlib.md5(doc_str.encode()).hexdigest()[:16]

            # Add metadata
            if '_indexed_at' not in doc:
                doc['_indexed_at'] = datetime.now().isoformat()

            prepared.append(doc)

        return prepared

class BaseIndexError(Exception):
    """Base exception for index-related errors."""
    pass

class IndexNotInitializedError(BaseIndexError):
    """Raised when attempting to use an uninitialized index."""
    pass

class QueryExecutionError(BaseIndexError):
    """Raised when query execution fails."""
    pass

class DocumentValidationError(BaseIndexError):
    """Raised when document validation fails."""
    pass