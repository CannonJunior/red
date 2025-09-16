"""
Production Deployment Configuration for Phase 3

Provides production-ready deployment configuration, monitoring,
health checks, and operational tooling for the multi-index system.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration for production."""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    ssl_mode: str = "require"

@dataclass
class RedisConfig:
    """Redis configuration for production."""
    host: str
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    pool_size: int = 20
    cluster_mode: bool = False
    cluster_nodes: List[str] = field(default_factory=list)
    ssl: bool = False

@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str
    jwt_secret: str
    allowed_origins: List[str] = field(default_factory=list)
    cors_enabled: bool = True
    rate_limit_per_minute: int = 1000
    enable_https: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_tracing: bool = True
    jaeger_endpoint: Optional[str] = None
    log_level: str = "INFO"
    structured_logging: bool = True
    sentry_dsn: Optional[str] = None

@dataclass
class ScalingConfig:
    """Auto-scaling configuration."""
    min_replicas: int = 2
    max_replicas: int = 10
    target_cpu_percent: int = 70
    target_memory_percent: int = 80
    scale_up_cooldown: int = 300  # seconds
    scale_down_cooldown: int = 600  # seconds

@dataclass
class ProductionConfig:
    """Complete production configuration."""
    environment: str = "production"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9090
    workers: int = 4

    # Component configurations
    database: Optional[DatabaseConfig] = None
    redis: Optional[RedisConfig] = None
    security: Optional[SecurityConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    scaling: Optional[ScalingConfig] = None

    # Index configurations
    indices_config: Dict[str, Any] = field(default_factory=dict)

    # Resource limits
    memory_limit: str = "4Gi"
    cpu_limit: str = "2000m"
    storage_limit: str = "100Gi"

class ProductionConfigManager:
    """Manages production configuration from multiple sources."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv('CONFIG_PATH', 'config/production.yaml')
        self.config: Optional[ProductionConfig] = None

    def load_config(self) -> ProductionConfig:
        """Load configuration from file and environment variables."""
        try:
            # Start with default config
            config_dict = self._get_default_config()

            # Load from file if exists
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config_dict.update(file_config)

            # Override with environment variables
            env_config = self._load_from_environment()
            config_dict.update(env_config)

            # Create typed configuration
            self.config = self._create_typed_config(config_dict)

            logger.info(f"Loaded production configuration from {self.config_path}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load production config: {e}")
            # Return minimal safe config
            return ProductionConfig()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default production configuration."""
        return {
            'environment': 'production',
            'debug': False,
            'host': '0.0.0.0',
            'port': 9090,
            'workers': 4,
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'multi_index_prod',
                'username': 'postgres',
                'password': 'changeme',
                'pool_size': 20
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'pool_size': 20
            },
            'security': {
                'secret_key': 'changeme-in-production',
                'jwt_secret': 'changeme-in-production',
                'allowed_origins': ['https://yourdomain.com'],
                'rate_limit_per_minute': 1000,
                'enable_https': True
            },
            'monitoring': {
                'enable_metrics': True,
                'metrics_port': 9090,
                'enable_tracing': True,
                'log_level': 'INFO',
                'structured_logging': True
            },
            'scaling': {
                'min_replicas': 2,
                'max_replicas': 10,
                'target_cpu_percent': 70,
                'target_memory_percent': 80
            },
            'indices_config': {
                'vector': {
                    'enabled': True,
                    'embedding_model': 'nomic-embed-text',
                    'dimension': 768,
                    'batch_size': 100
                },
                'graph': {
                    'enabled': True,
                    'entity_extraction_model': 'llama3.2:1b',
                    'max_entities': 50
                },
                'metadata': {
                    'enabled': True,
                    'memory_limit': '2GB',
                    'threads': 4
                },
                'fts': {
                    'enabled': True,
                    'stemming': True,
                    'max_results': 100
                },
                'temporal': {
                    'enabled': True,
                    'max_versions': 50,
                    'retention_days': 365
                }
            }
        }

    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}

        # Database configuration
        if os.getenv('DATABASE_URL'):
            # Parse DATABASE_URL
            db_url = os.getenv('DATABASE_URL')
            # Simplified parsing - in production use proper URL parsing
            env_config['database'] = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', '5432')),
                'database': os.getenv('DB_NAME', 'multi_index_prod'),
                'username': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', ''),
                'pool_size': int(os.getenv('DB_POOL_SIZE', '20'))
            }

        # Redis configuration
        if os.getenv('REDIS_URL'):
            env_config['redis'] = {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', '6379')),
                'password': os.getenv('REDIS_PASSWORD'),
                'db': int(os.getenv('REDIS_DB', '0'))
            }

        # Security configuration
        env_config['security'] = {
            'secret_key': os.getenv('SECRET_KEY', 'changeme-in-production'),
            'jwt_secret': os.getenv('JWT_SECRET', 'changeme-in-production'),
            'allowed_origins': os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else [],
            'enable_https': os.getenv('ENABLE_HTTPS', 'true').lower() == 'true'
        }

        # Monitoring configuration
        env_config['monitoring'] = {
            'enable_metrics': os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            'metrics_port': int(os.getenv('METRICS_PORT', '9090')),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'sentry_dsn': os.getenv('SENTRY_DSN')
        }

        # Application settings
        if os.getenv('PORT'):
            env_config['port'] = int(os.getenv('PORT'))
        if os.getenv('WORKERS'):
            env_config['workers'] = int(os.getenv('WORKERS'))

        return env_config

    def _create_typed_config(self, config_dict: Dict[str, Any]) -> ProductionConfig:
        """Create typed configuration from dictionary."""
        # Create component configs
        database_config = None
        if 'database' in config_dict:
            database_config = DatabaseConfig(**config_dict['database'])

        redis_config = None
        if 'redis' in config_dict:
            redis_config = RedisConfig(**config_dict['redis'])

        security_config = None
        if 'security' in config_dict:
            security_config = SecurityConfig(**config_dict['security'])

        monitoring_config = None
        if 'monitoring' in config_dict:
            monitoring_config = MonitoringConfig(**config_dict['monitoring'])

        scaling_config = None
        if 'scaling' in config_dict:
            scaling_config = ScalingConfig(**config_dict['scaling'])

        # Create main config
        return ProductionConfig(
            environment=config_dict.get('environment', 'production'),
            debug=config_dict.get('debug', False),
            host=config_dict.get('host', '0.0.0.0'),
            port=config_dict.get('port', 9090),
            workers=config_dict.get('workers', 4),
            database=database_config,
            redis=redis_config,
            security=security_config,
            monitoring=monitoring_config,
            scaling=scaling_config,
            indices_config=config_dict.get('indices_config', {}),
            memory_limit=config_dict.get('memory_limit', '4Gi'),
            cpu_limit=config_dict.get('cpu_limit', '2000m'),
            storage_limit=config_dict.get('storage_limit', '100Gi')
        )

    def validate_config(self, config: ProductionConfig) -> List[str]:
        """Validate production configuration."""
        errors = []

        # Security validations
        if config.security:
            if config.security.secret_key == 'changeme-in-production':
                errors.append("SECRET_KEY must be changed in production")

            if config.security.jwt_secret == 'changeme-in-production':
                errors.append("JWT_SECRET must be changed in production")

            if not config.security.allowed_origins:
                errors.append("ALLOWED_ORIGINS should be configured for security")

        # Database validations
        if config.database:
            if config.database.password == 'changeme':
                errors.append("Database password must be changed in production")

        # Resource validations
        if config.workers < 2:
            errors.append("Production should run with at least 2 workers")

        # Monitoring validations
        if config.monitoring and not config.monitoring.enable_metrics:
            errors.append("Metrics should be enabled in production")

        return errors

    def export_kubernetes_config(self, config: ProductionConfig) -> Dict[str, Any]:
        """Export Kubernetes deployment configuration."""
        k8s_config = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': 'multi-index-system',
                'labels': {
                    'app': 'multi-index-system',
                    'version': 'v3.0.0'
                }
            },
            'spec': {
                'replicas': config.scaling.min_replicas if config.scaling else 2,
                'selector': {
                    'matchLabels': {
                        'app': 'multi-index-system'
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': 'multi-index-system'
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': 'multi-index-system',
                            'image': 'multi-index-system:v3.0.0',
                            'ports': [
                                {'containerPort': config.port, 'name': 'http'},
                                {'containerPort': config.monitoring.metrics_port if config.monitoring else 9090, 'name': 'metrics'}
                            ],
                            'env': self._get_k8s_env_vars(config),
                            'resources': {
                                'requests': {
                                    'memory': config.memory_limit,
                                    'cpu': config.cpu_limit
                                },
                                'limits': {
                                    'memory': config.memory_limit,
                                    'cpu': config.cpu_limit
                                }
                            },
                            'livenessProbe': {
                                'httpGet': {
                                    'path': '/health',
                                    'port': config.port
                                },
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/ready',
                                    'port': config.port
                                },
                                'initialDelaySeconds': 5,
                                'periodSeconds': 5
                            }
                        }]
                    }
                }
            }
        }

        return k8s_config

    def _get_k8s_env_vars(self, config: ProductionConfig) -> List[Dict[str, Any]]:
        """Get Kubernetes environment variables."""
        env_vars = [
            {'name': 'ENVIRONMENT', 'value': config.environment},
            {'name': 'PORT', 'value': str(config.port)},
            {'name': 'WORKERS', 'value': str(config.workers)}
        ]

        # Database env vars
        if config.database:
            env_vars.extend([
                {'name': 'DB_HOST', 'value': config.database.host},
                {'name': 'DB_PORT', 'value': str(config.database.port)},
                {'name': 'DB_NAME', 'value': config.database.database},
                {'name': 'DB_USER', 'value': config.database.username},
                {'name': 'DB_PASSWORD', 'valueFrom': {'secretKeyRef': {'name': 'db-secret', 'key': 'password'}}}
            ])

        # Redis env vars
        if config.redis:
            env_vars.extend([
                {'name': 'REDIS_HOST', 'value': config.redis.host},
                {'name': 'REDIS_PORT', 'value': str(config.redis.port)},
                {'name': 'REDIS_DB', 'value': str(config.redis.db)}
            ])

        # Security env vars
        if config.security:
            env_vars.extend([
                {'name': 'SECRET_KEY', 'valueFrom': {'secretKeyRef': {'name': 'app-secret', 'key': 'secret-key'}}},
                {'name': 'JWT_SECRET', 'valueFrom': {'secretKeyRef': {'name': 'app-secret', 'key': 'jwt-secret'}}},
                {'name': 'ALLOWED_ORIGINS', 'value': ','.join(config.security.allowed_origins)}
            ])

        # Monitoring env vars
        if config.monitoring:
            env_vars.extend([
                {'name': 'ENABLE_METRICS', 'value': str(config.monitoring.enable_metrics).lower()},
                {'name': 'LOG_LEVEL', 'value': config.monitoring.log_level}
            ])

            if config.monitoring.sentry_dsn:
                env_vars.append({
                    'name': 'SENTRY_DSN',
                    'valueFrom': {'secretKeyRef': {'name': 'monitoring-secret', 'key': 'sentry-dsn'}}
                })

        return env_vars

    def export_docker_compose(self, config: ProductionConfig) -> Dict[str, Any]:
        """Export Docker Compose configuration."""
        compose_config = {
            'version': '3.8',
            'services': {
                'multi-index-system': {
                    'image': 'multi-index-system:v3.0.0',
                    'ports': [
                        f"{config.port}:{config.port}",
                        f"{config.monitoring.metrics_port if config.monitoring else 9090}:9090"
                    ],
                    'environment': self._get_docker_env_vars(config),
                    'depends_on': ['postgres', 'redis'],
                    'restart': 'unless-stopped',
                    'deploy': {
                        'replicas': config.scaling.min_replicas if config.scaling else 2,
                        'resources': {
                            'limits': {
                                'memory': config.memory_limit,
                                'cpus': config.cpu_limit.replace('m', '') + 'm' if 'm' not in config.cpu_limit else config.cpu_limit
                            }
                        }
                    },
                    'healthcheck': {
                        'test': f"curl -f http://localhost:{config.port}/health || exit 1",
                        'interval': '30s',
                        'timeout': '10s',
                        'retries': 3
                    }
                },
                'postgres': {
                    'image': 'postgres:15',
                    'environment': {
                        'POSTGRES_DB': config.database.database if config.database else 'multi_index_prod',
                        'POSTGRES_USER': config.database.username if config.database else 'postgres',
                        'POSTGRES_PASSWORD': config.database.password if config.database else 'changeme'
                    },
                    'volumes': ['postgres_data:/var/lib/postgresql/data'],
                    'restart': 'unless-stopped'
                },
                'redis': {
                    'image': 'redis:7-alpine',
                    'restart': 'unless-stopped',
                    'command': 'redis-server --appendonly yes',
                    'volumes': ['redis_data:/data']
                }
            },
            'volumes': {
                'postgres_data': {},
                'redis_data': {}
            }
        }

        return compose_config

    def _get_docker_env_vars(self, config: ProductionConfig) -> Dict[str, str]:
        """Get Docker environment variables."""
        env_vars = {
            'ENVIRONMENT': config.environment,
            'PORT': str(config.port),
            'WORKERS': str(config.workers)
        }

        # Database env vars
        if config.database:
            env_vars.update({
                'DB_HOST': 'postgres',  # Docker service name
                'DB_PORT': str(config.database.port),
                'DB_NAME': config.database.database,
                'DB_USER': config.database.username,
                'DB_PASSWORD': config.database.password
            })

        # Redis env vars
        if config.redis:
            env_vars.update({
                'REDIS_HOST': 'redis',  # Docker service name
                'REDIS_PORT': str(config.redis.port),
                'REDIS_DB': str(config.redis.db)
            })

        # Security env vars
        if config.security:
            env_vars.update({
                'SECRET_KEY': config.security.secret_key,
                'JWT_SECRET': config.security.jwt_secret,
                'ALLOWED_ORIGINS': ','.join(config.security.allowed_origins)
            })

        # Monitoring env vars
        if config.monitoring:
            env_vars.update({
                'ENABLE_METRICS': str(config.monitoring.enable_metrics).lower(),
                'LOG_LEVEL': config.monitoring.log_level
            })

            if config.monitoring.sentry_dsn:
                env_vars['SENTRY_DSN'] = config.monitoring.sentry_dsn

        return env_vars

# Monitoring and health check utilities

class ProductionMonitoring:
    """Production monitoring and health checks."""

    def __init__(self, config: ProductionConfig):
        self.config = config
        self.health_checks = {}
        self.metrics = {}

    def register_health_check(self, name: str, check_func: callable):
        """Register a health check function."""
        self.health_checks[name] = check_func

    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }

        overall_healthy = True

        for name, check_func in self.health_checks.items():
            try:
                check_result = await check_func()
                results['checks'][name] = check_result

                if not check_result.get('healthy', True):
                    overall_healthy = False

            except Exception as e:
                results['checks'][name] = {
                    'healthy': False,
                    'error': str(e)
                }
                overall_healthy = False

        results['status'] = 'healthy' if overall_healthy else 'unhealthy'
        return results

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        metrics_lines = []

        # System metrics
        metrics_lines.extend([
            "# HELP multi_index_system_info System information",
            "# TYPE multi_index_system_info gauge",
            f"multi_index_system_info{{version=\"3.0.0\",environment=\"{self.config.environment}\"}} 1",
            ""
        ])

        # Health metrics
        for check_name, result in self.health_checks.items():
            healthy = 1 if result.get('healthy', False) else 0
            metrics_lines.extend([
                f"# HELP multi_index_health_{check_name} Health check for {check_name}",
                f"# TYPE multi_index_health_{check_name} gauge",
                f"multi_index_health_{check_name} {healthy}",
                ""
            ])

        return "\n".join(metrics_lines)

def create_production_app(config_path: Optional[str] = None) -> Any:
    """Create production-ready application instance."""
    # Load configuration
    config_manager = ProductionConfigManager(config_path)
    config = config_manager.load_config()

    # Validate configuration
    errors = config_manager.validate_config(config)
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        raise ValueError("Invalid production configuration")

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.monitoring.log_level if config.monitoring else 'INFO'),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if not config.monitoring or not config.monitoring.structured_logging
               else '%(message)s'  # Structured logging would use JSON formatter
    )

    # Initialize monitoring
    monitoring = ProductionMonitoring(config)

    logger.info(f"Starting Multi-Index System v3.0.0 in {config.environment} mode")
    logger.info(f"Configuration loaded from: {config_path or 'environment variables'}")

    # Return configuration and monitoring for use by main application
    return config, monitoring