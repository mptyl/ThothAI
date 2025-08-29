# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Simplified vector database configuration management.
Cleaner structure with reduced complexity and better organization.
"""
import os
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================

@dataclass
class VectorBackendConfig:
    """Configuration for a vector database backend."""
    name: str
    required_fields: list[str]
    param_mapping: Dict[str, str] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    connection_builder: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    embedding_dims: Dict[str, int] = field(default_factory=dict)


@dataclass 
class EmbeddingConfig:
    """Configuration for embedding models."""
    provider: str
    model: str
    api_key: str
    dimension: int
    batch_size: int = 100
    timeout: int = 30
    base_url: Optional[str] = None
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'EmbeddingConfig':
        """Create EmbeddingConfig from dictionary."""
        provider = config.get('embedding_provider', '').lower()
        model = config.get('embedding_model', '')
        
        # Determine embedding dimension based on provider/model
        dimension = cls._get_embedding_dimension(provider, model)
        
        return cls(
            provider=provider,
            model=model,
            api_key=config.get('embedding_api_key', ''),
            dimension=dimension,
            batch_size=config.get('embedding_batch_size', 100),
            timeout=config.get('embedding_timeout', 30),
            base_url=config.get('embedding_base_url')
        )
    
    @staticmethod
    def _get_embedding_dimension(provider: str, model: str) -> int:
        """Get embedding dimension for provider/model combination."""
        dimensions = {
            'openai': {
                'text-embedding-3-small': 1536,
                'text-embedding-3-large': 3072,
                'default': 1536
            },
            'cohere': {'default': 1024},
            'mistral': {'default': 1024},
            'default': {'default': 384}
        }
        
        provider_dims = dimensions.get(provider, dimensions['default'])
        
        # Check specific model first
        for model_key, dim in provider_dims.items():
            if model_key != 'default' and model_key in model:
                return dim
        
        return provider_dims.get('default', 384)


# =============================================================================
# BACKEND CONFIGURATIONS
# =============================================================================

VECTOR_BACKENDS = {
    'qdrant': VectorBackendConfig(
        name='qdrant',
        required_fields=['host', 'port'],
        param_mapping={'host': 'host', 'port': 'port', 'collection': 'name'}
    ),
    
    'chroma': VectorBackendConfig(
        name='chroma',
        required_fields=['host'],
        param_mapping={'host': 'host', 'collection': 'name'},
        defaults={'port': 8000}
    ),
    
    'pgvector': VectorBackendConfig(
        name='pgvector',
        required_fields=['host', 'port', 'database', 'user', 'password'],
        param_mapping={'collection': 'name'},
        defaults={'port': 5432},
        connection_builder=lambda cfg: {
            'connection_string': f"postgresql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg.get('port', 5432)}/{cfg['database']}"
        }
    ),
    
    'pinecone': VectorBackendConfig(
        name='pinecone',
        required_fields=['api_key', 'environment'],
        param_mapping={'api_key': 'api_key', 'environment': 'environment', 'collection': 'name'}
    ),
    
    'milvus': VectorBackendConfig(
        name='milvus',
        required_fields=['host'],
        param_mapping={'host': 'host', 'port': 'port', 'collection': 'name'},
        defaults={'port': 19530}
    ),
    
    'weaviate': VectorBackendConfig(
        name='weaviate',
        required_fields=['host'],
        param_mapping={'collection': 'name'},
        defaults={'port': 8080},
        connection_builder=lambda cfg: {
            'url': f"http://{cfg['host']}:{cfg.get('port', 8080)}"
        }
    )
}


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def get_vectordb_config(db: dict) -> dict:
    """
    Get vector database configuration from database info.
    
    Args:
        db: Database information dictionary
        
    Returns:
        Vector database configuration
    """
    index = _get_vectordb_index(db["schema"], db["db_name"])
    vector_db = db["vector_db"]
    
    return {
        "vector_db_type": vector_db["vect_type"],
        "host": vector_db["host"],
        "port": vector_db["port"],
        "collection_name": index
    }


def _get_vectordb_index(schema: str, db_name: str) -> str:
    """Generate index name for vector database."""
    if schema and schema != "public":
        return f"{schema}__{db_name}"
    return db_name


def extract_vector_db_config_from_workspace(workspace: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract vector database configuration from workspace.
    Simplified version with cleaner structure.
    
    Args:
        workspace: Workspace configuration dictionary
        
    Returns:
        Extracted vector database configuration
        
    Raises:
        ValueError: If required configuration is missing
    """
    # Get SQL database configuration
    sql_db = workspace.get('sql_db', {})
    if not isinstance(sql_db, dict):
        raise ValueError(f"Invalid workspace structure: sql_db is not a dict but {type(sql_db)}")
    
    # Get vector database configuration
    vector_db = sql_db.get('vector_db')
    if not vector_db:
        raise ValueError(
            "Vector database configuration not found in workspace. "
            "Please configure it in Django admin."
        )
    
    # Extract and validate required fields
    config = _extract_required_fields(vector_db)
    
    # Add optional fields
    _add_optional_fields(config, vector_db)
    
    # Handle embedding configuration
    _configure_embedding(config, vector_db)
    
    # Clean up the configuration
    cleaned = _clean_config(config)
    
    logger.info(f"Vector DB config loaded: {_mask_sensitive(cleaned)}")
    return cleaned


def build_vector_db_params(vector_db_config: Dict[str, Any], vect_type: str) -> Dict[str, Any]:
    """
    Build parameters for vector database initialization.
    Simplified version with cleaner logic flow.
    
    Args:
        vector_db_config: Vector database configuration
        vect_type: Type of vector database
        
    Returns:
        Parameters for VectorStoreFactory.create()
        
    Raises:
        ValueError: If backend is unsupported or config is incomplete
    """
    vect_type = vect_type.lower()
    
    # Validate backend type
    if vect_type not in VECTOR_BACKENDS:
        raise ValueError(
            f"Unsupported backend '{vect_type}'. "
            f"Available: {', '.join(VECTOR_BACKENDS.keys())}"
        )
    
    backend = VECTOR_BACKENDS[vect_type]
    params = {'backend': vect_type}
    
    # Apply defaults
    _apply_defaults(vector_db_config, backend)
    
    # Validate required fields
    _validate_required_fields(vector_db_config, backend, vect_type)
    
    # Map parameters
    _map_parameters(params, vector_db_config, backend)
    
    # Handle connection building
    _build_connection(params, vector_db_config, backend)
    
    # Configure embedding
    _add_embedding_params(params, vector_db_config, vect_type)
    
    return params


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_required_fields(vector_db: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and validate required fields from vector DB config."""
    required = {
        'host': 'Vector DB host',
        'port': 'Vector DB port',
        'vect_type': 'Vector DB type',
        'embedding_provider': 'Embedding provider',
        'embedding_model': 'Embedding model'
    }
    
    config = {}
    missing = []
    
    for field, description in required.items():
        value = vector_db.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(f"{field} ({description})")
        else:
            config[field] = value.lower() if field == 'vect_type' else value
    
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    
    return config


def _add_optional_fields(config: Dict[str, Any], vector_db: Dict[str, Any]) -> None:
    """Add optional fields to configuration."""
    config['name'] = vector_db.get('name') or 'thoth_vectors'
    
    optional = ['api_key', 'environment', 'database', 'user', 'password', 
                'path', 'url', 'tenant']
    
    for field in optional:
        value = vector_db.get(field)
        if value:
            config[field] = value


def _configure_embedding(config: Dict[str, Any], vector_db: Dict[str, Any]) -> None:
    """Configure embedding settings."""
    config['embedding_batch_size'] = vector_db.get('embedding_batch_size') or 100
    config['embedding_timeout'] = vector_db.get('embedding_timeout') or 30
    
    # Handle API key - only env var we keep for security
    api_key = vector_db.get('embedding_api_key') or os.getenv('EMBEDDING_API_KEY')
    if not api_key:
        raise ValueError(
            "Embedding API key not found. Set EMBEDDING_API_KEY env var "
            "or configure in workspace."
        )
    config['embedding_api_key'] = api_key
    
    # Optional base URL
    base_url = vector_db.get('embedding_base_url')
    if base_url:
        config['embedding_base_url'] = base_url


def _clean_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values and empty strings from config."""
    return {
        k: v for k, v in config.items()
        if v is not None and (not isinstance(v, str) or v.strip())
    }


def _apply_defaults(config: Dict[str, Any], backend: VectorBackendConfig) -> None:
    """Apply default values from backend configuration."""
    for key, default_value in backend.defaults.items():
        if key not in config:
            logger.debug(f"Using default for {key}: {default_value}")
            config[key] = default_value


def _validate_required_fields(config: Dict[str, Any], backend: VectorBackendConfig, 
                             vect_type: str) -> None:
    """Validate that all required fields are present."""
    missing = [field for field in backend.required_fields if field not in config]
    
    if missing:
        raise ValueError(
            f"Incomplete config for {vect_type}. "
            f"Missing: {missing}. Required: {backend.required_fields}"
        )


def _map_parameters(params: Dict[str, Any], config: Dict[str, Any], 
                   backend: VectorBackendConfig) -> None:
    """Map configuration parameters using backend mapping."""
    for factory_key, config_key in backend.param_mapping.items():
        if config_key in config:
            params[factory_key] = config[config_key]


def _build_connection(params: Dict[str, Any], config: Dict[str, Any], 
                     backend: VectorBackendConfig) -> None:
    """Build connection parameters if backend has connection builder."""
    if backend.connection_builder:
        built_params = backend.connection_builder(config)
        params.update(built_params)
    else:
        # Add required fields not in param_mapping
        for field in backend.required_fields:
            if field not in backend.param_mapping.values() and field in config:
                params[field] = config[field]


def _add_embedding_params(params: Dict[str, Any], config: Dict[str, Any], 
                          vect_type: str) -> None:
    """Add embedding parameters to configuration."""
    # Create embedding config
    embedding = EmbeddingConfig.from_dict(config)
    
    # Add base embedding parameters
    params['embedding_provider'] = embedding.provider
    params['embedding_model'] = embedding.model
    params['embedding_dim'] = embedding.dimension
    
    # Add additional params based on backend
    # Qdrant doesn't accept all embedding params
    if vect_type != 'qdrant':
        params['embedding_api_key'] = embedding.api_key
        params['embedding_batch_size'] = embedding.batch_size
        params['embedding_timeout'] = embedding.timeout
        if embedding.base_url:
            params['embedding_base_url'] = embedding.base_url
    else:
        # For Qdrant, only add essential params
        params['embedding_api_key'] = embedding.api_key


def _mask_sensitive(config: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive information in configuration for logging."""
    masked = config.copy()
    sensitive_keys = ['embedding_api_key', 'api_key', 'password']
    
    for key in sensitive_keys:
        if key in masked:
            masked[key] = '***'
    
    return masked


def get_supported_vector_backends() -> list[str]:
    """Get list of supported vector database backends."""
    return list(VECTOR_BACKENDS.keys())