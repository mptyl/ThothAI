#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# ThothAI Log Cleanup Script for Local Development
# Usage: ./scripts/cleanup-logs.sh [days_to_keep] [compress_after_days]

# Configuration
DAYS_TO_KEEP=${1:-7}
COMPRESS_AFTER=${2:-1}
DRY_RUN=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Usage: $0 [days_to_keep] [compress_after_days] [--dry-run]"
            echo "  days_to_keep: Days to keep logs (default: 7)"
            echo "  compress_after_days: Compress logs older than N days (default: 1)"
            echo "  --dry-run: Show what would be done without actually doing it"
            exit 0
            ;;
    esac
done

echo "=== ThothAI Log Cleanup (Local Development) ==="
echo "Settings: Keep ${DAYS_TO_KEEP} days, compress after ${COMPRESS_AFTER} days"
if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN MODE - No files will be modified"
fi
echo ""

# Function to get file size in human readable format
human_size() {
    local size=$1
    local units=("B" "KB" "MB" "GB")
    local unit=0
    
    while [ $size -gt 1024 ] && [ $unit -lt 3 ]; do
        size=$((size / 1024))
        unit=$((unit + 1))
    done
    
    echo "${size}${units[$unit]}"
}

# Function to show statistics
show_stats() {
    echo "Current log statistics:"
    
    # Backend logs
    if [ -d "./backend/logs" ]; then
        local backend_size=$(du -sb ./backend/logs 2>/dev/null | cut -f1)
        echo "  Backend logs: $(human_size $backend_size)"
    else
        echo "  Backend logs: directory not found"
    fi
    
    # SQL-Generator logs
    if [ -d "./frontend/sql_generator/logs" ]; then
        local sql_size=$(du -sb ./frontend/sql_generator/logs 2>/dev/null | cut -f1)
        echo "  SQL-Generator logs: $(human_size $sql_size)"
    else
        echo "  SQL-Generator logs: directory not found"
    fi
    
    echo ""
}

# Function to compress old logs
compress_old_logs() {
    echo "Compressing logs older than ${COMPRESS_AFTER} days..."
    local count=0
    
    # Find and compress old log files
    for dir in "./backend/logs" "./frontend/sql_generator/logs/temp"; do
        if [ -d "$dir" ]; then
            while IFS= read -r -d '' file; do
                if [ ! -f "${file}.gz" ]; then
                    if [ "$DRY_RUN" = true ]; then
                        echo "  Would compress: $file"
                    else
                        gzip "$file"
                        echo "  Compressed: $file"
                    fi
                    count=$((count + 1))
                fi
            done < <(find "$dir" -name "*.log" -type f -mtime +${COMPRESS_AFTER} -print0 2>/dev/null)
        fi
    done
    
    echo "  Total files compressed: $count"
    echo ""
}

# Function to remove old logs
remove_old_logs() {
    echo "Removing logs older than ${DAYS_TO_KEEP} days..."
    local count=0
    local saved_space=0
    
    # Find and remove old log files (both compressed and rotated)
    for dir in "./backend/logs" "./frontend/sql_generator/logs/temp"; do
        if [ -d "$dir" ]; then
            while IFS= read -r -d '' file; do
                local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
                saved_space=$((saved_space + file_size))
                
                if [ "$DRY_RUN" = true ]; then
                    echo "  Would remove: $file ($(human_size $file_size))"
                else
                    rm -f "$file"
                    echo "  Removed: $file ($(human_size $file_size))"
                fi
                count=$((count + 1))
            done < <(find "$dir" \( -name "*.log.*" -o -name "*.log.gz" \) -type f -mtime +${DAYS_TO_KEEP} -print0 2>/dev/null)
        fi
    done
    
    echo "  Total files removed: $count"
    echo "  Space freed: $(human_size $saved_space)"
    echo ""
}

# Main execution
show_stats

# Compress old logs
compress_old_logs

# Remove very old logs
remove_old_logs

# Show final statistics
echo "=== Cleanup Complete ==="
if [ "$DRY_RUN" = false ]; then
    show_stats
fi