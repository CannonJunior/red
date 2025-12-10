"""
Extraction strategies for MCP tools.

Pluggable strategies with automatic fall-through.
"""

from .base import (
    ExtractionStrategy,
    ExtractionResult,
    ExtractionResponse,
    ConfidenceLevel
)

__all__ = [
    "ExtractionStrategy",
    "ExtractionResult",
    "ExtractionResponse",
    "ConfidenceLevel",
]
