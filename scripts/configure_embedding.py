#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
ThothAI Embedding Configuration Script
Configures thoth-qdrant extras based on embedding provider in config.yml.local
"""

import yaml
import sys
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, List


class EmbeddingConfigurator:
    def __init__(self, config_path: str = "config.yml.local"):
        self.config_path = Path(config_path)
        self.config = None
        self.root_dir = Path.cwd()
        
        # Provider to extra mapping
        self.provider_extra_map = {
            'openai': 'openai',
            'mistral': 'mistral', 
            'cohere': 'cohere'
        }
        
        # pyproject.toml files to update
        self.pyproject_files = [
            self.root_dir / "backend" / "pyproject.toml",
            self.root_dir / "frontend" / "sql_generator" / "pyproject.toml"
        ]
    
    def load_config(self) -> bool:
        """Load YAML configuration file"""
        if not self.config_path.exists():
            print(f"Error: Configuration file {self.config_path} not found")
            return False
        
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def get_embedding_provider(self) -> Optional[str]:
        """Get the configured embedding provider"""
        if not self.config:
            return None
        
        embedding = self.config.get('embedding', {})
        provider = embedding.get('provider')
        
        if not provider:
            print("Warning: No embedding provider configured")
            return None
        
        if provider not in self.provider_extra_map:
            print(f"Warning: Unknown embedding provider '{provider}', supported: {list(self.provider_extra_map.keys())}")
            return None
        
        return provider
    
    def update_pyproject_toml(self, file_path: Path, embedding_extra: str) -> bool:
        """Update pyproject.toml with the correct thoth-qdrant extra"""
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping")
            return True
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Pattern to match thoth-qdrant dependency with any extras
            pattern = r'(thoth-qdrant)\[([^\]]+)\](==|>=)([0-9.]+)'
            
            # Find current thoth-qdrant dependency
            match = re.search(pattern, content)
            if not match:
                print(f"Warning: thoth-qdrant dependency not found in {file_path}")
                return True
            
            current_line = match.group(0)
            package_name = match.group(1)
            operator = match.group(3)
            version = match.group(4)
            
            # Replace with new extra
            new_line = f"{package_name}[{embedding_extra}]{operator}{version}"
            
            if current_line == new_line:
                print(f"  {file_path.relative_to(self.root_dir)}: Already configured for {embedding_extra}")
                return True
            
            # Replace in content - use the full match which includes quotes and commas
            full_match = match.group(0)
            new_content = content.replace(full_match, new_line)
            
            # Write back to file
            with open(file_path, 'w') as f:
                f.write(new_content)
            
            print(f"  {file_path.relative_to(self.root_dir)}: Updated thoth-qdrant[{embedding_extra}]")
            return True
            
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False
    
    def run_uv_sync(self, project_dir: Path) -> bool:
        """Run uv sync in the specified project directory"""
        try:
            print(f"  Running uv sync in {project_dir.relative_to(self.root_dir)}...")
            result = subprocess.run(
                ["uv", "sync"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"  ✓ Dependencies synchronized successfully")
                return True
            else:
                print(f"  ✗ uv sync failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ✗ uv sync timed out")
            return False
        except FileNotFoundError:
            print(f"  ✗ uv command not found - please install uv first")
            return False
        except Exception as e:
            print(f"  ✗ Error running uv sync: {e}")
            return False
    
    def configure(self) -> bool:
        """Main configuration method"""
        print("Configuring embedding provider dependencies...")
        
        # Load configuration
        if not self.load_config():
            return False
        
        # Get embedding provider
        provider = self.get_embedding_provider()
        if not provider:
            print("No valid embedding provider found - keeping current configuration")
            return True
        
        embedding_extra = self.provider_extra_map[provider]
        print(f"Configuring for embedding provider: {provider} (extra: {embedding_extra})")
        
        # Update pyproject.toml files
        success = True
        for pyproject_file in self.pyproject_files:
            if not self.update_pyproject_toml(pyproject_file, embedding_extra):
                success = False
        
        if not success:
            print("Some pyproject.toml files failed to update")
            return False
        
        # Run uv sync for each project
        project_dirs = [
            self.root_dir / "backend",
            self.root_dir / "frontend" / "sql_generator"
        ]
        
        print("\nSynchronizing dependencies...")
        for project_dir in project_dirs:
            if not project_dir.exists():
                print(f"Warning: {project_dir} not found, skipping uv sync")
                continue
            
            if not self.run_uv_sync(project_dir):
                print(f"Warning: Failed to sync dependencies in {project_dir}")
                # Don't fail completely, as Docker build might still work
        
        print(f"\n✓ Embedding configuration completed for provider: {provider}")
        return True


def main():
    """Main entry point"""
    # Get config file from command line or use default
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yml.local"
    
    configurator = EmbeddingConfigurator(config_file)
    if not configurator.configure():
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()