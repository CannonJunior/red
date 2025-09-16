"""
Advanced Index Implementations for Phase 2

This module provides concrete implementations of all index types:
- VectorIndex: ChromaDB-based vector storage and retrieval
- GraphIndex: Kùzu-based graph database for relationships
- MetadataIndex: DuckDB-based structured data storage
- FTSIndex: Full-text search with ranking
- TemporalIndex: Version control and temporal queries
- AdaptiveIndex: Machine learning-based index optimization

All indices support the common IndexInterface for coordinated operations.
"""

from .base import IndexInterface, IndexCapabilities
from .vector_index import VectorIndex
from .graph_index import GraphIndex
from .metadata_index import MetadataIndex
from .fts_index import FTSIndex
from .temporal_index import TemporalIndex
from .adaptive import AdaptiveIndexManager

__all__ = [
    "IndexInterface",
    "IndexCapabilities",
    "VectorIndex",
    "GraphIndex",
    "MetadataIndex",
    "FTSIndex",
    "TemporalIndex",
    "AdaptiveIndexManager"
]