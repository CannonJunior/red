"""
Base classes for extraction strategies.

Defines interface for all extraction strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence level for extracted data"""
    HIGH = "high"      # 80-100%
    MEDIUM = "medium"  # 50-79%
    LOW = "low"        # 0-49%
    UNKNOWN = "unknown"


@dataclass
class ExtractionResult:
    """Result of data extraction for a single placeholder"""
    placeholder: str
    value: str
    confidence: ConfidenceLevel
    source: Optional[str] = None  # Source location (doc name, section)
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExtractionResponse:
    """Response from extraction strategy"""
    results: Dict[str, ExtractionResult]  # {placeholder_name: ExtractionResult}
    strategy_name: str
    success: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def get_value(self, placeholder: str, default: str = "") -> str:
        """Get extracted value for placeholder"""
        result = self.results.get(placeholder)
        return result.value if result else default

    def get_confidence(self, placeholder: str) -> ConfidenceLevel:
        """Get confidence level for placeholder"""
        result = self.results.get(placeholder)
        return result.confidence if result else ConfidenceLevel.UNKNOWN


class ExtractionStrategy(ABC):
    """
    Abstract base class for extraction strategies.

    Strategies extract data from documents to fill template placeholders.
    Each strategy implements a different approach (LLM, keyword matching, etc.)
    """

    def __init__(self, config=None):
        """
        Initialize strategy.

        Args:
            config: MCPToolConfig instance
        """
        from ..config import get_config
        self.config = config or get_config()

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name (e.g., 'llm_smart', 'keyword_matching')"""
        pass

    @property
    def priority(self) -> int:
        """
        Priority for fall-through chain (lower = higher priority).

        Default priorities:
        - Manual mapping: 0 (highest)
        - LLM structured: 10
        - LLM smart: 20
        - Keyword matching: 30 (lowest)
        """
        return 50

    @abstractmethod
    async def extract(
        self,
        documents: str,
        placeholders: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResponse:
        """
        Extract data for placeholders from documents.

        Args:
            documents: Combined document text
            placeholders: List of placeholder names to extract
            context: Optional context (e.g., template type, user hints)

        Returns:
            ExtractionResponse with results
        """
        pass

    def can_handle(self, placeholders: List[str]) -> bool:
        """
        Check if strategy can handle these placeholders.

        Default: Can handle any placeholders.
        Override for strategies with specific requirements.
        """
        return True
