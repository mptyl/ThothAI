# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Configuration manager for thothai-cli."""

from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Manages ThothAI configuration from .env.docker file."""
    
    def __init__(self, env_path: Path = None):
        self.env_path = env_path or Path.cwd() / '.env.docker'
        self.config: Dict[str, Any] = {}
        self.load_env()
    
    def load_env(self) -> None:
        """Load configuration from .env.docker file."""
        if not self.env_path.exists():
            raise FileNotFoundError(f".env.docker not found: {self.env_path}")
        
        # Simple .env parser (avoiding external dependency on python-dotenv)
        with open(self.env_path) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    self.config[key.strip()] = value.strip()
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        # Check for at least one AI provider API key
        ai_providers = [
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY',
            'MISTRAL_API_KEY', 'DEEPSEEK_API_KEY', 'OPENROUTER_API_KEY',
            'GROQ_API_KEY'
        ]
        
        has_provider = any(self.config.get(key) for key in ai_providers)
        if not has_provider:
            errors.append("At least one AI provider API key must be configured")
        
        # Check embedding
        if not self.config.get('EMBEDDING_PROVIDER'):
            errors.append("EMBEDDING_PROVIDER must be configured")
        
        if errors:
            for error in errors:
                print(f"  ✗ {error}")
            return False
        
        return True
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    @property
    def deployment_mode(self):
        """Get deployment mode (compose or swarm)."""
        return self.config.get('DEPLOYMENT_MODE', 'compose')
    
    @property
    def stack_name(self):
        """Get stack name for Swarm deployments."""
        return self.config.get('STACK_NAME', 'thoth')
    
    @property
    def build_mode(self):
        """Get build mode (build or hub)."""
        return self.config.get('BUILD_MODE', 'hub')

