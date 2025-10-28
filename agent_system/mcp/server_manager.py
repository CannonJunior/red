"""
Zero-Cost MCP Server Manager for Agent-Native RAG System.

This module implements the RED-aligned MCP server lifecycle management with:
- COST-FIRST: $0 operational expenses through localhost-only services
- AGENT-NATIVE: MCP interfaces for AI agent orchestration
- LOCAL-FIRST: Complete localhost deployment with no external dependencies
- SIMPLE-SCALE: Optimized for 5 users
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import redis

# Import path utilities for dynamic project root resolution
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from project_paths import get_project_root, expand_path_variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """RED-aligned MCP server configuration."""
    server_id: str
    server_type: str = "mcp"
    connection: Dict[str, Any] = None
    permissions: Dict[str, Any] = None
    performance: Dict[str, Any] = None
    health_check: Dict[str, Any] = None
    red_compliance: Dict[str, bool] = None

    def __post_init__(self):
        """Initialize default RED-compliant configuration."""
        if self.connection is None:
            project_root = str(get_project_root())
            self.connection = {
                "protocol": "stdio",
                "working_directory": project_root,
                "environment": {
                    "PYTHONPATH": project_root,
                    "OLLAMA_HOST": "localhost:11434",
                    "REDIS_URL": "redis://localhost:6379",
                    "CHROMA_DB_PATH": "./chromadb_data"
                }
            }

        if self.permissions is None:
            project_root = str(get_project_root())
            self.permissions = {
                "local_directory_access": [project_root],
                "chromadb_access": True,
                "ollama_access": True,
                "redis_streams_access": True
            }

        if self.performance is None:
            self.performance = {
                "mojo_optimization": True,
                "simd_acceleration": True,
                "max_concurrent_operations": 5
            }

        if self.health_check is None:
            self.health_check = {
                "enabled": True,
                "interval": 10,
                "timeout": 2,
                "local_services": ["ollama", "redis", "chromadb"]
            }

        if self.red_compliance is None:
            self.red_compliance = {
                "cost_first": True,
                "agent_native": True,
                "mojo_optimized": True,
                "local_first": True,
                "simple_scale": True
            }


@dataclass
class MCPServerStatus:
    """MCP server runtime status."""
    server_id: str
    status: str  # "running", "stopped", "error", "starting"
    pid: Optional[int] = None
    uptime: float = 0.0
    last_health_check: float = 0.0
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "requests_per_second": 0.0,
                "average_latency_ms": 0.0
            }


class ZeroCostMCPServerManager:
    """
    Zero-cost MCP server manager for agent-native RAG system.

    Implements RED principles:
    - COST-FIRST: No external dependencies or paid services
    - AGENT-NATIVE: MCP interfaces for AI agent consumption
    - LOCAL-FIRST: Localhost-only deployment
    - SIMPLE-SCALE: Optimized for 5 users
    """

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize the zero-cost MCP server manager."""
        if config_dir is None:
            # Use dynamic project root
            project_root = get_project_root()
            config_dir = str(project_root / "agent-system" / "config")
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.servers: Dict[str, MCPServerConfig] = {}
        self.server_processes: Dict[str, subprocess.Popen] = {}
        self.server_status: Dict[str, MCPServerStatus] = {}

        # Redis connection for event streaming
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            self.redis_client.ping()
            logger.info("Connected to Redis for event streaming")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Event streaming disabled.")
            self.redis_client = None

        # Load existing configurations
        self._load_configurations()

        logger.info("Zero-Cost MCP Server Manager initialized")

    def _load_configurations(self):
        """Load MCP server configurations from local filesystem."""
        config_files = list(self.config_dir.glob("*.json"))

        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)

                # Expand path variables in configuration
                if 'connection' in config_data:
                    if 'working_directory' in config_data['connection']:
                        config_data['connection']['working_directory'] = expand_path_variables(
                            config_data['connection']['working_directory']
                        )
                    if 'environment' in config_data['connection']:
                        for key, value in config_data['connection']['environment'].items():
                            if isinstance(value, str) and ('/' in value or '${' in value):
                                config_data['connection']['environment'][key] = expand_path_variables(value)

                if 'permissions' in config_data:
                    if 'local_directory_access' in config_data['permissions']:
                        config_data['permissions']['local_directory_access'] = [
                            expand_path_variables(path)
                            for path in config_data['permissions']['local_directory_access']
                        ]

                server_config = MCPServerConfig(**config_data)
                self.servers[server_config.server_id] = server_config

                # Initialize status
                self.server_status[server_config.server_id] = MCPServerStatus(
                    server_id=server_config.server_id,
                    status="stopped"
                )

                logger.info(f"Loaded configuration for server: {server_config.server_id}")

            except Exception as e:
                logger.error(f"Failed to load config {config_file}: {e}")

    def register_server(self, config: MCPServerConfig) -> bool:
        """Register a new MCP server with RED-compliant configuration."""
        try:
            # Validate RED compliance
            if not self._validate_red_compliance(config):
                logger.error(f"Server {config.server_id} fails RED compliance validation")
                return False

            # Store configuration
            self.servers[config.server_id] = config

            # Initialize status
            self.server_status[config.server_id] = MCPServerStatus(
                server_id=config.server_id,
                status="stopped"
            )

            # Save configuration to filesystem
            config_file = self.config_dir / f"{config.server_id}.json"
            with open(config_file, 'w') as f:
                json.dump(asdict(config), f, indent=2)

            # Publish event to Redis Streams
            self._publish_event("server_registered", {
                "server_id": config.server_id,
                "timestamp": time.time()
            })

            logger.info(f"Registered MCP server: {config.server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register server {config.server_id}: {e}")
            return False

    def start_server(self, server_id: str) -> bool:
        """Start an MCP server with zero-cost deployment."""
        if server_id not in self.servers:
            logger.error(f"Server {server_id} not found")
            return False

        if server_id in self.server_processes:
            logger.warning(f"Server {server_id} already running")
            return True

        try:
            config = self.servers[server_id]

            # Update status
            self.server_status[server_id].status = "starting"

            # Prepare command
            command = config.connection.get("command")
            args = config.connection.get("args", [])
            working_dir = config.connection.get("working_directory", str(get_project_root()))
            env = os.environ.copy()
            env.update(config.connection.get("environment", {}))

            # Start process
            if command:
                full_command = [command] + args
                process = subprocess.Popen(
                    full_command,
                    cwd=working_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                self.server_processes[server_id] = process

                # Update status
                self.server_status[server_id].status = "running"
                self.server_status[server_id].pid = process.pid
                self.server_status[server_id].uptime = time.time()

                # Publish event
                self._publish_event("server_started", {
                    "server_id": server_id,
                    "pid": process.pid,
                    "timestamp": time.time()
                })

                logger.info(f"Started MCP server {server_id} with PID {process.pid}")
                return True
            else:
                logger.error(f"No command specified for server {server_id}")
                self.server_status[server_id].status = "error"
                self.server_status[server_id].error_message = "No command specified"
                return False

        except Exception as e:
            logger.error(f"Failed to start server {server_id}: {e}")
            self.server_status[server_id].status = "error"
            self.server_status[server_id].error_message = str(e)
            return False

    def stop_server(self, server_id: str) -> bool:
        """Stop an MCP server gracefully."""
        if server_id not in self.server_processes:
            logger.warning(f"Server {server_id} not running")
            return True

        try:
            process = self.server_processes[server_id]

            # Graceful shutdown
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing server {server_id}")
                process.kill()
                process.wait()

            # Clean up
            del self.server_processes[server_id]

            # Update status
            self.server_status[server_id].status = "stopped"
            self.server_status[server_id].pid = None

            # Publish event
            self._publish_event("server_stopped", {
                "server_id": server_id,
                "timestamp": time.time()
            })

            logger.info(f"Stopped MCP server: {server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop server {server_id}: {e}")
            return False

    def get_server_status(self, server_id: str) -> Optional[MCPServerStatus]:
        """Get current status of an MCP server."""
        if server_id not in self.server_status:
            return None

        status = self.server_status[server_id]

        # Update runtime metrics
        if status.status == "running" and server_id in self.server_processes:
            process = self.server_processes[server_id]
            if process.poll() is not None:
                # Process has terminated
                status.status = "error"
                status.error_message = f"Process terminated with code {process.returncode}"
                status.pid = None

        return status

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered MCP servers with their status."""
        server_list = []

        for server_id, config in self.servers.items():
            status = self.get_server_status(server_id)

            server_info = {
                "server_id": server_id,
                "config": asdict(config),
                "status": asdict(status) if status else None
            }

            server_list.append(server_info)

        return server_list

    def health_check(self, server_id: str) -> Dict[str, Any]:
        """Perform health check on an MCP server."""
        if server_id not in self.servers:
            return {"status": "error", "message": "Server not found"}

        config = self.servers[server_id]
        status = self.get_server_status(server_id)

        health_result = {
            "server_id": server_id,
            "status": status.status if status else "unknown",
            "timestamp": time.time(),
            "checks": {}
        }

        # Check local services
        for service in config.health_check.get("local_services", []):
            health_result["checks"][service] = self._check_local_service(service)

        # Update last health check time
        if status:
            status.last_health_check = time.time()

        return health_result

    def _check_local_service(self, service: str) -> Dict[str, Any]:
        """Check if a local service is running."""
        try:
            if service == "ollama":
                # Check Ollama on localhost:11434
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                return {"status": "healthy", "response_time": response.elapsed.total_seconds()}

            elif service == "redis":
                # Check Redis connection
                if self.redis_client:
                    self.redis_client.ping()
                    return {"status": "healthy", "response_time": 0.001}
                else:
                    return {"status": "unhealthy", "error": "No Redis connection"}

            elif service == "chromadb":
                # Check ChromaDB (basic filesystem check)
                chromadb_path = get_project_root() / "chromadb_data"
                if chromadb_path.exists():
                    return {"status": "healthy", "response_time": 0.001}
                else:
                    return {"status": "unhealthy", "error": "ChromaDB path not found"}

            else:
                return {"status": "unknown", "error": f"Unknown service: {service}"}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def _validate_red_compliance(self, config: MCPServerConfig) -> bool:
        """Validate that server configuration complies with RED principles."""
        try:
            # Check COST-FIRST: No external paid services
            command = config.connection.get("command", "")
            if any(external in command for external in ["api.openai.com", "api.anthropic.com", "api.cohere.ai"]):
                logger.error("RED violation: External paid API detected")
                return False

            # Check LOCAL-FIRST: Localhost-only services
            env = config.connection.get("environment", {})
            for key, value in env.items():
                if isinstance(value, str) and "localhost" not in value and key.endswith("_HOST"):
                    logger.error(f"RED violation: Non-localhost service detected: {key}={value}")
                    return False

            # Check SIMPLE-SCALE: Max 5 concurrent operations
            max_ops = config.performance.get("max_concurrent_operations", 0)
            if max_ops > 5:
                logger.error(f"RED violation: Exceeds 5-user scale limit: {max_ops}")
                return False

            return True

        except Exception as e:
            logger.error(f"RED compliance validation failed: {e}")
            return False

    def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to Redis Streams for agent coordination."""
        if not self.redis_client:
            return

        try:
            event = {
                "event_type": event_type,
                "timestamp": time.time(),
                **data
            }

            self.redis_client.xadd("mcp_events", event)

        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")

    async def start_monitoring(self):
        """Start continuous monitoring of MCP servers."""
        logger.info("Starting MCP server monitoring")

        while True:
            try:
                for server_id in list(self.servers.keys()):
                    health = self.health_check(server_id)

                    # Publish health status
                    self._publish_event("health_check", health)

                # Wait for next check interval
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(30)


# Default server configurations for RED-aligned services
def _get_default_servers():
    """Get default server configurations with dynamic paths."""
    project_root = str(get_project_root())
    return [
        MCPServerConfig(
            server_id="local_rag_server",
            connection={
                "protocol": "stdio",
                "command": "uv run rag-system/mcp_rag_server.py",
                "working_directory": project_root,
                "environment": {
                    "PYTHONPATH": project_root,
                    "OLLAMA_HOST": "localhost:11434",
                    "REDIS_URL": "redis://localhost:6379",
                    "CHROMA_DB_PATH": "./chromadb_data"
                }
            }
        ),
        MCPServerConfig(
            server_id="multi_index_server",
            connection={
                "protocol": "stdio",
                "command": "uv run multi-index-system/mcp/protocol_handler.py",
                "working_directory": project_root,
                "environment": {
                    "PYTHONPATH": project_root,
                    "OLLAMA_HOST": "localhost:11434",
                    "REDIS_URL": "redis://localhost:6379"
                }
            }
        )
    ]

DEFAULT_SERVERS = _get_default_servers()


def initialize_default_servers():
    """Initialize default MCP servers for the RAG system."""
    manager = ZeroCostMCPServerManager()

    for server_config in DEFAULT_SERVERS:
        success = manager.register_server(server_config)
        if success:
            logger.info(f"Registered default server: {server_config.server_id}")
        else:
            logger.error(f"Failed to register default server: {server_config.server_id}")

    return manager


if __name__ == "__main__":
    # Initialize and start the MCP server manager
    manager = initialize_default_servers()

    # Start monitoring
    asyncio.run(manager.start_monitoring())