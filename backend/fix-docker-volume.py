#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Docker Volume Repair Tool for ThothAI
Fixes missing dev_databases in Docker volume
"""

import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, capture_output=False):
    """Execute a command and handle errors"""
    try:
        if capture_output:
            result = subprocess.run(command, capture_output=True, text=True, shell=False)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(command, shell=False)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)


def main():
    print("=" * 60)
    print("    ThothAI Docker Volume Repair Tool")
    print("=" * 60)
    print("\nThis script will check and repair the Docker volume\n")
    
    # Check if Docker is running
    success, _, _ = run_command(["docker", "info"], capture_output=True)
    if not success:
        print("[ERROR] Docker is not running. Please start Docker Desktop.")
        input("Press Enter to exit...")
        return 1
    
    # Check if volume exists
    success, stdout, _ = run_command(["docker", "volume", "ls"], capture_output=True)
    if not success or "thoth-shared-data" not in stdout:
        print("[ERROR] Docker volume 'thoth-shared-data' does not exist.")
        print("Run install.bat/install.sh or setup-docker script first.")
        input("Press Enter to exit...")
        return 1
    
    # Check current volume contents
    print("Checking current volume contents...")
    list_cmd = [
        "docker", "run", "--rm",
        "-v", "thoth-shared-data:/target",
        "alpine", "sh", "-c",
        "ls -la /target/"
    ]
    run_command(list_cmd)
    
    # Check if local dev_databases exists
    data_dir = Path("data")
    dev_databases_dir = data_dir / "dev_databases"
    
    if not dev_databases_dir.exists():
        print("\n[ERROR] No dev_databases found in local data directory")
        print("Make sure you have the data/dev_databases folder in your project")
        input("Press Enter to exit...")
        return 1
    
    print("\nForcing copy of dev_databases to Docker volume...")
    
    # Get current directory with proper path handling
    current_dir = Path.cwd()
    if platform.system() == "Windows":
        source_path = str(current_dir / "data").replace("\\", "/")
    else:
        source_path = str(current_dir / "data")
    
    # Force copy dev_databases (remove old one if exists)
    copy_cmd = [
        "docker", "run", "--rm",
        "-v", f"{source_path}:/source:ro",
        "-v", "thoth-shared-data:/target",
        "alpine", "sh", "-c",
        "rm -rf /target/dev_databases 2>/dev/null; cp -r /source/dev_databases /target/ && echo 'COPY_SUCCESS' || echo 'COPY_FAILED'"
    ]
    
    success, stdout, stderr = run_command(copy_cmd, capture_output=True)
    
    if success and "COPY_SUCCESS" in stdout:
        print("SUCCESS: dev_databases copied")
    else:
        print("ERROR: Copy failed")
        if stderr:
            print(f"Error details: {stderr}")
    
    # Verify the copy
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
            "cp -f /source/db.sqlite3 /target/ 2>/dev/null"
        ]
        run_command(copy_db_cmd)
        print("db.sqlite3 copied")
    
    # Show final volume contents
    print("\nFinal volume contents:")
    run_command(list_cmd)
    
    print("\n" + "=" * 60)
    print("Volume repair complete!")
    print("You can now run: docker-compose up --build")
    print("=" * 60)
    
    input("\nPress Enter to exit...")
    return 0


if __name__ == "__main__":
    sys.exit(main())