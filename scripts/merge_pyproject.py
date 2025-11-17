#!/usr/bin/env python3
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Merge pyproject.toml files
Merges base pyproject.toml with pyproject.toml.local to create pyproject.toml.merged
"""

import toml
import sys
from pathlib import Path
from typing import Dict, Any, List

def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries"""
    result = base.copy()
    
    for key, value in overlay.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # For lists, we extend (except for dependencies where we may want to replace)
                if key == 'dependencies':
                    # Special handling for dependencies - filter and extend
                    result[key] = merge_dependencies(result[key], value)
                else:
                    result[key].extend(value)
            else:
                result[key] = value
        else:
            result[key] = value
    
    return result

def merge_dependencies(base_deps: List[str], local_deps: List[str]) -> List[str]:
    """Merge dependency lists intelligently"""
    # Remove any existing thoth-dbmanager from base
    base_deps = [d for d in base_deps if not d.startswith('thoth-dbmanager')]
    
    # Add all local dependencies
    base_deps.extend(local_deps)
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for dep in base_deps:
        if dep not in seen:
            seen.add(dep)
            result.append(dep)
    
    return result

def merge_pyproject(project_dir: Path = Path.cwd()) -> bool:
    """Merge pyproject.toml files in the given directory"""
    base_path = project_dir / 'pyproject.toml'
    local_path = project_dir / 'pyproject.toml.local'
    merged_path = project_dir / 'pyproject.toml.merged'
    
    if not base_path.exists():
        print(f"Error: Base pyproject.toml not found in {project_dir}")
        return False
    
    print(f"Merging pyproject.toml in {project_dir}")
    
    # Load base configuration
    try:
        with open(base_path) as f:
            base_config = toml.load(f)
    except Exception as e:
        print(f"Error loading base pyproject.toml: {e}")
        return False
    
    # Load local configuration if it exists
    if local_path.exists():
        try:
            with open(local_path) as f:
                local_config = toml.load(f)
        except Exception as e:
            print(f"Error loading pyproject.toml.local: {e}")
            return False
        
        # Merge configurations
        merged_config = deep_merge(base_config, local_config)
        print(f"  Merged with {local_path.name}")
    else:
        # No local config, just use base
        merged_config = base_config
        print("  No local configuration found, using base only")
    
    # Write merged configuration
    try:
        with open(merged_path, 'w') as f:
            toml.dump(merged_config, f)
        print(f"  Created {merged_path.name}")
        return True
    except Exception as e:
        print(f"Error writing merged pyproject.toml: {e}")
        return False

def main():
    """Main entry point"""
    # Get directory from command line or use current directory
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = Path.cwd()
    
    if not project_dir.exists():
        print(f"Error: Directory {project_dir} does not exist")
        sys.exit(1)
    
    if merge_pyproject(project_dir):
        print("Merge completed successfully")
        sys.exit(0)
    else:
        print("Merge failed")
        sys.exit(1)

if __name__ == "__main__":
    main()