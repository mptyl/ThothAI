# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Centralized Configuration Management for ThothAI SQL Generator

This module provides a unified configuration system that:
- Loads configuration from environment variables and .env files
- Validates configuration values
- Provides sensible defaults
- Centralizes all configuration access
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8180
    reload: bool = False
    workers: int = 1
    log_level: str = "info"
    
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Load server configuration from environment."""
        return cls(
            host=os.getenv('SERVER_HOST', '0.0.0.0'),
            port=int(os.getenv('SERVER_PORT', os.getenv('PORT', '8180'))),
            reload=os.getenv('SERVER_RELOAD', 'false').lower() == 'true',
            workers=int(os.getenv('SERVER_WORKERS', '1')),
            log_level=os.getenv('SERVER_LOG_LEVEL', 'info').lower()
        )


@dataclass
class DjangoConfig:
    """Django backend configuration."""
    server_url: str = "http://localhost:8200"
    api_key: Optional[str] = None
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'DjangoConfig':
        """Load Django configuration from environment."""
        is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
        
        # Default URLs based on environment
        if is_docker:
            default_url = 'http://backend:8000'  # Docker service name and internal port
        else:
            default_url = 'http://localhost:8200'  # Local development port
        
        # Check multiple possible env var names for compatibility
        server_url = (
            os.getenv('DJANGO_SERVER') or
            os.getenv('DJANGO_SERVER_URL') or
            os.getenv('BACKEND_URL') or
            default_url
        )
        
        api_key = (
            os.getenv('DJANGO_API_KEY') or
            os.getenv('BACKEND_API_KEY')
        )
        
        return cls(
            server_url=server_url.rstrip('/'),  # Remove trailing slash
            api_key=api_key,
            timeout=int(os.getenv('DJANGO_TIMEOUT', '30'))
        )


@dataclass
class VectorDBConfig:
    """Vector database configuration."""
    type: str = "qdrant"
    host: str = "localhost"
    port: int = 6334
    collection_name: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'VectorDBConfig':
        """Load vector DB configuration from environment."""
        # Support both local and Docker configurations
        is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
        
        default_host = 'thoth-qdrant' if is_docker else 'localhost'
        default_port = 6333 if is_docker else 6334
        
        return cls(
            type=os.getenv('VECTOR_DB_TYPE', 'qdrant').lower(),
            host=os.getenv('VECTOR_DB_HOST', default_host),
            port=int(os.getenv('VECTOR_DB_PORT', str(default_port))),
            collection_name=os.getenv('VECTOR_DB_COLLECTION'),
            api_key=os.getenv('VECTOR_DB_API_KEY'),
            timeout=int(os.getenv('VECTOR_DB_TIMEOUT', '30'))
        )


@dataclass
class EmbeddingConfig:
    """Embedding configuration."""
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    api_key: Optional[str] = None
    batch_size: int = 100
    timeout: int = 30
    dimension: int = 1536
    
    @classmethod
    def from_env(cls) -> 'EmbeddingConfig':
        """Load embedding configuration from environment."""
        provider = os.getenv('EMBEDDING_PROVIDER', 'openai').lower()
        model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
        
        # Determine dimension based on model
        dimension = 1536  # default
        if provider == 'openai':
            if 'text-embedding-3-large' in model:
                dimension = 3072
            elif 'text-embedding-3-small' in model:
                dimension = 1536
        elif provider == 'cohere':
            dimension = 1024
        elif provider == 'mistral':
            dimension = 1024
        
        # Override with explicit dimension if provided
        dimension = int(os.getenv('EMBEDDING_DIMENSION', str(dimension)))
        
        return cls(
            provider=provider,
            model=model,
            api_key=os.getenv('EMBEDDING_API_KEY'),
            batch_size=int(os.getenv('EMBEDDING_BATCH_SIZE', '100')),
            timeout=int(os.getenv('EMBEDDING_TIMEOUT', '30')),
            dimension=dimension
        )


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logfire_enabled: bool = True
    logfire_token: Optional[str] = None
    file_logging: bool = True
    log_dir: str = "logs"
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Load logging configuration from environment."""
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            logfire_enabled=os.getenv('LOGFIRE_ENABLED', 'true').lower() == 'true',
            logfire_token=os.getenv('LOGFIRE_TOKEN'),
            file_logging=os.getenv('FILE_LOGGING', 'true').lower() == 'true',
            log_dir=os.getenv('LOG_DIR', 'logs')
        )


@dataclass
class PerformanceConfig:
    """Performance tuning configuration."""
    max_parallel_sqls: int = 12
    max_parallel_tests: int = 3
    sql_generation_timeout: int = 60
    test_generation_timeout: int = 30
    evaluation_timeout: int = 30
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    @classmethod
    def from_env(cls) -> 'PerformanceConfig':
        """Load performance configuration from environment."""
        return cls(
            max_parallel_sqls=int(os.getenv('MAX_PARALLEL_SQLS', '12')),
            max_parallel_tests=int(os.getenv('MAX_PARALLEL_TESTS', '3')),
            sql_generation_timeout=int(os.getenv('SQL_GENERATION_TIMEOUT', '60')),
            test_generation_timeout=int(os.getenv('TEST_GENERATION_TIMEOUT', '30')),
            evaluation_timeout=int(os.getenv('EVALUATION_TIMEOUT', '30')),
            cache_enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            cache_ttl=int(os.getenv('CACHE_TTL', '3600'))
        )


@dataclass
class ThothConfig:
    """Main configuration container for ThothAI SQL Generator."""
    server: ServerConfig = field(default_factory=ServerConfig)
    django: DjangoConfig = field(default_factory=DjangoConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Runtime flags
    is_docker: bool = False
    is_local: bool = True
    environment: str = "development"
    
    @classmethod
    def load(cls, env_file: Optional[str] = None) -> 'ThothConfig':
        """
        Load configuration from environment and optional .env file.
        
        Strategy:
        - Use .env.local for local development
        - Use .env.docker for Docker deployment (including production)
        - Look for .env files at project root (parent of sql_generator)
        
        Args:
            env_file: Path to .env file (optional)
        
        Returns:
            Loaded configuration object
        """
        # Determine project root (parent of sql_generator)
        current_dir = Path(__file__).parent.parent  # sql_generator dir
        project_root = current_dir.parent  # thoth_ui dir
        
        # Load .env file if specified
        if env_file:
            load_dotenv(env_file)
            logger.info(f"Loaded configuration from {env_file}")
        else:
            # Determine which .env to use based on DOCKER_CONTAINER env var
            # This env var should be set in docker-compose.yml
            is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
            
            if is_docker:
                # Docker environment (including production)
                env_path = project_root / '.env.docker'
                environment = 'docker'
            else:
                # Local development
                env_path = project_root / '.env.local'
                environment = 'local'
            
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded configuration from {env_path}")
            else:
                logger.warning(f"No .env file found at {env_path}")
        
        # Re-check after loading .env file
        is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
        if not env_file:
            environment = 'docker' if is_docker else 'local'
        
        config = cls(
            server=ServerConfig.from_env(),
            django=DjangoConfig.from_env(),
            vector_db=VectorDBConfig.from_env(),
            embedding=EmbeddingConfig.from_env(),
            logging=LoggingConfig.from_env(),
            performance=PerformanceConfig.from_env(),
            is_docker=is_docker,
            is_local=not is_docker,
            environment=environment
        )
        
        return config
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        # Check required Django configuration
        if not self.django.api_key:
            issues.append("Django API key is not configured (DJANGO_API_KEY)")
        
        # Check embedding configuration
        if not self.embedding.api_key:
            issues.append("Embedding API key is not configured (EMBEDDING_API_KEY)")
        
        # Check server configuration
        if self.server.port < 1 or self.server.port > 65535:
            issues.append(f"Invalid server port: {self.server.port}")
        
        # Check performance configuration
        if self.performance.max_parallel_sqls < 1:
            issues.append(f"Invalid max_parallel_sqls: {self.performance.max_parallel_sqls}")
        
        if self.performance.max_parallel_tests < 1:
            issues.append(f"Invalid max_parallel_tests: {self.performance.max_parallel_tests}")
        
        # Warn about development mode in production
        if self.environment == "production" and self.server.reload:
            issues.append("Server reload is enabled in production environment")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for serialization)."""
        return {
            'server': {
                'host': self.server.host,
                'port': self.server.port,
                'reload': self.server.reload,
                'workers': self.server.workers,
                'log_level': self.server.log_level
            },
            'django': {
                'server_url': self.django.server_url,
                'api_key': '***' if self.django.api_key else None,
                'timeout': self.django.timeout
            },
            'vector_db': {
                'type': self.vector_db.type,
                'host': self.vector_db.host,
                'port': self.vector_db.port,
                'collection_name': self.vector_db.collection_name,
                'api_key': '***' if self.vector_db.api_key else None
            },
            'embedding': {
                'provider': self.embedding.provider,
                'model': self.embedding.model,
                'api_key': '***' if self.embedding.api_key else None,
                'batch_size': self.embedding.batch_size,
                'dimension': self.embedding.dimension
            },
            'logging': {
                'level': self.logging.level,
                'logfire_enabled': self.logging.logfire_enabled,
                'file_logging': self.logging.file_logging,
                'log_dir': self.logging.log_dir
            },
            'performance': {
                'max_parallel_sqls': self.performance.max_parallel_sqls,
                'max_parallel_tests': self.performance.max_parallel_tests,
                'cache_enabled': self.performance.cache_enabled,
                'cache_ttl': self.performance.cache_ttl
            },
            'environment': {
                'is_docker': self.is_docker,
                'is_local': self.is_local,
                'environment': self.environment
            }
        }
    
    def get_django_headers(self) -> Dict[str, str]:
        """Get headers for Django API requests."""
        headers = {
            'Content-Type': 'application/json'
        }
        if self.django.api_key:
            headers['X-API-Key'] = self.django.api_key
        return headers


# Global configuration instance
_config: Optional[ThothConfig] = None


def get_config(reload: bool = False) -> ThothConfig:
    """
    Get the global configuration instance.
    
    Args:
        reload: Force reload configuration from environment
    
    Returns:
        Global configuration object
    """
    global _config
    if _config is None or reload:
        _config = ThothConfig.load()
        
        # Validate configuration
        issues = _config.validate()
        if issues:
            logger.warning(f"Configuration validation issues: {issues}")
    
    return _config


def reset_config():
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None