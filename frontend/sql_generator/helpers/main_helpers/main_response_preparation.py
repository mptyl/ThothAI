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
Response preparation helper for SQL Generator.

This module handles the final response preparation phase of the SQL generation pipeline:
- SQL formatting and finalization
- SQL explanation generation
- Logging and state storage
"""

import json
import logging
import sqlparse
from typing import TYPE_CHECKING, Optional

from fastapi import Request

from model.system_state import SystemState
from helpers.dual_logger import log_error
from helpers.thoth_log_api import send_thoth_log

if TYPE_CHECKING:
    from main import GenerateSQLRequest

logger = logging.getLogger(__name__)
log_level = logging.getLogger().getEffectiveLevel()

# Dictionary to store SystemState for each workspace for Like functionality
WORKSPACE_STATES = {}


async def _prepare_final_response_phase(
    state: SystemState,
    request: "GenerateSQLRequest",
    http_request: Request,
    success: bool,
    selected_sql: Optional[str] = None
):
    """
    Prepare the final response including SQL formatting, explanation, and logging.
    
    Args:
        state: System state with results
        request: The original SQL generation request
        http_request: HTTP request for checking disconnection
        success: Whether SQL generation was successful
        selected_sql: The selected SQL query (if successful)
        
    Yields:
        Final response messages to client
    """
    # Update state with final results for logging
    if success:
        state.generated_sql = state.last_SQL
        
        # Critical check: verify SQL was actually generated
        if not state.last_SQL:
            error_details = {
                "workspace_id": request.workspace_id,
                "question": state.question,
                "success_flag": success,
                "selected_sql": selected_sql if selected_sql else None
            }
            log_error(f"Critical: Success reported but no SQL in state.last_SQL: {json.dumps(error_details)}")
            
            # Store error for logging
            state.execution.sql_generation_failure_message = "SQL generation reported success but no SQL was found"
            state.execution.sql_status = "FAILED"
            state.generation.generated_sql = f"ERROR: {state.execution.sql_generation_failure_message}"
            
            error_msg = {
                "type": "critical_error",
                "component": "sql_finalization",
                "message": "SQL generation reported success but no SQL was found",
                "details": "Internal state inconsistency detected",
                "impact": "Cannot proceed without a valid SQL statement",
                "action": "This is an internal error - please report this issue"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield "ERROR: Internal error - SQL generation state inconsistency\n"
            # Don't return - continue to log the error
        else:
            # Correct SQL delimiters based on database type before formatting
            try:
                if hasattr(state, 'database') and hasattr(state.database, 'db_type'):
                    from helpers.sql_delimiter_corrector import correct_sql_delimiters
                    corrected_sql = correct_sql_delimiters(state.last_SQL, state.database.db_type)
                    state.last_SQL = corrected_sql
                    logger.debug(f"SQL delimiters corrected for database type: {state.database.db_type}")
                else:
                    logger.warning("Database type not available, skipping delimiter correction")
            except Exception as e:
                logger.error(f"Error correcting SQL delimiters: {e}")
                # Continue with original SQL if correction fails
                pass
            
            # Format and send SQL
            formatted_sql = sqlparse.format(
                state.last_SQL, 
                reindent=True, 
                keyword_case='upper'
            )
            sql_formatted_data = json.dumps({
                "type": "sql_formatted",
                "sql": formatted_sql
            }, ensure_ascii=True)
            yield f"SQL_FORMATTED:{sql_formatted_data}\n"
        
        # Send SQL_READY marker for frontend
        yield "THOTHLOG:SQL generation successful. Ready for execution.\n"
        
        try:
            # Get SQL status and evaluation information from execution state
            sql_status = getattr(state.execution, 'sql_status', 'GOLD') if hasattr(state, 'execution') else 'GOLD'
            evaluation_case = getattr(state.execution, 'evaluation_case', '') if hasattr(state, 'execution') else ''
            pass_rates = getattr(state.execution, 'pass_rates', {}) if hasattr(state, 'execution') else {}
            best_pass_rate = max(pass_rates.values()) if pass_rates else 1.0
            
            sql_ready_data = json.dumps({
                "type": "sql_ready",
                "sql": state.last_SQL,
                "workspace_id": request.workspace_id,
                "timestamp": state.started_at.isoformat() if state.started_at else None,
                "username": state.username,
                "agent": state.successful_agent_name,
                # NEW: Include SQL status and evaluation details
                "sql_status": sql_status,
                "evaluation_case": evaluation_case,
                "pass_rate": best_pass_rate,
                "is_silver": sql_status == "SILVER",
                "is_gold": sql_status == "GOLD"
            }, ensure_ascii=True)
            
            yield f"SQL_READY:{sql_ready_data}\n"
            yield "THOTHLOG:Query ready for paginated execution\n"
            
        except Exception as e:
            log_error(f"Error preparing SQL_READY data: {e}")
            yield f"THOTHLOG:Error preparing query for execution: {str(e)}\n"
    else:
        # Handle failure case - check if we have an error message to log
        if hasattr(state.execution, 'sql_generation_failure_message') and state.execution.sql_generation_failure_message:
            # Use error message as placeholder for SQL in logging
            state.generation.generated_sql = f"ERROR: {state.execution.sql_generation_failure_message}"
            # Ensure sql_status is set to FAILED
            if not hasattr(state.execution, 'sql_status') or not state.execution.sql_status:
                state.execution.sql_status = "FAILED"
            logger.info(f"Processing failed SQL generation for logging: {state.execution.sql_generation_failure_message}")
            yield f"THOTHLOG:SQL generation failed: {state.execution.sql_generation_failure_message}\n"
        else:
            # Generic failure without specific message
            state.generation.generated_sql = "ERROR: SQL generation failed"
            state.execution.sql_status = "FAILED"
            state.execution.sql_generation_failure_message = "SQL generation failed without specific error message"
            logger.info("Processing failed SQL generation without specific error message")
            yield "THOTHLOG:SQL generation failed\n"
    
    # Check for client disconnection before SQL explanation
    if await http_request.is_disconnected():
        logger.info("Client disconnected before SQL explanation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    # Generate SQL explanation if successful AND if it was requested
    # Check if explain_generated_query flag was set to true in the request
    explain_requested = state.services.request_flags.get("explain_generated_query", False)
    
    if success and state.last_SQL and explain_requested:
        yield "THOTHLOG:Generating SQL explanation...\n"
        try:
            agent_manager = state.agents_and_tools
            if log_level <= logging.INFO:
                logger.debug(f"Agent manager available: {agent_manager is not None}, Has method: {hasattr(agent_manager, 'explain_generated_sql') if agent_manager else False}")
            
            if agent_manager and hasattr(agent_manager, 'explain_generated_sql'):
                # Extract schema and context
                schema_text = state.used_mschema if hasattr(state, 'used_mschema') and state.used_mschema else ""
                
                evidence_text = ""
                if hasattr(state, 'evidence') and state.evidence:
                    evidence_text = "\n".join([f"- {item}" for item in state.evidence])
                
                cot_text = state.cot if hasattr(state, 'cot') and state.cot else ""
                language = state.original_language if hasattr(state, 'original_language') and state.original_language else "English"
                
                # Generate explanation
                explanation = await agent_manager.explain_generated_sql(
                    question=state.question,
                    generated_sql=state.last_SQL,
                    database_schema=schema_text,
                    hints=evidence_text,
                    chain_of_thought=cot_text,
                    language=language
                )
                
                if explanation:
                    state.sql_explanation = explanation
                    
                    explanation_data = json.dumps({
                        "type": "sql_explanation",
                        "explanation": explanation,
                        "language": language
                    }, ensure_ascii=True)
                    
                    yield f"SQL_EXPLANATION:{explanation_data}\n"
                    yield "THOTHLOG:SQL explanation generated successfully\n"
                else:
                    yield "THOTHLOG:Warning: Failed to generate SQL explanation\n"
            else:
                yield "THOTHLOG:SQL explainer agent not available\n"
                
        except Exception as e:
            log_error(f"Error generating SQL explanation: {e}")
            yield f"THOTHLOG:Error generating explanation: {str(e)}\n"
    elif success and state.last_SQL and not explain_requested:
        # Explanation was not requested initially, don't generate it
        logger.debug(f"SQL explanation not requested for workspace {request.workspace_id}, skipping generation")
    
    # Store state for Like functionality
    if state.last_SQL:
        WORKSPACE_STATES[request.workspace_id] = state
        logger.debug(f"Stored SystemState for workspace {request.workspace_id} for Like functionality")
    
    # Send the log
    logger.info(f"Attempting to send ThothLog for workspace {request.workspace_id}, SQL success: {bool(state.last_SQL)}")
    try:
        log_result = await send_thoth_log(
            state, 
            request.workspace_id, 
            state.workspace_name,
            username=state.username,
            started_at=state.started_at
        )
        if log_result:
            logger.info(f"ThothLog sent successfully with ID: {log_result.get('id', 'unknown')}")
        else:
            logger.error("ThothLog send_thoth_log returned None")
    except Exception as e:
        logger.error(f"Exception sending ThothLog: {str(e)}", exc_info=True)
    
    # Send final message based on success status
    if success:
        yield "THOTHLOG:Process completed successfully - all details have been logged to the system\n"
    else:
        yield "THOTHLOG:Process completed with errors - all details have been logged to the system\n"