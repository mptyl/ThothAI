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
Unified Error Handling System for ThothAI SQL Generator

This module provides a centralized error handling system with:
- Standard error types and classifications
- Consistent error message formatting
- Automatic logging integration
- User-friendly error messages
"""

import logging
import traceback
from typing import Optional, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass
from helpers.logging_config import log_error, log_warning, log_info

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for prioritization and handling."""
    CRITICAL = "critical"  # System failure, cannot continue
    ERROR = "error"        # Operation failed, but system stable
    WARNING = "warning"    # Issue detected, but operation continues
    INFO = "info"          # Informational, not an error


class ErrorCategory(Enum):
    """Categories of errors for better organization and handling."""
    CONFIGURATION = "configuration"
    DATABASE = "database"
    VECTOR_DB = "vector_db"
    AI_AGENT = "ai_agent"
    VALIDATION = "validation"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RESOURCE = "resource"
    USER_INPUT = "user_input"
    INTERNAL = "internal"


@dataclass
class ThothError:
    """
    Standardized error representation for the ThothAI system.
    
    Attributes:
        category: The category of the error
        severity: The severity level
        message: User-friendly error message
        details: Technical details for debugging
        error_code: Optional error code for reference
        context: Additional context information
        original_exception: The original exception if any
    """
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    error_code: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    original_exception: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "error_code": self.error_code,
            "context": self.context
        }
    
    def to_user_message(self) -> str:
        """Generate a user-friendly error message."""
        if self.severity == ErrorSeverity.WARNING:
            return f"Warning: {self.message}"
        elif self.severity == ErrorSeverity.CRITICAL:
            return f"Critical Error: {self.message}"
        elif self.severity == ErrorSeverity.ERROR:
            return f"Error: {self.message}"
        else:
            return f"{self.message}"
    
    def to_log_message(self) -> str:
        """Generate a detailed log message."""
        parts = [
            f"[{self.category.value.upper()}]",
            f"[{self.severity.value.upper()}]",
            self.message
        ]
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.error_code:
            parts.append(f"Code: {self.error_code}")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " | ".join(parts)


class ErrorHandler:
    """
    Centralized error handler for the ThothAI system.
    
    Provides methods for handling different types of errors consistently.
    """
    
    @staticmethod
    def handle_configuration_error(
        message: str,
        details: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ) -> ThothError:
        """Handle configuration-related errors."""
        error = ThothError(
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.ERROR,
            message=message,
            details=details or (str(exception) if exception else None),
            error_code="CONFIG_ERROR",
            context=context,
            original_exception=exception
        )
        log_error(error.to_log_message())
        if exception:
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return error
    
    @staticmethod
    def handle_database_error(
        message: str,
        operation: Optional[str] = None,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThothError:
        """Handle database-related errors."""
        details = f"Operation: {operation}" if operation else None
        if exception:
            details = f"{details}. Error: {str(exception)}" if details else str(exception)
        
        error = ThothError(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.ERROR,
            message=message,
            details=details,
            error_code="DB_ERROR",
            context=context,
            original_exception=exception
        )
        log_error(error.to_log_message())
        return error
    
    @staticmethod
    def handle_vector_db_error(
        message: str,
        operation: Optional[str] = None,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThothError:
        """Handle vector database-related errors."""
        details = f"Vector DB operation: {operation}" if operation else None
        if exception:
            details = f"{details}. Error: {str(exception)}" if details else str(exception)
        
        error = ThothError(
            category=ErrorCategory.VECTOR_DB,
            severity=ErrorSeverity.ERROR,
            message=message,
            details=details,
            error_code="VECTOR_DB_ERROR",
            context=context,
            original_exception=exception
        )
        log_error(error.to_log_message())
        return error
    
    @staticmethod
    def handle_ai_agent_error(
        agent_name: str,
        message: str,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        is_retry: bool = False
    ) -> ThothError:
        """Handle AI agent-related errors."""
        # ModelRetry is not an error, it's a normal retry mechanism
        if is_retry or (exception and "ModelRetry" in str(type(exception).__name__)):
            error = ThothError(
                category=ErrorCategory.AI_AGENT,
                severity=ErrorSeverity.INFO,
                message=f"Agent {agent_name}: {message}",
                details=str(exception) if exception else None,
                error_code="AGENT_RETRY",
                context=context,
                original_exception=exception
            )
            log_info(error.to_log_message())
        else:
            error = ThothError(
                category=ErrorCategory.AI_AGENT,
                severity=ErrorSeverity.ERROR,
                message=f"Agent {agent_name} failed: {message}",
                details=str(exception) if exception else None,
                error_code="AGENT_ERROR",
                context=context,
                original_exception=exception
            )
            log_error(error.to_log_message())
        return error
    
    @staticmethod
    def handle_validation_error(
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThothError:
        """Handle validation errors."""
        details = None
        if field:
            details = f"Field: {field}"
            if value is not None:
                details += f", Value: {value}"
        
        error = ThothError(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            message=message,
            details=details,
            error_code="VALIDATION_ERROR",
            context=context
        )
        log_warning(error.to_log_message())
        return error
    
    @staticmethod
    def handle_user_input_error(
        message: str,
        input_value: Optional[str] = None,
        suggestion: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThothError:
        """Handle user input errors."""
        details = None
        if input_value:
            details = f"Input: {input_value}"
        if suggestion:
            details = f"{details}. Suggestion: {suggestion}" if details else f"Suggestion: {suggestion}"
        
        error = ThothError(
            category=ErrorCategory.USER_INPUT,
            severity=ErrorSeverity.WARNING,
            message=message,
            details=details,
            error_code="USER_INPUT_ERROR",
            context=context
        )
        log_warning(error.to_log_message())
        return error
    
    @staticmethod
    def handle_resource_error(
        message: str,
        resource_type: Optional[str] = None,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThothError:
        """Handle resource-related errors (memory, disk, etc.)."""
        details = f"Resource: {resource_type}" if resource_type else None
        if exception:
            details = f"{details}. Error: {str(exception)}" if details else str(exception)
        
        error = ThothError(
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.CRITICAL,
            message=message,
            details=details,
            error_code="RESOURCE_ERROR",
            context=context,
            original_exception=exception
        )
        log_error(error.to_log_message())
        return error
    
    @staticmethod
    def handle_network_error(
        message: str,
        url: Optional[str] = None,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThothError:
        """Handle network-related errors."""
        details = f"URL: {url}" if url else None
        if exception:
            details = f"{details}. Error: {str(exception)}" if details else str(exception)
        
        error = ThothError(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.ERROR,
            message=message,
            details=details,
            error_code="NETWORK_ERROR",
            context=context,
            original_exception=exception
        )
        log_error(error.to_log_message())
        return error
    
    @staticmethod
    def handle_internal_error(
        message: str,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ThothError:
        """Handle internal/unexpected errors."""
        error = ThothError(
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.CRITICAL,
            message=message,
            details=str(exception) if exception else None,
            error_code="INTERNAL_ERROR",
            context=context,
            original_exception=exception
        )
        log_error(error.to_log_message())
        if exception:
            logger.error(f"Internal error traceback: {traceback.format_exc()}")
        return error


# Convenience functions for common error scenarios
def safe_execute(func, *args, error_handler=None, error_message="Operation failed", **kwargs):
    """
    Safely execute a function with automatic error handling.
    
    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        error_handler: Optional custom error handler
        error_message: Default error message if execution fails
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        Tuple of (success, result_or_error)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        if error_handler:
            error = error_handler(error_message, exception=e)
        else:
            error = ErrorHandler.handle_internal_error(error_message, exception=e)
        return False, error


async def safe_execute_async(func, *args, error_handler=None, error_message="Operation failed", **kwargs):
    """
    Safely execute an async function with automatic error handling.
    
    Args:
        func: Async function to execute
        *args: Arguments to pass to the function
        error_handler: Optional custom error handler
        error_message: Default error message if execution fails
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        Tuple of (success, result_or_error)
    """
    try:
        result = await func(*args, **kwargs)
        return True, result
    except Exception as e:
        if error_handler:
            error = error_handler(error_message, exception=e)
        else:
            error = ErrorHandler.handle_internal_error(error_message, exception=e)
        return False, error