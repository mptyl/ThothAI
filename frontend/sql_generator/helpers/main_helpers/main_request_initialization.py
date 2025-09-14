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
Request initialization helper for SQL Generator.

This module handles the initialization and validation of request state
for the SQL generation pipeline.
"""

import json
from typing import Optional, Tuple, TYPE_CHECKING
from fastapi import Request
from fastapi.responses import PlainTextResponse

from model.system_state import SystemState

if TYPE_CHECKING:
    from main import GenerateSQLRequest
from helpers.main_helpers.main_methods import (
    _setup_dbmanager_and_agents,
    _is_positive,
    build_not_ready_error_details
)
from helpers.db_info import get_db_schema
from helpers.dual_logger import log_error
from helpers.language_utils import resolve_language_name

# Valid UI flags that should be preserved and saved
VALID_UI_FLAGS = {
    'show_sql',
    'explain_generated_query', 
    'treat_empty_result_as_error',
    'belt_and_suspenders'
}

def _filter_ui_flags(flags: dict) -> dict:
    """
    Filter request flags to include only valid UI flags.
    
    Removes backend technical flags (use_schema, use_examples, use_lsh, use_vector)
    and keeps only frontend UI flags for display and behavior control.
    
    Args:
        flags: Dictionary of flags from the request
        
    Returns:
        Dictionary containing only valid UI flags
    """
    if not flags:
        return {}
    
    # Filter to only valid UI flags
    filtered_flags = {k: v for k, v in flags.items() if k in VALID_UI_FLAGS}
    
    # Ensure all UI flags are present with default values if missing
    for flag_name in VALID_UI_FLAGS:
        if flag_name not in filtered_flags:
            # Default values for missing UI flags
            if flag_name == 'show_sql':
                filtered_flags[flag_name] = True
            elif flag_name == 'explain_generated_query':
                filtered_flags[flag_name] = True
            elif flag_name == 'treat_empty_result_as_error':
                filtered_flags[flag_name] = False
            elif flag_name == 'belt_and_suspenders':
                filtered_flags[flag_name] = False
    
    return filtered_flags


async def _initialize_request_state(
    request: "GenerateSQLRequest", 
    http_request: Request
) -> Tuple[SystemState, Optional[PlainTextResponse]]:
    """
    Initialize and validate the request state for SQL generation.
    
    Args:
        request: The SQL generation request
        http_request: The HTTP request object
        
    Returns:
        Tuple of (SystemState, Optional[PlainTextResponse])
        - SystemState if initialization successful
        - PlainTextResponse with error if initialization failed
    """
    # Create the required context objects from frontend data
    from model.contexts.request_context import RequestContext  
    from model.contexts.database_context import DatabaseContext
    
    # Create request context from what the frontend provides
    # Normalize functionality_level to uppercase as expected by RequestContext validator
    functionality_level = request.functionality_level.upper() if request.functionality_level else "BASIC"
    request_context = RequestContext(
        question=request.question,  # Original question from UI
        original_question=request.question,  # Preserve a copy for state/logs
        username=http_request.headers.get("X-Username", "anonymous"),
        workspace_id=request.workspace_id,
        workspace_name="Unknown",  # Will be updated after setup
        functionality_level=functionality_level
    )
    
    # Create minimal database context (will be updated after setup)
    database_context = DatabaseContext()
    
    # Initialize SystemState with the contexts
    from model.system_state import SemanticContext, SchemaDerivations, GenerationResults, ExecutionState
    
    state = SystemState(
        request=request_context,
        database=database_context,
        semantic=SemanticContext(),  # Empty initially
        schemas=SchemaDerivations(),  # Empty initially
        generation=GenerationResults(),  # Empty initially
        execution=ExecutionState(),  # Empty initially
        submitted_question=request.question  # Initially same as original
    )
    
    # Directly call setup without caching to avoid state corruption issues
    try:
        setup_result = await _setup_dbmanager_and_agents(request.workspace_id, request)
    except Exception as e:
        error_details = {
            "workspace_id": request.workspace_id,
            "question": state.question,  # Use the working question from state
            "functionality_level": request.functionality_level,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        log_error(f"Critical failure in _setup_dbmanager_and_agents: {json.dumps(error_details)}")
        
        detail = (
            "ERROR: Setup failed while preparing resources for SQL generation.\n"
            f"Reason: {type(e).__name__}: {str(e)}\n"
            "Hints: Check DJANGO_API_KEY, database plugins, and vector DB backends configuration.\n"
        )
        return None, PlainTextResponse(detail, status_code=500)

    # Update request context with workspace name, scope and language from setup
    workspace_config = setup_result.get("workspace_config", {})
    scope = workspace_config.get("sql_db", {}).get("scope", "")
    language = resolve_language_name(workspace_config.get("sql_db", {}).get("language", "English"))
    updated_request = request_context.model_copy(update={
        "workspace_name": setup_result.get("workspace_name", "Unknown"),
        "scope": scope,
        "language": language
    })
    
    # Update database context with configuration from setup
    # Also get treat_empty_result_as_error from request flags if provided
    treat_empty_as_error = request.flags.get("treat_empty_result_as_error", False) if request.flags else False
    
    updated_database = database_context.model_copy(update={
        "dbmanager": setup_result.get("dbmanager"),
        "treat_empty_result_as_error": treat_empty_as_error
    })
    
    # Create services context with external services from setup
    from model.contexts.external_services import ExternalServices
    services_context = ExternalServices(
        vdbmanager=setup_result.get("vdbmanager"),
        agents_and_tools=setup_result.get("agent_manager"),
        sql_db_config=setup_result.get("sql_db_config", {}),
        workspace=workspace_config,
        number_of_tests_to_generate=workspace_config.get("number_of_tests_to_generate", 3),
        number_of_sql_to_generate=workspace_config.get("number_of_sql_to_generate", 12),
        # Store only UI flags from the request (filter out backend flags)
        request_flags=_filter_ui_flags(request.flags)
    )
    
    # Recreate SystemState with updated contexts
    state = SystemState(
        request=updated_request,
        database=updated_database,
        semantic=SemanticContext(),  # Empty initially
        schemas=SchemaDerivations(),  # Empty initially
        generation=GenerationResults(),  # Empty initially
        execution=ExecutionState(),  # Empty initially
        services=services_context,
        submitted_question=request.question  # Initially same as original
    )
    
    # Get managers for validation (the properties should be accessible via database context)
    dbmanager = setup_result.get("dbmanager")
    vdbmanager = setup_result.get("vdbmanager")
    dbmanager_status = setup_result.get("dbmanager_status", "Not initialized")
    vdbmanager_status = setup_result.get("vdbmanager_status", "Not initialized")
    
    if not _is_positive(dbmanager_status, dbmanager) or not _is_positive(vdbmanager_status, vdbmanager):
        error_details = {
            "workspace_id": request.workspace_id,
            "workspace_name": state.workspace_name,
            "dbmanager_status": dbmanager_status,
            "vdbmanager_status": vdbmanager_status,
            "dbmanager_exists": dbmanager is not None,
            "vdbmanager_exists": vdbmanager is not None
        }
        log_error(f"Critical failure in manager validation: {json.dumps(error_details)}")
        
        details = build_not_ready_error_details(
            workspace_name=state.workspace_name,
            workspace_config=setup_result.get("workspace_config", {}),
            sql_db_config=setup_result.get("sql_db_config"),
            dbmanager_status=dbmanager_status,
            vdbmanager_status=vdbmanager_status,
            dbmanager=dbmanager,
            vdbmanager=vdbmanager,
        )
        return None, PlainTextResponse(details, status_code=400)
    
    # Critical Step 3: Get database schema with error handling
    try:
        state.full_schema = get_db_schema(state.dbmanager.db_id, state.dbmanager.schema)
        if not state.full_schema:
            raise ValueError("Database schema is empty - no tables found")
    except Exception as e:
        error_details = {
            "workspace_id": request.workspace_id,
            "db_id": state.dbmanager.db_id if state.dbmanager else None,
            "schema": state.dbmanager.schema if state.dbmanager else None,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        log_error(f"Critical failure in get_db_schema: {json.dumps(error_details)}")
        
        error_msg = (
            "ERROR: Failed to retrieve database schema.\n"
            f"Database: {state.dbmanager.db_id if state.dbmanager else 'Unknown'}\n"
            f"Reason: {str(e)}\n"
            "\nThis is a critical error - cannot proceed without database schema.\n"
            "Please verify:\n"
            "1. Database connection is active\n"
            "2. Database contains tables\n"
            "3. User has permission to read schema\n"
        )
        return None, PlainTextResponse(error_msg, status_code=500)
    
    return state, None
