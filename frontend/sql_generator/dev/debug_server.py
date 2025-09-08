#!/usr/bin/env python

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
Debug server for SQL Generator with integrated Python debugger support.
"""

import uvicorn
import sys
import os

if __name__ == "__main__":
    # Import qui per poter mettere breakpoint nel modulo main
    from main import app
    
    # Priority: command line arg > PORT env > default 8180
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv('PORT', '8180'))
    
    # Use debug level for debug server unless overridden
    debug_log_level = os.getenv('LOGGING_LEVEL', 'DEBUG').lower()
    
    print(f"Starting debug server on port {port}")
    print("Tip: Add 'import pdb; pdb.set_trace()' in your code where you want to break")
    print(f"Endpoint: POST http://localhost:{port}/generate-sql")
    
    # Configure uvicorn logging
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn"]["level"] = debug_log_level.upper()
    uvicorn_log_config["loggers"]["uvicorn.error"]["level"] = debug_log_level.upper()
    uvicorn_log_config["loggers"]["uvicorn.access"]["level"] = debug_log_level.upper()
    
    # Keep access logs for debug server unless explicitly set to WARNING or higher
    access_log = debug_log_level.upper() not in ['WARNING', 'ERROR', 'CRITICAL']
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        reload=True,  # Auto-reload on code changes
        log_config=uvicorn_log_config,
        access_log=access_log
    )