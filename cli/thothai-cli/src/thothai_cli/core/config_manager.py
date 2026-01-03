# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Configuration manager for thothai-cli."""

import yaml
from pathlib import Path
from typing import Dict, Any


def detect_server_name() -> str | None:
    """Try to detect server name/hostname."""
    import socket
    try:
        hostname = socket.gethostname()
        
        # Check if hostname looks like a domain (has dots and isn't localhost)
        if '.' in hostname and not hostname.startswith(('localhost', '127')):
            return hostname
        
        # Try to get the primary IP address
        try:
            # Connect to an external host to get primary IP (doesn't actually send data)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            
            # Try reverse DNS lookup
            try:
                return socket.gethostbyaddr(ip)[0]
            except Exception:
                return None
        except Exception:
            return None
    except Exception:
        return None


class ConfigManager:
    """Manages ThothAI configuration and generates .env.docker."""
    
    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()


    
    def load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        # Check for at least one AI provider
        providers = self.config.get('ai_providers', {})
        active_providers = [
            name for name, data in providers.items()
            if data.get('enabled') and data.get('api_key')
        ]
        
        if not active_providers:
            errors.append("At least one AI provider must be configured with a valid API key")
        
        # Check embedding
        embedding = self.config.get('embedding', {})
        if not embedding.get('provider'):
            errors.append("Embedding provider must be configured")
        
        if errors:
            for error in errors:
                print(f"  ✗ {error}")
            return False
        
        return True
    
    def generate_env_docker(self, remote_hostname: str | None = None) -> bool:
        """Generate .env.docker file from configuration.
        
        Args:
            remote_hostname: Optional hostname for remote deployments. When provided,
                             uses this for SERVER_NAME instead of local detection.
                             This enables proper domain configuration for remote servers.
        """
        env_lines = []
        
        # AI Providers
        providers = self.config.get('ai_providers', {})
        
        if providers.get('openai', {}).get('enabled'):
            env_lines.append(f"OPENAI_API_KEY={providers['openai']['api_key']}")
        
        if providers.get('anthropic', {}).get('enabled'):
            env_lines.append(f"ANTHROPIC_API_KEY={providers['anthropic']['api_key']}")
        
        if providers.get('gemini', {}).get('enabled'):
            env_lines.append(f"GEMINI_API_KEY={providers['gemini']['api_key']}")
        
        if providers.get('mistral', {}).get('enabled'):
            env_lines.append(f"MISTRAL_API_KEY={providers['mistral']['api_key']}")
        
        if providers.get('deepseek', {}).get('enabled'):
            env_lines.append(f"DEEPSEEK_API_KEY={providers['deepseek']['api_key']}")
            env_lines.append(f"DEEPSEEK_API_BASE={providers['deepseek']['api_base']}")
        
        if providers.get('openrouter', {}).get('enabled'):
            env_lines.append(f"OPENROUTER_API_KEY={providers['openrouter']['api_key']}")
            env_lines.append(f"OPENROUTER_API_BASE={providers['openrouter']['api_base']}")
        
        if providers.get('ollama', {}).get('enabled'):
            env_lines.append(f"OLLAMA_API_BASE={providers['ollama']['api_base']}")
        
        if providers.get('lm_studio', {}).get('enabled'):
            env_lines.append(f"LM_STUDIO_API_BASE={providers['lm_studio']['api_base']}")
        
        if providers.get('groq', {}).get('enabled'):
            env_lines.append(f"GROQ_API_KEY={providers['groq']['api_key']}")
        
        # Embedding
        embedding = self.config.get('embedding', {})
        env_lines.append(f"EMBEDDING_PROVIDER={embedding.get('provider')}")
        env_lines.append(f"EMBEDDING_MODEL={embedding.get('model')}")
        
        if embedding.get('api_key'):
            env_lines.append(f"EMBEDDING_API_KEY={embedding['api_key']}")
        else:
            provider_name = embedding.get('provider')
            if provider_name in providers and providers[provider_name].get('enabled'):
                env_lines.append(f"EMBEDDING_API_KEY={providers[provider_name]['api_key']}")
        
        # Monitoring
        monitoring = self.config.get('monitoring', {})
        if monitoring.get('enabled', True):
            env_lines.append(f"LOGFIRE_TOKEN={monitoring.get('logfire_token', '')}")
        
        # Backend AI model
        backend_ai = self.config.get('backend_ai_model', {})
        if backend_ai:
            env_lines.append(f"BACKEND_AI_PROVIDER={backend_ai.get('ai_provider','')}")
            env_lines.append(f"BACKEND_AI_MODEL={backend_ai.get('ai_model','')}")
        
        # Admin
        admin = self.config.get('admin', {})
        if admin.get('email'):
            env_lines.append(f"DJANGO_SUPERUSER_EMAIL={admin['email']}")
        env_lines.append(f"DJANGO_SUPERUSER_USERNAME={admin.get('username', 'admin')}")
        env_lines.append(f"DJANGO_SUPERUSER_PASSWORD={admin.get('password', 'admin123')}")
        
        # Ports
        ports = self.config.get('ports', {})
        env_lines.append(f"FRONTEND_PORT={ports.get('frontend', 3040)}")
        env_lines.append(f"BACKEND_PORT={ports.get('backend', 8040)}")
        env_lines.append(f"SQL_GENERATOR_PORT={ports.get('sql_generator', 8020)}")
        env_lines.append(f"WEB_PORT={ports.get('nginx', 8040)}")
        mermaid_port = ports.get('mermaid_service') or ports.get('mermaid') or 8003
        env_lines.append(f"MERMAID_SERVICE_PORT={mermaid_port}")
        env_lines.append("MERMAID_SERVICE_URL=http://mermaid-service:8001")
        
        # Runtime settings
        runtime = self.config.get('runtime', {})
        env_lines.append(f"DEBUG={str(runtime.get('debug', False)).upper()}")
        backend_level = str(runtime.get('backend_log_level', 'INFO')).upper()
        frontend_level = str(runtime.get('frontend_log_level', 'INFO')).upper()
        env_lines.append(f"BACKEND_LOGGING_LEVEL={backend_level}")
        env_lines.append(f"FRONTEND_LOGGING_LEVEL={frontend_level}")
        
        # Database plugins
        databases = self.config.get('databases', {})
        enabled_dbs = ['sqlite']  # sqlite is always enabled
        if databases.get('postgresql'):
            enabled_dbs.append('postgresql')
        if databases.get('mysql'):
            enabled_dbs.append('mysql')
        if databases.get('mariadb'):
            enabled_dbs.append('mariadb')
        if databases.get('sqlserver'):
            enabled_dbs.append('sqlserver')
        if databases.get('informix'):
            enabled_dbs.append('informix')
        env_lines.append(f"ENABLED_DATABASES={','.join(enabled_dbs)}")
        
        # Additional required variables
        env_lines.append('DB_ROOT_PATH=/app/data')
        env_lines.append('DB_NAME_DOCKER=/app/backend_db/db.sqlite3')
        env_lines.append('DB_NAME_LOCAL=db.sqlite3')
        env_lines.append('NODE_ENV=production')
        
        docker_cfg = self.config.get('docker', {})
        env_lines.append(f"DOCKER_USERNAME={docker_cfg.get('image_registry', 'tylconsulting')}")
        env_lines.append(f"VERSION={docker_cfg.get('image_version', 'latest')}")

        # SERVER_NAME logic:
        # 1. If remote_hostname is provided (remote deployment), use it
        # 2. Otherwise, use config value or local detection (local deployment)
        if remote_hostname:
            server_name = remote_hostname
            print(f"[dim]Using remote server name: {server_name}[/dim]")
        else:
            server_name = self.config.get('server_name') or detect_server_name()
            if server_name:
                print(f"[dim]Detected server name: {server_name}[/dim]")
        
        if server_name:
            env_lines.append(f"SERVER_NAME={server_name}")
            
            # Set ALLOWED_HOSTS for Django backend
            # Include the server_name (whether local or remote) plus standard hosts
            allowed_hosts = self.config.get('allowed_hosts')
            web_port = ports.get('nginx', 8040)
            frontend_port = ports.get('frontend', 3040)
            if not allowed_hosts:
                allowed_hosts = f"{server_name},{server_name}:{web_port},localhost,127.0.0.1,host.docker.internal"
            
            env_lines.append(f"ALLOWED_HOSTS={allowed_hosts}")
            
            # For remote deployments, set CORS_ALLOWED_ORIGINS so frontend can make API calls
            if remote_hostname:
                cors_origins = f"http://{server_name}:{frontend_port},http://{server_name}:{web_port}"
                env_lines.append(f"CORS_ALLOWED_ORIGINS={cors_origins}")
        
        # Write .env.docker
        env_path = self.config_path.parent / '.env.docker'
        with open(env_path, 'w') as f:
            f.write('# Auto-generated by thothai-cli\n')
            f.write('# DO NOT EDIT - Modify config.yml.local instead\n\n')
            f.write('\n'.join(env_lines))
            f.write('\n')
        
        # Secure file permissions
        env_path.chmod(0o600)
        
        return True
    

    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
