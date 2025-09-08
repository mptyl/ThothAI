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
SQL Generation Pipeline Steps

This module contains helper functions to break down the large generate_response
function into smaller, manageable, testable pieces.
"""

import json
from typing import AsyncGenerator, Any
import logging

logger = logging.getLogger(__name__)


async def validate_question_step(state: Any, http_request: Any) -> AsyncGenerator[str, None]:
    """
    Step 1: Validate the user's question with translation if needed.
    
    Yields status messages and handles validation failures.
    """
    # Check for client disconnection
    if await http_request.is_disconnected():
        logger.info("Client disconnected before validation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    # Check if validator is available
    has_validator = bool(getattr(state.agents_and_tools, 'question_validator_agent', None))
    
    if not has_validator:
        yield "THOTHLOG:No validator available, proceeding without validation...\n"
        return
    
    # Run validation with translation
    validation_result = await state.run_question_validation_with_translation()
    
    # Handle state updates from validation/translation
    state.question = validation_result.question
    if validation_result.original_question:
        state.original_question = validation_result.original_question
    if validation_result.original_language:
        state.original_language = validation_result.original_language
    
    # Check validation result
    if not validation_result.is_valid:
        error_details = {
            "workspace_id": state.workspace_id if hasattr(state, 'workspace_id') else None,
            "question": state.question,
            "validation_message": validation_result.message,
            "original_language": getattr(validation_result, 'original_language', None)
        }
        logger.error(f"Question validation failed: {json.dumps(error_details)}")
        
        error_msg = {
            "type": "validation_failed",
            "component": "question_validator",
            "message": validation_result.message,
            "impact": "Cannot proceed with SQL generation",
            "action": "Please rephrase your question or check the requirements"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield validation_result.message + "\n"
        raise StopAsyncIteration  # Signal to stop the pipeline


async def extract_keywords_step(state: Any, http_request: Any) -> AsyncGenerator[str, None]:
    """
    Step 2: Extract keywords from the question.
    
    Yields status messages about keyword extraction.
    """
    # Check for client disconnection
    if await http_request.is_disconnected():
        logger.info("Client disconnected before keyword extraction")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    yield "THOTHLOG:Extracting keywords from question...\n"
    
    # Extract keywords using the agent
    if state.agents_and_tools and hasattr(state.agents_and_tools, 'kw_agent'):
        from keyword_extraction import extract_keywords
        state.keywords = await extract_keywords(
            state,
            state.question,
            state.agents_and_tools.kw_agent
        )
        
        if state.keywords:
            yield f"THOTHLOG:Extracted {len(state.keywords)} keywords\n"
            # Send keywords to frontend
            keywords_json = json.dumps({
                "keywords": list(state.keywords),
                "count": len(state.keywords)
            }, ensure_ascii=True)
            yield f"KEYWORDS:{keywords_json}\n"
        else:
            yield "THOTHLOG:No keywords extracted\n"
    else:
        yield "THOTHLOG:Keyword extraction not available\n"


async def retrieve_context_step(
    state: Any, 
    http_request: Any,
    vdbmanager: Any
) -> AsyncGenerator[str, None]:
    """
    Step 3: Retrieve context from vector DB and LSH.
    
    Always executes vector DB and LSH operations for optimal SQL generation.
    Yields status messages about context retrieval.
    """
    # Vector DB retrieval - Always execute if vdbmanager is available
    if vdbmanager:
        if await http_request.is_disconnected():
            logger.info("Client disconnected before vector DB operations")
            yield "CANCELLED:Operation cancelled by user\n"
            return
        
        yield "THOTHLOG:Searching vector database for relevant schema...\n"
        
        try:
            from helpers.main_helpers.main_schema_extraction_from_vectordb import (
                extract_schema_via_vector_db,
                format_schema_for_display
            )
            
            # Extract schema from vector DB
            evidence_list, sql_examples = await extract_schema_via_vector_db(
                state,
                vdbmanager,
                state.question,
                state.keywords
            )
            
            # Store in state
            state.evidence = evidence_list if evidence_list else []
            state.sql_shots = sql_examples if sql_examples else []
            
            # Format for display
            formatted_schema = format_schema_for_display(evidence_list, sql_examples)
            state.schema_from_vector_db = formatted_schema
            
            # Send to frontend
            if formatted_schema:
                schema_json = json.dumps({
                    "tables": len(evidence_list) if evidence_list else 0,
                    "examples": len(sql_examples) if sql_examples else 0
                }, ensure_ascii=True)
                yield f"SCHEMA_CONTEXT:{schema_json}\n"
                yield f"THOTHLOG:Found {len(evidence_list) if evidence_list else 0} relevant tables and {len(sql_examples) if sql_examples else 0} SQL examples\n"
            
        except Exception as e:
            logger.error(f"Error extracting schema from vector DB: {e}")
            yield f"WARNING:Vector DB extraction failed: {str(e)}\n"
    
    # LSH retrieval - Always execute if dbmanager is available
    if state.dbmanager:
        if await http_request.is_disconnected():
            logger.info("Client disconnected before LSH extraction")
            yield "CANCELLED:Operation cancelled by user\n"
            return
        
        yield "THOTHLOG:Searching for similar SQL examples using LSH...\n"
        
        try:
            from helpers.lsh_search import search_similar_questions_lsh
            
            lsh_results = search_similar_questions_lsh(
                state.dbmanager,
                state.question,
                state.keywords,
                k=5
            )
            
            if lsh_results:
                # Update state with LSH results
                state.sql_shots = lsh_results
                
                # Send to frontend
                lsh_json = json.dumps({
                    "similar_queries": len(lsh_results),
                    "method": "LSH"
                }, ensure_ascii=True)
                yield f"SIMILAR_QUERIES:{lsh_json}\n"
                yield f"THOTHLOG:Found {len(lsh_results)} similar SQL examples via LSH\n"
            else:
                yield "THOTHLOG:No similar examples found via LSH\n"
                
        except Exception as e:
            logger.error(f"Error in LSH search: {e}")
            yield f"WARNING:LSH search failed: {str(e)}\n"


async def generate_sql_candidates_step(
    state: Any,
    http_request: Any,
    num_sqls: int
) -> AsyncGenerator[str, None]:
    """
    Step 4: Generate SQL candidates.
    
    Yields status messages and generated SQL queries.
    """
    if await http_request.is_disconnected():
        logger.info("Client disconnected before SQL generation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    yield f"THOTHLOG:Generating {num_sqls} SQL candidates based on context...\n"
    
    # Generate SQL queries
    sql_agent = state.agents_and_tools.sql_agent if state.agents_and_tools else None
    
    if not sql_agent:
        yield "ERROR:SQL generation agent not available\n"
        raise StopAsyncIteration
    
    # Run SQL generation
    try:
        state.sql_results = await sql_agent.run(state.question)
        
        if state.sql_results and len(state.sql_results) > 0:
            state.sql_count = len(state.sql_results)
            state.generated_sqls = [sql for sql, _ in state.sql_results]
            
            # Send SQL candidates to frontend
            sql_json = json.dumps({
                "count": state.sql_count,
                "sqls": state.generated_sqls
            }, ensure_ascii=True)
            yield f"SQL_CANDIDATES:{sql_json}\n"
            yield f"THOTHLOG:Generated {state.sql_count} SQL candidates\n"
        else:
            yield "ERROR:Failed to generate SQL queries\n"
            raise StopAsyncIteration
            
    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        yield f"ERROR:SQL generation failed: {str(e)}\n"
        raise StopAsyncIteration


async def test_and_evaluate_step(
    state: Any,
    http_request: Any
) -> AsyncGenerator[str, None]:
    """
    Step 5: Generate tests and evaluate SQL candidates.
    
    Yields status messages about testing and evaluation.
    """
    # Test generation
    if await http_request.is_disconnected():
        logger.info("Client disconnected before test generation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    yield "THOTHLOG:Generating test cases for SQL validation...\n"
    
    test_generator = state.agents_and_tools.test_generator_agent if state.agents_and_tools else None
    
    if test_generator:
        try:
            test_results = await test_generator.run(state)
            
            if test_results:
                state.generated_tests = test_results
                state.generated_tests_json = json.dumps(test_results, ensure_ascii=False)
                
                yield f"THOTHLOG:Generated {len(test_results)} test suites\n"
                
                # Send test info to frontend
                test_json = json.dumps({
                    "test_count": len(test_results)
                }, ensure_ascii=True)
                yield f"TESTS_GENERATED:{test_json}\n"
            else:
                yield "WARNING:No tests were generated\n"
                
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            yield f"WARNING:Test generation failed: {str(e)}\n"
    
    # Evaluation
    if await http_request.is_disconnected():
        logger.info("Client disconnected before evaluation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    yield "THOTHLOG:Evaluating SQL candidates against test criteria...\n"
    
    evaluator = state.agents_and_tools.evaluator_agent if state.agents_and_tools else None
    
    if evaluator and state.generated_tests:
        try:
            evaluation_result = await evaluator.run(state)
            
            if evaluation_result:
                state.evaluation_results = evaluation_result
                state.evaluation_results_json = json.dumps(evaluation_result, ensure_ascii=False)
                
                yield f"THOTHLOG:Evaluation complete\n"
                
                # Send evaluation info to frontend
                eval_json = json.dumps({
                    "evaluated": True
                }, ensure_ascii=True)
                yield f"EVALUATION_COMPLETE:{eval_json}\n"
            else:
                yield "WARNING:Evaluation produced no results\n"
                
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            yield f"WARNING:Evaluation failed: {str(e)}\n"