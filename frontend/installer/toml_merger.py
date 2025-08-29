# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache 2.0 License.
# See the LICENSE.md file in the project root for full license information.

"""
TOML Configuration Merger for pyproject.toml management.
Merges base pyproject.toml with local overrides to maintain user database configurations.
"""

import toml
from pathlib import Path
from typing import Dict, Any
import sys


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.
    
    Args:
        base: Base dictionary (pyproject.toml)
        override: Override dictionary (pyproject.local.toml)
    
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursive merge for nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Override value
            result[key] = value
    
    return result


def merge_pyproject_files(
    base_path: Path = Path("pyproject.toml"),
    local_path: Path = Path("pyproject.local.toml"),
    output_path: Path = Path(".pyproject.merged.toml")
) -> bool:
    """
    Merge base pyproject.toml with local overrides.
    
    Args:
        base_path: Path to base pyproject.toml
        local_path: Path to local overrides (may not exist)
        output_path: Path for merged output
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load base configuration
        if not base_path.exists():
            print(f"Error: Base file {base_path} not found")
            return False
        
        with open(base_path, 'r') as f:
            base_config = toml.load(f)
        
        # Load local overrides if they exist
        if local_path.exists():
            with open(local_path, 'r') as f:
                local_config = toml.load(f)
            
            # Merge configurations
            merged = deep_merge(base_config, local_config)
            print(f"Merged {base_path} with {local_path}")
        else:
            # No local overrides, use base only
            merged = base_config
            print(f"No local overrides found, using base configuration only")
        
        # Write merged configuration
        with open(output_path, 'w') as f:
            toml.dump(merged, f)
        
        print(f"Merged configuration written to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error merging TOML files: {e}")
        return False


def create_local_config_from_chosen_db(
    chosen_db_path: Path = Path("installer/chosen_db.json"),
    local_path: Path = Path("pyproject.local.toml")
) -> bool:
    """
    Create or update pyproject.local.toml based on chosen_db.json selections.
    
    Args:
        chosen_db_path: Path to chosen_db.json from installer
        local_path: Path to pyproject.local.toml to create/update
    
    Returns:
        True if successful, False otherwise
    """
    import json
    
    try:
        # Load database selections
        if not chosen_db_path.exists():
            print(f"No database selection file found at {chosen_db_path}")
            # Create default with PostgreSQL and SQLite (included in base)
            local_config = {}
        else:
            with open(chosen_db_path, 'r') as f:
                chosen_db = json.load(f)
            
            # Build optional dependencies based on selections
            optional_deps = {}
            
            # Check for MariaDB
            if chosen_db.get("mariadb", False):
                optional_deps["mariadb"] = ["mariadb>=1.1.0"]
            
            # Check for SQL Server
            if chosen_db.get("sqlserver", False):
                optional_deps["sqlserver"] = ["pyodbc>=4.0.0"]
            
            # If both are selected, also create all-databases
            if chosen_db.get("mariadb", False) and chosen_db.get("sqlserver", False):
                optional_deps["all-databases"] = [
                    "mariadb>=1.1.0",
                    "pyodbc>=4.0.0"
                ]
            
            # Create local config structure
            local_config = {}
            if optional_deps:
                local_config["project"] = {"optional-dependencies": optional_deps}
        
        # Write local configuration
        with open(local_path, 'w') as f:
            if local_config:
                toml.dump(local_config, f)
                print(f"Created {local_path} with database selections")
            else:
                # Empty file for default (PostgreSQL + SQLite only)
                f.write("# Using default database configuration (PostgreSQL + SQLite)\n")
                print(f"Created {local_path} with default configuration")
        
        return True
        
    except Exception as e:
        print(f"Error creating local config: {e}")
        return False


if __name__ == "__main__":
    # Command line interface
    if len(sys.argv) > 1:
        if sys.argv[1] == "merge":
            # Merge configurations
            success = merge_pyproject_files()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "create-local":
            # Create local config from chosen_db.json
            success = create_local_config_from_chosen_db()
            sys.exit(0 if success else 1)
    else:
        print("Usage:")
        print("  python toml_merger.py merge         # Merge pyproject.toml with local overrides")
        print("  python toml_merger.py create-local  # Create local config from chosen_db.json")
        sys.exit(1)