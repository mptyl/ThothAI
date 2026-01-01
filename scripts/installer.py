#!/usr/bin/env python3
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
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
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import toml
import json

class ThothInstaller:
    def __init__(self, config_path: str = "config.yml.local", no_cache: bool = False, build_locally: bool = False):
        self.base_dir = Path.cwd()
        self.config_path = Path(config_path)
        self.config = None
        self.errors = []
        self.password_file = self.base_dir / '.admin_password.hash'
        self.no_cache = no_cache
        self.build_locally = build_locally
        
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
            
        # Step 3: Generate .env.docker
        if not self.generate_env_docker():
            return False
            
        # Step 4: Create Docker network if needed
        if not self.create_docker_network():
            return False
            
        # Step 5: Create Docker volumes if needed
        if not self.create_docker_volumes():
            return False
            
        # Step 6: Generate Django secrets if needed
        if not self.generate_django_secrets():
            return False
            
        # Step 7: Build and start Docker containers
        if not self.docker_compose_up():
            return False
            
        # Step 8: Wait for backend to be ready
        if not self.wait_for_backend():
            return False
            
        # Step 9: Run initial setup commands if greenfield
        if not self.run_initial_setup_commands():
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
        
        # Groq
        if providers.get('groq', {}).get('enabled'):
            env_lines.append(f"GROQ_API_KEY={providers['groq']['api_key']}")
        
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

        # Backend AI model selection
        backend_ai = self.config.get('backend_ai_model', {})
        if backend_ai:
            env_lines.append(f"BACKEND_AI_PROVIDER={backend_ai.get('ai_provider','')}")
            env_lines.append(f"BACKEND_AI_MODEL={backend_ai.get('ai_model','')}")

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
        mermaid_port = ports.get('mermaid_service') or ports.get('mermaid') or 8003
        env_lines.append(f"MERMAID_SERVICE_PORT={mermaid_port}")
        env_lines.append("MERMAID_SERVICE_URL=http://mermaid-service:8001")

        # Development settings
        # Runtime settings
        runtime = self.config.get('runtime', {})
        env_lines.append(f"DEBUG={str(runtime.get('debug', False)).upper()}")
        backend_level = str(runtime.get('backend_log_level', 'INFO')).upper()
        frontend_level = str(runtime.get('frontend_log_level', 'INFO')).upper()
        env_lines.append(f"BACKEND_LOGGING_LEVEL={backend_level}")
        env_lines.append(f"FRONTEND_LOGGING_LEVEL={frontend_level}")
        
        # Database plugins - generate ENABLED_DATABASES for runtime filtering
        # This allows using generic Docker images with all drivers while only
        # exposing databases explicitly enabled in config.yml.local
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
        
        # Additional required environment variables
        env_lines.append('DB_ROOT_PATH=/app/data')
        env_lines.append('DB_NAME_DOCKER=/app/backend_db/db.sqlite3')
        env_lines.append('DB_NAME_LOCAL=db.sqlite3')
        env_lines.append('NODE_ENV=production')
        
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
            'thoth-shared-data',
            'thoth-data-exchange'
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
            '-v', 'thoth-secrets:/vol/secrets',
            'alpine', 'ls', '/vol/secrets/'
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
                '-v', 'thoth-secrets:/vol/secrets',
                'alpine', 'sh', '-c',
                f'echo "{content}" > /vol/secrets/{filename} && chmod 640 /vol/secrets/{filename}'
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
        """Prepare images and start Docker containers"""
        print("\nPreparing Docker images...")
        
        # Determine which compose file to use and if we should pull
        if self.build_locally:
            compose_file = self.config.get('docker', {}).get('compose_file', 'docker-compose.yml')
            print(f"Local build requested. Using {compose_file}")
            
            # Build with cache option
            build_args = ['docker', 'compose', '-f', compose_file, 'build']
            if self.no_cache or not self.config.get('docker', {}).get('build_cache', True):
                build_args.append('--no-cache')
            
            print("Building Docker images...")
            result = subprocess.run(build_args)
            if result.returncode != 0:
                print("Error: Docker build failed")
                return False
        else:
            # Default behavior: pull from hub
            hub_compose = 'docker-compose-hub.yml'
            if not Path(hub_compose).exists():
                print(f"Error: {hub_compose} not found. Cannot pull images.")
                return False
                
            print(f"Attempting to pull images from Docker Hub using {hub_compose}...")
            # We need DOCKER_USERNAME for the hub compose file
            docker_username = self.config.get('docker', {}).get('username', 'tylconsulting')
            env = os.environ.copy()
            env['DOCKER_USERNAME'] = docker_username
            
            result = subprocess.run(['docker', 'compose', '-f', hub_compose, 'pull'], env=env)
            if result.returncode != 0:
                print("\n" + "!" * 60)
                print("  ERROR: Failed to pull images from Docker Hub.")
                print("  Please check your internet connection or Docker login.")
                print("  To build images locally instead, use the --build flag.")
                print("!" * 60 + "\n")
                return False
            
            print("✓ Images pulled successfully")
            compose_file = hub_compose

        # Start containers
        print(f"\nStarting containers using {compose_file}...")
        env = os.environ.copy()
        env['DOCKER_USERNAME'] = self.config.get('docker', {}).get('username', 'tylconsulting')
        
        result = subprocess.run(
            ['docker', 'compose', '-f', compose_file, 'up', '-d'],
            env=env
        )
        if result.returncode != 0:
            print("Error: Failed to start containers")
            return False
        
        print("All services started successfully")
        return True
    
    def clean_cache(self) -> bool:
        """Clean Docker build cache"""
        print("\nCleaning Docker build cache...")
        result = subprocess.run(['docker', 'builder', 'prune', '-a', '-f'])
        if result.returncode == 0:
            print("✓ Docker build cache cleaned")
            return True
        print("Error: Failed to clean Docker build cache")
        return False

    def prune_resources(self, force: bool = False) -> bool:
        """Remove all ThothAI resources"""
        if not force:
            print("\n" + "!" * 60)
            print("  WARNING: This will remove all ThothAI containers, images, volumes, and networks!")
            confirm = input("  Are you sure you want to continue? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("  Aborted.")
                return True
        
        print("\nPruning ThothAI resources...")
        
        # 1. Stop and remove containers
        print("Stopping and removing containers...")
        container_filter = 'name=thoth-'
        result = subprocess.run(['docker', 'ps', '-a', '--filter', container_filter, '--format', '{{.ID}}'], capture_output=True, text=True)
        containers = result.stdout.strip().split('\n')
        if containers and containers[0]:
            subprocess.run(['docker', 'rm', '-f'] + containers)
            print(f"✓ Removed {len(containers)} containers")
        else:
            print("No matching containers found.")

        # 2. Remove volumes
        print("Removing volumes...")
        volume_filter = 'name=thoth-'
        result = subprocess.run(['docker', 'volume', 'ls', '-q', '--filter', volume_filter], capture_output=True, text=True)
        volumes = result.stdout.strip().split('\n')
        if volumes and volumes[0]:
            subprocess.run(['docker', 'volume', 'rm'] + volumes)
            print(f"✓ Removed {len(volumes)} volumes")
        else:
            print("No matching volumes found.")

        # 3. Remove networks
        print("Removing networks...")
        network_filter = 'name=thoth-'
        result = subprocess.run(['docker', 'network', 'ls', '-q', '--filter', network_filter], capture_output=True, text=True)
        networks = result.stdout.strip().split('\n')
        # Filter out built-in networks if they somehow match
        networks = [n for n in networks if n]
        if networks:
            subprocess.run(['docker', 'network', 'rm'] + networks)
            print(f"✓ Removed {len(networks)} networks")
        else:
            print("No matching networks found.")

        # 4. Remove images
        print("Removing images...")
        # Get all images and filter manually for better pattern matching
        result = subprocess.run(['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'], capture_output=True, text=True)
        all_images = result.stdout.strip().split('\n')
        thoth_images = [img for img in all_images if img.startswith('thoth-') or img.startswith('tylconsulting/thoth-')]
        
        if thoth_images:
            subprocess.run(['docker', 'rmi', '-f'] + thoth_images)
            print(f"✓ Removed {len(thoth_images)} images")
        else:
            print("No matching images found.")

        print("\n✓ Prune completed.")
        return True
    
    def wait_for_backend(self) -> bool:
        """Wait for backend container to be ready"""
        print("\nWaiting for backend to be ready...")
        import time
        
        compose_file = self.config.get('docker', {}).get('compose_file', 'docker-compose.yml')
        max_attempts = 30
        
        for i in range(max_attempts):
            result = subprocess.run(
                ['docker', 'compose', '-f', compose_file, 'exec', '-T', 'backend', 
                 'python', '-c', 'print("ready")'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("Backend is ready")
                return True
            
            time.sleep(2)
            if i > 0 and i % 5 == 0:
                print(f"Still waiting... ({i}/{max_attempts})")
        
        print("Warning: Backend may not be fully ready")
        return True  # Continue anyway
    
    def run_initial_setup_commands(self) -> bool:
        """Run initial setup commands for greenfield installation"""
        print("\nChecking for initial setup...")
        
        compose_file = self.config.get('docker', {}).get('compose_file', 'docker-compose.yml')
        
        # Check if this is a greenfield installation
        result = subprocess.run(
            ['docker', 'compose', '-f', compose_file, 'exec', '-T', 'backend', 'python', 
             '-c', 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings"); '
                   'import django; django.setup(); from thoth_core.models import Workspace; '
                   'print(Workspace.objects.count())'],
            capture_output=True,
            text=True
        )
        
        try:
            workspace_count = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else -1
        except ValueError:
            workspace_count = -1
        
        if workspace_count == 0:
            print("Greenfield installation detected. Running initial setup commands...")
            print("=" * 60)
            
            # Check if any AI provider is configured
            providers = self.config.get('ai_providers', {})
            ai_configured = any(
                provider.get('enabled') and provider.get('api_key')
                for provider in providers.values()
            )
            
            if ai_configured:
                print("AI provider configured. Running automated analysis for demo database...")
                print("")
                
                # 1. Generate database scope
                print("1. Generating database scope...")
                result = subprocess.run(
                    ['docker', 'compose', '-f', compose_file, 'exec', '-T', 'backend', 
                     'python', 'manage.py', 'generate_db_scope_demo'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Warning: Scope generation failed or skipped")
                    if result.stderr:
                        print(f"Details: {result.stderr}")
                else:
                    print("Database scope generated successfully")
                print("")
                
                # 2. Generate database documentation
                print("2. Generating database documentation...")
                result = subprocess.run(
                    ['docker', 'compose', '-f', compose_file, 'exec', '-T', 'backend',
                     'python', 'manage.py', 'generate_db_documentation_demo'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Warning: Documentation generation failed or skipped")
                    if result.stderr:
                        print(f"Details: {result.stderr}")
                else:
                    print("Database documentation generated successfully")
                print("")
                
                # 3. Run GDPR scan
                print("3. Scanning for GDPR-sensitive data...")
                result = subprocess.run(
                    ['docker', 'compose', '-f', compose_file, 'exec', '-T', 'backend',
                     'python', 'manage.py', 'scan_gdpr_demo'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Warning: GDPR scan failed or skipped")
                    if result.stderr:
                        print(f"Details: {result.stderr}")
                else:
                    print("GDPR scan completed successfully")
                
                print("")
                print("=" * 60)
                print("AI-assisted analysis completed for demo workspace.")
                print("=" * 60)
            else:
                print("No AI provider API keys configured.")
                print("Skipping automated scope, documentation, and GDPR scan.")
                print("To enable AI features, configure one of these in config.yml.local:")
                print("  - OPENAI_API_KEY")
                print("  - ANTHROPIC_API_KEY")
                print("  - GEMINI_API_KEY")
                print("  - MISTRAL_API_KEY")
                print("  - DEEPSEEK_API_KEY")
                print("=" * 60)
        elif workspace_count > 0:
            print(f"Found {workspace_count} workspace(s). Skipping initial setup.")
        else:
            print("Could not determine workspace count. Skipping initial setup.")
        
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Thoth AI Installer')
    parser.add_argument('--no-cache', action='store_true',
                        help='Build Docker images without cache')
    parser.add_argument('--build', action='store_true',
                        help='Build images locally instead of pulling from Docker Hub')
    parser.add_argument('--pull', action='store_true',
                        help='Pull images from Docker Hub (default)')
    parser.add_argument('--prune', action='store_true',
                        help='Remove all ThothAI resources (containers, volumes, images, networks)')
    parser.add_argument('--clean-cache', action='store_true',
                        help='Clean Docker build cache')
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation for prune')
    parser.add_argument('--generate-env-only', action='store_true',
                        help='Generate .env.docker and exit (no Docker actions)')
    parser.add_argument('--config', default='config.yml.local',
                        help='Path to configuration file (default: config.yml.local)')
    args = parser.parse_args()
    
    # Create installer with parsed arguments
    installer = ThothInstaller(
        config_path=args.config, 
        no_cache=args.no_cache,
        build_locally=args.build
    )

    if args.generate_env_only:
        if not installer.load_config():
            sys.exit(1)
        if not installer.generate_env_docker():
            sys.exit(1)
        sys.exit(0)

    if args.clean_cache:
        if not installer.clean_cache():
            sys.exit(1)
        if not args.prune: # If only clean-cache, exit here
            sys.exit(0)

    if args.prune:
        if not installer.prune_resources(force=args.force):
            sys.exit(1)
        sys.exit(0)

    if not installer.run():
        sys.exit(1)
