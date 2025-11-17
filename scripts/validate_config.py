#!/usr/bin/env python3
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Thoth AI Configuration Validator
Validates YAML configuration and API keys
"""

import yaml
import sys
import requests
from pathlib import Path
from typing import Dict, Optional, List

class ConfigValidator:
    def __init__(self, config_path: str = "config.yml.local"):
        self.config_path = Path(config_path)
        self.config = None
        self.errors = []
        self.warnings = []
        
    def load_config(self) -> bool:
        """Load YAML configuration file"""
        if not self.config_path.exists():
            self.errors.append(f"Configuration file {self.config_path} not found")
            return False
        
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            return True
        except Exception as e:
            self.errors.append(f"Error loading configuration: {e}")
            return False
    
    def validate(self) -> bool:
        """Complete validation pipeline"""
        print("Validating configuration...")
        
        if not self.load_config():
            return False
        
        # Structure validation
        self.check_version()
        self.check_ai_providers()
        self.check_embedding()
        self.check_backend_ai_model()
        self.check_databases()
        self.check_admin()
        self.check_monitoring()
        self.check_ports()
        
        # API validation if no structural errors
        if not self.errors:
            self.validate_api_keys()
        
        # Print results
        self.print_results()
        
        return len(self.errors) == 0
    
    def check_version(self):
        """Check configuration version"""
        version = self.config.get('version')
        if not version:
            self.errors.append("Configuration version missing")
        elif version != "1.0":
            self.warnings.append(f"Configuration version {version} may not be compatible")
    
    def check_ai_providers(self):
        """Check that at least one AI provider is configured"""
        providers = self.config.get('ai_providers', {})
        
        if not providers:
            self.errors.append("No AI providers configured")
            return
        
        active_providers = []
        for name, data in providers.items():
            if data.get('enabled'):
                if not data.get('api_key') and name not in ['ollama', 'lm_studio']:
                    self.errors.append(f"Provider {name} is enabled but has no API key")
                else:
                    active_providers.append(name)
        
        if not active_providers:
            self.errors.append("At least one AI provider must be enabled with a valid API key")

    def check_backend_ai_model(self):
        """Validate backend_ai_model presence and viability with provider"""
        backend_ai = self.config.get('backend_ai_model')
        providers = self.config.get('ai_providers', {})

        if not backend_ai:
            self.errors.append("backend_ai_model section is missing")
            return

        ai_provider = (backend_ai.get('ai_provider') or '').strip()
        ai_model = (backend_ai.get('ai_model') or '').strip()

        if not ai_provider:
            self.errors.append("backend_ai_model.ai_provider is not specified")
            return
        if not ai_model:
            self.errors.append("backend_ai_model.ai_model is not specified")
            return

        if ai_provider not in providers:
            self.errors.append(f"backend_ai_model.ai_provider '{ai_provider}' is not defined under ai_providers")
            return

        provider_cfg = providers.get(ai_provider, {})
        if not provider_cfg.get('enabled'):
            self.errors.append(f"backend_ai_model.ai_provider '{ai_provider}' is not enabled")
            return

        # API key requirements by provider
        providers_no_key = ['ollama', 'lm_studio']
        if ai_provider not in providers_no_key:
            if not provider_cfg.get('api_key'):
                self.errors.append(f"backend_ai_model.ai_provider '{ai_provider}' requires an API key")
                return

        # Live validation of the model against provider
        print(f"Validating backend_ai_model: provider={ai_provider}, model={ai_model} ...", end=" ")
        ok = self._validate_backend_model_with_provider(ai_provider, ai_model, provider_cfg)
        if ok:
            print("OK")
        else:
            print("FAILED")
            self.errors.append(
                f"backend_ai_model validation failed for provider '{ai_provider}' with model '{ai_model}'"
            )

    def _validate_backend_model_with_provider(self, provider: str, model: str, cfg: Dict) -> bool:
        """Attempt a minimal chat/completion call to verify provider+model works."""
        try:
            timeout = 6
            if provider == 'openai':
                headers = {"Authorization": f"Bearer {cfg.get('api_key')}", "Content-Type": "application/json"}
                r = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                    timeout=timeout,
                )
                return r.status_code in [200, 400, 422]
            if provider == 'anthropic':
                headers = {"x-api-key": cfg.get('api_key'), "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
                r = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                    timeout=timeout,
                )
                return r.status_code in [200, 400, 422]
            if provider == 'gemini':
                key = cfg.get('api_key')
                url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}"
                r = requests.post(url, json={"contents": [{"parts": [{"text": "ping"}]}]}, timeout=timeout)
                return r.status_code in [200, 400]
            if provider == 'mistral':
                headers = {"Authorization": f"Bearer {cfg.get('api_key')}", "Content-Type": "application/json"}
                r = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                    timeout=timeout,
                )
                return r.status_code in [200, 400]
            if provider in ['deepseek', 'openrouter', 'groq', 'lm_studio']:
                # OpenAI-compatible chat/completions
                api_base = cfg.get('api_base') or (
                    'https://api.deepseek.com/v1' if provider == 'deepseek' else
                    'https://openrouter.ai/api/v1' if provider == 'openrouter' else
                    'https://api.groq.com/openai/v1' if provider == 'groq' else
                    'http://localhost:1234/v1'
                )
                headers = {"Content-Type": "application/json"}
                if provider != 'lm_studio':
                    headers["Authorization"] = f"Bearer {cfg.get('api_key')}"
                r = requests.post(
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                    timeout=timeout,
                )
                return r.status_code in [200, 400]
            if provider == 'ollama':
                api_base = cfg.get('api_base') or 'http://127.0.0.1:11434'
                r = requests.post(
                    f"{api_base}/api/chat",
                    json={"model": model, "messages": [{"role": "user", "content": "ping"}]},
                    timeout=timeout,
                )
                return r.status_code in [200, 404, 400]  # 404 if model not pulled
        except Exception:
            return False
        return False
    
    def check_embedding(self):
        """Check embedding configuration"""
        embedding = self.config.get('embedding', {})
        
        if not embedding:
            self.errors.append("Embedding configuration missing")
            return
        
        provider = embedding.get('provider')
        if not provider:
            self.errors.append("Embedding provider not specified")
            return
        
        if provider not in ['openai', 'mistral', 'cohere']:
            self.errors.append(f"Invalid embedding provider: {provider}")
            return
        
        # Check if embedding has API key
        embed_key = embedding.get('api_key')
        if not embed_key:
            # Check if provider's main API key exists
            providers = self.config.get('ai_providers', {})
            provider_data = providers.get(provider, {})
            if not (provider_data.get('enabled') and provider_data.get('api_key')):
                self.errors.append(f"Embedding provider '{provider}' requires an API key")
        
        # Check model
        model = embedding.get('model')
        if not model:
            self.errors.append("Embedding model not specified")
    
    def check_databases(self):
        """Check database configuration"""
        databases = self.config.get('databases', {})
        
        if not databases:
            self.errors.append("Database configuration missing")
            return
        
        # SQLite must always be enabled
        if not databases.get('sqlite', True):
            self.errors.append("SQLite support cannot be disabled")
        
        # Check valid database names
        valid_dbs = ['sqlite', 'postgresql', 'mysql', 'mariadb', 'sqlserver']
        for db_name, enabled in databases.items():
            if db_name not in valid_dbs:
                self.warnings.append(f"Unknown database type: {db_name}")
    
    def check_admin(self):
        """Check admin configuration"""
        admin = self.config.get('admin', {})
        
        if not admin:
            self.errors.append("Admin configuration missing")
            return
        
        username = admin.get('username')
        if not username:
            self.errors.append("Admin username not specified")
        
        # Email is optional
        # Password will be requested interactively
    
    def check_monitoring(self):
        """Check monitoring configuration"""
        monitoring = self.config.get('monitoring', {})
        
        # Monitoring enabled by default
        if monitoring.get('enabled', True):
            token = monitoring.get('logfire_token')
            if not token:
                self.errors.append("Monitoring is enabled but Logfire token not provided")
    
    def check_ports(self):
        """Check port configuration"""
        ports = self.config.get('ports', {})
        
        if not ports:
            self.errors.append("Port configuration missing")
            return
        
        required_ports = ['frontend', 'backend', 'sql_generator', 'nginx', 'qdrant']
        used_ports = {}
        
        for port_name in required_ports:
            port = ports.get(port_name)
            
            if port is None:
                self.errors.append(f"Port for {port_name} not specified")
                continue
            
            if not isinstance(port, int):
                self.errors.append(f"Port for {port_name} must be a number")
                continue
            
            if port < 1024 or port > 65535:
                self.errors.append(f"Port for {port_name} must be between 1024 and 65535")
                continue
            
            # Check for duplicates
            if port in used_ports:
                self.errors.append(f"Port {port} is used by both {used_ports[port]} and {port_name}")
            else:
                used_ports[port] = port_name
    
    def validate_api_keys(self):
        """Validate API keys with providers"""
        print("Validating API keys with providers...")
        
        providers = self.config.get('ai_providers', {})
        
        for name, data in providers.items():
            if not data.get('enabled'):
                continue
            
            api_key = data.get('api_key')
            if not api_key and name not in ['ollama', 'lm_studio']:
                continue
            
            print(f"  Checking {name} API key...", end=" ")
            
            if name == 'openai':
                if self.validate_openai_key(api_key):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append(f"OpenAI API key is invalid")
            
            elif name == 'anthropic':
                if self.validate_anthropic_key(api_key):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append(f"Anthropic API key is invalid")
            
            elif name == 'mistral':
                if self.validate_mistral_key(api_key):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append(f"Mistral API key is invalid")
            
            elif name == 'gemini':
                if self.validate_gemini_key(api_key):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append(f"Gemini API key is invalid")
            
            elif name == 'ollama':
                if self.validate_ollama_endpoint(data.get('api_base')):
                    print("OK")
                else:
                    print("UNREACHABLE")
                    self.warnings.append(f"Ollama endpoint is unreachable at {data.get('api_base')}")
            
            elif name == 'lm_studio':
                if self.validate_lm_studio_endpoint(data.get('api_base')):
                    print("OK")
                else:
                    print("UNREACHABLE")
                    self.warnings.append(f"LM Studio endpoint is unreachable at {data.get('api_base')}")
            
            elif name == 'deepseek':
                if self.validate_openai_compatible_key(api_key, data.get('api_base', 'https://api.deepseek.com/v1')):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append(f"DeepSeek API key is invalid")
            
            elif name == 'openrouter':
                if self.validate_openai_compatible_key(api_key, data.get('api_base', 'https://openrouter.ai/api/v1')):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append(f"OpenRouter API key is invalid")
            
            elif name == 'groq':
                if self.validate_groq_key(api_key):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append(f"Groq API key is invalid")
            
            else:
                print("SKIPPED (Unknown provider)")
        
        # Validate Logfire if monitoring enabled
        monitoring = self.config.get('monitoring', {})
        if monitoring.get('enabled', True):
            token = monitoring.get('logfire_token')
            if token:
                print("  Checking Logfire token...", end=" ")
                if self.validate_logfire_token(token):
                    print("OK")
                else:
                    print("INVALID")
                    self.errors.append("Logfire token is invalid")
    
    def validate_openai_key(self, api_key: str) -> bool:
        """Test OpenAI API key"""
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def validate_anthropic_key(self, api_key: str) -> bool:
        """Test Anthropic API key"""
        try:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            # Anthropic doesn't have a simple list endpoint, so we check with a minimal request
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-opus-20240229",
                    "messages": [],
                    "max_tokens": 1
                },
                timeout=5
            )
            # 400 means the key is valid but request is malformed (expected)
            # 401 means invalid key
            return response.status_code in [400, 422]
        except:
            return False
    
    def validate_mistral_key(self, api_key: str) -> bool:
        """Test Mistral API key"""
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(
                "https://api.mistral.ai/v1/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def validate_gemini_key(self, api_key: str) -> bool:
        """Test Gemini API key"""
        try:
            response = requests.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def validate_logfire_token(self, token: str) -> bool:
        """Test Logfire token"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                "https://logfire.pydantic.dev/api/v1/projects",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def validate_ollama_endpoint(self, api_base: str) -> bool:
        """Test Ollama endpoint"""
        try:
            response = requests.get(f"{api_base}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def validate_lm_studio_endpoint(self, api_base: str) -> bool:
        """Test LM Studio endpoint"""
        try:
            response = requests.get(f"{api_base}/v1/models", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def validate_openai_compatible_key(self, api_key: str, api_base: str) -> bool:
        """Test OpenAI-compatible API key (DeepSeek, OpenRouter, etc.)"""
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(
                f"{api_base}/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def validate_groq_key(self, api_key: str) -> bool:
        """Test Groq API key"""
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "=" * 60)
        
        if self.errors:
            print("VALIDATION FAILED")
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors:
            print("VALIDATION SUCCESSFUL")
            if not self.warnings:
                print("Configuration is valid and all API keys verified")
            else:
                print("Configuration is valid with warnings")
        
        print("=" * 60)


if __name__ == "__main__":
    # Get config file from command line or use default
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yml.local"
    
    validator = ConfigValidator(config_file)
    if not validator.validate():
        sys.exit(1)
    sys.exit(0)
