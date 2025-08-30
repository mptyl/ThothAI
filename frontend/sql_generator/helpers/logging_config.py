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

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Dictionary to store already created loggers
_loggers = {}

# Get logging level from environment variable
def get_logging_level():
    """Get logging level from environment variable LOGGING_LEVEL."""
    level_str = os.getenv('LOGGING_LEVEL', 'INFO').upper()
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_mapping.get(level_str, logging.INFO)

# Simplified Docker detection logic
def is_running_locally():
    """
    Determine if application is running locally or in Docker.
    
    Returns:
        bool: True if running locally, False if in Docker
    """
    return os.getenv('DOCKER_CONTAINER', 'false').lower() != 'true'

def setup_logger(name, level=None):
    """
    Configure centralized logger.
    - Docker: writes only to console (StreamHandler)
    - Local: writes to both console and file
    
    Args:
        name (str): Logger name
        level (int): Logging level (if None, uses LOGGING_LEVEL env var)
        
    Returns:
        logging.Logger: Configured logger
    """
    # Return existing logger if already created
    if name in _loggers:
        return _loggers[name]
    
    # Use environment level if none specified
    if level is None:
        level = get_logging_level()
    
    # Configure logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Always add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if running locally
    if is_running_locally():
        log_dir = Path("logs/temp")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{name}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to parent loggers
    logger.propagate = False
    
    # Store logger for reuse
    _loggers[name] = logger
    
    return logger

def get_logger(name):
    """
    Get existing logger or create new one using centralized configuration.
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: Configured logger
    """
    if name in _loggers:
        return _loggers[name]
    else:
        return setup_logger(name)

def configure_root_logger():
    """
    Configure root logger.
    - Docker: all logs go only to console
    - Local: all logs go to both console and file
    This function should be called at application startup.
    """
    level = get_logging_level()
    
    # Configure with basicConfig for consistency
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # Force reconfiguration
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Add file handler if running locally
    if is_running_locally():
        log_dir = Path("logs/temp")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        log_file = log_dir / "thoth_app.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy modules when log level is WARNING or higher
    if level >= logging.WARNING:
        noisy_modules = [
            "thoth_dbmanager",
            "thoth_dbmanager.adapters",
            "thoth_dbmanager.adapters.sqlite",
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error"
        ]
        
        for module_name in noisy_modules:
            logging.getLogger(module_name).setLevel(logging.ERROR)
    
    # Set uvicorn loggers to respect our level
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)

def configure_module_logging_levels():
    """
    Configure specific logging levels for different modules.
    This allows fine-grained control over logging verbosity.
    """
    level = get_logging_level()
    
    # In production (INFO or higher), reduce verbosity for specific modules
    if level >= logging.INFO:
        # Set verbose modules to WARNING or ERROR
        verbose_modules = {
            'thoth_log_api': logging.WARNING,  # Reduce API logging verbosity
            'httpx': logging.WARNING,           # Reduce HTTP client logging
            'httpcore': logging.WARNING,        # Reduce HTTP core logging
            'uvicorn.access': logging.WARNING,  # Reduce access logs
            'thoth_dbmanager.adapters': logging.WARNING,  # Reduce DB adapter logs
            'qdrant_client': logging.WARNING,   # Reduce Qdrant client logs
        }
        
        for module_name, module_level in verbose_modules.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(module_level)
    
    # In DEBUG mode, we might want to silence some very verbose modules
    elif level == logging.DEBUG:
        # Even in debug, some modules are too verbose
        super_verbose_modules = {
            'httpcore.http11': logging.INFO,    # HTTP protocol details
            'httpcore.connection': logging.INFO, # Connection pool details
        }
        
        for module_name, module_level in super_verbose_modules.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(module_level)

# Note: log_info, log_warning, log_error, log_debug functions are available in dual_logger.py
# which provides dual logging to both standard logger and Logfire

# Main application logger
app_logger = setup_logger("thoth_app", level=get_logging_level())

# Configure module-specific logging levels
configure_module_logging_levels()
