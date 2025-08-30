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
ThothLog API functions for logging SQL generation operations to Django backend
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import pytz
import json

logger = logging.getLogger(__name__)

async def send_thoth_log(state: Any, workspace_id: int, workspace_name: str = None, username: str = None, started_at: datetime = None) -> Optional[Dict[str, Any]]:
    """
    Send ThothLog data to Django backend after SQL generation.
    
    Args:
        system_state: The SystemState object containing all generation data
        workspace_id: The workspace ID for this operation
        workspace_name: The workspace name (optional)
        username: The authenticated username (optional)
        started_at: The timestamp when the endpoint was called (optional)
        
    Returns:
        Dict with response from API or None if error
    """
    logger.info(f"send_thoth_log called for workspace {workspace_id}")
    try:
        django_server = os.getenv("DJANGO_SERVER", "http://localhost:8200")
        api_key = os.getenv("DJANGO_API_KEY")
        logger.info(f"Django server: {django_server}, API key present: {bool(api_key)}")
        
        if not api_key:
            logger.warning("DJANGO_API_KEY not found, cannot send ThothLog")
            return None
            
        # Prepare log data matching Django ThothLog model fields
        # Convert arrays and dicts to JSON strings for text fields
        keywords_str = json.dumps(list(state.keywords) if state.keywords else [], ensure_ascii=False)
        evidences_str = json.dumps(list(state.evidence) if state.evidence else [], ensure_ascii=False)
        
        # Format SQL shots as JSON string
        sql_shots = [
            {"question": q, "sql": s, "description": d} 
            for q, s, d in (state.sql_shots or [])
        ]
        similar_questions_str = json.dumps(sql_shots, ensure_ascii=False)
        
        # Use the pre-formatted JSON string if available, otherwise format the list
        # if hasattr(system_state, 'generated_tests_json') and system_state.generated_tests_json:
        #     generated_tests_str = system_state.generated_tests_json
        # else:
        #     generated_tests_str = json.dumps(system_state.generated_tests if hasattr(system_state, 'generated_tests') else [], ensure_ascii=False)
        
        # Format similar_columns, schema_with_examples and schema_from_vector_db
        similar_columns_str = json.dumps(state.similar_columns if state.similar_columns else {}, ensure_ascii=False)
        schema_with_examples_str = json.dumps(state.schema_with_examples if state.schema_with_examples else {}, ensure_ascii=False)
        schema_from_vector_db_str = json.dumps(state.schema_from_vector_db if state.schema_from_vector_db else {}, ensure_ascii=False)
        
        # Show preview if available
       
     
        # 9) terminated_at - calculated just before sending log with local timezone
        # Get local timezone using pytz for better compatibility
        from tzlocal import get_localzone
        local_tz = get_localzone()
        terminated_at = datetime.now(local_tz)
        
        # Ensure started_at is in local timezone if it exists
        if started_at:
            # If started_at is timezone-naive, localize it
            if started_at.tzinfo is None:
                started_at = local_tz.localize(started_at)
            # If it's timezone-aware but in UTC, convert to local
            elif started_at.tzinfo.tzname(started_at) == 'UTC':
                started_at = started_at.astimezone(local_tz)
        
        log_data = {
            # 1) Username of authenticated user (default if not provided)
            "username": username or "anonymous",
            # 2) Workspace name
            "workspace": workspace_name or f"Workspace_{workspace_id}",
            # 3) Started at timestamp from when endpoint was called (with local timezone)
            "started_at": started_at.isoformat() if started_at else datetime.now(local_tz).isoformat(),
            # 9) Terminated at timestamp (just before sending log)
            "terminated_at": terminated_at.isoformat(),
            "question": state.original_question or state.question or "No question provided",
            "db_language": state.dbmanager.language if state.dbmanager and hasattr(state.dbmanager, 'language') else "en",
            "question_language": state.original_language or state.language,
            "translated_question": state.question if state.original_question != state.question else "",
            # 4) Keywords from SystemState
            "keywords_list": keywords_str,
            # 5) Evidences from SystemState  
            "evidences": evidences_str,
            # 6) SQL shots as similar_questions
            "similar_questions": similar_questions_str,
            # 7) Reduced schema = reduced_mschema from SystemState
            "reduced_schema": state.reduced_mschema if state.reduced_mschema else "",
            # 8) Used MSchema from SystemState  
            "used_mschema": state.used_mschema if state.used_mschema else "",
            # 8) Generated tests from SystemState (simplified: just thinking and answers)
            "generated_tests": state.generated_tests_json if hasattr(state, 'generated_tests_json') else "",
            # 9) Generated tests count
            "generated_tests_count": len(state.generated_tests) if hasattr(state, 'generated_tests') else 0,
            # Evaluation results (separate from tests)
            "evaluation_results": state.evaluation_results_json if hasattr(state, 'evaluation_results_json') else "",
            "evaluation_count": len(state.evaluation_results) if hasattr(state, 'evaluation_results') else 0,
            # 10) Generated SQL and explanation - empty for now, will be populated later
            "generated_sql": state.generated_sql if hasattr(state, 'generated_sql') and state.generated_sql is not None else "",
            "sql_explanation": state.sql_explanation if hasattr(state, 'sql_explanation') and state.sql_explanation is not None else "",
            # 11) Directives from SystemState
            "directives": state.directives if hasattr(state, 'directives') else "",
            # 12) Successful agent name from SystemState
            "successful_agent_name": state.successful_agent_name if hasattr(state, 'successful_agent_name') else "",
            # 13) SQL generation failure message from SystemState
            "sql_generation_failure_message": state.sql_generation_failure_message if hasattr(state, 'sql_generation_failure_message') else "",
            # 14) Pool of generated SQL queries from SystemState
            "pool_of_generated_sql": state.generated_sqls_json if hasattr(state, 'generated_sqls_json') else "[]",
            # 15) Schema link strategy fields from SystemState
            "available_context_tokens": state.available_context_tokens if hasattr(state, 'available_context_tokens') else None,
            "full_schema_tokens_count": state.full_schema_tokens_count if hasattr(state, 'full_schema_tokens_count') else None,
            # 16) Schema link strategy decision
            "schema_link_strategy": state.schema_link_strategy if hasattr(state, 'schema_link_strategy') else "",
            # 17) Similar columns from LSH/Vector search
            "similar_columns": similar_columns_str,
            # 18) Schema with examples from LSH/Vector search
            "schema_with_examples": schema_with_examples_str,
            # 19) Schema from vector database with column descriptions
            "schema_from_vector_db": schema_from_vector_db_str,
            # 20) Selection metrics including detailed test results
            "selection_metrics": state.selection_metrics_json if hasattr(state, 'selection_metrics_json') else "",
        }
        
        # Log summary of data being sent only in DEBUG level
        logger.debug(f"Sending ThothLog: {log_data.get('generated_tests_count', 0)} tests, {log_data.get('evaluation_count', 0)} evaluations")
        
        # API endpoint for ThothLog
        url = f"{django_server}/api/thoth-logs/"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
              
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json=log_data, 
                headers=headers, 
                timeout=10.0
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"ThothLog sent successfully, ID: {result.get('id', 'unknown')}")
            return result
            
    except httpx.HTTPStatusError as e:
        # Log error concisely
        if e.response.status_code == 400:
            try:
                error_details = e.response.json()
                field_errors = ", ".join([f"{field}: {errors}" for field, errors in error_details.items()])
                logger.error(f"ThothLog validation error (400): {field_errors}")
            except:
                logger.error(f"ThothLog HTTP error {e.response.status_code}: {e.response.text[:200]}")
        else:
            logger.error(f"ThothLog HTTP error {e.response.status_code}")
        logger.debug(f"Full response: {e.response.text}")  # Full details only in DEBUG
        return None
    except httpx.RequestError as e:
        logger.error(f"ThothLog connection error: {str(e)} (Backend: {django_server})")
        return None
    except Exception as e:
        logger.error(f"ThothLog unexpected error: {str(e)}")
        logger.debug("Traceback: ", exc_info=True)  # Stack trace only in DEBUG
        return None