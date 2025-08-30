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
State factory for creating SystemState instances with proper context initialization.

This factory provides methods to create SystemState instances from various sources
and to create specialized dependency objects for different agents.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from tzlocal import get_localzone
from pydantic import BaseModel

from .system_state import SystemState
from .contexts import (
    RequestContext,
    DatabaseContext,
    SemanticContext,
    SchemaDerivations,
    GenerationResults,
    ExecutionState,
    ExternalServices
)

# Import existing dependency types
from .sql_generation_deps import SqlGenerationDeps
from .evaluator_deps import EvaluatorDeps
from .agent_dependencies import (
    KeywordExtractionDeps,
    ValidationDeps,
    TestGenerationDeps,
    TranslationDeps,
    SqlExplanationDeps,
    AskHumanDeps
)
from .exceptions import StateFactoryError, AgentExecutionError


class StateFactory:
    """
    Factory for creating SystemState instances and agent dependencies.
    
    This factory encapsulates the logic for creating properly initialized
    SystemState instances from different sources (requests, workspace data, etc.)
    and for extracting specialized dependency objects for different agents.
    """
    
    @staticmethod
    def create_from_request(
        question: str,
        username: str,
        workspace_id: int,
        workspace_name: str,
        functionality_level: str,
        workspace_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SystemState:
        """
        Create a SystemState from a user request.
        
        Args:
            question: The user's natural language question
            username: Username making the request  
            workspace_id: ID of the workspace
            workspace_name: Name of the workspace
            functionality_level: SQL generator complexity level
            workspace_data: Complete workspace configuration data
            **kwargs: Additional parameters for context initialization
            
        Returns:
            SystemState: Fully initialized SystemState instance
        """
        
        # Extract workspace-specific configuration
        workspace_dict = workspace_data or {}
        sql_db_data = workspace_dict.get("sql_db", {}) if workspace_dict else {}
        
        # Create request context
        request_context = RequestContext(
            question=question,
            username=username,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            functionality_level=functionality_level,
            language=sql_db_data.get("language", "English"),
            scope=sql_db_data.get("scope", ""),
            started_at=kwargs.get("started_at", datetime.now(get_localzone()))
        )
        
        # Create database context
        database_context = DatabaseContext(
            full_schema=kwargs.get("full_schema", {}),
            directives=sql_db_data.get("directives", "Use only existing field names and table names"),
            db_type=kwargs.get("db_type", "postgresql"),
            treat_empty_result_as_error=kwargs.get("treat_empty_result_as_error", True),
            dbmanager=kwargs.get("dbmanager")
        )
        
        # Create external services context
        services_context = ExternalServices(
            vdbmanager=kwargs.get("vdbmanager"),
            agents_and_tools=kwargs.get("agents_and_tools"),
            sql_db_config=kwargs.get("sql_db_config"),
            number_of_tests_to_generate=kwargs.get("number_of_tests_to_generate", 5),
            number_of_sql_to_generate=kwargs.get("number_of_sql_to_generate", 10),
            workspace=workspace_dict
        )
        
        # Create SystemState with contexts
        return SystemState(
            request=request_context,
            database=database_context,
            semantic=SemanticContext(),  # Empty initially
            schemas=SchemaDerivations(),  # Empty initially
            generation=GenerationResults(),  # Empty initially
            execution=ExecutionState(),  # Empty initially
            services=services_context
        )
    
    @staticmethod
    def create_minimal(
        question: str,
        username: str = "test_user",
        workspace_id: int = 1,
        workspace_name: str = "Test Workspace",
        functionality_level: str = "BASIC"
    ) -> SystemState:
        """
        Create a minimal SystemState for testing purposes.
        
        Args:
            question: The user's question
            username: Username (default: test_user)
            workspace_id: Workspace ID (default: 1)
            workspace_name: Workspace name (default: Test Workspace)
            functionality_level: Functionality level (default: BASIC)
            
        Returns:
            SystemState: Minimal SystemState instance
        """
        # Create minimal workspace data with default scope
        workspace_data = {
            "sql_db": {
                "language": "English",
                "scope": "Test database for minimal SystemState"
            }
        }
        
        return StateFactory.create_from_request(
            question=question,
            username=username,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            functionality_level=functionality_level,
            workspace_data=workspace_data
        )
    
    @staticmethod
    def create_agent_deps(state: SystemState, agent_type: str) -> BaseModel:
        """
        Create specialized dependency objects for different agent types.
        
        Args:
            state: The SystemState to extract dependencies from
            agent_type: Type of agent needing dependencies
            
        Returns:
            BaseModel: Specialized dependency object for the agent
            
        Raises:
            ValueError: If agent_type is not supported
        """
        
        if agent_type == "sql_generation":
            return SqlGenerationDeps(
                db_type=state.database.db_type,
                db_schema_str=state.schemas.used_mschema or state.schemas.reduced_mschema,
                treat_empty_result_as_error=state.database.treat_empty_result_as_error,
                last_SQL=state.execution.last_SQL,
                last_execution_error=state.execution.last_execution_error,
                last_generation_success=state.execution.last_generation_success
            )
            
        elif agent_type == "evaluator":
            return EvaluatorDeps()  # Empty as evaluator uses template data only
            
        elif agent_type == "keyword_extraction":
            return KeywordExtractionDeps(
                question=state.question,
                scope=state.request.scope,
                language=state.request.language
            )
            
        elif agent_type == "question_validation":
            return ValidationDeps(
                question=state.question,
                scope=state.request.scope,
                language=state.request.language,
                workspace=state.services.workspace
            )
            
        elif agent_type == "test_generation":
            return TestGenerationDeps(
                question=state.question,
                schema_info=state.schemas.used_mschema or state.schemas.reduced_mschema,
                evidence=list(state.semantic.evidence),
                sql_examples=list(state.semantic.sql_shots),
                number_of_tests_to_generate=state.services.number_of_tests_to_generate
            )
            
        elif agent_type == "question_translation":
            return TranslationDeps(
                question=state.question,
                target_language=state.request.language,
                scope=state.request.scope
            )
            
        elif agent_type == "sql_explanation":
            return SqlExplanationDeps(
                generated_sql=state.generation.generated_sql or "",
                question=state.question,
                schema_info=state.schemas.used_mschema or state.schemas.reduced_mschema,
                language=state.request.language
            )
            
        elif agent_type == "ask_human":
            return AskHumanDeps(
                question=state.question,
                context="SQL Generation Context",
                issue_description="Need human assistance for complex query"
            )
            
        else:
            raise AgentExecutionError(f"Unsupported agent type: {agent_type}", agent_type=agent_type)
    
    @staticmethod
    def get_context_summary(state: SystemState) -> str:
        """
        Get a comprehensive summary of all contexts in the SystemState.
        
        Args:
            state: The SystemState to summarize
            
        Returns:
            str: Human-readable summary of all contexts
        """
        summaries = []
        
        # Request context
        summaries.append(f"Request: {state.question[:50] if state.question else state.original_question[:50]}... ({state.request.functionality_level})")
        
        # Database context  
        summaries.append(state.database.get_schema_summary())
        
        # Semantic context
        summaries.append(state.semantic.get_semantic_summary())
        
        # Schema derivations
        summaries.append(state.schemas.get_schema_derivations_summary())
        
        # Generation results
        summaries.append(state.generation.get_generation_summary())
        
        # Execution state
        summaries.append(state.execution.get_execution_summary())
        
        # External services
        summaries.append(state.services.get_services_summary())
        
        return " | ".join(summaries)