# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import os
import glob
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up log files older than specified days (default: 30 days)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep logs (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days_to_keep = options['days']
        dry_run = options['dry_run']
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Get logs directory
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        
        if not os.path.exists(logs_dir):
            self.stdout.write(
                self.style.WARNING(f'Logs directory does not exist: {logs_dir}')
            )
            return
        
        # Find all log files (including rotated ones)
        log_patterns = [
            os.path.join(logs_dir, 'thoth.log.*'),  # Rotated logs
            os.path.join(logs_dir, '*.log.*'),      # Any other rotated logs
        ]
        
        deleted_count = 0
        total_size = 0
        
        self.stdout.write(f'Looking for log files older than {days_to_keep} days...')
        
        for pattern in log_patterns:
            for log_file in glob.glob(pattern):
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    
                    if file_mtime < cutoff_date:
                        file_size = os.path.getsize(log_file)
                        total_size += file_size
                        
                        if dry_run:
                            self.stdout.write(
                                f'Would delete: {log_file} '
                                f'(modified: {file_mtime.strftime("%Y-%m-%d %H:%M:%S")}, '
                                f'size: {self._format_size(file_size)})'
                            )
                        else:
                            os.remove(log_file)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Deleted: {log_file} '
                                    f'(modified: {file_mtime.strftime("%Y-%m-%d %H:%M:%S")}, '
                                    f'size: {self._format_size(file_size)})'
                                )
                            )
                            logger.info(f'Log cleanup: deleted {log_file}')
                        
                        deleted_count += 1
                        
                except OSError as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing {log_file}: {e}')
                    )
                    logger.error(f'Log cleanup error: {e}')
        
        # Summary
        if deleted_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No old log files found to clean up.')
            )
        else:
            action = "Would delete" if dry_run else "Deleted"
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} {deleted_count} log file(s), '
                    f'freed {self._format_size(total_size)} of disk space.'
                )
            )
            
        if not dry_run and deleted_count > 0:
            logger.info(
                f'Log cleanup completed: {deleted_count} files deleted, '
                f'{self._format_size(total_size)} freed'
            )

    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
