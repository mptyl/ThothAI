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
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)

# Track sent logs to prevent duplicates
_sent_logs = set()

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
    logger.info(f"send_thoth_log called for workspace {workspace_id}, question: {state.question[:50] if state.question else 'N/A'}...")
    
    # Create a unique key for this log to prevent duplicates
    log_key = f"{workspace_id}_{username or 'anon'}_{state.question[:100] if state.question else ''}_{started_at.isoformat() if started_at else ''}"
    log_hash = hashlib.md5(log_key.encode()).hexdigest()
    
    if log_hash in _sent_logs:
        logger.warning(f"Duplicate log detected for workspace {workspace_id}, skipping send")
        return None
    
    try:
        django_server = os.getenv("DJANGO_SERVER", "http://localhost:8200")
        api_key = os.getenv("DJANGO_API_KEY")
        logger.info(f"Django server: {django_server}, API key present: {bool(api_key)}")
        
        if not api_key:
            logger.warning("DJANGO_API_KEY not found, cannot send ThothLog")
            return None
            
        # Prepare log data matching Django ThothLog model fields
        # NEW: Get data from specialized contexts instead of direct state access
        
        # Keywords from SemanticContext
        keywords_str = json.dumps(list(state.semantic.keywords) if hasattr(state, 'semantic') and state.semantic.keywords else [], ensure_ascii=False)
        
        # Evidence from SemanticContext
        evidences_str = json.dumps(list(state.semantic.evidence) if hasattr(state, 'semantic') and state.semantic.evidence else [], ensure_ascii=False)
        
        # SQL shots from SemanticContext (formatted for gold_sql_extracted)
        gold_sql_shots = []
        if hasattr(state, 'semantic') and state.semantic.sql_shots:
            gold_sql_shots = [
                {"question": q, "sql": s, "hint": h} 
                for q, s, h in state.semantic.sql_shots
            ]
        gold_sql_extracted_str = json.dumps(gold_sql_shots, ensure_ascii=False)
        
        # Schema data from SchemaDerivations context
        lsh_similar_columns_str = json.dumps(state.schemas.similar_columns if hasattr(state, 'schemas') and state.schemas.similar_columns else {}, ensure_ascii=False)
        schema_with_examples_str = json.dumps(state.schemas.schema_with_examples if hasattr(state, 'schemas') and state.schemas.schema_with_examples else {}, ensure_ascii=False)
        schema_from_vector_db_str = json.dumps(state.schemas.schema_from_vector_db if hasattr(state, 'schemas') and state.schemas.schema_from_vector_db else {}, ensure_ascii=False)
        
        # SQL shots for similar_questions (backward compatibility)
        similar_questions_str = gold_sql_extracted_str  # Same data, different field name
        
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
        
        # Collect per-attempt relevance events from state
        relevance_events: List[Dict[str, Any]] = []
        raw_events = getattr(state, 'relevance_guard_events', []) if hasattr(state, 'relevance_guard_events') else []
        if raw_events:
            for event in raw_events:
                if isinstance(event, dict):
                    relevance_events.append(event)

        # Start from any running totals accumulated during validation
        base_summary = dict(getattr(state, 'relevance_guard_summary', {}) or {})

        # Build a fresh summary from events (if any)
        computed_summary: Dict[str, Any] = {
            "events_recorded": len(relevance_events),
            "total_tests": sum(event.get('tests_total', 0) for event in relevance_events),
            "strict_total": sum(event.get('strict', 0) for event in relevance_events),
            "weak_total": sum(event.get('weak', 0) for event in relevance_events),
            "irrelevant_total": sum(event.get('irrelevant', 0) for event in relevance_events),
            "strict_evaluations": 0,
            "strict_failures": 0,
            "timeouts": 0,
        }
        for event in relevance_events:
            evaluation = event.get('strict_evaluation') or {}
            status = evaluation.get('status')
            if status == 'timeout':
                computed_summary["timeouts"] += 1
            if status == 'completed':
                answers = evaluation.get('answers') or []
                computed_summary["strict_evaluations"] += len(answers)
                computed_summary["strict_failures"] += evaluation.get('failed', 0)

        # IMPORTANT: Do not wipe non-zero running totals with zero computed values
        # When no events are present at this point (e.g., telemetry flush timing),
        # preserve the base summary that validators already aggregated.
        if relevance_events:
            # Merge numbers by simple overwrite since they were recomputed from events
            relevance_summary = {**base_summary, **computed_summary}
        else:
            relevance_summary = dict(base_summary)
            # Provide stable keys so the admin UI renders consistently
            # but avoid overwriting non-zero values with zeros
            relevance_summary.setdefault("events_recorded", base_summary.get("events_recorded", 0))
            relevance_summary.setdefault("total_tests", base_summary.get("total_tests", 0))
            relevance_summary.setdefault("strict_total", base_summary.get("strict_total", 0))
            relevance_summary.setdefault("weak_total", base_summary.get("weak_total", 0))
            relevance_summary.setdefault("irrelevant_total", base_summary.get("irrelevant_total", 0))
            relevance_summary.setdefault("strict_evaluations", base_summary.get("strict_evaluations", 0))
            relevance_summary.setdefault("strict_failures", base_summary.get("strict_failures", 0))
            relevance_summary.setdefault("timeouts", base_summary.get("timeouts", 0))
            if base_summary and not raw_events:
                logger.debug("Relevance summary present but no events attached; preserving base totals.")

        # Fallback: if we still have zeros but evidence-critical tests exist, rebuild
        # a minimal relevance summary directly from current state using pure-Python classifier.
        try:
            def _all_zero(summary: Dict[str, Any]) -> bool:
                return (
                    int(summary.get("events_recorded", 0)) == 0
                    and int(summary.get("total_tests", 0)) == 0
                    and int(summary.get("strict_total", 0)) == 0
                    and int(summary.get("weak_total", 0)) == 0
                    and int(summary.get("irrelevant_total", 0)) == 0
                )

            if _all_zero(relevance_summary):
                # Try to extract evidence-critical tests from state
                ev_tests: List[str] = []
                try:
                    if hasattr(state, 'filtered_tests') and state.filtered_tests:
                        ev_tests = [t for t in state.filtered_tests if isinstance(t, str) and '[EVIDENCE-CRITICAL]' in t]
                    elif hasattr(state, 'generated_tests') and state.generated_tests:
                        for _, answers in state.generated_tests:
                            if isinstance(answers, list):
                                ev_tests.extend([t for t in answers if isinstance(t, str) and '[EVIDENCE-CRITICAL]' in t])
                except Exception:
                    ev_tests = []

                # SQL string to classify against
                sql_for_class = None
                try:
                    sql_for_class = (
                        getattr(state.generation, 'generated_sql', None)
                        if hasattr(state, 'generation') else None
                    ) or getattr(state, 'last_SQL', None)
                except Exception:
                    sql_for_class = getattr(state, 'last_SQL', None)

                if ev_tests and sql_for_class:
                    try:
                        # Lazy import to avoid circular imports at module load
                        from agents.validators.relevance_guard import classify_tests, load_config_from_env
                        cfg = None
                        try:
                            cfg = load_config_from_env()
                        except Exception:
                            cfg = None
                        question_text = getattr(getattr(state, 'request', None), 'question', None) or getattr(state, 'question', '') or ''
                        q_lang = None
                        db_lang = None
                        try:
                            q_lang = getattr(getattr(state, 'request', None), 'original_language', None) or getattr(state, 'original_language', None)
                            db_lang = getattr(getattr(state, 'request', None), 'language', None)
                        except Exception:
                            pass
                        classification = classify_tests(
                            question=question_text,
                            sql=sql_for_class,
                            tests=ev_tests,
                            cfg=cfg,
                            langs=(q_lang or '', db_lang or ''),
                        )

                        # Build a minimal, correct summary
                        relevance_summary = {
                            "events_recorded": 1,
                            "total_tests": len(ev_tests),
                            "strict_total": len(classification.get('strict', [])),
                            "weak_total": len(classification.get('weak', [])),
                            "irrelevant_total": len(classification.get('irrelevant', [])),
                            # Keep evaluation counters at zero; we didn't re-run strict evaluator here
                            "strict_evaluations": int(base_summary.get("strict_evaluations", 0) or 0),
                            "strict_failures": int(base_summary.get("strict_failures", 0) or 0),
                            "timeouts": int(base_summary.get("timeouts", 0) or 0),
                        }
                        logger.info("Rebuilt evidence relevance summary via fallback classifier (no telemetry events available)")
                    except Exception as e:
                        logger.debug(f"Fallback relevance classification skipped due to error: {e}")
        except Exception as e:
            logger.debug(f"Error in fallback relevance summary computation: {e}")

        model_retry_events: List[Dict[str, Any]] = []
        raw_retry_events = getattr(state, 'model_retry_events', []) if hasattr(state, 'model_retry_events') else []
        if raw_retry_events:
            for event in raw_retry_events:
                if isinstance(event, dict):
                    model_retry_events.append(event)

        retry_history = list(getattr(state, 'retry_history', []) or [])

        log_data = {
            # Basic request information from RequestContext
            "username": state.request.username if hasattr(state, 'request') else (username or "anonymous"),
            "workspace": state.request.workspace_name if hasattr(state, 'request') else (workspace_name or f"Workspace_{workspace_id}"),
            "started_at": state.request.started_at.isoformat() if hasattr(state, 'request') and state.request.started_at else (started_at.isoformat() if started_at else datetime.now(local_tz).isoformat()),
            "terminated_at": terminated_at.isoformat(),
            "question": state.request.question if hasattr(state, 'request') else (state.original_question or state.question or "No question provided"),
            "db_language": "en",  # Default fallback since language attribute is not available in current context structure
            "question_language": (state.request.original_language if hasattr(state, 'request') and state.request.original_language else (state.original_language if hasattr(state, 'original_language') else "en")) or "en",
            "translated_question": state.request.question if hasattr(state, 'request') and state.request.original_question and state.request.original_question != state.request.question else "",
            
            # NEW: Flags from ExternalServices
            "flags_activated": state.services.request_flags if hasattr(state, 'services') and state.services.request_flags else {},
            
            # Data from SemanticContext
            "keywords_list": keywords_str,
            "evidences": evidences_str,
            "similar_questions": similar_questions_str,  # Backward compatibility
            
            # NEW: Gold SQL extracted from vector DB
            "gold_sql_extracted": gold_sql_extracted_str,
            
            # Data from SchemaDerivations
            "reduced_schema": state.schemas.reduced_mschema if hasattr(state, 'schemas') and state.schemas.reduced_mschema else "",
            "used_mschema": state.schemas.used_mschema if hasattr(state, 'schemas') and state.schemas.used_mschema else "",
            
            # NEW: LSH similar columns
            "lsh_similar_columns": lsh_similar_columns_str,
            "schema_with_examples": schema_with_examples_str,
            "schema_from_vector_db": schema_from_vector_db_str,
            # Data from GenerationResults context
            "generated_tests": state.generation.generated_tests_json if hasattr(state, 'generation') and state.generation.generated_tests_json else "",
            "generated_tests_count": len(state.generation.generated_tests) if hasattr(state, 'generation') and state.generation.generated_tests else 0,
            
            # NEW: Reduced tests (if test reduction was performed)
            "reduced_tests": state.generation.filtered_tests_json if hasattr(state, 'generation') and state.generation.filtered_tests_json else "",
            
            # Evaluation results from GenerationResults
            "evaluation_results": state.generation.evaluation_results_json if hasattr(state, 'generation') and state.generation.evaluation_results_json else "",
            
            # NEW: Evaluation judgments (detailed test-by-test results)
            "evaluation_judgments": json.dumps(state.generation.evaluation_results if hasattr(state, 'generation') and state.generation.evaluation_results else [], ensure_ascii=False),
            
            # Generated SQL and explanation from GenerationResults  
            "generated_sql": state.generation.generated_sql if hasattr(state, 'generation') and state.generation.generated_sql else "",
            "sql_explanation": state.generation.sql_explanation if hasattr(state, 'generation') and state.generation.sql_explanation else "",
            
            # Pool of generated SQL queries from GenerationResults
            "pool_of_generated_sql": state.generation.generated_sqls_json if hasattr(state, 'generation') and state.generation.generated_sqls_json else "[]",
            
            # Directives and agent info (backward compatibility)
            "directives": state.directives if hasattr(state, 'directives') else "",
            "successful_agent_name": state.generation.successful_agent_name if hasattr(state, 'generation') and state.generation.successful_agent_name else "",
            "sql_generation_failure_message": state.execution.sql_generation_failure_message if hasattr(state, 'execution') and state.execution.sql_generation_failure_message else "",
            
            # NEW: SQL status and evaluation case
            "sql_status": getattr(state.execution, 'sql_status', '') if hasattr(state, 'execution') else '',
            "evaluation_case": getattr(state.execution, 'evaluation_case', '') if hasattr(state, 'execution') else '',
            
            # NEW: Evaluation details (always sent)
            "evaluation_details": json.dumps(getattr(state.execution, 'evaluation_details', []), ensure_ascii=False) if hasattr(state, 'execution') else "[]",
            "pass_rates": json.dumps(getattr(state.execution, 'pass_rates', {}), ensure_ascii=False) if hasattr(state, 'execution') else "{}",
            "selected_sql_complexity": getattr(state.execution, 'selected_sql_complexity', None) if hasattr(state, 'execution') else None,
            
            # NEW: All timing information from ExecutionState
            # Validation phase timing
            "validation_start": getattr(state.execution, 'validation_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'validation_start_time', None) else None,
            "validation_end": getattr(state.execution, 'validation_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'validation_end_time', None) else None,
            "validation_duration_ms": int(getattr(state.execution, 'validation_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Keyword generation phase timing
            "keyword_generation_start": getattr(state.execution, 'keyword_generation_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'keyword_generation_start_time', None) else None,
            "keyword_generation_end": getattr(state.execution, 'keyword_generation_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'keyword_generation_end_time', None) else None,
            "keyword_generation_duration_ms": int(getattr(state.execution, 'keyword_generation_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Schema preparation phase timing
            "schema_preparation_start": getattr(state.execution, 'schema_preparation_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'schema_preparation_start_time', None) else None,
            "schema_preparation_end": getattr(state.execution, 'schema_preparation_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'schema_preparation_end_time', None) else None,
            "schema_preparation_duration_ms": int(getattr(state.execution, 'schema_preparation_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Context retrieval phase timing
            "context_retrieval_start": getattr(state.execution, 'context_retrieval_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'context_retrieval_start_time', None) else None,
            "context_retrieval_end": getattr(state.execution, 'context_retrieval_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'context_retrieval_end_time', None) else None,
            "context_retrieval_duration_ms": int(getattr(state.execution, 'context_retrieval_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # SQL generation phase timing
            "sql_generation_start": getattr(state.execution, 'sql_generation_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'sql_generation_start_time', None) else None,
            "sql_generation_end": getattr(state.execution, 'sql_generation_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'sql_generation_end_time', None) else None,
            "sql_generation_duration_ms": int(getattr(state.execution, 'sql_generation_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Test generation phase timing  
            "test_generation_start": getattr(state.execution, 'test_generation_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'test_generation_start_time', None) else None,
            "test_generation_end": getattr(state.execution, 'test_generation_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'test_generation_end_time', None) else None,
            "test_generation_duration_ms": int(getattr(state.execution, 'test_generation_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Test reduction phase timing (optional)
            "test_reduction_start": getattr(state.execution, 'test_reduction_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'test_reduction_start_time', None) else None,
            "test_reduction_end": getattr(state.execution, 'test_reduction_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'test_reduction_end_time', None) else None,
            "test_reduction_duration_ms": int(getattr(state.execution, 'test_reduction_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Evaluation phase timing
            "evaluation_start": getattr(state.execution, 'evaluation_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'evaluation_start_time', None) else None,
            "evaluation_end": getattr(state.execution, 'evaluation_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'evaluation_end_time', None) else None,
            "evaluation_duration_ms": int(getattr(state.execution, 'evaluation_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # SQL selection phase timing
            "sql_selection_start": getattr(state.execution, 'sql_selection_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'sql_selection_start_time', None) else None,
            "sql_selection_end": getattr(state.execution, 'sql_selection_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'sql_selection_end_time', None) else None,
            "sql_selection_duration_ms": int(getattr(state.execution, 'sql_selection_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Belt and Suspenders timing (if performed)
            "belt_and_suspenders_start": getattr(state.execution, 'belt_and_suspenders_start_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'belt_and_suspenders_start_time', None) else None,
            "belt_and_suspenders_end": getattr(state.execution, 'belt_and_suspenders_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'belt_and_suspenders_end_time', None) else None,
            "belt_and_suspenders_duration_ms": int(getattr(state.execution, 'belt_and_suspenders_duration_ms', 0)) if hasattr(state, 'execution') else 0,
            
            # Escalation tracking flags
            "advanced_escalation": getattr(state.execution, 'advanced_escalation', False) if hasattr(state, 'execution') else False,
            "expert_escalation": getattr(state.execution, 'expert_escalation', False) if hasattr(state, 'execution') else False,
            
            # Final process end time
            "process_end_time": getattr(state.execution, 'process_end_time', None).isoformat() if hasattr(state, 'execution') and getattr(state.execution, 'process_end_time', None) else terminated_at.isoformat(),
            
            # Schema data
            "similar_columns": lsh_similar_columns_str,  # backward compatibility, now contains LSH data
            # 20) Selection metrics including detailed test results
            "selection_metrics": state.selection_metrics_json if hasattr(state, 'selection_metrics_json') else "",
            # 21) Enhanced Evaluation fields
            "enhanced_evaluation_thinking": state.enhanced_evaluation_result[0] if state.enhanced_evaluation_result else "",
            "enhanced_evaluation_answers": state.enhanced_evaluation_result[1] if state.enhanced_evaluation_result else [],
            "enhanced_evaluation_selected_sql": state.enhanced_evaluation_selected_sql if hasattr(state, 'enhanced_evaluation_selected_sql') and state.enhanced_evaluation_selected_sql is not None else "",

            # Evidence relevance and retry telemetry
            "evidence_relevance_events": relevance_events,
            "evidence_relevance_summary": relevance_summary,
            "model_retry_events": model_retry_events,
            "retry_history": retry_history,
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
            
            # Mark this log as sent to prevent duplicates
            _sent_logs.add(log_hash)
            
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
