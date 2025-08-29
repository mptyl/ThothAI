#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "=== Thoth Startup with Log Management ==="

# Change to app directory
cd /app

# Run log cleanup immediately on startup
echo "Running initial log cleanup..."
uv run python manage.py cleanup_logs

# Install crontab
echo "Installing crontab..."
crontab /app/scripts/crontab

# Start cron daemon
echo "Starting cron daemon..."
cron

# Create log file for cron if it doesn't exist
touch /var/log/cron.log

# Function to handle shutdown gracefully
cleanup() {
    echo "Shutting down..."
    # Stop cron
    pkill cron || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Run the main startup script first
echo "Running startup script..."
/app/scripts/start.sh

# Start the main application
echo "Starting Django application..."
exec "$@"
