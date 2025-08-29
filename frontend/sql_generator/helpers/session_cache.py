# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Session cache utilities for SQL Generator service.

Provides helpers to initialize and cache workspace-specific setup when a
cache miss occurs.
"""

from typing import Any, Dict

from .main_helpers.main_methods import _setup_dbmanager_and_agents


async def ensure_cached_setup(
    session_cache: Dict[str, Dict[str, Any]],
    cache_key: str,
    workspace_id: int,
    request: Any,
) -> Dict[str, Any]:
    """
    Ensure the setup for the given workspace is performed and stored in cache.

    Parameters
    - session_cache: The in-memory cache mapping cache_key to cached entries
    - cache_key: Key under which to store the setup result
    - workspace_id: Workspace identifier
    - request: The original request object, forwarded to setup routine

    Returns
    - The setup_result dictionary produced by the setup routine

    Raises
    - Propagates any exception raised by the setup routine
    """

    setup_result = await _setup_dbmanager_and_agents(workspace_id, request)

    # Store in cache for subsequent calls in the same session/workspace
    session_cache[cache_key] = {
        "workspace_id": workspace_id,
        "setup_result": setup_result,
    }

    return setup_result


