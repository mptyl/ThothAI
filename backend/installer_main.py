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

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import re
import os
import subprocess
import asyncio
import threading
from typing import List, Optional

app = FastAPI(title="ThothAI Database Configuration", version="1.0.0")

# Mount static files - updated for the new structure
app.mount("/static", StaticFiles(directory="installer/static"), name="static")

# Pydantic models
class DatabaseConfig(BaseModel):
    databases: List[str]
    vectordbs: List[str]

class ConfigResponse(BaseModel):
    databases: List[str]
    vectordbs: List[str]
    message: str
    local_warnings: Optional[List[str]] = None

class DockerStatusResponse(BaseModel):
    status: str
    message: str
    phase: Optional[str] = None

# Constants - updated for the new structure
PYPROJECT_FILE = "pyproject.toml"
PYPROJECT_LOCAL_FILE = "pyproject.local.toml"
PYPROJECT_MERGED_FILE = ".pyproject.merged.toml"
PYPROJECT_BACKUP = "pyproject.toml.backup"
CONFIG_FILE = "installer/chosen_db.json"
CONFIG_FILE_EXAMPLE = "installer/chosen_db.json.example"

# Sister directories and their templates - relative paths maintained for compatibility
# Absolute paths are calculated dynamically in the functions that use them
SISTER_PROJECTS = [
    {"path": "../thoth_ui", "name": "thoth_ui"},
    {"path": "../ThothUI", "name": "ThothUI"},
    {"path": "../thothui", "name": "thothui"}
]

# Versions are dynamically extracted from the template

def extract_version_from_pyproject() -> str:
    """Extract the thoth-dbmanager version from pyproject.toml"""
    if not os.path.exists(PYPROJECT_FILE):
        return "0.5.7"  # Default version
    
    try:
        with open(PYPROJECT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to find version in pyproject.toml
        dbmanager_pattern = re.compile(r'"thoth-dbmanager\[.*?\]==([\d\.]+)"')
        
        dbmanager_match = dbmanager_pattern.search(content)
        dbmanager_version = dbmanager_match.group(1) if dbmanager_match else "0.5.7"
        
        return dbmanager_version
        
    except Exception as e:
        print(f"Warning: Error extracting version from pyproject.toml: {e}")
        return "0.5.7"

# Valid database values
VALID_DATABASES = {"sqlite", "postgresql", "mariadb", "sqlserver"}  # Only supported databases
VALID_VECTORDBS = {"qdrant"}  # Only Qdrant is supported now

# Docker Compose status
docker_status = {
    "running": False,
    "phase": "idle",
    "message": "Ready"
}

# Docker Compose status for sister directory
docker_sister_status = {
    "running": False,
    "phase": "idle",
    "message": "Ready"
}

def load_config() -> dict:
    """Load configuration from JSON file with fallback to example"""
    
    # If local file doesn't exist but example exists, copy it
    if not os.path.exists(CONFIG_FILE) and os.path.exists(CONFIG_FILE_EXAMPLE):
        try:
            import shutil
            shutil.copy2(CONFIG_FILE_EXAMPLE, CONFIG_FILE)
        except Exception as e:
            print(f"Warning: Could not copy example file: {e}")
    
    # If no file exists, use defaults (SQLite and PostgreSQL)
    if not os.path.exists(CONFIG_FILE):
        return {"databases": ["sqlite", "postgresql"], "vectordbs": ["qdrant"]}
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Validate loaded data
            databases = [db for db in config.get("databases", []) if db in VALID_DATABASES]
            vectordbs = [vdb for vdb in config.get("vectordbs", []) if vdb in VALID_VECTORDBS]
            
            # Ensure SQLite is always included for databases
            if "sqlite" not in databases:
                databases.append("sqlite")
            # Qdrant is the only vector database
            vectordbs = ["qdrant"]
                
            return {"databases": databases, "vectordbs": vectordbs}
    except (json.JSONDecodeError, KeyError):
        return {"databases": ["sqlite"], "vectordbs": ["qdrant"]}

def save_config(databases: List[str], vectordbs: List[str]) -> None:
    """Save configuration to JSON file"""
    config = {
        "databases": databases,
        "vectordbs": vectordbs
    }
    # Ensure the directory exists
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def update_pyproject_local(databases: List[str]) -> None:
    """Update pyproject.local.toml with selected database extras"""
    import toml
    
    # Determine which extra databases are selected (beyond default PostgreSQL and SQLite)
    extra_databases = [db for db in databases if db not in ["postgresql", "sqlite"]]
    
    # Create local configuration
    local_config = {}
    
    if extra_databases:
        optional_deps = {}
        
        # Add MariaDB if selected
        if "mariadb" in extra_databases:
            optional_deps["mariadb"] = ["mariadb>=1.1.0"]
        
        # Add SQL Server if selected
        if "sqlserver" in extra_databases:
            optional_deps["sqlserver"] = ["pyodbc>=4.0.0"]
        
        # If both are selected, also create all-databases
        if "mariadb" in extra_databases and "sqlserver" in extra_databases:
            optional_deps["all-databases"] = [
                "mariadb>=1.1.0",
                "pyodbc>=4.0.0"
            ]
        
        local_config["project"] = {"optional-dependencies": optional_deps}
    
    # Write local configuration
    with open(PYPROJECT_LOCAL_FILE, 'w') as f:
        if local_config:
            toml.dump(local_config, f)
            print(f"[SUCCESS] Updated {PYPROJECT_LOCAL_FILE} with database selections")
        else:
            # Empty config for default (PostgreSQL + SQLite only)
            f.write("# Using default database configuration (PostgreSQL + SQLite)\n")
            print(f"[SUCCESS] Updated {PYPROJECT_LOCAL_FILE} with default configuration")

def merge_pyproject_files() -> bool:
    """Merge pyproject.toml with local overrides for uv sync"""
    try:
        # Import the merger utility
        from installer.toml_merger import merge_pyproject_files as do_merge
        from pathlib import Path
        
        # Perform the merge - convert strings to Path objects
        return do_merge(
            base_path=Path(os.path.abspath(PYPROJECT_FILE)),
            local_path=Path(os.path.abspath(PYPROJECT_LOCAL_FILE)),
            output_path=Path(os.path.abspath(PYPROJECT_MERGED_FILE))
        )
    except ImportError:
        # Fallback if toml_merger is not available
        print("Warning: toml_merger not found, using basic merge")
        import shutil
        
        if os.path.exists(PYPROJECT_LOCAL_FILE):
            # For now, just use the base file
            shutil.copy2(PYPROJECT_FILE, PYPROJECT_MERGED_FILE)
        else:
            shutil.copy2(PYPROJECT_FILE, PYPROJECT_MERGED_FILE)
        
        return True
    except Exception as e:
        print(f"Error merging TOML files: {e}")
        return False

def update_pyproject_toml(databases: List[str]) -> None:
    """Update local configuration - no longer modifies base pyproject.toml"""
    # Update the local configuration file
    update_pyproject_local(databases)
    
    # Save configuration to JSON for backward compatibility
    save_config(databases, ["qdrant"])
    
    print(f"Configuration updated for databases: {', '.join(databases)}")

def update_sister_pyproject(sister_path: str, databases: List[str]) -> bool:
    """Update pyproject.local.toml for a sister directory (frontend projects)"""
    import toml
    
    pyproject_path = os.path.join(sister_path, "pyproject.toml")
    pyproject_local_path = os.path.join(sister_path, "pyproject.local.toml")
    
    if not os.path.exists(pyproject_path):
        print(f"Warning: pyproject.toml not found in: {sister_path}")
        return False
    
    try:
        # Read the base pyproject.toml to check if it uses thoth-dbmanager
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if thoth-dbmanager exists
        if 'thoth-dbmanager' in content:
            # Determine which extra databases are selected (beyond default PostgreSQL and SQLite)
            extra_databases = [db for db in databases if db not in ["postgresql", "sqlite"]]
            
            # Create local configuration for sister project
            local_config = {}
            
            if extra_databases:
                optional_deps = {}
                
                # Add MariaDB if selected
                if "mariadb" in extra_databases:
                    optional_deps["mariadb"] = ["mariadb>=1.1.0"]
                
                # Add SQL Server if selected
                if "sqlserver" in extra_databases:
                    optional_deps["sqlserver"] = ["pyodbc>=4.0.0"]
                
                # If both are selected, also create all-databases
                if "mariadb" in extra_databases and "sqlserver" in extra_databases:
                    optional_deps["all-databases"] = [
                        "mariadb>=1.1.0",
                        "pyodbc>=4.0.0"
                    ]
                
                local_config["project"] = {"optional-dependencies": optional_deps}
            
            # Write local configuration
            with open(pyproject_local_path, 'w') as f:
                if local_config:
                    toml.dump(local_config, f)
                    print(f"[SUCCESS] Created {pyproject_local_path} with database selections")
                else:
                    # Empty config for default (PostgreSQL + SQLite only)
                    f.write("# Using default database configuration (PostgreSQL + SQLite)\n")
                    print(f"[SUCCESS] Created {pyproject_local_path} with default configuration")
            
            print(f"Frontend local config updated: {sister_path}")
            return True
        else:
            print(f"Info: No thoth-dbmanager found in {sister_path}")
            return False
        
    except Exception as e:
        print(f"Warning: Error updating sister pyproject.local.toml {sister_path}: {e}")
        return False

def update_requirements_file_legacy(file_path: str, databases: List[str], vectordbs: List[str]) -> tuple[bool, bool]:
    """Update a single requirements.txt file with new configurations"""
    if not os.path.exists(file_path):
        return False, False

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Pattern to find lines to modify (supports both == and >=)
    dbmanager_pattern = re.compile(r'^thoth-dbmanager\[.*?\](==|>=)(.+)$')
    vdbmanager_pattern = re.compile(r'^thoth-vdbmanager\[.*?\](==|>=)(.+)$')

    dbmanager_found = False
    vdbmanager_found = False

    # Modify existing lines
    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Check thoth-dbmanager
        dbmanager_match = dbmanager_pattern.match(line_stripped)
        if dbmanager_match:
            operator = dbmanager_match.group(1)  # == or >=
            version = dbmanager_match.group(2)
            db_list = ','.join(sorted(databases)) if databases else ''
            lines[i] = f"thoth-dbmanager[{db_list}]{operator}{version}\n"
            dbmanager_found = True

        # Check thoth-vdbmanager
        vdbmanager_match = vdbmanager_pattern.match(line_stripped)
        if vdbmanager_match:
            operator = vdbmanager_match.group(1)  # == or >=
            version = vdbmanager_match.group(2)
            vdb_list = ','.join(sorted(vectordbs)) if vectordbs else ''
            lines[i] = f"thoth-vdbmanager[{vdb_list}]{operator}{version}\n"
            vdbmanager_found = True

    # Write the updated file only if lines were found
    if dbmanager_found or vdbmanager_found:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    return dbmanager_found, vdbmanager_found

def update_pyproject_files(databases: List[str]) -> List[str]:
    """Update pyproject.toml in backend and sister directories
    
    Returns:
        List of warnings for local development
    """
    local_warnings = []
    
    # Update the main pyproject.toml
    try:
        update_pyproject_toml(databases)
        print("Backend pyproject.toml updated with selected databases")
        
        # Run uv sync to install the new dependencies
        print("\n" + "="*50)
        print("Updating Python dependencies...")
        print("="*50)
        
        # Check if databases requiring system dependencies are selected
        system_dep_databases = {'mariadb', 'sqlserver'}  # Database extras that require additional drivers
        selected_system_deps = [db for db in databases if db in system_dep_databases]
        
        # Prepare installation instructions for local development
        local_install_instructions = {}
        if selected_system_deps:
            import platform
            system_platform = platform.system().lower()
            
            for db in selected_system_deps:
                if db == 'mariadb':
                    if system_platform == 'darwin':
                        local_install_instructions[db] = "brew install mariadb-connector-c"
                    elif system_platform == 'linux':
                        local_install_instructions[db] = "sudo apt-get install libmariadb-dev"
                    else:
                        local_install_instructions[db] = "Install MariaDB Connector/C for your platform"
                        
                elif db == 'mysql':
                    if system_platform == 'darwin':
                        local_install_instructions[db] = "brew install mysql-client"
                    elif system_platform == 'linux':
                        local_install_instructions[db] = "sudo apt-get install libmysqlclient-dev"
                    else:
                        local_install_instructions[db] = "Install MySQL client libraries for your platform"
                        
                elif db == 'sqlserver':
                    local_install_instructions[db] = "Install ODBC drivers from https://docs.microsoft.com/en-us/sql/connect/odbc/"
        
        try:
            # Merge configuration files before uv sync
            if not merge_pyproject_files():
                raise Exception("Failed to merge configuration files")
            
            # Run uv sync with merged configuration
            print("\nInstalling Python dependencies with merged configuration...")
            # Backup original pyproject.toml
            import shutil
            backup_file = "pyproject.toml.backup"
            shutil.copy2(PYPROJECT_FILE, backup_file)
            try:
                # Temporarily replace pyproject.toml with merged version
                shutil.copy2(PYPROJECT_MERGED_FILE, PYPROJECT_FILE)
                
                result = subprocess.run(
                    ["uv", "sync"],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=os.path.abspath(".")
                )
            finally:
                # Restore original pyproject.toml
                shutil.copy2(backup_file, PYPROJECT_FILE)
                os.remove(backup_file)
            
            if result.returncode != 0:
                print("\nNote: Base dependencies installation had issues")
                print("This is expected for local development if system dependencies are missing.")
                print("Docker deployment will work correctly with all selected databases.")
            else:
                print("Base dependencies installed")
            
            # Try to install database-specific extras
            failed_local_databases = []
            if selected_system_deps:
                print("\nChecking database driver support...")
                for db in selected_system_deps:
                    # Temporarily use merged file for extra installation
                    import shutil
                    backup_file = "pyproject.toml.backup"
                    shutil.copy2(PYPROJECT_FILE, backup_file)
                    try:
                        shutil.copy2(PYPROJECT_MERGED_FILE, PYPROJECT_FILE)
                        extra_result = subprocess.run(
                            ["uv", "sync", "--extra", db],
                            capture_output=True,
                            text=True,
                            check=False,
                            cwd=os.path.abspath(".")
                        )
                    finally:
                        shutil.copy2(backup_file, PYPROJECT_FILE)
                        os.remove(backup_file)
                    if extra_result.returncode != 0:
                        # Try with MARIADB_CONFIG environment variable for MariaDB
                        if db == 'mariadb':
                            mariadb_config_paths = [
                                '/usr/local/bin/mariadb_config',
                                '/usr/bin/mariadb_config',
                                '/opt/homebrew/bin/mariadb_config',
                                '/opt/local/bin/mariadb_config'
                            ]
                            for path in mariadb_config_paths:
                                if os.path.exists(path):
                                    os.environ['MARIADB_CONFIG'] = path
                                    # Use merged configuration for retry
                                    backup_file2 = "pyproject.toml.backup2"
                                    shutil.copy2(PYPROJECT_FILE, backup_file2)
                                    try:
                                        shutil.copy2(PYPROJECT_MERGED_FILE, PYPROJECT_FILE)
                                        retry_result = subprocess.run(
                                            ["uv", "sync", "--extra", db],
                                            capture_output=True,
                                            text=True,
                                            check=False,
                                            cwd=os.path.abspath("."),
                                            env=os.environ.copy()
                                        )
                                    finally:
                                        shutil.copy2(backup_file2, PYPROJECT_FILE)
                                        os.remove(backup_file2)
                                    if retry_result.returncode == 0:
                                        print(f"  {db} support available locally")
                                        break
                            else:
                                failed_local_databases.append(db)
                        else:
                            failed_local_databases.append(db)
                    else:
                        print(f"  {db} support available locally")
            
            # Show status
            print("\n" + "="*60)
            print("CONFIGURATION SUMMARY")
            print("="*60)
            print(f"\nConfiguration updated for databases: {', '.join(databases)}")
            print("\nDocker Deployment: All selected databases will work")
            
            local_warnings = []
            if failed_local_databases:
                print("\nLocal Development Notice:")
                print("The following databases require system dependencies for local development:")
                for db in failed_local_databases:
                    if db in local_install_instructions:
                        warning = f"{db}: {local_install_instructions[db]}"
                        print(f"  - {warning}")
                        local_warnings.append(warning)
                print("\nNote: This only affects local development. Docker deployment will work perfectly.")
            else:
                print("\nLocal Development: All dependencies available")
            
            print("\n" + "="*60)
                    
        except FileNotFoundError:
            print("Warning: uv command not found.")
            print("Please ensure uv is installed and run 'uv sync' manually.")
            local_warnings = ["uv command not found. Please install uv first."]
            
    except HTTPException:
        # Re-raise HTTP exceptions as they are (installation failures)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating pyproject.toml: {str(e)}")
    
    # Process sister directories
    updated_files = [PYPROJECT_FILE]
    
    # Process sister directories
    current_dir = os.path.abspath(".")
    parent_dir = os.path.dirname(current_dir)
    
    for sister_project in SISTER_PROJECTS:
        project_name = sister_project["name"]
        sister_path = os.path.join(parent_dir, project_name)
        
        if os.path.exists(sister_path):
            if update_sister_pyproject(sister_path, databases):
                pyproject_file = os.path.join(sister_path, "pyproject.toml")
                updated_files.append(pyproject_file)
                print(f"{project_name}: pyproject.toml updated")

    # Log updated files
    print(f"Total pyproject.toml files updated: {len(updated_files)}")
    if len(updated_files) > 1:
        print(f"Backend + {len(updated_files)-1} frontend project(s) updated with database extras")
    
    # Return warnings for local development
    return local_warnings

def run_docker_compose():
    """Execute docker compose up --build -d in background"""
    global docker_status

    try:
        docker_status["running"] = True
        docker_status["phase"] = "starting"
        docker_status["message"] = "Preparing Docker environment..."

        # Use absolute path of current directory to ensure correct context
        thoth_be_path = os.path.abspath(".")
        docker_compose_file = os.path.join(thoth_be_path, "docker-compose.yml")
        if not os.path.exists(docker_compose_file):
            docker_status["running"] = False
            docker_status["phase"] = "error"
            docker_status["message"] = "docker-compose.yml file not found"
            return
        
        # IMPORTANT: Merge configurations and run uv sync before Docker build
        docker_status["message"] = "Merging configuration files..."
        if not merge_pyproject_files():
            docker_status["running"] = False
            docker_status["phase"] = "error"
            docker_status["message"] = "Failed to merge configuration files"
            return
        
        docker_status["message"] = "Installing dependencies with merged configuration..."
        # Temporarily replace pyproject.toml with merged version for uv sync
        import shutil
        backup_file = os.path.join(thoth_be_path, "pyproject.toml.backup")
        try:
            shutil.copy2(os.path.join(thoth_be_path, PYPROJECT_FILE), backup_file)
            shutil.copy2(os.path.join(thoth_be_path, PYPROJECT_MERGED_FILE), os.path.join(thoth_be_path, PYPROJECT_FILE))
            
            sync_result = subprocess.run(
                ["uv", "sync"],
                capture_output=True,
                text=True,
                check=False,
                cwd=thoth_be_path
            )
        finally:
            # Restore original pyproject.toml
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, os.path.join(thoth_be_path, PYPROJECT_FILE))
                os.remove(backup_file)
        
        if sync_result.returncode != 0:
            print(f"Warning: uv sync had issues: {sync_result.stderr}")
            # Continue anyway - Docker might still work

        # First, try to pull images separately (better for Windows)
        # But don't fail if pull doesn't work - build can pull images too
        docker_status["phase"] = "pulling"
        docker_status["message"] = "Pulling Docker images (this may take several minutes on first run)..."
        
        try:
            pull_process = subprocess.Popen(
                ["docker", "compose", "pull"],
                cwd=thoth_be_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait for pull to complete
            pull_stdout, _ = pull_process.communicate()
            
            if pull_process.returncode != 0:
                # Don't fail - just log and continue
                print(f"Warning: docker compose pull failed with output:\n{pull_stdout}")
                docker_status["message"] = "Pull had issues, continuing with build (will pull during build)..."
        except Exception as e:
            print(f"Warning: Exception during pull: {e}")
            docker_status["message"] = "Skipping separate pull, will pull during build..."
        
        # Now build and start containers (with --pull flag to ensure images are pulled)
        docker_status["phase"] = "building"
        docker_status["message"] = "Building and starting containers (pulling images if needed)..."

        process = subprocess.Popen(
            ["docker", "compose", "up", "--build", "--pull", "always", "-d"],
            cwd=thoth_be_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Monitor output without interfering with performance
        stdout, _ = process.communicate()

        if process.returncode == 0:
            docker_status["running"] = False
            docker_status["phase"] = "completed"
            docker_status["message"] = "Docker Compose completed successfully"
        else:
            docker_status["running"] = False
            docker_status["phase"] = "error"
            # Show more of the error for debugging
            error_lines = stdout.split('\n')[-5:] if stdout else ["Unknown error"]
            docker_status["message"] = f"Docker Compose error: {' '.join(error_lines)}"

    except Exception as e:
        docker_status["running"] = False
        docker_status["phase"] = "error"
        docker_status["message"] = f"Error: {str(e)}"

def run_docker_compose_sister():
    """Execute docker compose up --build -d in sister directory in background"""
    global docker_sister_status

    try:
        docker_sister_status["running"] = True
        docker_sister_status["phase"] = "starting"
        docker_sister_status["message"] = "Starting Frontend Docker Compose..."

        # Find sister directory (thoth_ui, ThothUI, or thothui) using absolute paths
        current_dir = os.path.abspath(".")
        parent_dir = os.path.dirname(current_dir)
        sister_names = ["thoth_ui", "ThothUI", "thothui"]
        sister_path = None

        for name in sister_names:
            candidate_path = os.path.join(parent_dir, name)
            docker_compose_file = os.path.join(candidate_path, "docker-compose.yml")
            if os.path.exists(candidate_path) and os.path.exists(docker_compose_file):
                sister_path = candidate_path
                break

        if not sister_path:
            docker_sister_status["running"] = False
            docker_sister_status["phase"] = "error"
            docker_sister_status["message"] = "Sister directory with docker-compose.yml not found"
            return
        
        # IMPORTANT: Merge configurations and run uv sync for sister project before Docker build
        sister_pyproject = os.path.join(sister_path, "pyproject.toml")
        sister_local = os.path.join(sister_path, "pyproject.local.toml")
        sister_merged = os.path.join(sister_path, ".pyproject.merged.toml")
        
        if os.path.exists(sister_pyproject):
            docker_sister_status["message"] = "Merging Frontend configuration files..."
            
            # Import merger and do the merge
            from installer.toml_merger import merge_pyproject_files as do_merge
            
            if not do_merge(
                base_path=sister_pyproject,
                local_path=sister_local,
                output_path=sister_merged
            ):
                print(f"Warning: Failed to merge Frontend configuration files")
                # Continue anyway - might work with base config
            
            docker_sister_status["message"] = "Installing Frontend dependencies..."
            sync_result = subprocess.run(
                ["uv", "sync", "--project", sister_merged],
                capture_output=True,
                text=True,
                check=False,
                cwd=sister_path
            )
            
            if sync_result.returncode != 0:
                print(f"Warning: Frontend uv sync had issues: {sync_result.stderr}")
                # Continue anyway - Docker might still work

        # First, try to pull images separately (better for Windows)
        # But don't fail if pull doesn't work - build can pull images too
        docker_sister_status["phase"] = "pulling"
        docker_sister_status["message"] = "Pulling Frontend Docker images (this may take several minutes)..."
        
        try:
            pull_process = subprocess.Popen(
                ["docker", "compose", "pull"],
                cwd=sister_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait for pull to complete
            pull_stdout, _ = pull_process.communicate()
            
            if pull_process.returncode != 0:
                # Don't fail - just log and continue
                print(f"Warning: docker compose pull failed for Frontend with output:\n{pull_stdout}")
                docker_sister_status["message"] = "Pull had issues, continuing with build (will pull during build)..."
        except Exception as e:
            print(f"Warning: Exception during Frontend pull: {e}")
            docker_sister_status["message"] = "Skipping separate pull, will pull during build..."
        
        # Now build and start containers (with --pull flag to ensure images are pulled)
        docker_sister_status["phase"] = "building"
        docker_sister_status["message"] = f"Building and starting Frontend containers in {sister_path} (pulling images if needed)..."

        process = subprocess.Popen(
            ["docker", "compose", "up", "--build", "--pull", "always", "-d"],
            cwd=sister_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Monitor output without interfering with performance
        stdout, _ = process.communicate()

        if process.returncode == 0:
            docker_sister_status["running"] = False
            docker_sister_status["phase"] = "completed"
            docker_sister_status["message"] = f"Frontend Docker Compose completed successfully"
        else:
            # Check if it's actually an error or just warnings
            # Docker compose often returns non-zero exit codes for warnings
            if stdout and ("Successfully built" in stdout or "Successfully tagged" in stdout):
                docker_sister_status["running"] = False
                docker_sister_status["phase"] = "completed"
                docker_sister_status["message"] = f"Frontend Docker Compose completed with warnings"
            else:
                docker_sister_status["running"] = False
                docker_sister_status["phase"] = "error"
                # Show more of the error message and look for the actual error
                # Since stderr is redirected to stdout, we use stdout for error messages
                error_output = stdout if stdout else "Unknown error"
                error_lines = error_output.split('\n')
                # Find the actual error line (often starts with 'ERROR' or contains 'failed')
                actual_error = None
                for line in error_lines:
                    if 'ERROR' in line.upper() or 'FAILED' in line.upper():
                        actual_error = line
                        break
                
                if actual_error:
                    docker_sister_status["message"] = f"Sister Docker Compose error: {actual_error[:500]}"
                else:
                    # Show last meaningful lines of output
                    meaningful_lines = [l for l in error_lines if l.strip() and not l.startswith('#')]
                    if meaningful_lines:
                        docker_sister_status["message"] = f"Sister Docker Compose error: {meaningful_lines[-1][:500]}"
                    else:
                        docker_sister_status["message"] = f"Sister Docker Compose error: {error_output[:500]}..."

    except Exception as e:
        docker_sister_status["running"] = False
        docker_sister_status["phase"] = "error"
        docker_sister_status["message"] = f"Error: {str(e)}"

@app.get("/")
async def read_index():
    """Serve the main HTML page"""
    return FileResponse('installer/index.html')

@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Return current configuration"""
    config = load_config()
    return ConfigResponse(
        databases=config["databases"],
        vectordbs=config["vectordbs"],
        message="Configuration loaded successfully"
    )

@app.post("/api/update-config", response_model=ConfigResponse)
async def update_config(config: DatabaseConfig):
    """Update configuration and pyproject.toml file"""

    # Validate selected databases
    invalid_databases = [db for db in config.databases if db not in VALID_DATABASES]
    if invalid_databases:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid databases: {', '.join(invalid_databases)}"
        )

    # Qdrant is the only supported vector database now
    config.vectordbs = ["qdrant"]
    
    # Ensure SQLite is always included
    if "sqlite" not in config.databases:
        config.databases.append("sqlite")

    # Weaviate removed: no mutual exclusivity checks needed

    try:
        # Save configuration BEFORE updating pyproject
        # This ensures any processes reading from JSON find updated values
        save_config(config.databases, config.vectordbs)

        # Update pyproject.toml with new configuration and get warnings
        local_warnings = update_pyproject_files(config.databases)
        
        # Determine which new database drivers were configured
        system_dep_databases = {'mariadb', 'sqlserver'}  # Database extras that require additional drivers
        new_drivers = [db for db in config.databases if db in system_dep_databases]
        
        # Short success message
        success_message = "Configuration updated successfully. Docker will use the new settings."

        return ConfigResponse(
            databases=config.databases,
            vectordbs=config.vectordbs,
            message=success_message.strip(),
            local_warnings=local_warnings if local_warnings else None
        )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/docker-deploy", response_model=DockerStatusResponse)
async def start_docker_deploy():
    """Start Docker Compose process in background"""
    global docker_status

    if docker_status["running"]:
        return DockerStatusResponse(
            status="running",
            message="Docker Compose already running",
            phase=docker_status["phase"]
        )

    try:
        # Before starting deployment, force save requirements.txt
        # Load current configuration
        config = load_config()
        databases = config.get("databases", [])
        vectordbs = config.get("vectordbs", [])

        # Update pyproject.toml with current configuration
        update_pyproject_files(databases)

    except Exception as e:
        return DockerStatusResponse(
            status="error",
            message=f"Error saving requirements.txt: {str(e)}",
            phase="error"
        )

    # Start process in a separate thread
    thread = threading.Thread(target=run_docker_compose)
    thread.daemon = True
    thread.start()

    return DockerStatusResponse(
        status="started",
        message="Docker Compose started",
        phase="starting"
    )

@app.get("/api/docker-status", response_model=DockerStatusResponse)
async def get_docker_status():
    """Return current Docker Compose process status"""
    global docker_status

    status = "running" if docker_status["running"] else "idle"
    if docker_status["phase"] == "error":
        status = "error"
    elif docker_status["phase"] == "completed":
        status = "completed"

    return DockerStatusResponse(
        status=status,
        message=docker_status["message"],
        phase=docker_status["phase"]
    )

@app.post("/api/docker-deploy-sister", response_model=DockerStatusResponse)
async def start_docker_deploy_sister():
    """Start Docker Compose process for sister directory in background"""
    global docker_sister_status

    if docker_sister_status["running"]:
        return DockerStatusResponse(
            status="running",
            message="Frontend Docker Compose already running",
            phase=docker_sister_status["phase"]
        )

    try:
        # Before starting deployment, force save requirements.txt
        # Load current configuration
        config = load_config()
        databases = config.get("databases", [])
        vectordbs = config.get("vectordbs", [])

        # Update pyproject.toml with current configuration
        update_pyproject_files(databases)

    except Exception as e:
        return DockerStatusResponse(
            status="error",
            message=f"Error saving requirements.txt: {str(e)}",
            phase="error"
        )

    # Start process in a separate thread
    thread = threading.Thread(target=run_docker_compose_sister)
    thread.daemon = True
    thread.start()

    return DockerStatusResponse(
        status="started",
        message="Frontend Docker Compose started",
        phase="starting"
    )

@app.get("/api/docker-status-sister", response_model=DockerStatusResponse)
async def get_docker_status_sister():
    """Return current Docker Compose process status for sister directory"""
    global docker_sister_status

    status = "running" if docker_sister_status["running"] else "idle"
    if docker_sister_status["phase"] == "error":
        status = "error"
    elif docker_sister_status["phase"] == "completed":
        status = "completed"

    return DockerStatusResponse(
        status=status,
        message=docker_sister_status["message"],
        phase=docker_sister_status["phase"]
    )

@app.post("/api/shutdown")
async def shutdown_server():
    """Gracefully terminate the installer server"""
    import signal
    import os
    
    def shutdown():
        os.kill(os.getpid(), signal.SIGTERM)
    
    # Delay to allow response to be sent
    import threading
    threading.Timer(1.0, shutdown).start()
    
    return {"message": "Server shutting down..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8199)
