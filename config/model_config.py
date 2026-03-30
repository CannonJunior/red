"""
AI Model Configuration.

All model selections are driven by environment variables so they can be
updated without code changes. Never hardcode model names in application logic.

Claude 4.6 model hierarchy (as of 2026-03-28):
    Primary (complex tasks): claude-sonnet-4-6
    Fast (batch/classify):   claude-haiku-4-5-20251001
    Local (zero-cost):       Ollama qwen2.5:3b (via OLLAMA_MODEL)

Usage:
    from config.model_config import get_model, ModelTier
    model = get_model(ModelTier.PRIMARY)
"""

import os
from enum import Enum
from typing import Dict


class ModelTier(str, Enum):
    """Model selection tiers by capability vs cost tradeoff."""
    PRIMARY = "primary"       # Best quality — Sonnet 4.6
    FAST = "fast"             # High throughput — Haiku 4.5
    LOCAL = "local"           # Zero cost — Ollama (private/offline)


# Default model IDs — override via environment variables
_DEFAULTS: Dict[str, str] = {
    "CLAUDE_MODEL_PRIMARY": "claude-sonnet-4-6",
    "CLAUDE_MODEL_FAST": "claude-haiku-4-5-20251001",
    "OLLAMA_MODEL": "qwen2.5:3b",
    "OLLAMA_MODEL_LARGE": "llama3.1",
}


def get_model(tier: ModelTier) -> str:
    """
    Get the model ID for a given tier from environment configuration.

    Args:
        tier: ModelTier enum value.

    Returns:
        str: Model ID string (e.g., "claude-sonnet-4-6").
    """
    env_map = {
        ModelTier.PRIMARY: "CLAUDE_MODEL_PRIMARY",
        ModelTier.FAST: "CLAUDE_MODEL_FAST",
        ModelTier.LOCAL: "OLLAMA_MODEL",
    }
    env_key = env_map[tier]
    return os.getenv(env_key, _DEFAULTS[env_key])


def get_thinking_config(budget_tokens: int = 8000) -> Dict:
    """
    Get extended thinking configuration for complex analysis tasks.

    Use for: bid/no-bid analysis, cost estimation, win strategy development.

    Args:
        budget_tokens: Maximum tokens for extended thinking (default 8000).
                       Range: 1024-32000. Higher = more thorough, slower.

    Returns:
        Dict: Thinking parameter block for Anthropic API.
    """
    return {
        "type": "enabled",
        "budget_tokens": budget_tokens,
    }


# Task-specific model recommendations
TASK_MODELS: Dict[str, str] = {
    "bid_no_bid_analysis": "primary",       # Strategic reasoning
    "document_drafting": "primary",          # High-quality prose
    "cost_estimation": "primary",            # Financial accuracy
    "meeting_synthesis": "primary",          # Structured output
    "opportunity_scoring": "fast",           # Batch classification
    "requirement_classification": "fast",    # High-volume tagging
    "template_filling": "fast",              # Structured slot-filling
    "local_draft": "local",                  # Zero-cost first draft
}


def get_task_model(task: str) -> str:
    """
    Get the recommended model for a specific task type.

    Args:
        task: Task name from TASK_MODELS keys.

    Returns:
        str: Model ID string.
    """
    tier_name = TASK_MODELS.get(task, "fast")
    tier = ModelTier(tier_name)
    return get_model(tier)
