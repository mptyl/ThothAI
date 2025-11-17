#!/usr/bin/env python3
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
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
import toml


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
        
        # Projects to update (base and local paths)
        self.projects = [
            {
                'name': 'backend',
                'base': self.root_dir / "backend" / "pyproject.toml",
                'local': self.root_dir / "backend" / "pyproject.toml.local",
            },
            {
                'name': 'frontend/sql_generator',
                'base': self.root_dir / "frontend" / "sql_generator" / "pyproject.toml",
                'local': self.root_dir / "frontend" / "sql_generator" / "pyproject.toml.local",
            }
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
    
    def _extract_qdrant_dep(self, base_path: Path) -> Optional[Dict[str, str]]:
        """Extract thoth-qdrant dep (name, op, version) from base pyproject"""
        if not base_path.exists():
            return None
        data = toml.load(base_path)
        deps = data.get('project', {}).get('dependencies', [])
        for d in deps:
            if isinstance(d, str) and d.startswith('thoth-qdrant'):
                m = re.match(r'^(thoth-qdrant)(?:\[[^\]]+\])?(==|>=)([0-9.]+)$', d)
                if m:
                    return {'name': m.group(1), 'op': m.group(2), 'ver': m.group(3)}
        return None

    def update_pyproject_local(self, base_path: Path, local_path: Path, embedding_extra: str) -> bool:
        """Ensure pyproject.toml.local declares thoth-qdrant with the right extra.
        Avoids editing tracked pyproject.toml.
        """
        try:
            q = self._extract_qdrant_dep(base_path)
            if not q:
                print(f"Warning: thoth-qdrant not found in {base_path}, skipping")
                return True

            desired = f"thoth-qdrant[{embedding_extra}]{q['op']}{q['ver']}"

            # Load or init local config
            if local_path.exists():
                local_cfg = toml.load(local_path)
            else:
                local_cfg = {'tool': {'uv': {'sources': {}}}, 'project': {'dependencies': []}}

            deps = local_cfg.setdefault('project', {}).setdefault('dependencies', [])
            # Remove any previous thoth-qdrant override
            deps = [d for d in deps if not (isinstance(d, str) and d.startswith('thoth-qdrant'))]
            deps.append(desired)
            local_cfg['project']['dependencies'] = deps

            with open(local_path, 'w') as f:
                toml.dump(local_cfg, f)

            print(f"  {local_path.relative_to(self.root_dir)}: set {desired}")
            return True

        except Exception as e:
            print(f"Error updating {local_path}: {e}")
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
        
        # Update pyproject.toml.local files instead of tracked base files
        success = True
        for proj in self.projects:
            if not self.update_pyproject_local(proj['base'], proj['local'], embedding_extra):
                success = False
        
        if not success:
            print("Some pyproject.toml files failed to update")
            return False
        
        # Do not run uv sync here to avoid touching lockfiles in working tree.
        # Docker builds use backend/pyproject.toml.merged which is generated by installer.
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
