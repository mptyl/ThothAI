# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
Utility functions for managing shared paths between Docker and local development.
"""

import os
from django.conf import settings


def get_data_exchange_path():
    """
    Get path to data_exchange directory for runtime import/export.
    
    Returns:
        str: Absolute path to data_exchange directory
    """
    if os.getenv("DOCKER_ENV"):  # Running in Docker
        return "/app/data_exchange"
    else:  # Running locally
        return os.path.join(settings.BASE_DIR.parent, "data_exchange")


def get_shared_data_path():
    """
    Get path to shared data directory for inter-service communication.
    
    Returns:
        str: Absolute path to shared data directory
    """
    if os.getenv("DOCKER_ENV"):  # Running in Docker
        return "/app/data"
    else:  # Running locally
        return os.path.join(settings.BASE_DIR.parent, "data")


def get_setup_csv_path():
    """
    Get path to setup_csv directory for initial system configuration.
    Note: This directory is copied into Docker containers during build,
    not mounted as a volume.
    
    Returns:
        str: Absolute path to setup_csv directory
    """
    return os.path.join(settings.BASE_DIR.parent, "setup_csv")


def ensure_directories_exist():
    """
    Ensure all shared directories exist.
    Creates them if they don't exist.
    """
    directories = [
        get_data_exchange_path(),
        get_shared_data_path(),
    ]
    
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)


def get_export_path(filename=None):
    """
    Get full path for an export file.
    
    Args:
        filename (str, optional): Name of the file to export.
    
    Returns:
        str: Full path to the export file or directory
    """
    base_path = get_data_exchange_path()
    if filename:
        return os.path.join(base_path, filename)
    return base_path


def get_import_path(filename=None):
    """
    Get full path for an import file from data_exchange.
    Note: For initial setup files, use get_setup_csv_path() instead.
    
    Args:
        filename (str, optional): Name of the file to import.
    
    Returns:
        str: Full path to the import file or directory
    """
    base_path = get_data_exchange_path()
    if filename:
        return os.path.join(base_path, filename)
    return base_path