"""
Core components for the multi-index system.

This module contains the fundamental building blocks:
- SmartQueryRouter: AI-powered query routing and intent recognition
- MultiIndexCoordinator: Data synchronization across multiple indices
- HealthMonitor: Real-time system monitoring and metrics
"""

from .query_router import SmartQueryRouter
from .coordinator import MultiIndexCoordinator
from .monitoring import HealthMonitor

__all__ = ["SmartQueryRouter", "MultiIndexCoordinator", "HealthMonitor"]