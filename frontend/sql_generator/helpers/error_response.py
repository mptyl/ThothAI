# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Standardized Error Response Module for SQL Generator Service

Provides consistent error formatting across all API endpoints.
"""

import os
import traceback
from typing import Optional, Dict, Any
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Standard error detail model."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    trace: Optional[str] = None


class StandardErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: ErrorDetail
    environment: Optional[str] = None
    request_id: Optional[str] = None


def get_environment_info() -> str:
    """Get current environment (local/docker/production)."""
    if os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true':
        return "docker"
    elif os.getenv('ENVIRONMENT') == 'production':
        return "production"
    else:
        return "local"


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    exception: Optional[Exception] = None,
    include_trace: bool = False,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_code: Application-specific error code (e.g., "AUTH_FAILED", "DB_ERROR")
        message: Human-readable error message
        details: Additional error details
        exception: Original exception if available
        include_trace: Whether to include stack trace (only in dev)
        request_id: Request ID for tracking
        
    Returns:
        JSONResponse with standardized error format
    """
    environment = get_environment_info()
    
    # Only include trace in development environments
    trace = None
    if include_trace and environment in ['local', 'docker'] and exception:
        trace = traceback.format_exc()
    
    # Log the error
    if exception:
        logger.error(f"Error {error_code}: {message}", exc_info=exception)
    else:
        logger.error(f"Error {error_code}: {message}")
    
    error_detail = ErrorDetail(
        code=error_code,
        message=message,
        details=details,
        trace=trace
    )
    
    response = StandardErrorResponse(
        success=False,
        error=error_detail,
        environment=environment if environment != 'production' else None,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response.dict(exclude_none=True)
    )


# Common error codes
class ErrorCodes:
    """Standard error codes for the application."""
    
    # Authentication & Authorization
    AUTH_MISSING = "AUTH_MISSING"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    
    # Validation
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_REQUEST = "INVALID_REQUEST"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    
    # Database
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    DB_TIMEOUT = "DB_TIMEOUT"
    
    # Vector Database
    VECTOR_DB_ERROR = "VECTOR_DB_ERROR"
    VECTOR_DB_UNAVAILABLE = "VECTOR_DB_UNAVAILABLE"
    
    # Agent Execution
    AGENT_INIT_FAILED = "AGENT_INIT_FAILED"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    
    # SQL Generation
    SQL_GENERATION_FAILED = "SQL_GENERATION_FAILED"
    SQL_VALIDATION_FAILED = "SQL_VALIDATION_FAILED"
    SQL_EXECUTION_FAILED = "SQL_EXECUTION_FAILED"
    
    # Workspace
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    WORKSPACE_CONFIG_ERROR = "WORKSPACE_CONFIG_ERROR"
    
    # System
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


def handle_exception(
    exception: Exception,
    default_message: str = "An unexpected error occurred",
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Handle an exception and return appropriate error response.
    
    Args:
        exception: The exception to handle
        default_message: Default message if exception message is not suitable
        request_id: Request ID for tracking
        
    Returns:
        JSONResponse with error details
    """
    # Map specific exceptions to error codes and status codes
    if isinstance(exception, ValueError):
        return create_error_response(
            status_code=400,
            error_code=ErrorCodes.VALIDATION_FAILED,
            message=str(exception) or default_message,
            exception=exception,
            include_trace=True,
            request_id=request_id
        )
    elif isinstance(exception, KeyError):
        return create_error_response(
            status_code=400,
            error_code=ErrorCodes.MISSING_PARAMETER,
            message=f"Missing required parameter: {str(exception)}",
            exception=exception,
            include_trace=True,
            request_id=request_id
        )
    elif "database" in str(exception).lower() or "connection" in str(exception).lower():
        return create_error_response(
            status_code=503,
            error_code=ErrorCodes.DB_CONNECTION_FAILED,
            message="Database connection error",
            details={"original_error": str(exception)},
            exception=exception,
            include_trace=True,
            request_id=request_id
        )
    elif "agent" in str(exception).lower():
        return create_error_response(
            status_code=500,
            error_code=ErrorCodes.AGENT_EXECUTION_FAILED,
            message="Agent execution failed",
            details={"original_error": str(exception)},
            exception=exception,
            include_trace=True,
            request_id=request_id
        )
    else:
        # Generic internal error
        return create_error_response(
            status_code=500,
            error_code=ErrorCodes.INTERNAL_ERROR,
            message=default_message,
            details={"error_type": type(exception).__name__},
            exception=exception,
            include_trace=True,
            request_id=request_id
        )