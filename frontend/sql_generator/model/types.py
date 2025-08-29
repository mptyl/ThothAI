# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Common type definitions for the SQL generator models.

This module contains shared type definitions to avoid circular imports.
"""

from typing import Any, Dict, TypedDict


class TableInfo(TypedDict):
    """Type definition for database table information."""
    table_description: str
    columns: Dict[str, Dict[str, Any]]