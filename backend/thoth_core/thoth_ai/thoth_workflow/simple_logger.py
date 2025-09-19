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
Simple logging system for async tasks that outputs to console and file only.
"""

import logging
import os
from datetime import datetime
from typing import Optional


def setup_simple_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup a simple logger that outputs to console and optionally to file.
    
    Args:
        name: Name of the logger
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def get_db_elements_logger(sqldb_id: int, workspace_id: int = None) -> logging.Logger:
    """
    Get a logger for database elements creation task.
    
    Args:
        sqldb_id: ID of the database being processed
        workspace_id: Optional ID of the workspace
        
    Returns:
        Configured logger instance
    """
    # Generate log file path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_part = f"ws_{workspace_id}" if workspace_id else "no_workspace"
    log_filename = f"db_elements_{workspace_part}_db_{sqldb_id}_{timestamp}.log"
    log_file_path = os.path.join("logs", "db_elements", log_filename)
    
    # Create logger with unique name
    logger_name = f"db_elements_db_{sqldb_id}_{timestamp}"
    return setup_simple_logger(logger_name, log_file_path)