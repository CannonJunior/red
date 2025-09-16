"""
Multi-Index Knowledge Base System

A sophisticated multi-index architecture for enhanced data retrieval,
relationship modeling, and collaborative data sharing with agent-native interfaces.

Components:
- Smart Query Router with intent recognition
- Multi-index coordinator for data synchronization
- Graph database integration (Kùzu)
- Observable D3 visualizations
- MCP agent interface layer
- Health monitoring and metrics
"""

__version__ = "1.0.0"
__author__ = "Claude Code"

from .core.query_router import SmartQueryRouter
from .core.coordinator import MultiIndexCoordinator
from .core.monitoring import HealthMonitor

__all__ = [
    "SmartQueryRouter",
    "MultiIndexCoordinator",
    "HealthMonitor"
]