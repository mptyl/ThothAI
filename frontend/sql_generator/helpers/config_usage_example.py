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
Example usage of the centralized configuration manager.

This file demonstrates how to use the configuration system in different parts of the application.
"""

from helpers.config_manager import get_config
import httpx


# Example 1: Access server configuration
def start_server():
    """Start the server using centralized configuration."""
    config = get_config()
    
    print(f"Starting server on {config.server.host}:{config.server.port}")
    print(f"Environment: {config.environment}")
    print(f"Running in Docker: {config.is_docker}")
    
    # Use the configuration values
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level
    )


# Example 2: Connect to Django backend
async def fetch_workspace(workspace_id: int):
    """Fetch workspace configuration from Django backend."""
    config = get_config()
    
    url = f"{config.django.server_url}/api/workspaces/{workspace_id}/"
    headers = config.get_django_headers()
    
    async with httpx.AsyncClient(timeout=config.django.timeout) as client:
        response = await client.get(url, headers=headers)
        return response.json()


# Example 3: Setup vector database connection
def setup_vector_db():
    """Setup vector database using centralized configuration."""
    config = get_config()
    
    from thoth_qdrant import VectorStoreFactory
    
    # Build parameters from configuration
    params = {
        'backend': config.vector_db.type,
        'host': config.vector_db.host,
        'port': config.vector_db.port,
        'name': config.vector_db.collection_name or 'default',
        'embedding_provider': config.embedding.provider,
        'embedding_model': config.embedding.model,
        'embedding_api_key': config.embedding.api_key,
        'embedding_batch_size': config.embedding.batch_size,
        'embedding_dim': config.embedding.dimension
    }
    
    return VectorStoreFactory.create(**params)


# Example 4: Configure logging
def setup_application_logging():
    """Setup logging using centralized configuration."""
    config = get_config()
    
    import logging
    
    # Set logging level
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format
    )
    
    # Setup Logfire if enabled
    if config.logging.logfire_enabled and config.logging.logfire_token:
        import logfire
        logfire.configure(token=config.logging.logfire_token)
    
    # Setup file logging if enabled
    if config.logging.file_logging:
        from pathlib import Path
        log_dir = Path(config.logging.log_dir)
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / 'thoth.log')
        file_handler.setFormatter(logging.Formatter(config.logging.format))
        logging.getLogger().addHandler(file_handler)


# Example 5: Use performance configuration
async def generate_sqls_parallel(prompts: list):
    """Generate SQLs in parallel using performance configuration."""
    config = get_config()
    
    import asyncio
    
    max_parallel = config.performance.max_parallel_sqls
    
    # Process in batches
    results = []
    for i in range(0, len(prompts), max_parallel):
        batch = prompts[i:i + max_parallel]
        
        # Set timeout from configuration
        tasks = [
            asyncio.wait_for(
                generate_single_sql(prompt),
                timeout=config.performance.sql_generation_timeout
            )
            for prompt in batch
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        results.extend(batch_results)
    
    return results


async def generate_single_sql(prompt):
    """Placeholder for SQL generation."""
    # Implementation here
    pass


# Example 6: Validate configuration on startup
def validate_startup_configuration():
    """Validate configuration on application startup."""
    config = get_config()
    
    # Check for configuration issues
    issues = config.validate()
    
    if issues:
        print("Configuration warnings:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration validated successfully")
    
    # Display configuration summary
    print("\nConfiguration Summary:")
    print(f"  Environment: {config.environment}")
    print(f"  Server: {config.server.host}:{config.server.port}")
    print(f"  Django Backend: {config.django.server_url}")
    print(f"  Vector DB: {config.vector_db.type} at {config.vector_db.host}:{config.vector_db.port}")
    print(f"  Embedding: {config.embedding.provider}/{config.embedding.model}")
    print(f"  Parallelism: {config.performance.max_parallel_sqls} SQLs, {config.performance.max_parallel_tests} tests")


# Example 7: Export configuration for debugging
def export_configuration():
    """Export current configuration (with sensitive data masked)."""
    config = get_config()
    
    import json
    
    config_dict = config.to_dict()
    print(json.dumps(config_dict, indent=2))
    
    # This will show configuration with API keys masked as '***'