# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Example usage of the unified error handling system.

This file demonstrates how to use the error handling system in different scenarios.
"""

from helpers.error_handling import ErrorHandler, safe_execute, safe_execute_async

# Example 1: Database connection error
def connect_to_database(config):
    """Example function that might fail during database connection."""
    if not config.get("host"):
        raise ValueError("Database host not configured")
    # Simulate connection logic
    return f"Connected to {config['host']}"

# Usage with error handling
def setup_database(config):
    """Setup database with proper error handling."""
    success, result = safe_execute(
        connect_to_database,
        config,
        error_handler=ErrorHandler.handle_database_error,
        error_message="Failed to connect to database"
    )
    
    if not success:
        # result is a ThothError object
        print(result.to_user_message())
        return None
    
    # result is the actual connection
    return result


# Example 2: AI Agent error handling
async def run_sql_agent(agent, prompt):
    """Example of handling AI agent errors."""
    try:
        result = await agent.run(prompt)
        return result
    except Exception as e:
        # Check if it's a ModelRetry (normal retry mechanism)
        is_retry = "ModelRetry" in str(type(e).__name__)
        
        error = ErrorHandler.handle_ai_agent_error(
            agent_name="SQL Generator",
            message="Failed to generate SQL",
            exception=e,
            is_retry=is_retry
        )
        
        # Handle based on severity
        if error.severity.value == "info":
            # It's just a retry, continue
            return None
        else:
            # Real error, propagate
            raise


# Example 3: Vector database error
def search_vector_db(query, vdb_manager):
    """Example of handling vector database errors."""
    try:
        results = vdb_manager.search(query)
        return results
    except Exception as e:
        error = ErrorHandler.handle_vector_db_error(
            message="Failed to search vector database",
            operation="similarity_search",
            exception=e,
            context={"query": query}
        )
        
        # Return empty results with error logged
        return []


# Example 4: User input validation
def validate_user_question(question):
    """Example of handling validation errors."""
    if not question or len(question.strip()) < 5:
        error = ErrorHandler.handle_user_input_error(
            message="Question is too short",
            input_value=question,
            suggestion="Please provide a more detailed question (at least 5 characters)"
        )
        return False, error
    
    if len(question) > 1000:
        error = ErrorHandler.handle_user_input_error(
            message="Question is too long",
            input_value=f"{question[:50]}...",
            suggestion="Please limit your question to 1000 characters"
        )
        return False, error
    
    return True, None


# Example 5: Configuration error
def load_workspace_config(workspace_id):
    """Example of handling configuration errors."""
    try:
        # Simulate loading configuration
        if workspace_id not in [1, 2, 3, 4]:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        return {"id": workspace_id, "name": f"Workspace {workspace_id}"}
    except Exception as e:
        error = ErrorHandler.handle_configuration_error(
            message=f"Failed to load workspace configuration",
            details=f"Workspace ID: {workspace_id}",
            exception=e,
            context={"workspace_id": workspace_id}
        )
        return None


# Example 6: Network error
async def fetch_from_api(url):
    """Example of handling network errors."""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        error = ErrorHandler.handle_network_error(
            message="Failed to fetch data from API",
            url=url,
            exception=e
        )
        return None