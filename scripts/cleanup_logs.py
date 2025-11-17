#!/usr/bin/env python3
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
ThothAI Log Cleanup Script for Local Development (Python version)
Usage: python scripts/cleanup_logs.py [--days DAYS] [--compress-after DAYS] [--dry-run]
"""

import os
import sys
import glob
import gzip
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def human_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def get_directory_size(path):
    """Get total size of directory"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_directory_size(entry.path)
    except (OSError, PermissionError):
        pass
    return total


def show_statistics(log_dirs):
    """Show current log statistics"""
    print("Current log statistics:")
    
    for name, path in log_dirs.items():
        if os.path.exists(path):
            size = get_directory_size(path)
            print(f"  {name}: {human_size(size)}")
        else:
            print(f"  {name}: directory not found")
    
    print()


def compress_file(file_path, dry_run=False):
    """Compress a single file with gzip"""
    gz_path = f"{file_path}.gz"
    
    if os.path.exists(gz_path):
        return False, 0
    
    file_size = os.path.getsize(file_path)
    
    if dry_run:
        print(f"  Would compress: {file_path}")
        return True, file_size
    
    try:
        with open(file_path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        print(f"  Compressed: {file_path}")
        return True, file_size
    except Exception as e:
        print(f"  Error compressing {file_path}: {e}")
        return False, 0


def compress_old_logs(log_dirs, compress_after_days, dry_run=False):
    """Compress logs older than specified days"""
    print(f"Compressing logs older than {compress_after_days} days...")
    
    cutoff_date = datetime.now() - timedelta(days=compress_after_days)
    total_count = 0
    total_size = 0
    
    for name, path in log_dirs.items():
        if not os.path.exists(path):
            continue
        
        # Find all .log files
        pattern = os.path.join(path, "**", "*.log")
        for log_file in glob.glob(pattern, recursive=True):
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if mtime < cutoff_date:
                    compressed, size = compress_file(log_file, dry_run)
                    if compressed:
                        total_count += 1
                        total_size += size
            except OSError as e:
                print(f"  Error processing {log_file}: {e}")
    
    print(f"  Total files compressed: {total_count}")
    if total_size > 0:
        print(f"  Space saved by compression: {human_size(total_size)}")
    print()


def remove_old_logs(log_dirs, days_to_keep, dry_run=False):
    """Remove logs older than specified days"""
    print(f"Removing logs older than {days_to_keep} days...")
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    total_count = 0
    total_size = 0
    
    for name, path in log_dirs.items():
        if not os.path.exists(path):
            continue
        
        # Patterns for rotated and compressed logs
        patterns = [
            os.path.join(path, "**", "*.log.*"),
            os.path.join(path, "**", "*.log.gz"),
        ]
        
        for pattern in patterns:
            for log_file in glob.glob(pattern, recursive=True):
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    if mtime < cutoff_date:
                        file_size = os.path.getsize(log_file)
                        
                        if dry_run:
                            print(f"  Would remove: {log_file} ({human_size(file_size)})")
                        else:
                            os.remove(log_file)
                            print(f"  Removed: {log_file} ({human_size(file_size)})")
                        
                        total_count += 1
                        total_size += file_size
                        
                except OSError as e:
                    print(f"  Error processing {log_file}: {e}")
    
    print(f"  Total files removed: {total_count}")
    if total_size > 0:
        print(f"  Space freed: {human_size(total_size)}")
    print()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="ThothAI Log Cleanup Script for Local Development"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to keep logs (default: 7)"
    )
    parser.add_argument(
        "--compress-after",
        type=int,
        default=1,
        help="Compress logs older than N days (default: 1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    
    args = parser.parse_args()
    
    # Define log directories
    log_dirs = {
        "Backend logs": "./backend/logs",
        "SQL-Generator logs": "./frontend/sql_generator/logs",
    }
    
    print("=== ThothAI Log Cleanup (Local Development) ===")
    print(f"Settings: Keep {args.days} days, compress after {args.compress_after} days")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
    print()
    
    # Show initial statistics
    show_statistics(log_dirs)
    
    # Compress old logs
    compress_old_logs(log_dirs, args.compress_after, args.dry_run)
    
    # Remove very old logs
    remove_old_logs(log_dirs, args.days, args.dry_run)
    
    # Show final statistics
    print("=== Cleanup Complete ===")
    if not args.dry_run:
        show_statistics(log_dirs)


if __name__ == "__main__":
    main()