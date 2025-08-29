#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Direct runner for SQL Generator FastAPI application.

This script runs the FastAPI application directly without module imports,
avoiding the relative import issues.
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path so all imports work as absolute imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Import the FastAPI app directly
    from main import app, log_level
    
    # Get port from command line argument or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    
    # Configure uvicorn logging to match our app's logging level
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn"]["level"] = logging.getLevelName(log_level)
    uvicorn_log_config["loggers"]["uvicorn.error"]["level"] = logging.getLevelName(log_level)
    uvicorn_log_config["loggers"]["uvicorn.access"]["level"] = logging.getLevelName(log_level)
    
    # Disable access logs completely if WARNING or higher
    access_log = log_level <= logging.INFO
    
    print(f"Starting SQL Generator service on port {port} with log level {logging.getLevelName(log_level)}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_config=uvicorn_log_config, access_log=access_log)

