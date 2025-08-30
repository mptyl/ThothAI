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
Simplified Vector Database Configuration Utilities

This module provides a cleaner, more maintainable approach to vector database configuration.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class VectorDBConfig:
    """Configuration for a vector database backend."""
    backend_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    collection: Optional[str] = None
    api_key: Optional[str] = None
    environment: Optional[str] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.backend_type == 'qdrant':
            if not self.host:
                errors.append("Qdrant requires 'host'")
            if not self.port:
                errors.append("Qdrant requires 'port'")
                
        elif self.backend_type == 'chroma':
            if not self.host:
                errors.append("Chroma requires 'host'")
            if not self.port:
                self.port = 8000  # Default port
                
        elif self.backend_type == 'pgvector':
            required = ['host', 'port', 'database', 'user', 'password']
            for field in required:
                if not getattr(self, field):
                    errors.append(f"PGVector requires '{field}'")
                    
        elif self.backend_type == 'pinecone':
            if not self.api_key:
                errors.append("Pinecone requires 'api_key'")
            if not self.environment:
                errors.append("Pinecone requires 'environment'")
        else:
            errors.append(f"Unknown backend type: {self.backend_type}")
            
        return errors
    
    def to_factory_params(self) -> Dict[str, Any]:
        """Convert to parameters for VectorStoreFactory."""
        params = {'backend': self.backend_type}
        
        if self.backend_type == 'qdrant':
            params.update({
                'host': self.host,
                'port': self.port,
                'name': self.collection or 'default'
            })
            
        elif self.backend_type == 'chroma':
            params.update({
                'host': self.host,
                'port': self.port or 8000,
                'name': self.collection or 'default'
            })
            
        elif self.backend_type == 'pgvector':
            params.update({
                'connection_string': f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}",
                'name': self.collection or 'vectors'
            })
            
        elif self.backend_type == 'pinecone':
            params.update({
                'api_key': self.api_key,
                'environment': self.environment,
                'name': self.collection or 'default'
            })
            
        return params


def extract_vector_config(workspace: Dict[str, Any]) -> Optional[VectorDBConfig]:
    """
    Extract vector database configuration from workspace.
    
    Args:
        workspace: Workspace configuration dictionary
        
    Returns:
        VectorDBConfig object or None if not configured
    """
    vector_config = workspace.get('vector_db_config', {})
    if not vector_config:
        logger.info("No vector database configuration found in workspace")
        return None
    
    backend_type = vector_config.get('type', '').lower()
    if not backend_type:
        logger.warning("Vector database type not specified")
        return None
    
    # Create configuration object
    config = VectorDBConfig(
        backend_type=backend_type,
        host=vector_config.get('host'),
        port=vector_config.get('port'),
        collection=vector_config.get('collection'),
        api_key=vector_config.get('api_key'),
        environment=vector_config.get('environment'),
        database=vector_config.get('database'),
        user=vector_config.get('user'),
        password=vector_config.get('password')
    )
    
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error(f"Vector database configuration errors: {errors}")
        return None
    
    return config


def build_vector_params(workspace: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Build vector database parameters from workspace configuration.
    
    This is a simplified version that extracts configuration and converts
    it to factory parameters in one step.
    
    Args:
        workspace: Workspace configuration dictionary
        
    Returns:
        Parameters for VectorStoreFactory or None if not configured
    """
    config = extract_vector_config(workspace)
    if not config:
        return None
    
    try:
        params = config.to_factory_params()
        logger.info(f"Built vector database parameters for {config.backend_type}")
        return params
    except Exception as e:
        logger.error(f"Failed to build vector database parameters: {e}")
        return None