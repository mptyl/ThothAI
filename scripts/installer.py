#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Thoth AI Installer
Configures and builds the Thoth AI system based on YAML configuration
"""

import os
import sys
import yaml
import subprocess
import shutil
import getpass
import hashlib
import secrets
import string
from pathlib import Path
from typing import Dict, Any, List, Optional
import toml
import json

class ThothInstaller:
    def __init__(self, config_path: str = "config.yml.local"):
        self.base_dir = Path.cwd()
        self.config_path = Path(config_path)
        self.config = None
        self.errors = []
        self.password_file = self.base_dir / '.admin_password.hash'
        
    def run(self) -> bool:
        """Main installation pipeline"""
        print("=" * 60)
        print("  Thoth AI Installer")
        print("=" * 60)
        
        # Step 1: Load and validate configuration
        if not self.load_config():
            return False
            
        # Step 2: Request admin password
        if not self.get_admin_password():
            return False
            
        # Step 3: Generate pyproject.toml.local files
        if not self.generate_pyproject_locals():
            return False
            
        # Step 4: Merge pyproject.toml files
        if not self.merge_pyprojects():
            return False
            
        # Step 5: Generate .env.docker
        if not self.generate_env_docker():
            return False
            
        # Step 6: Create Docker network if needed
        if not self.create_docker_network():
            return False
            
        # Step 7: Create Docker volumes if needed
        if not self.create_docker_volumes():
            return False
            
        # Step 8: Generate Django secrets if needed
        if not self.generate_django_secrets():
            return False
            
        # Step 9: Build and start Docker containers
        if not self.docker_compose_up():
            return False
            
        print("\nInstallation completed successfully!")
        self.print_access_info()
        return True
    
    def load_config(self) -> bool:
        """Load and validate YAML configuration"""
        print("\nLoading configuration...")
        
        # Check if config.yml.local exists
        if not self.config_path.exists():
            if Path("config.yml").exists():
                print("config.yml.local not found")
                print("Creating from template...")
                shutil.copy("config.yml", self.config_path)
                print(f"Please edit {self.config_path} with your configuration and run installer again")
                return False
            else:
                print("Error: No configuration file found")
                return False
        
        # Load YAML
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
            
        # Basic validation (detailed validation in validate_config.py)
        return self.validate_basic_config()
    
    def validate_basic_config(self) -> bool:
        """Basic configuration validation"""
        print("Validating configuration...")
        
        # Check for at least one AI provider
        providers = self.config.get('ai_providers', {})
        active_providers = [
            name for name, data in providers.items()
            if data.get('enabled') and data.get('api_key')
        ]
        
        if not active_providers:
            self.errors.append("At least one AI provider must be configured with a valid API key")
        
        # Check embedding configuration
        embedding = self.config.get('embedding', {})
        if not embedding.get('provider'):
            self.errors.append("Embedding provider must be configured")
        
        # Check monitoring if enabled
        monitoring = self.config.get('monitoring', {})
        if monitoring.get('enabled', True):
            if not monitoring.get('logfire_token'):
                self.errors.append("Monitoring is enabled but Logfire token not provided")
        
        if self.errors:
            print("\nConfiguration errors found:")
            for error in self.errors:
                print(f"  - {error}")
            return False
        
        print("Configuration valid")
        return True
    
    def get_admin_password(self) -> bool:
        """Handle admin password with state management"""
        print("\nAdmin Password Configuration")
        print("-" * 30)
        
        # Check if password is already in config
        if 'password' in self.config.get('admin', {}):
            password = self.config['admin']['password']
            if len(password) >= 8:
                print("Using password from configuration")
                # Save hash for future reference
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                with open(self.password_file, 'w') as f:
                    f.write(password_hash)
                self.password_file.chmod(0o600)  # Secure file permissions
                return True
            else:
                print("Password in configuration is too short (min 8 chars)")
        
        # Check if password already exists
        if self.password_file.exists():
            print("Admin password: ******")
            choice = input("Keep existing password? [Y/n]: ").strip().lower()
            
            if choice in ['', 'y', 'yes']:
                # Read stored password (in production, this would be encrypted)
                # For now, we'll need to ask again as we only store the hash
                print("Using existing password configuration")
                # In a real implementation, we'd decrypt the stored password
                # For this version, we'll ask for it again
                password = getpass.getpass("Enter existing admin password: ")
                self.config['admin']['password'] = password
                return True
            else:
                print("Enter new password")
        
        # Get new password
        while True:
            password = getpass.getpass("Admin password (min 8 chars): ")
            if len(password) < 8:
                print("Password must be at least 8 characters")
                continue
                
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Passwords do not match")
                continue
                
            # Store password in config
            self.config['admin']['password'] = password
            
            # Save hash for future reference
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            with open(self.password_file, 'w') as f:
                f.write(password_hash)
            self.password_file.chmod(0o600)  # Secure file permissions
            
            print("Password configured")
            return True
    
    def generate_pyproject_locals(self) -> bool:
        """Generate pyproject.toml.local files based on database configuration"""
        print("\nGenerating dependency configurations...")
        
        databases = self.config.get('databases', {})
        
        # Build database extras list
        db_extras = ['sqlite']  # Always include sqlite
        if databases.get('postgresql'):
            db_extras.append('postgresql')
        if databases.get('mysql'):
            db_extras.append('mysql')
        if databases.get('mariadb'):
            db_extras.append('mariadb')
        if databases.get('sqlserver'):
            db_extras.append('sqlserver')
        
        # Generate backend pyproject.toml.local
        backend_local = {
            'tool': {
                'uv': {
                    'sources': {
                        'thoth-dbmanager': {
                            'index': 'pypi'
                        }
                    }
                }
            },
            'project': {
                'dependencies': [
                    f"thoth-dbmanager[{','.join(db_extras)}]"
                ]
            }
        }
        
        backend_path = self.base_dir / 'backend' / 'pyproject.toml.local'
        backend_path.parent.mkdir(exist_ok=True)
        with open(backend_path, 'w') as f:
            toml.dump(backend_local, f)
        print(f"Generated {backend_path}")
        
        # SQL generator doesn't need database-specific dependencies
        # but we create an empty .local for consistency
        sql_gen_local = {
            'tool': {'uv': {'sources': {}}},
            'project': {'dependencies': []}
        }
        sql_gen_path = self.base_dir / 'frontend' / 'sql_generator' / 'pyproject.toml.local'
        sql_gen_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sql_gen_path, 'w') as f:
            toml.dump(sql_gen_local, f)
        print(f"Generated {sql_gen_path}")
        
        return True
    
    def merge_pyprojects(self) -> bool:
        """Merge base and local pyproject.toml files"""
        print("\nMerging pyproject.toml files...")
        
        for project_dir in ['backend', 'frontend/sql_generator']:
            project_path = self.base_dir / project_dir
            base_path = project_path / 'pyproject.toml'
            local_path = project_path / 'pyproject.toml.local'
            merged_path = project_path / 'pyproject.toml.merged'
            
            if not base_path.exists():
                print(f"Warning: Base pyproject.toml not found in {project_dir}")
                continue
            
            # Load base
            with open(base_path) as f:
                base_config = toml.load(f)
            
            # Load local if exists
            if local_path.exists():
                with open(local_path) as f:
                    local_config = toml.load(f)
                
                # Merge dependencies
                if 'project' in local_config and 'dependencies' in local_config['project']:
                    base_deps = base_config.get('project', {}).get('dependencies', [])
                    local_deps = local_config['project']['dependencies']
                    
                    # Remove any existing thoth-dbmanager dependency
                    base_deps = [d for d in base_deps if not d.startswith('thoth-dbmanager')]
                    
                    # Add new dependencies from local
                    base_deps.extend(local_deps)
                    
                    if 'project' not in base_config:
                        base_config['project'] = {}
                    base_config['project']['dependencies'] = base_deps
                
                # Merge tool.uv.sources if exists
                if 'tool' in local_config and 'uv' in local_config['tool'] and 'sources' in local_config['tool']['uv']:
                    if 'tool' not in base_config:
                        base_config['tool'] = {}
                    if 'uv' not in base_config['tool']:
                        base_config['tool']['uv'] = {}
                    if 'sources' not in base_config['tool']['uv']:
                        base_config['tool']['uv']['sources'] = {}
                    base_config['tool']['uv']['sources'].update(local_config['tool']['uv']['sources'])
            
            # Write merged
            with open(merged_path, 'w') as f:
                toml.dump(base_config, f)
            
            print(f"Created {merged_path}")
        
        return True
    
    def generate_env_docker(self) -> bool:
        """Generate .env.docker file from configuration"""
        print("\nGenerating environment configuration...")
        
        env_lines = []
        
        # All AI Providers from config
        providers = self.config.get('ai_providers', {})
        
        # OpenAI
        if providers.get('openai', {}).get('enabled'):
            env_lines.append(f"OPENAI_API_KEY={providers['openai']['api_key']}")
        
        # Anthropic
        if providers.get('anthropic', {}).get('enabled'):
            env_lines.append(f"ANTHROPIC_API_KEY={providers['anthropic']['api_key']}")
        
        # Gemini
        if providers.get('gemini', {}).get('enabled'):
            env_lines.append(f"GEMINI_API_KEY={providers['gemini']['api_key']}")
        
        # Mistral
        if providers.get('mistral', {}).get('enabled'):
            env_lines.append(f"MISTRAL_API_KEY={providers['mistral']['api_key']}")
        
        # DeepSeek
        if providers.get('deepseek', {}).get('enabled'):
            env_lines.append(f"DEEPSEEK_API_KEY={providers['deepseek']['api_key']}")
            env_lines.append(f"DEEPSEEK_API_BASE={providers['deepseek']['api_base']}")
        
        # OpenRouter
        if providers.get('openrouter', {}).get('enabled'):
            env_lines.append(f"OPENROUTER_API_KEY={providers['openrouter']['api_key']}")
            env_lines.append(f"OPENROUTER_API_BASE={providers['openrouter']['api_base']}")
        
        # Ollama (no API key needed)
        if providers.get('ollama', {}).get('enabled'):
            env_lines.append(f"OLLAMA_API_BASE={providers['ollama']['api_base']}")
        
        # LM Studio (no API key needed)
        if providers.get('lm_studio', {}).get('enabled'):
            env_lines.append(f"LM_STUDIO_API_BASE={providers['lm_studio']['api_base']}")
        
        # Embedding
        embedding = self.config.get('embedding', {})
        env_lines.append(f"EMBEDDING_PROVIDER={embedding.get('provider')}")
        env_lines.append(f"EMBEDDING_MODEL={embedding.get('model')}")
        
        if embedding.get('api_key'):
            env_lines.append(f"EMBEDDING_API_KEY={embedding['api_key']}")
        else:
            # Use provider's key if available
            provider_name = embedding.get('provider')
            if provider_name in providers and providers[provider_name].get('enabled'):
                env_lines.append(f"EMBEDDING_API_KEY={providers[provider_name]['api_key']}")
        
        # Monitoring
        monitoring = self.config.get('monitoring', {})
        if monitoring.get('enabled', True):
            env_lines.append(f"LOGFIRE_TOKEN={monitoring.get('logfire_token', '')}")
        
        # Admin
        admin = self.config.get('admin', {})
        if admin.get('email'):
            env_lines.append(f"DJANGO_SUPERUSER_EMAIL={admin['email']}")
        env_lines.append(f"DJANGO_SUPERUSER_USERNAME={admin.get('username', 'admin')}")
        env_lines.append(f"DJANGO_SUPERUSER_PASSWORD={admin['password']}")
        
        # Ports
        ports = self.config.get('ports', {})
        env_lines.append(f"FRONTEND_PORT={ports.get('frontend', 3040)}")
        env_lines.append(f"BACKEND_PORT={ports.get('backend', 8040)}")
        env_lines.append(f"SQL_GENERATOR_PORT={ports.get('sql_generator', 8020)}")
        env_lines.append(f"WEB_PORT={ports.get('nginx', 80)}")
        
        # Development settings
        dev = self.config.get('development', {})
        env_lines.append(f"DEBUG={str(dev.get('debug', False)).upper()}")
        env_lines.append(f"LOG_LEVEL={dev.get('log_level', 'INFO')}")
        
        # Additional required environment variables
        env_lines.append('DB_ROOT_PATH=/app/data')
        env_lines.append('DB_NAME_DOCKER=/app/backend_db/db.sqlite3')
        env_lines.append('DB_NAME_LOCAL=db.sqlite3')
        env_lines.append('NODE_ENV=production')
        env_lines.append('BACKEND_LOGGING_LEVEL=INFO')
        env_lines.append('FRONTEND_LOGGING_LEVEL=INFO')
        
        # Write .env.docker
        env_path = self.base_dir / '.env.docker'
        with open(env_path, 'w') as f:
            f.write('# Auto-generated by Thoth installer\n')
            f.write('# DO NOT EDIT - Modify config.yaml.local instead\n\n')
            f.write('\n'.join(env_lines))
            f.write('\n')
        
        # Secure file permissions
        env_path.chmod(0o600)
        
        print(f"Generated {env_path}")
        return True
    
    def create_docker_volumes(self) -> bool:
        """Create required Docker volumes if they don't exist"""
        print("\nSetting up Docker volumes...")
        
        volumes = [
            'thoth-secrets',
            'thoth-backend-static',
            'thoth-backend-media',
            'thoth-frontend-cache',
            'thoth-qdrant-data',
            'thoth-shared-data'
        ]
        
        for volume_name in volumes:
            # Check if volume exists
            result = subprocess.run(
                ['docker', 'volume', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True
            )
            
            if volume_name in result.stdout.split('\n'):
                print(f"Volume '{volume_name}' already exists")
            else:
                result = subprocess.run(
                    ['docker', 'volume', 'create', volume_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Error: Failed to create volume '{volume_name}': {result.stderr}")
                    return False
                print(f"Created volume '{volume_name}'")
        
        return True
    
    def generate_django_secrets(self) -> bool:
        """Generate Django secret key and API key if they don't exist"""
        print("\nGenerating Django secrets...")
        
        def generate_secret_key(length=50):
            """Generate a Django-compatible secret key"""
            chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
            return ''.join(secrets.choice(chars) for _ in range(length))
        
        def generate_api_key(length=32):
            """Generate a secure API key using URL-safe base64 encoding"""
            return secrets.token_urlsafe(length)
        
        # Check if secrets already exist in the volume
        check_cmd = [
            'docker', 'run', '--rm', 
            '-v', 'thoth-secrets:/secrets',
            'alpine', 'ls', '/secrets/'
        ]
        
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        existing_files = result.stdout.split('\n') if result.returncode == 0 else []
        
        secrets_to_generate = []
        
        if 'django_secret_key' not in existing_files:
            secret_key = generate_secret_key()
            secrets_to_generate.append(('django_secret_key', secret_key))
            print("Generating new Django SECRET_KEY")
        else:
            print("Django SECRET_KEY already exists")
        
        if 'django_api_key' not in existing_files:
            api_key = generate_api_key()
            secrets_to_generate.append(('django_api_key', api_key))
            print("Generating new Django API_KEY")
        else:
            print("Django API_KEY already exists")
        
        # Write secrets to volume if needed
        for filename, content in secrets_to_generate:
            write_cmd = [
                'docker', 'run', '--rm',
                '-v', 'thoth-secrets:/secrets',
                'alpine', 'sh', '-c',
                f'echo "{content}" > /secrets/{filename} && chmod 640 /secrets/{filename}'
            ]
            
            result = subprocess.run(write_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error: Failed to write {filename}: {result.stderr}")
                return False
            print(f"Successfully generated {filename}")
        
        return True
    
    def create_docker_network(self) -> bool:
        """Create Docker network if it doesn't exist"""
        print("\nSetting up Docker network...")
        
        network_name = self.config.get('docker', {}).get('network_name', 'thoth-network')
        
        # Check if network exists
        result = subprocess.run(
            ['docker', 'network', 'ls', '--format', '{{.Name}}'],
            capture_output=True,
            text=True
        )
        
        if network_name in result.stdout.split('\n'):
            print(f"Network '{network_name}' already exists")
        else:
            result = subprocess.run(
                ['docker', 'network', 'create', network_name],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Error: Failed to create network: {result.stderr}")
                return False
            print(f"Created network '{network_name}'")
        
        return True
    
    def docker_compose_up(self) -> bool:
        """Build and start Docker containers"""
        print("\nBuilding and starting Docker containers...")
        print("This may take several minutes on first run...\n")
        
        compose_file = self.config.get('docker', {}).get('compose_file', 'docker-compose.yml')
        
        # Check if docker-compose file exists
        if not Path(compose_file).exists():
            print(f"Error: {compose_file} not found")
            return False
        
        # Build with cache option
        build_args = ['docker', 'compose', '-f', compose_file, 'build']
        if not self.config.get('docker', {}).get('build_cache', True):
            build_args.append('--no-cache')
        
        print("Building Docker images...")
        result = subprocess.run(build_args)
        if result.returncode != 0:
            print("Error: Docker build failed")
            return False
        
        # Start containers
        print("Starting containers...")
        result = subprocess.run(
            ['docker', 'compose', '-f', compose_file, 'up', '-d']
        )
        if result.returncode != 0:
            print("Error: Failed to start containers")
            return False
        
        print("All services started successfully")
        return True
    
    def print_access_info(self):
        """Print access information"""
        ports = self.config.get('ports', {})
        admin = self.config.get('admin', {})
        
        print("\n" + "=" * 60)
        print("  Thoth AI is ready!")
        print("=" * 60)
        print("\nAccess URLs:")
        print(f"  Main Application:  http://localhost:{ports.get('nginx', 80)}")
        print(f"  Frontend Direct:   http://localhost:{ports.get('frontend', 3040)}")
        print(f"  Backend API:       http://localhost:{ports.get('backend', 8040)}")
        print(f"  Admin Panel:       http://localhost:{ports.get('nginx', 80)}/admin")
        
        print("\nLogin Credentials:")
        if admin.get('email'):
            print(f"  Email:    {admin['email']}")
        print(f"  Username: {admin.get('username', 'admin')}")
        print(f"  Password: [as configured]")
        
        print("\nUseful Commands:")
        print("  View logs:    docker compose logs -f")
        print("  Stop:         docker compose down")
        print("  Restart:      docker compose restart")
        
        # Platform-specific update command
        import platform
        if platform.system() == "Windows":
            print("  Update:       git pull && .\\install.ps1")
        else:
            print("  Update:       git pull && ./install.sh")


if __name__ == "__main__":
    installer = ThothInstaller()
    if not installer.run():
        sys.exit(1)