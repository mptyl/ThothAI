# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

import os
import logging
from django.conf import settings
from pathlib import Path

logger = logging.getLogger(__name__)

def get_setup_csv_path(filename, source="docker"):
    """
    Resolve the absolute path for a setup CSV file, handling different environments.
    
    Args:
        filename (str): The name of the CSV file (e.g., 'basicaimodel.csv')
        source (str): The source type ('local' or 'docker')
        
    Returns:
        str: The absolute path to the CSV file to use
    """
    # Potential base directories for setup_csv
    potential_roots = [
        # 1. Docker root (copied via Dockerfile)
        Path("/setup_csv"),
        # 2. Project root (standard development structure)
        settings.BASE_DIR.parent / "setup_csv",
        # 3. Backend root (fallback)
        settings.BASE_DIR / "setup_csv",
    ]
    
    # 1. Try to find the source-specific file first (e.g., setup_csv/docker/file.csv)
    for root in potential_roots:
        source_path = root / source / filename
        if source_path.exists():
            logger.info(f"Found source-specific CSV at: {source_path}")
            return str(source_path)
            
    # 2. Try to find the generic file (e.g., setup_csv/file.csv)
    for root in potential_roots:
        generic_path = root / filename
        if generic_path.exists():
            logger.info(f"Found generic CSV at: {generic_path}")
            return str(generic_path)
    
    # 3. Return the default expected path even if it doesn't exist (caller will handle error)
    # Default to project root structure
    default_path = settings.BASE_DIR.parent / "setup_csv" / filename
    logger.warning(f"CSV file {filename} not found in standard locations. Defaulting to: {default_path}")
    return str(default_path)
