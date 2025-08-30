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
Preprocessing phases helper for SQL Generator.

This module contains the preprocessing phases of the SQL generation pipeline:
- Question validation and translation
- Keyword extraction
- Context retrieval from vector databases
"""

import json
import logging
from typing import TYPE_CHECKING

from fastapi import Request

from model.system_state import SystemState
from helpers.dual_logger import log_error, log_warning
from helpers.main_helpers.main_keyword_extraction import extract_keywords
from helpers.main_helpers.main_schema_link_strategy import decide_schema_link_strategy
from helpers.main_helpers.main_generate_mschema import to_mschema

if TYPE_CHECKING:
    from main import GenerateSQLRequest

logger = logging.getLogger(__name__)


async def _validate_question_phase(
    state: SystemState,
    request: "GenerateSQLRequest",
    http_request: Request
):
    """
    Validate the user's question using the question validator agent.
    Handles language detection and translation coordination.
    
    Args:
        state: The system state
        request: The SQL generation request
        http_request: The HTTP request object
        
    Yields:
        Progress messages to client
    """
    # Check for client disconnection before validation
    if await http_request.is_disconnected():
        logger.info("Client disconnected before validation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    # Validation
    has_validator = bool(getattr(state.agents_and_tools, 'question_validator_agent', None))
    if has_validator:
        validation_result = await state.run_question_validation_with_translation()
        
        # Handle translation if it occurred
        if validation_result.original_language and validation_result.original_language != state.request.language:
            # Translation happened
            state.translated_question = validation_result.question
            state.submitted_question = validation_result.question  # Use translated version
        else:
            # No translation needed
            state.submitted_question = state.original_question  # Use original
        
        if not validation_result.is_valid:
            error_details = {
                "workspace_id": request.workspace_id,
                "question": state.question,
                "validation_message": validation_result.message,
                "original_language": getattr(validation_result, 'original_language', None)
            }
            log_error(f"Question validation failed: {json.dumps(error_details)}")
            
            error_msg = {
                "type": "validation_failed",
                "component": "question_validator",
                "message": validation_result.message,
                "impact": "Cannot proceed with SQL generation",
                "action": "Please rephrase your question or check the requirements"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield validation_result.message + "\n"
            return
    else:
        yield "THOTHLOG:No validator available, proceeding without validation...\n"


async def _extract_keywords_phase(
    state: SystemState,
    request: "GenerateSQLRequest",
    http_request: Request
):
    """
    Extract keywords from the validated question using the keyword extraction agent.
    
    Args:
        state: The system state
        request: The SQL generation request
        http_request: The HTTP request object
        
    Yields:
        Progress messages to client
    """
    # Check for client disconnection before keyword extraction
    if await http_request.is_disconnected():
        logger.info("Client disconnected before keyword extraction")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    yield "THOTHLOG:Extracting keywords...\n"
    has_kw_agent = bool(getattr(state.agents_and_tools, 'keyword_extraction_agent', None))
    if has_kw_agent:
        state.keywords = await extract_keywords(state, state.question, state.agents_and_tools.keyword_extraction_agent)
        # Keywords are now stored in state.keywords
    else:
        # Critical: keyword extraction is required for the process
        error_details = {
            "workspace_id": request.workspace_id,
            "workspace_name": state.workspace_name,
            "agents_available": dir(state.agents_and_tools) if state.agents_and_tools else []
        }
        log_error(f"Critical: Keyword extraction agent not available: {json.dumps(error_details)}")
        
        error_msg = {
            "type": "critical_error",
            "component": "keyword_extraction",
            "message": "Keyword extraction agent is not configured",
            "details": "The keyword extraction agent is required but not available in this workspace",
            "impact": "Cannot proceed without keyword extraction - it's essential for context retrieval",
            "action": "Please check workspace agent configuration and ensure keyword_extraction_agent is configured"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield "ERROR: Keyword extraction agent not available - cannot proceed with SQL generation\n"
        return


async def _retrieve_context_phase(
    state: SystemState,
    request: "GenerateSQLRequest",
    http_request: Request
):
    """
    Retrieve context information from vector databases and prepare schema.
    Includes evidence retrieval, SQL examples, LSH extraction, and schema preparation.
    
    Args:
        state: The system state
        request: The SQL generation request
        http_request: The HTTP request object
        
    Yields:
        Progress messages to client
    """
    # Check for client disconnection before vector DB operations
    if await http_request.is_disconnected():
        logger.info("Client disconnected before vector DB operations")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    # Get evidences and SQL shots from vector databases
    evidence_success, evidence_list, evidence_error = state.get_evidence_from_vector_db()
    sql_success, sql_examples, sql_error = state.get_sql_from_vector_db()
    
    # Check if vector DB is completely unavailable (critical issue)
    if not state.vdbmanager:
        error_details = {
            "workspace_id": request.workspace_id,
            "workspace_name": state.workspace_name,
            "vdbmanager_status": "Unknown"
        }
        log_error(f"Critical: Vector database manager not available: {json.dumps(error_details)}")
        
        error_msg = {
            "type": "critical_error",
            "component": "vector_database",
            "message": "Vector database is not accessible",
            "details": "The vector database service is required but not available",
            "impact": "Cannot retrieve context, examples, or similar queries - SQL generation quality will be severely impacted",
            "action": "Please ensure Qdrant service is running and properly configured in workspace settings"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield "ERROR: Vector database not available - terminating SQL generation\n"
        return
    
    # If vector DB operations failed, send warning to user but continue
    if not evidence_success or not sql_success:
        yield "THOTHLOG:Vector database operations encountered issues\n"
        
        if not evidence_success and evidence_error:
            log_error(f"Evidence retrieval failed for workspace {request.workspace_id}: {evidence_error}")
            # Send formatted error to frontend
            error_data = json.dumps({
                "type": "vector_db_warning",
                "component": "evidence_retrieval",
                "message": evidence_error,
                "severity": "warning"
            }, ensure_ascii=True)
            yield f"SYSTEM_WARNING:{error_data}\n"
        
        if not sql_success and sql_error:
            log_error(f"SQL examples retrieval failed for workspace {request.workspace_id}: {sql_error}")
            # Send formatted error to frontend
            error_data = json.dumps({
                "type": "vector_db_warning",
                "component": "sql_examples_retrieval",
                "message": sql_error,
                "severity": "warning"
            }, ensure_ascii=True)
            yield f"SYSTEM_WARNING:{error_data}\n"
        
        yield "THOTHLOG:Proceeding with SQL generation despite vector DB issues...\n"
    
    # Check for client disconnection before LSH extraction
    if await http_request.is_disconnected():
        logger.info("Client disconnected before LSH extraction")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    # Extract schema using LSH similarity search  
    yield "THOTHLOG:Extracting example values from LSH\n"
    try:
        state.extract_schema_via_lsh() # updates similar_columns and schema_with_examples - VITAL, not optional!
        if not state.similar_columns and not state.schema_with_examples:
            log_warning(f"LSH extraction returned empty results for workspace {request.workspace_id}")
            yield "THOTHLOG:LSH extraction returned no results - continuing with reduced context\n"
    except Exception as e:
        error_details = {
            "workspace_id": request.workspace_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "keywords": state.keywords
        }
        log_error(f"Critical failure in LSH schema extraction: {json.dumps(error_details)}")
        
        # LSH files must be present - this is critical
        error_msg = {
            "type": "critical_error",
            "component": "lsh_extraction",
            "message": "Failed to extract schema using LSH",
            "details": str(e),
            "impact": "Cannot retrieve example values and similar columns - SQL generation accuracy will be severely impacted",
            "action": "Please ensure LSH files are generated and accessible for this database"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield f"ERROR: LSH schema extraction failed - {str(e)}\n"
        return
    
    # Extract schema from vector database
    yield "THOTHLOG:Extracting schema from vector database\n"
    try:
        state.extract_schema_from_vectordb() # updates schema_from_vector_db with column descriptions
        if not state.schema_from_vector_db:
            log_warning(f"Vector DB schema extraction returned empty results for workspace {request.workspace_id}")
            yield "THOTHLOG:Vector DB schema extraction returned no results - continuing with reduced context\n"
    except Exception as e:
        error_details = {
            "workspace_id": request.workspace_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "vdbmanager_exists": state.vdbmanager is not None
        }
        log_error(f"Vector DB schema extraction failed (non-critical): {json.dumps(error_details)}")
        
        # This can be tolerated - log warning but continue
        warning_msg = {
            "type": "vector_db_warning",
            "component": "schema_extraction",
            "message": f"Failed to extract schema from vector database: {str(e)}",
            "severity": "warning"
        }
        yield f"SYSTEM_WARNING:{json.dumps(warning_msg, ensure_ascii=True)}\n"
        yield "THOTHLOG:Continuing without vector DB schema enrichment\n"
        state.schema_from_vector_db = {}  # Set to empty to continue
    
    # Decide and implement schema strategy
    state.schema_link_strategy = await decide_schema_link_strategy(state)
    
    if state.schema_link_strategy == "WITHOUT_SCHEMA_LINK":
        # Create full schema without filtering
        yield "THOTHLOG:Generating SQL with FULL ENRICHED SCHEMA\n"
        state.create_enriched_schema()
        state.full_mschema = to_mschema(state.enriched_schema)
        state.used_mschema = state.full_mschema
    else:
        # WITH_SCHEMA_LINK 
        yield "THOTHLOG:Generating SQL with FILTERED REDUCED SCHEMA\n"
        state.create_filtered_schema()
        state.reduced_mschema = to_mschema(state.filtered_schema)
        state.used_mschema = state.reduced_mschema