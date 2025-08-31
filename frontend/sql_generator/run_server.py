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
Direct runner for SQL Generator FastAPI application.

This script runs the FastAPI application directly without module imports,
avoiding the relative import issues.
"""

import sys
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8180
    
    # Configure uvicorn logging to match our app's logging level
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn"]["level"] = logging.getLevelName(log_level)
    uvicorn_log_config["loggers"]["uvicorn.error"]["level"] = logging.getLevelName(log_level)
    uvicorn_log_config["loggers"]["uvicorn.access"]["level"] = logging.getLevelName(log_level)
    
    # Disable access logs completely if WARNING or higher
    access_log = log_level <= logging.INFO
    
    print(f"Starting SQL Generator service on port {port} with log level {logging.getLevelName(log_level)}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_config=uvicorn_log_config, access_log=access_log)

