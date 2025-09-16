"""
Smart Query Router with Intent Recognition

This module provides intelligent query routing across multiple indices based on:
- Query intent analysis using local LLM
- Performance characteristics of different indices
- Data availability and freshness
- User context and preferences

Following the zero-cost, local-first philosophy with Ollama integration.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import re

# Import existing components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from ollama_config import ollama_config

# Try relative import first, fallback to absolute
try:
    from ..config.settings import get_config
except ImportError:
    from config.settings import get_config

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Types of query intents that can be detected."""
    SEMANTIC_SEARCH = "semantic_search"      # Vector similarity search
    RELATIONSHIP_QUERY = "relationship"      # Graph traversal queries
    FACTUAL_LOOKUP = "factual"              # Metadata/structured queries
    FULL_TEXT_SEARCH = "full_text"          # Text-based search
    TEMPORAL_QUERY = "temporal"             # Time-based or version queries
    ANALYTICAL = "analytical"               # Analysis and insights queries
    BROWSE = "browse"                       # Browse and exploration queries
    HYBRID = "hybrid"                       # Requires multiple indices
    UNKNOWN = "unknown"

@dataclass
class QueryContext:
    """Context information for query routing decisions."""
    user_id: Optional[str] = None
    workspace: str = "default"
    previous_queries: List[str] = None
    preferred_indices: Set[str] = None
    response_time_preference: str = "balanced"  # "fast", "balanced", "comprehensive"

    def __post_init__(self):
        if self.previous_queries is None:
            self.previous_queries = []
        if self.preferred_indices is None:
            self.preferred_indices = set()

@dataclass
class RouteDecision:
    """Routing decision with reasoning and execution plan."""
    primary_index: str
    secondary_indices: List[str]
    intent: QueryIntent
    confidence: float
    reasoning: str
    estimated_time: float
    fallback_strategy: Optional[str] = None

class SmartQueryRouter:
    """
    AI-powered query router that analyzes intent and routes to optimal indices.

    Uses local Ollama LLM for intent recognition to maintain zero-cost architecture.
    """

    def __init__(self):
        """Initialize the smart query router."""
        self.config = get_config()
        self.query_patterns = self._build_query_patterns()
        self.performance_cache = {}  # Cache performance metrics for routing decisions
        self.intent_cache = {}       # Cache intent classifications

        # Initialize Ollama for intent recognition
        self.ollama_client = ollama_config
        self.intent_model = self._select_intent_model()

        logger.info("SmartQueryRouter initialized")

    def _select_intent_model(self) -> str:
        """Select the best available model for intent recognition."""
        # Use the same logic as the RAG system for model selection
        connection_test = self.ollama_client.test_connection()

        if connection_test['connected'] and connection_test['models']:
            available_models = connection_test['models']

            # Prefer smaller, faster models for intent recognition
            preferred_models = ["qwen2.5:1.5b", "qwen2.5:3b", "llama3.1:8b"]

            for model in preferred_models:
                if model in available_models:
                    logger.info(f"Selected intent recognition model: {model}")
                    return model

            # Use first available model
            model = available_models[0]
            logger.info(f"Using first available model for intent recognition: {model}")
            return model

        # Fallback
        logger.warning("No Ollama models available, using fallback intent recognition")
        return "qwen2.5:3b"

    def _build_query_patterns(self) -> Dict[QueryIntent, List[str]]:
        """Build regex patterns for quick intent classification."""
        return {
            QueryIntent.SEMANTIC_SEARCH: [
                r"what\s+is|explain|describe|similar\s+to|like|meaning",
                r"find\s+.*\s+about|search\s+for|related\s+to"
            ],
            QueryIntent.RELATIONSHIP_QUERY: [
                r"how\s+.*\s+connected|relationship|links?\s+between",
                r"connected\s+to|related\s+entities|graph|network"
            ],
            QueryIntent.FACTUAL_LOOKUP: [
                r"count|how\s+many|total|sum|average|max|min",
                r"when\s+was|who\s+is|where\s+is|list\s+all"
            ],
            QueryIntent.FULL_TEXT_SEARCH: [
                r"contains?|includes?|mentions?|text\s+.*\s+saying",
                r"exact\s+phrase|quote|\".*\""
            ],
            QueryIntent.TEMPORAL_QUERY: [
                r"when|before|after|since|until|history|changes",
                r"version|updated|modified|created|timeline"
            ]
        }

    async def route_query(self, query: str, context: Optional[QueryContext] = None) -> RouteDecision:
        """
        Route a query to the optimal index combination.

        Args:
            query: The user query to route
            context: Additional context for routing decisions

        Returns:
            RouteDecision with routing plan and reasoning
        """
        start_time = time.time()

        if context is None:
            context = QueryContext()

        # Step 1: Quick pattern-based intent detection
        pattern_intent = self._classify_by_patterns(query)

        # Step 2: AI-powered intent analysis (if patterns are uncertain)
        if pattern_intent == QueryIntent.UNKNOWN:
            ai_intent = await self._classify_with_ai(query)
        else:
            ai_intent = pattern_intent

        # Step 3: Select optimal indices based on intent and context
        routing_decision = self._select_indices(query, ai_intent, context)

        # Step 4: Add performance estimates
        routing_decision.estimated_time = self._estimate_query_time(routing_decision)

        processing_time = time.time() - start_time
        logger.info(f"Query routed in {processing_time:.3f}s: {ai_intent.value} -> {routing_decision.primary_index}")

        return routing_decision

    def _classify_by_patterns(self, query: str) -> QueryIntent:
        """Quick pattern-based classification for common query types."""
        query_lower = query.lower()

        for intent, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        return QueryIntent.UNKNOWN

    async def _classify_with_ai(self, query: str) -> QueryIntent:
        """Use AI to classify query intent when patterns are insufficient."""
        # Check cache first
        cache_key = hash(query.lower())
        if cache_key in self.intent_cache:
            return self.intent_cache[cache_key]

        prompt = f"""Analyze this user query and classify its intent. Respond with only one word from this list:
semantic_search, relationship, factual, full_text, temporal, hybrid

Query: "{query}"

Classification:"""

        try:
            messages = [{"role": "user", "content": prompt}]
            result = self.ollama_client.chat_response(self.intent_model, messages)

            if result['success']:
                response = result['data']['message']['content'].strip().lower()

                # Map response to QueryIntent
                intent_mapping = {
                    'semantic_search': QueryIntent.SEMANTIC_SEARCH,
                    'relationship': QueryIntent.RELATIONSHIP_QUERY,
                    'factual': QueryIntent.FACTUAL_LOOKUP,
                    'full_text': QueryIntent.FULL_TEXT_SEARCH,
                    'temporal': QueryIntent.TEMPORAL_QUERY,
                    'hybrid': QueryIntent.HYBRID
                }

                intent = intent_mapping.get(response, QueryIntent.SEMANTIC_SEARCH)

                # Cache the result
                self.intent_cache[cache_key] = intent

                return intent
            else:
                logger.warning(f"AI intent classification failed: {result['error']}")
                return QueryIntent.SEMANTIC_SEARCH

        except Exception as e:
            logger.error(f"Error in AI intent classification: {e}")
            return QueryIntent.SEMANTIC_SEARCH

    def _select_indices(self, query: str, intent: QueryIntent, context: QueryContext) -> RouteDecision:
        """Select the optimal combination of indices based on intent and context."""
        enabled_indices = self.config.get_enabled_indices()

        # Intent-based routing logic
        if intent == QueryIntent.SEMANTIC_SEARCH:
            primary = "vector"
            secondary = ["metadata"] if "metadata" in enabled_indices else []
            reasoning = "Vector search for semantic similarity"

        elif intent == QueryIntent.RELATIONSHIP_QUERY:
            if "graph" in enabled_indices:
                primary = "graph"
                secondary = ["vector"]
                reasoning = "Graph traversal for relationship queries"
            else:
                primary = "vector"
                secondary = ["metadata"]
                reasoning = "Graph index disabled, using vector with metadata fallback"

        elif intent == QueryIntent.FACTUAL_LOOKUP:
            primary = "metadata"
            secondary = ["vector"] if context.response_time_preference != "fast" else []
            reasoning = "Structured data lookup for factual queries"

        elif intent == QueryIntent.FULL_TEXT_SEARCH:
            if "fts" in enabled_indices:
                primary = "fts"
                secondary = ["vector"]
                reasoning = "Full-text search with semantic fallback"
            else:
                primary = "vector"
                secondary = []
                reasoning = "FTS disabled, using vector search"

        elif intent == QueryIntent.TEMPORAL_QUERY:
            if "temporal" in enabled_indices:
                primary = "temporal"
                secondary = ["metadata", "vector"]
                reasoning = "Temporal index for time-based queries"
            else:
                primary = "metadata"
                secondary = ["vector"]
                reasoning = "Temporal index disabled, using metadata with vector fallback"

        elif intent == QueryIntent.HYBRID:
            primary = "vector"
            secondary = [idx for idx in ["graph", "metadata", "fts"] if idx in enabled_indices]
            reasoning = "Multi-index approach for complex queries"

        else:  # UNKNOWN
            primary = "vector"
            secondary = ["metadata"]
            reasoning = "Default vector search with metadata support"

        # Apply user preferences
        if context.preferred_indices:
            available_preferred = context.preferred_indices.intersection(enabled_indices.keys())
            if available_preferred and primary not in available_preferred:
                original_primary = primary
                primary = list(available_preferred)[0]
                reasoning += f" (switched from {original_primary} due to user preference)"

        # Confidence scoring based on multiple factors
        confidence = self._calculate_confidence(query, intent, primary, enabled_indices)

        return RouteDecision(
            primary_index=primary,
            secondary_indices=secondary,
            intent=intent,
            confidence=confidence,
            reasoning=reasoning,
            estimated_time=0.0,  # Will be filled in later
            fallback_strategy="vector" if primary != "vector" else "metadata"
        )

    def _calculate_confidence(self, query: str, intent: QueryIntent, primary_index: str, enabled_indices: Dict) -> float:
        """Calculate confidence score for routing decision."""
        base_confidence = 0.8

        # Higher confidence for exact pattern matches
        if self._classify_by_patterns(query) == intent:
            base_confidence += 0.1

        # Lower confidence if primary index is disabled
        if primary_index not in enabled_indices:
            base_confidence -= 0.3

        # Adjust based on query complexity
        if len(query.split()) > 10:  # Complex query
            base_confidence -= 0.1

        return max(0.1, min(1.0, base_confidence))

    def _estimate_query_time(self, decision: RouteDecision) -> float:
        """Estimate query execution time based on routing decision."""
        base_times = {
            "vector": 0.05,    # 50ms for vector search
            "graph": 0.1,      # 100ms for graph traversal
            "metadata": 0.03,  # 30ms for structured queries
            "fts": 0.02,       # 20ms for full-text search
            "temporal": 0.08   # 80ms for temporal queries
        }

        primary_time = base_times.get(decision.primary_index, 0.05)
        secondary_time = sum(base_times.get(idx, 0.02) for idx in decision.secondary_indices) * 0.5

        return primary_time + secondary_time

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about query routing performance."""
        return {
            "cache_size": len(self.intent_cache),
            "performance_cache_size": len(self.performance_cache),
            "enabled_indices": list(self.config.get_enabled_indices().keys()),
            "intent_model": self.intent_model
        }

    def clear_cache(self):
        """Clear routing caches."""
        self.intent_cache.clear()
        self.performance_cache.clear()
        logger.info("Query router caches cleared")