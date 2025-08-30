#!/usr/bin/env python3

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

"""
Cross-platform Docker setup script for ThothAI
Works on Windows, macOS, and Linux
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, shell=False, capture_output=False):
    """Execute a command and handle errors"""
    try:
        if capture_output:
            result = subprocess.run(command, shell=shell, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(command, shell=shell)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)


def docker_command_exists():
    """Check if docker command is available"""
    success, _, _ = run_command(["docker", "--version"], capture_output=True)
    return success


def create_network():
    """Create Docker network if it doesn't exist"""
    print("Checking Docker network 'thothnet'...")
    
    # Check if network exists
    success, stdout, _ = run_command(["docker", "network", "ls"], capture_output=True)
    if success and "thothnet" in stdout:
        print("Network 'thothnet' already exists")
        return True
    
    # Create network
    print("Creating Docker network 'thothnet'...")
    success, _, error = run_command(["docker", "network", "create", "thothnet"])
    if success:
        print("Network 'thothnet' created successfully")
        return True
    else:
        print(f"Error creating network: {error}")
        return False


def create_volume():
    """Create Docker volume if it doesn't exist"""
    print("Checking Docker volume 'thoth-shared-data'...")
    
    # Check if volume exists
    success, stdout, _ = run_command(["docker", "volume", "ls"], capture_output=True)
    if success and "thoth-shared-data" in stdout:
        print("Volume 'thoth-shared-data' already exists")
        return True
    
    # Create volume
    print("Creating Docker volume 'thoth-shared-data'...")
    success, _, error = run_command(["docker", "volume", "create", "thoth-shared-data"])
    if success:
        print("Volume 'thoth-shared-data' created successfully")
        return True
    else:
        print(f"Error creating volume: {error}")
        return False


def create_directories():
    """Create necessary directories"""
    print("Creating necessary directories...")
    directories = ["logs", "exports", "setup_csv", "qdrant_storage"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"  Created/verified: {directory}")
    
    return True


def check_env_file():
    """Check if root .env.docker file exists"""
    root_env = Path("../.env.docker")
    if not root_env.exists():
        print("\n[WARNING] .env.docker file not found in root directory!")
        print("Please create .env.docker from .env.template and configure your API keys")
        return False
    print("Environment file .env.docker found in root directory")
    return True


def copy_data_to_volume():
    """Copy dev_databases to Docker volume"""
    data_dir = Path("data")
    dev_databases_dir = data_dir / "dev_databases"
    
    if not dev_databases_dir.exists():
        print("[INFO] No dev_databases found in ./data directory")
        return True
    
    print("Checking Docker volume contents...")
    
    # Get absolute path for Windows compatibility
    current_dir = Path.cwd()
    
    # Build the Docker command to copy files
    # On Windows, we need to use the absolute path
    if platform.system() == "Windows":
        # Windows path needs to be converted to Docker format
        source_path = str(current_dir / "data").replace("\\", "/")
    else:
        source_path = str(current_dir / "data")
    
    # First, show current volume contents for debugging
    list_cmd = [
        "docker", "run", "--rm",
        "-v", "thoth-shared-data:/target",
        "alpine", "sh", "-c",
        "ls -la /target/ 2>/dev/null || echo 'Volume is empty'"
    ]
    
    print("Current Docker volume contents:")
    success, stdout, _ = run_command(list_cmd, capture_output=True)
    if success:
        print(stdout)
    
    # More reliable check if dev_databases exists in the volume
    check_cmd = [
        "docker", "run", "--rm",
        "-v", "thoth-shared-data:/target",
        "alpine", "sh", "-c",
        "test -d /target/dev_databases && echo 'EXISTS' || echo 'NOT_EXISTS'"
    ]
    
    success, stdout, _ = run_command(check_cmd, capture_output=True)
    
    if success and "EXISTS" in stdout.strip():
        print("dev_databases already exists in Docker volume")
        return True
    
    print("dev_databases not found in volume, copying now...")
    
    # Copy dev_databases directory
    copy_cmd = [
        "docker", "run", "--rm",
        "-v", f"{source_path}:/source:ro",
        "-v", "thoth-shared-data:/target",
        "alpine", "sh", "-c",
        "cp -r /source/dev_databases /target/ && echo 'COPY_SUCCESS' || echo 'COPY_FAILED'"
    ]
    
    print(f"Executing: docker run with volume mapping {source_path}:/source")
    success, stdout, stderr = run_command(copy_cmd, capture_output=True)
    
    if success and "COPY_SUCCESS" in stdout:
        print("dev_databases copied successfully!")
        
        # Verify the copy worked
        verify_cmd = [
            "docker", "run", "--rm",
            "-v", "thoth-shared-data:/target",
            "alpine", "sh", "-c",
            "test -d /target/dev_databases && echo 'Verified: dev_databases exists' || echo 'ERROR: dev_databases not found'"
        ]
        success, stdout, _ = run_command(verify_cmd, capture_output=True)
        print(stdout.strip())
        
        # Also copy db.sqlite3 if it exists
        db_file = data_dir / "db.sqlite3"
        if db_file.exists():
            copy_db_cmd = [
                "docker", "run", "--rm",
                "-v", f"{source_path}:/source:ro",
                "-v", "thoth-shared-data:/target",
                "alpine", "sh", "-c",
                "cp /source/db.sqlite3 /target/ 2>/dev/null || true"
            ]
            run_command(copy_db_cmd)
            print("db.sqlite3 copied")
        
        # Show final volume contents
        print("\nFinal Docker volume contents:")
        run_command(list_cmd, capture_output=False)
        
        return True
    else:
        print(f"[WARNING] Could not copy files to Docker volume")
        if "COPY_FAILED" in stdout:
            print("Copy operation failed")
        if stderr:
            print(f"Error: {stderr}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("ThothAI Docker Environment Setup")
    print(f"Platform: {platform.system()}")
    print("=" * 60)
    print()
    
    # Check Docker is installed
    if not docker_command_exists():
        print("[ERROR] Docker is not installed or not in PATH")
        print("Please install Docker Desktop and ensure it's running")
        return 1
    
    print("Docker is available")
    print()
    
    # Execute setup steps
    steps = [
        ("Creating Docker network", create_network),
        ("Creating Docker volume", create_volume),
        ("Creating directories", create_directories),
        ("Checking environment file", check_env_file),
        ("Copying data to volume", copy_data_to_volume)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"[ERROR] Failed at step: {step_name}")
            return 1
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Docker setup complete!")
    print("\nTo start ThothAI, run:")
    if platform.system() == "Windows":
        print("  docker-compose up --build")
    else:
        print("  docker compose up --build")
    print("\nAccess the application at:")
    print("  http://localhost:8040/admin")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())