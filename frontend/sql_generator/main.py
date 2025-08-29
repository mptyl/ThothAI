# Copyright (c) 2025 Marco Pancotti
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
FastAPI Main Application for SQL Generator

This module provides the main FastAPI application for handling SQL generation requests.
It exposes a single API endpoint: generate_sql that receives question and workspace.
"""

import json
import logging
import os
import time
import sqlparse
import logfire

from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel, Field
from pydantic_ai.settings import ModelSettings
from datetime import datetime
from tzlocal import get_localzone

from agents.core.agent_manager import ThothAgentManager
from thoth_dbmanager import ThothDbFactory
from thoth_qdrant import VectorStoreFactory
from helpers.vectordb_config_utils import extract_vector_db_config_from_workspace, build_vector_db_params
from helpers.main_helpers.main_methods import  _initialize_vdbmanager, _initialize_dbmanager, _get_workspace_config, _get_workspace, initialize_database_plugins, _is_positive, build_not_ready_error_details 
from helpers.template_preparation import TemplateLoader
from model.system_state import SystemState
from model.sql_explanation import SqlExplanationRequest, SqlExplanationResponse
from services.paginated_query_service import PaginatedQueryService, PaginationRequest, PaginationResponse
from helpers.session_cache import ensure_cached_setup
from helpers.dual_logger import log_info, log_error, log_warning, log_debug
from helpers.db_info import get_db_schema
from helpers.main_helpers.main_request_initialization import _initialize_request_state
from helpers.main_helpers.main_preprocessing_phases import (
    _validate_question_phase,
    _extract_keywords_phase,
    _retrieve_context_phase
)
from helpers.main_helpers.main_generation_phases import (
    _generate_sql_candidates_phase,
    _evaluate_and_select_phase
)
from helpers.main_helpers.main_response_preparation import (
    _prepare_final_response_phase,
    WORKSPACE_STATES
)
from helpers.main_helpers.main_keyword_extraction import extract_keywords
from helpers.main_helpers.main_schema_extraction_from_vectordb import extract_schema_via_vector_db, format_schema_for_display
from helpers.main_helpers.main_generate_mschema import create_filtered_schema, to_mschema
from helpers.thoth_log_api import send_thoth_log
from helpers.main_helpers.main_methods import _setup_dbmanager_and_agents
from helpers.main_helpers.main_schema_link_strategy import decide_schema_link_strategy
from helpers.main_helpers.main_sql_generation import generate_sql_units



# Load environment variables FIRST, before any other imports
# Determine which .env file to use based on environment
is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
project_root = Path(__file__).parent.parent  # thoth_ui dir

if is_docker:
    # Docker environment - use .env.docker from project root
    env_path = project_root / '.env.docker'
else:
    # Local development - use .env.local from project root
    env_path = project_root / '.env.local'

if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"WARNING: No .env file found at {env_path}")

# Configure logfire and instrument PydanticAI at startup
logfire.configure(
    send_to_logfire="if-token-present",
    scrubbing=False,
)
# Instrument PydanticAI immediately after configuring logfire
# This ensures ALL PydanticAI agent activity is tracked from the beginning
logfire.instrument_pydantic_ai()

# Logfire configuration will be confirmed after logging is set up

# Configure logging using centralized configuration
from helpers.logging_config import configure_root_logger, get_logging_level

# Set up logging immediately after loading env vars
configure_root_logger()
log_level = get_logging_level()

# Create logger for this module
logger = logging.getLogger(__name__)

# Initialize database plugins
available_plugins = initialize_database_plugins()

# Log confirmation that logfire and PydanticAI are configured
if os.getenv('LOGFIRE_TOKEN'):
    log_debug("Logfire configured and PydanticAI instrumented successfully")
else:
    logger.info("Logfire token not found, telemetry will not be sent to logfire service")


# Global agent manager instance (legacy, not used directly anymore)
agent_manager: Optional[ThothAgentManager] = None

# Simple in-memory cache to reuse setup across calls in the same session/workspace
# Key strategy: prefer client-provided 'X-Session-Id' header, otherwise fall back to the workspace ID
# Value: dict with keys {"workspace_id", "setup_result"}
SESSION_CACHE: Dict[str, Dict[str, Any]] = {}

# Store the last SystemState for each workspace to support Like functionality
# Key: workspace_id, Value: SystemState
# WORKSPACE_STATES imported from main_response_preparation


class GenerateSQLRequest(BaseModel):
    """Request model for SQL generation."""
    question: str = Field(..., description="The user's question to convert to SQL")
    workspace_id: int = Field(..., description="The workspace ID to use for SQL generation")
    functionality_level: str = Field(..., description="Functionality level: Basic, Advanced, or Expert")
    flags: Dict[str, bool] = Field(..., description="Sidebar configuration flags")
    

class GenerateSQLResponse(BaseModel):
    """Response model for SQL generation."""
    message: str = Field(..., description="Response message")
    status: str = Field(..., description="Processing status")
    

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Status message")



@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: F811
    """Manage application lifespan events."""
    if log_level <= logging.INFO:
        logger.info("Starting SQL Generator service...")
    yield
    if log_level <= logging.INFO:
        logger.info("Shutting down SQL Generator service...")


# Create FastAPI application
app = FastAPI(
    title="ThothAI SQL Generator",
    description="AI-powered SQL generation service for natural language queries",
    version="0.1.0",
    lifespan=lifespan
)

# Global exception handler to avoid generic 500 with empty body
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    logger.exception("Unhandled exception")
    detail = (
        "ERROR: Unhandled server error while processing your request.\n"
        f"Path: {request.url.path}\n"
        f"Reason: {type(exc).__name__}: {str(exc)}\n"
        "Hints: Verify environment configuration (DJANGO_API_KEY, DB plugins, vector DB backends).\n"
    )
    return PlainTextResponse(detail, status_code=500)

# Add CORS middleware
# Configure CORS to support common localhost variants and any port
# Keeping allow_credentials=True, so we cannot use "*" for allow_origins.
# Use allow_origin_regex to match localhost and 127.0.0.1 on any port (http/https).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js frontend (dev)
        "http://localhost:3001",  # Next.js frontend (Docker)
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        message="SQL Generator service is running"
    )


@app.post("/generate-sql")
async def generate_sql(request: GenerateSQLRequest, http_request: Request):
    """
    Generate SQL from natural language question using workspace ID.
    
    This async generator:
    1. Validates and processes the natural language question
    2. Sets up dbmanager and agent pool based on workspace ID
    3. Returns streaming response with query results, hints, and agent config
    """
    # Initialize and validate request state
    state, error_response = await _initialize_request_state(request, http_request)
    if error_response:
        return error_response

    async def generate_response():
        """
        Main orchestration logic for SQL generation pipeline.
        Coordinates all phases of the SQL generation process.
        """
        # Initial log line for client as soon as stream starts
        yield f"THOTHLOG:Resources instantiated for workspace '{state.workspace_name}' - Validating question ...\n"       
        
        # Process each phase with simplified error handling
        phases = [
            ("Phase 1: Question Validation", _validate_question_phase(state, request, http_request)),
            ("Phase 2: Keyword Extraction", _extract_keywords_phase(state, request, http_request)),
            ("Phase 3: Context Retrieval", _retrieve_context_phase(state, request, http_request)),
            ("Phase 4: SQL Generation", _generate_sql_candidates_phase(state, request, http_request)),
        ]
        
        # Execute phases 1-4 with standard error handling
        for phase_name, phase_generator in phases:
            async for message in phase_generator:
                if message.startswith(("CANCELLED:", "CRITICAL_ERROR:", "ERROR:")):
                    yield message
                    return
                yield message
                if "CRITICAL_ERROR:" in message:
                    return
        
        # Phase 5: Evaluation and Selection (special handling for result tuple)
        success = False
        selected_sql = None
        async for message in _evaluate_and_select_phase(state, request, http_request):
            if isinstance(message, tuple) and len(message) == 3 and message[0] == "RESULT":
                # This is the result tuple (success, selected_sql)
                _, success, selected_sql = message
                break
            if message.startswith(("CANCELLED:", "CRITICAL_ERROR:", "ERROR:", "SQL_GENERATION_FAILED:")):
                yield message
                # Don't return for SQL_GENERATION_FAILED - we need to log it
                if message.startswith(("CANCELLED:", "CRITICAL_ERROR:", "ERROR:")):
                    return
            else:
                yield message
        
        # Phase 6: Final Response Preparation
        async for message in _prepare_final_response_phase(state, request, http_request, success, selected_sql):
            yield message

    return StreamingResponse(generate_response(), media_type="text/plain")


@app.post("/explain-sql", response_model=SqlExplanationResponse)
async def explain_sql(request: SqlExplanationRequest):
    """
    Generate an explanation for a SQL query that was already generated.
    
    This endpoint:
    1. Receives the generated SQL and all context used
    2. Uses the SQL explainer agent to generate a human-readable explanation
    3. Returns the explanation in the requested language (Italian/English)
    """
    start_time = time.time()
    
    try:
        # Get workspace configuration
        workspace_result = await _get_workspace(request.workspace_id)
        if not workspace_result['success']:
            return SqlExplanationResponse(
                explanation="",
                execution_time=time.time() - start_time,
                success=False,
                error=f"Failed to get workspace: {workspace_result.get('error', 'Unknown error')}"
            )
        
        workspace = workspace_result.get('workspace')
        if not workspace:
            return SqlExplanationResponse(
                explanation="",
                execution_time=time.time() - start_time,
                success=False,
                error="Workspace not found"
            )
        
        # Initialize agent manager if not cached
        setup_result = await ensure_cached_setup(
            request.workspace_id,
            workspace,
            request.username
        )
        
        if not setup_result.get("success"):
            return SqlExplanationResponse(
                explanation="",
                execution_time=time.time() - start_time,
                success=False,
                error=f"Failed to initialize agents: {setup_result.get('error', 'Unknown error')}"
            )
        
        agent_manager = setup_result.get("agent_manager")
        if not agent_manager:
            return SqlExplanationResponse(
                explanation="",
                execution_time=time.time() - start_time,
                success=False,
                error="Agent manager not initialized"
            )
        
        # Generate the explanation
        explanation = await agent_manager.explain_generated_sql(
            question=request.question,
            generated_sql=request.generated_sql,
            database_schema=request.database_schema,
            hints=request.evidence,
            chain_of_thought=request.chain_of_thought,
            language=request.language
        )
        
        if explanation:
            return SqlExplanationResponse(
                explanation=explanation,
                execution_time=time.time() - start_time,
                success=True,
                agent_used="sql_explainer_agent"
            )
        else:
            return SqlExplanationResponse(
                explanation="",
                execution_time=time.time() - start_time,
                success=False,
                error="Failed to generate explanation"
            )
            
    except Exception as e:
        log_error(f"Error in explain_sql endpoint: {e}")
        return SqlExplanationResponse(
            explanation="",
            execution_time=time.time() - start_time,
            success=False,
            error=str(e)
        )



@app.post("/execute-query", response_model=PaginationResponse)
async def execute_query(request: PaginationRequest):
    """
    Execute a SQL query with pagination support.
    
    This endpoint:
    1. Receives SQL and workspace ID
    2. Sets up dbmanager based on workspace ID
    3. Executes query with pagination
    4. Returns paginated results for AGGrid
    """
    try:
        # Setup dbmanager and agents for the workspace
        setup_result = await _setup_dbmanager_and_agents(request.workspace_id, GenerateSQLRequest(
            question="",  # Not needed for query execution
            workspace_id=request.workspace_id,
            functionality_level="Basic",  # Not needed for query execution
            flags={}  # Not needed for query execution
        ))
        
        # Get dbmanager from setup
        dbmanager = setup_result.get("dbmanager")
        if not dbmanager:
            return PaginationResponse(
                data=[],
                total_rows=0,
                page=request.page,
                page_size=request.page_size,
                has_next=False,
                has_previous=False,
                columns=[],
                error="Database manager not initialized"
            )
        
        # Create paginated query service
        paginated_service = PaginatedQueryService(dbmanager)
        
        # Execute paginated query
        response = paginated_service.execute_paginated_query(request)
        
        # Log the query execution (only if log level allows)
        if log_level <= logging.INFO:
            logger.debug(f"Executed paginated query for workspace {request.workspace_id}, page {request.page}")
        
        return response
        
    except Exception as e:
        log_error(f"Error executing paginated query: {e}")
        return PaginationResponse(
            data=[],
            total_rows=0,
            page=request.page,
            page_size=request.page_size,
            has_next=False,
            has_previous=False,
            columns=[],
            error=str(e)
        )


@app.post("/save-sql-feedback")
async def save_sql_feedback(request: Dict[str, Any]):
    """
    Save user feedback (Like) for the last successfully generated SQL query.
    Simply retrieves the last state and saves it to the vector database.
    """
    # Get the last state - we only keep one in memory
    workspace_id = request.get("workspace_id")
    
    if not workspace_id:
        log_error("No workspace_id provided in save-sql-feedback request")
        return {"success": False, "error": "workspace_id is required"}
    
    from helpers.main_helpers.main_response_preparation import WORKSPACE_STATES
    state = WORKSPACE_STATES.get(workspace_id)
    
    if not state:
        log_error(f"No state found for workspace_id {workspace_id}")
        return {"success": False, "error": "No SQL generation state found for this workspace"}
    
    if not state.last_SQL:
        log_error(f"No SQL found in state for workspace_id {workspace_id}")
        return {"success": False, "error": "No SQL query available to save"}
    
    # Import and create the SQL document
    from thoth_qdrant import SqlDocument
    
    # Use original_question if available (from translation), otherwise use question
    question_to_save = state.original_question if state.original_question else state.question
    
    if not question_to_save:
        log_error(f"No question found in state for workspace_id {workspace_id}")
        return {"success": False, "error": "No question available to save"}
    
    sql_doc = SqlDocument(
        question=question_to_save,
        sql=state.last_SQL,
        evidence=state.evidence[0] if state.evidence else ""  # Changed from 'hint' to 'evidence'
    )
    
    # Check if vdbmanager is available
    if not state.vdbmanager:
        log_error(f"Vector DB manager not available for workspace {workspace_id} - cannot save feedback")
        error_details = {
            "success": False, 
            "error": "Cannot save feedback - Vector database unavailable",
            "details": (
                "The vector database service is not accessible.\n\n"
                "Why this matters:\n"
                "• Your feedback helps improve future SQL generation\n"
                "• Saved SQL examples are used as references for similar queries\n\n"
                "To resolve:\n"
                "1. Ensure Qdrant service is running on the configured port\n"
                "2. Check vector database configuration in workspace settings\n"
                "3. Try saving your feedback again after resolving the connection issue"
            )
        }
        return error_details
    
    # Save to vector database
    try:
        # Use the correct method for adding SQL documents
        state.vdbmanager.add_sql(sql_doc)
        logger.info(f"SQL feedback saved for workspace {workspace_id}")
        logger.info(f"Saved - Question: '{question_to_save[:50]}...', SQL: '{state.last_SQL[:50]}...', Evidence: '{sql_doc.evidence[:50] if sql_doc.evidence else 'None'}...'")
        return {"success": True}
    except Exception as e:
        log_error(f"Error saving SQL feedback for workspace {workspace_id}: {str(e)}")
        return {"success": False, "error": f"Failed to save to vector database: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    # Priority: command line arg > PORT env > default 8180
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv('PORT', '8180'))
    uvicorn.run(app, host="0.0.0.0", port=port)
    