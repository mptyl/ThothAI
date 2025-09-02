# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
Test Error Injector for SQL Generator
Temporary module for testing error messages - to be removed after tuning
"""

import json
from typing import Optional
from fastapi.responses import StreamingResponse, PlainTextResponse


async def inject_test_error(question: str, workspace_id: int):
    """
    Check if question contains TEST pattern and return corresponding error.
    
    Args:
        question: The user's question
        workspace_id: The workspace ID
        
    Returns:
        Response object if TEST pattern found, None otherwise
    """
    
    # Check for TEST patterns
    if "TEST01" in question:
        # Validation failed error
        async def generate():
            error_msg = {
                "type": "validation_failed",
                "component": "question_validator",
                "message": "TEST01: Your question is not suitable for SQL generation",
                "impact": "Cannot proceed with SQL generation",
                "action": "Please rephrase your question or check the requirements"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield "TEST01: Question validation failed - question is not SQL-related\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST02" in question:
        # Keyword extraction agent not available
        async def generate():
            error_msg = {
                "type": "critical_error",
                "component": "keyword_extraction",
                "message": "TEST02: Keyword extraction agent is not configured",
                "details": "The keyword extraction agent is required but not available in this workspace",
                "impact": "Cannot proceed without keyword extraction - it's essential for context retrieval",
                "action": "Please check workspace agent configuration and ensure keyword_extraction_agent is configured"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield "ERROR: Keyword extraction agent not available - cannot proceed with SQL generation\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST03" in question:
        # Vector database not available
        async def generate():
            error_msg = {
                "type": "critical_error",
                "component": "vector_database",
                "message": "TEST03: Vector database is not available",
                "details": "Failed to connect to vector database service",
                "impact": "Cannot retrieve context without vector database",
                "action": "Please check vector database configuration and connectivity"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield "ERROR: Vector database not available - terminating SQL generation\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST04" in question:
        # SQL generation failed
        async def generate():
            error_msg = {
                "type": "critical_error",
                "component": "sql_generation",
                "message": "TEST04: Failed to generate SQL statements",
                "details": "ModelRetry: Max retries exceeded",
                "impact": "Cannot proceed without SQL generation",
                "action": "Please check agent configuration and model availability"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield f"ERROR: SQL generation failed - ModelRetry: Max retries exceeded\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST05" in question:
        # No SQL statements generated
        async def generate():
            error_msg = {
                "type": "critical_error",
                "component": "sql_generation",
                "message": "TEST05: No valid SQL statements were generated",
                "details": "All SQL generation attempts failed or produced invalid results",
                "impact": "Cannot proceed without at least one valid SQL statement",
                "action": "Please check: 1) Question clarity, 2) Database schema availability, 3) Agent configuration"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield "ERROR: No SQL statements could be generated for your question\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST06" in question:
        # Test generation failed
        async def generate():
            error_msg = {
                "type": "critical_error",
                "component": "test_generation",
                "message": "TEST06: Failed to generate validation tests",
                "details": "Test generation agent encountered an error",
                "impact": "Cannot validate SQL statements without tests",
                "action": "Please check test agent configuration and model availability"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield f"ERROR: Test generation failed - Test agent error\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST07" in question:
        # No validation tests generated
        async def generate():
            error_msg = {
                "type": "critical_error",
                "component": "test_generation",
                "message": "TEST07: No validation tests were generated",
                "details": "All test generation attempts failed",
                "impact": "Cannot validate SQL statements without tests",
                "action": "Please check test agent configuration in workspace settings"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield "ERROR: No validation tests could be generated\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST08" in question:
        # Setup failed (PlainTextResponse)
        detail = (
            "ERROR: Setup failed while preparing resources for SQL generation.\n"
            f"Reason: ConnectionError: Cannot connect to Django API\n"
            "Hints: Check DJANGO_API_KEY, database plugins, and vector DB backends configuration.\n"
        )
        return PlainTextResponse(detail, status_code=500)
    
    elif "TEST09" in question:
        # Database schema retrieval failed (PlainTextResponse)
        error_msg = (
            "ERROR: Failed to retrieve database schema.\n"
            f"Database: test_database\n"
            f"Reason: Database schema is empty - no tables found\n"
            "\nThis is a critical error - cannot proceed without database schema.\n"
            "Please verify:\n"
            "1. Database connection is active\n"
            "2. Database contains tables\n"
            "3. User has permission to read schema\n"
        )
        return PlainTextResponse(error_msg, status_code=500)
    
    elif "TEST10" in question:
        # Manager validation failed (PlainTextResponse)
        details = (
            "ERROR: DB Manager is not ready.\n"
            "\n"
            "Workspace: Test Workspace\n"
            "Configuration Status:\n"
            "- DB Manager: Failed - Connection refused\n"
            "- Vector DB Manager: Active\n"
            "\n"
            "Requirements:\n"
            "1. Valid database connection string\n"
            "2. Database driver installed\n"
            "3. Network connectivity to database\n"
            "\n"
            "Current Configuration:\n"
            "- Database Type: postgresql\n"
            "- Host: localhost\n"
            "- Port: 5432\n"
            "- Database: test_db\n"
            "\n"
            "Please check your database configuration and ensure the database is running.\n"
        )
        return PlainTextResponse(details, status_code=400)
    
    elif "TEST11" in question:
        # SQL_GENERATION_FAILED format
        async def generate():
            failure_data = json.dumps({
                "status": "failure",
                "workspace_id": workspace_id,
                "question": question,
                "error": "No SQL candidates passed evaluation",
                "details": {
                    "total_sqls": 12,
                    "passed_threshold": 0,
                    "evaluation_threshold": 90,
                    "best_score": 45
                }
            }, ensure_ascii=True)
            yield f"SQL_GENERATION_FAILED:{failure_data}\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST12" in question:
        # LSH schema extraction failed
        async def generate():
            error_msg = {
                "type": "critical_error",
                "component": "lsh_extraction",
                "message": "TEST12: LSH schema extraction failed",
                "details": "Failed to extract relevant schema using LSH",
                "impact": "Cannot proceed without schema information",
                "action": "Please check LSH configuration and database connectivity"
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield f"ERROR: LSH schema extraction failed - Connection timeout\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    elif "TEST13" in question:
        # Internal error state inconsistency
        async def generate():
            error_msg = {
                "type": "internal_error",
                "component": "state_management",
                "message": "TEST13: SQL generation state inconsistency detected",
                "details": "SystemState has no generated_sqls attribute after SQL generation phase",
                "impact": "Cannot proceed - internal state corruption",
                "action": "This is an internal error. Please try again or contact support."
            }
            yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
            yield "ERROR: Internal error - SQL generation state inconsistency\n"
        return StreamingResponse(generate(), media_type="text/plain")
    
    # No TEST pattern found
    return None