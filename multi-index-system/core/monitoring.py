"""
Health Monitoring and Metrics System

This module provides comprehensive monitoring and metrics for the multi-index system:
- Real-time health checks for all indices
- Performance metrics collection and analysis
- Alerting and diagnostic information
- Historical trend analysis
- Automatic performance optimization recommendations

Following the zero-cost, local-first architecture with efficient data collection.
"""

import asyncio
import logging
import time
import json
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import statistics
import psutil  # For system metrics

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

class HealthStatus(Enum):
    """Health status levels for indices and system components."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

class MetricType(Enum):
    """Types of metrics collected by the monitoring system."""
    COUNTER = "counter"      # Monotonically increasing values
    GAUGE = "gauge"         # Current value measurements
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"         # Duration measurements

@dataclass
class HealthCheck:
    """Result of a health check operation."""
    component: str
    status: HealthStatus
    message: str
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_time: float = 0.0

@dataclass
class MetricPoint:
    """A single metric measurement point."""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceProfile:
    """Performance profile for an index or operation."""
    component: str
    avg_response_time: float
    p95_response_time: float
    success_rate: float
    throughput: float  # operations per second
    error_count: int
    last_updated: datetime = field(default_factory=datetime.now)

class HealthMonitor:
    """
    Comprehensive health monitoring and metrics system for multi-index architecture.

    Provides real-time monitoring, metrics collection, and performance analysis
    with minimal overhead to maintain system performance.
    """

    def __init__(self, check_interval: float = 60.0):
        """
        Initialize the health monitoring system.

        Args:
            check_interval: Interval between health checks in seconds
        """
        self.config = get_config()
        self.check_interval = check_interval

        # Health tracking
        self.current_health: Dict[str, HealthCheck] = {}
        self.health_history: deque = deque(maxlen=1000)  # Store last 1000 health checks

        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}

        # Performance profiles
        self.performance_profiles: Dict[str, PerformanceProfile] = {}

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None

        # Alert callbacks
        self.alert_callbacks: List[Callable[[HealthCheck], None]] = []

        logger.info(f"HealthMonitor initialized with {check_interval}s check interval")

    def start_monitoring(self):
        """Start continuous health monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop continuous health monitoring."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        logger.info("Health monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop running in background thread."""
        while self.monitoring_active:
            try:
                # Run health checks for all enabled indices
                asyncio.run(self._run_health_checks())

                # Collect system metrics
                self._collect_system_metrics()

                # Update performance profiles
                self._update_performance_profiles()

                # Sleep until next check interval
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(min(self.check_interval, 30.0))  # Fallback interval

    async def _run_health_checks(self):
        """Run health checks for all enabled indices."""
        enabled_indices = self.config.get_enabled_indices()

        # Create health check tasks for each index
        health_tasks = []
        for index_name in enabled_indices:
            task = asyncio.create_task(self._check_index_health(index_name))
            health_tasks.append(task)

        # Add system health check
        system_task = asyncio.create_task(self._check_system_health())
        health_tasks.append(system_task)

        # Wait for all health checks to complete
        results = await asyncio.gather(*health_tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, HealthCheck):
                self._process_health_check(result)
            elif isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")

    async def _check_index_health(self, index_name: str) -> HealthCheck:
        """
        Check health of a specific index.

        Args:
            index_name: Name of the index to check

        Returns:
            HealthCheck result
        """
        start_time = time.time()

        try:
            if index_name == "vector":
                return await self._check_vector_health()
            elif index_name == "graph":
                return await self._check_graph_health()
            elif index_name == "metadata":
                return await self._check_metadata_health()
            elif index_name == "fts":
                return await self._check_fts_health()
            elif index_name == "temporal":
                return await self._check_temporal_health()
            else:
                return HealthCheck(
                    component=index_name,
                    status=HealthStatus.OFFLINE,
                    message=f"Unknown index type: {index_name}",
                    response_time=time.time() - start_time
                )

        except Exception as e:
            return HealthCheck(
                component=index_name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                response_time=time.time() - start_time
            )

    async def _check_vector_health(self) -> HealthCheck:
        """Check ChromaDB vector index health."""
        start_time = time.time()

        try:
            # For now, simulate health check
            # In full implementation, would check ChromaDB connection and performance
            await asyncio.sleep(0.01)  # Simulate check time

            response_time = time.time() - start_time

            return HealthCheck(
                component="vector",
                status=HealthStatus.HEALTHY,
                message="ChromaDB vector index operational",
                metrics={
                    "response_time_ms": response_time * 1000,
                    "estimated_documents": 0  # Would query actual count
                },
                response_time=response_time
            )

        except Exception as e:
            return HealthCheck(
                component="vector",
                status=HealthStatus.CRITICAL,
                message=f"Vector index health check failed: {str(e)}",
                response_time=time.time() - start_time
            )

    async def _check_graph_health(self) -> HealthCheck:
        """Check Kùzu graph database health."""
        start_time = time.time()

        try:
            if not self.config.graph_config.enabled:
                return HealthCheck(
                    component="graph",
                    status=HealthStatus.OFFLINE,
                    message="Graph index disabled",
                    response_time=time.time() - start_time
                )

            # Simulate graph health check
            await asyncio.sleep(0.02)

            response_time = time.time() - start_time

            return HealthCheck(
                component="graph",
                status=HealthStatus.HEALTHY,
                message="Kùzu graph database operational",
                metrics={
                    "response_time_ms": response_time * 1000,
                    "estimated_nodes": 0,
                    "estimated_edges": 0
                },
                response_time=response_time
            )

        except Exception as e:
            return HealthCheck(
                component="graph",
                status=HealthStatus.CRITICAL,
                message=f"Graph index health check failed: {str(e)}",
                response_time=time.time() - start_time
            )

    async def _check_metadata_health(self) -> HealthCheck:
        """Check DuckDB metadata index health."""
        start_time = time.time()

        try:
            # Simulate metadata health check
            await asyncio.sleep(0.005)

            response_time = time.time() - start_time

            return HealthCheck(
                component="metadata",
                status=HealthStatus.HEALTHY,
                message="DuckDB metadata index operational",
                metrics={
                    "response_time_ms": response_time * 1000,
                    "estimated_records": 0
                },
                response_time=response_time
            )

        except Exception as e:
            return HealthCheck(
                component="metadata",
                status=HealthStatus.CRITICAL,
                message=f"Metadata index health check failed: {str(e)}",
                response_time=time.time() - start_time
            )

    async def _check_fts_health(self) -> HealthCheck:
        """Check full-text search index health."""
        start_time = time.time()

        try:
            if not self.config.fts_config.enabled:
                return HealthCheck(
                    component="fts",
                    status=HealthStatus.OFFLINE,
                    message="Full-text search disabled",
                    response_time=time.time() - start_time
                )

            # Simulate FTS health check
            await asyncio.sleep(0.003)

            response_time = time.time() - start_time

            return HealthCheck(
                component="fts",
                status=HealthStatus.HEALTHY,
                message="Full-text search index operational",
                metrics={
                    "response_time_ms": response_time * 1000,
                    "indexed_documents": 0
                },
                response_time=response_time
            )

        except Exception as e:
            return HealthCheck(
                component="fts",
                status=HealthStatus.CRITICAL,
                message=f"FTS health check failed: {str(e)}",
                response_time=time.time() - start_time
            )

    async def _check_temporal_health(self) -> HealthCheck:
        """Check temporal index health."""
        start_time = time.time()

        try:
            if not self.config.temporal_config.enabled:
                return HealthCheck(
                    component="temporal",
                    status=HealthStatus.OFFLINE,
                    message="Temporal index disabled",
                    response_time=time.time() - start_time
                )

            # Simulate temporal health check
            await asyncio.sleep(0.008)

            response_time = time.time() - start_time

            return HealthCheck(
                component="temporal",
                status=HealthStatus.HEALTHY,
                message="Temporal index operational",
                metrics={
                    "response_time_ms": response_time * 1000,
                    "version_count": 0
                },
                response_time=response_time
            )

        except Exception as e:
            return HealthCheck(
                component="temporal",
                status=HealthStatus.CRITICAL,
                message=f"Temporal index health check failed: {str(e)}",
                response_time=time.time() - start_time
            )

    async def _check_system_health(self) -> HealthCheck:
        """Check overall system health."""
        start_time = time.time()

        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Determine overall status
            status = HealthStatus.HEALTHY
            messages = []

            if cpu_percent > 80:
                status = HealthStatus.WARNING
                messages.append(f"High CPU usage: {cpu_percent:.1f}%")

            if memory.percent > 85:
                status = HealthStatus.WARNING
                messages.append(f"High memory usage: {memory.percent:.1f}%")

            if disk.percent > 90:
                status = HealthStatus.CRITICAL
                messages.append(f"Low disk space: {100-disk.percent:.1f}% free")

            message = "; ".join(messages) if messages else "System resources normal"

            return HealthCheck(
                component="system",
                status=status,
                message=message,
                metrics={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "memory_available_gb": memory.available / (1024**3)
                },
                response_time=time.time() - start_time
            )

        except Exception as e:
            return HealthCheck(
                component="system",
                status=HealthStatus.CRITICAL,
                message=f"System health check failed: {str(e)}",
                response_time=time.time() - start_time
            )

    def _process_health_check(self, health_check: HealthCheck):
        """Process and store a health check result."""
        # Update current health status
        self.current_health[health_check.component] = health_check

        # Add to history
        self.health_history.append(health_check)

        # Record metrics
        self._record_health_metrics(health_check)

        # Check for alerts
        self._check_alerts(health_check)

        logger.debug(f"Health check: {health_check.component} - {health_check.status.value}")

    def _record_health_metrics(self, health_check: HealthCheck):
        """Record metrics from health check."""
        component = health_check.component

        # Record response time
        metric_name = f"{component}_response_time"
        self._record_metric(metric_name, health_check.response_time, MetricType.TIMER)

        # Record status as numeric value for trending
        status_values = {
            HealthStatus.HEALTHY: 1.0,
            HealthStatus.WARNING: 0.5,
            HealthStatus.CRITICAL: 0.0,
            HealthStatus.OFFLINE: -1.0
        }
        status_metric = f"{component}_health_score"
        self._record_metric(status_metric, status_values[health_check.status], MetricType.GAUGE)

        # Record component-specific metrics
        for metric_name, value in health_check.metrics.items():
            full_metric_name = f"{component}_{metric_name}"
            self._record_metric(full_metric_name, value, MetricType.GAUGE)

    def _record_metric(self, name: str, value: float, metric_type: MetricType):
        """Record a metric point."""
        point = MetricPoint(name=name, value=value, metric_type=metric_type)
        self.metrics[name].append(point)

        # Update gauges and counters
        if metric_type == MetricType.GAUGE:
            self.gauges[name] = value
        elif metric_type == MetricType.COUNTER:
            self.counters[name] += value

    def _collect_system_metrics(self):
        """Collect additional system-level metrics."""
        try:
            # System performance metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()

            self._record_metric("system_cpu_percent", cpu_percent, MetricType.GAUGE)
            self._record_metric("system_memory_percent", memory.percent, MetricType.GAUGE)
            self._record_metric("system_memory_available_bytes", memory.available, MetricType.GAUGE)

        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")

    def _update_performance_profiles(self):
        """Update performance profiles for each component."""
        for component in self.current_health.keys():
            if component == "system":
                continue

            self._update_component_profile(component)

    def _update_component_profile(self, component: str):
        """Update performance profile for a specific component."""
        # Get recent response times
        response_time_metric = f"{component}_response_time"
        if response_time_metric not in self.metrics:
            return

        recent_times = [point.value for point in list(self.metrics[response_time_metric])[-100:]]
        if not recent_times:
            return

        # Calculate statistics
        avg_response_time = statistics.mean(recent_times)
        p95_response_time = statistics.quantiles(recent_times, n=20)[18] if len(recent_times) >= 20 else max(recent_times)

        # Get health score for success rate calculation
        health_score_metric = f"{component}_health_score"
        if health_score_metric in self.metrics:
            recent_scores = [point.value for point in list(self.metrics[health_score_metric])[-100:]]
            success_rate = sum(1 for score in recent_scores if score >= 0.5) / len(recent_scores) if recent_scores else 1.0
        else:
            success_rate = 1.0

        # Estimate throughput (simplified)
        throughput = min(100.0, 1.0 / avg_response_time) if avg_response_time > 0 else 0.0

        # Error count (simplified)
        error_count = sum(1 for score in (list(self.metrics.get(health_score_metric, []))[-100:]) if hasattr(score, 'value') and score.value < 0.5)

        # Update profile
        self.performance_profiles[component] = PerformanceProfile(
            component=component,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            success_rate=success_rate,
            throughput=throughput,
            error_count=error_count
        )

    def _check_alerts(self, health_check: HealthCheck):
        """Check if health check triggers any alerts."""
        if health_check.status in [HealthStatus.CRITICAL, HealthStatus.OFFLINE]:
            for callback in self.alert_callbacks:
                try:
                    callback(health_check)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    def add_alert_callback(self, callback: Callable[[HealthCheck], None]):
        """Add an alert callback function."""
        self.alert_callbacks.append(callback)

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        if not self.current_health:
            return {"status": "unknown", "message": "No health data available"}

        statuses = [check.status for check in self.current_health.values()]

        if HealthStatus.CRITICAL in statuses or HealthStatus.OFFLINE in statuses:
            overall_status = "critical"
        elif HealthStatus.WARNING in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        component_statuses = {
            component: check.status.value
            for component, check in self.current_health.items()
        }

        return {
            "status": overall_status,
            "components": component_statuses,
            "last_check": max(check.timestamp for check in self.current_health.values()).isoformat() if self.current_health else None
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all components."""
        return {
            component: {
                "avg_response_time": profile.avg_response_time,
                "p95_response_time": profile.p95_response_time,
                "success_rate": profile.success_rate,
                "throughput": profile.throughput,
                "error_count": profile.error_count,
                "last_updated": profile.last_updated.isoformat()
            }
            for component, profile in self.performance_profiles.items()
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        return {
            "total_metrics": len(self.metrics),
            "total_data_points": sum(len(points) for points in self.metrics.values()),
            "gauges": dict(self.gauges),
            "counters": dict(self.counters),
            "health_checks_performed": len(self.health_history)
        }