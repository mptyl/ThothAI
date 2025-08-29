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
Refactored SystemState using contextual decomposition.

This module contains the new SystemState architecture that breaks down
the monolithic state into focused context classes, improving maintainability,
testing, and reducing coupling between components.
"""

import re
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple, TypedDict, Union, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext
from thoth_qdrant import ThothType
from helpers.dual_logger import log_info, log_error

# Import new context classes
from .contexts import (
    RequestContext,
    DatabaseContext,
    SemanticContext,
    SchemaDerivations,
    GenerationResults,
    ExecutionState,
    ExternalServices
)

from .types import TableInfo  # Centralized type definition
from .exceptions import (
    SchemaProcessingError, 
    VectorDatabaseError, 
    DatabaseConnectionError,
    ValidationError,
    AgentExecutionError
)
from .schema_processor import SchemaProcessor



#from agents.tools.schema_selector.select_columns import SelectColumnsTool


class SystemState(BaseModel):
    """
    Refactored SystemState using contextual decomposition.
    
    This class now serves as a coordinator that contains specialized context objects,
    each responsible for a specific aspect of the SQL generation workflow.
    This improves maintainability, reduces coupling, and makes testing easier.
    
    Context Objects:
    - request: Immutable data from user request
    - database: Database schema and configuration  
    - semantic: Keywords, evidence, and SQL examples
    - schemas: Processed and filtered schema variants
    - generation: SQL generation and test results
    - execution: Runtime state and error tracking
    - services: External services and managers
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Context objects - the new architecture
    request: RequestContext = Field(..., description="Immutable request data and user context")
    database: DatabaseContext = Field(..., description="Database schema and configuration context")
    semantic: SemanticContext = Field(default_factory=SemanticContext, description="Semantic analysis results context")
    schemas: SchemaDerivations = Field(default_factory=SchemaDerivations, description="Processed schema variants context")
    generation: GenerationResults = Field(default_factory=GenerationResults, description="Generation results context")
    execution: ExecutionState = Field(default_factory=ExecutionState, description="Runtime execution state context")
    services: ExternalServices = Field(default_factory=ExternalServices, description="External services context")
    
    # Schema processor for complex schema operations
    schema_processor: SchemaProcessor = Field(default_factory=SchemaProcessor, description="Schema processing operations handler", exclude=True)
    
    # Translation and processing fields
    original_question: str = Field(default="", description="Copy of the original question from request")
    translated_question: Optional[str] = Field(default=None, description="Translated question if translation occurred")
    submitted_question: str = Field(default="", description="The question to be processed (original or translated)")

    
    # ============================================================================
    # PROPERTY BRIDGES TO CONTEXT OBJECTS
    # 
    # These properties provide convenient access to data stored in context objects.
    # They maintain the original SystemState interface while delegating to
    # the appropriate specialized context objects.
    # ============================================================================
    
    # Request context properties
    
    @property
    def question(self) -> str:
        """
        Get the working question for processing.
        This is an alias for submitted_question for backward compatibility.
        """
        return self.submitted_question
    
    @question.setter
    def question(self, value: str):
        """Set the working question."""
        self.submitted_question = value
    
    @property  
    def username(self) -> str:
        """
        Get the username of the user making the request.
        
        This property provides access to the authenticated user's identifier
        from the request context. Used for logging, auditing, and user-specific
        processing.
        
        Returns:
            str: The username of the requesting user
            
        Note:
            This property is immutable after SystemState initialization.
        """
        return self.request.username
        
    @username.setter
    def username(self, value: str):
        raise AttributeError("Property 'username' is immutable and cannot be modified")
        
    @property
    def started_at(self) -> datetime:
        return self.request.started_at
        
    @property
    def workspace_name(self) -> str:
        return self.request.workspace_name
        
    @workspace_name.setter
    def workspace_name(self, value: str):
        raise AttributeError("Property 'workspace_name' is immutable and cannot be modified")
        
    @property
    def functionality_level(self) -> str:
        return self.request.functionality_level
        
    @functionality_level.setter
    def functionality_level(self, value: str):
        raise AttributeError("Property 'functionality_level' is immutable and cannot be modified")
        
    @property
    def language(self) -> str:
        return self.request.language
        
    @property
    def scope(self) -> str:
        return self.request.scope
        
    @property
    def original_question(self) -> Optional[str]:
        return self.request.original_question
        
    @property
    def original_language(self) -> Optional[str]:
        return self.request.original_language
    
    # Database context properties
    @property
    def full_schema(self) -> Dict[str, TableInfo]:
        """
        Get the complete database schema information.
        
        This property provides access to the full database schema containing
        all tables, columns, types, and metadata. This is the authoritative
        source of database structure information used throughout the system.
        
        Returns:
            Dict[str, TableInfo]: Dictionary mapping table names to their
                complete structure information including columns, types,
                descriptions, and constraints.
                
        Note:
            This property can be modified to update the database schema context.
        """
        return self.database.full_schema
        
    @full_schema.setter
    def full_schema(self, value: Dict[str, TableInfo]):
        self.database.full_schema = value
        
    @property
    def directives(self) -> str:
        return self.database.directives
        
    @property
    def treat_empty_result_as_error(self) -> bool:
        return self.database.treat_empty_result_as_error
        
    @property
    def dbmanager(self) -> Any:
        return self.database.dbmanager
    
    # Semantic context properties
    @property
    def keywords(self) -> List[str]:
        return list(self.semantic.keywords)
        
    @keywords.setter
    def keywords(self, value: List[str]):
        self.semantic.keywords = value
        
    @property
    def evidence(self) -> List[str]:
        return list(self.semantic.evidence)
        
    @evidence.setter
    def evidence(self, value: List[str]):
        self.semantic.evidence = value
        
    @property
    def evidence_for_template(self) -> str:
        return self.semantic.evidence_for_template
        
    @property
    def sql_shots(self) -> List[Tuple[str, str, str]]:
        return list(self.semantic.sql_shots)
        
    @property
    def sql_documents(self) -> List[Any]:
        return list(self.semantic.sql_documents)
    
    # Schema derivations properties
    @property
    def similar_columns(self) -> Dict[str, List[str]]:
        return dict(self.schemas.similar_columns)
    
    @similar_columns.setter
    def similar_columns(self, value: Dict[str, List[str]]):
        self.schemas.similar_columns = value
        
    @property
    def schema_with_examples(self) -> Dict[str, TableInfo]:
        return dict(self.schemas.schema_with_examples)
    
    @schema_with_examples.setter
    def schema_with_examples(self, value: Dict[str, TableInfo]):
        self.schemas.schema_with_examples = value
        
    @property
    def schema_from_vector_db(self) -> Dict[str, TableInfo]:
        return dict(self.schemas.schema_from_vector_db)
    
    @schema_from_vector_db.setter
    def schema_from_vector_db(self, value: Dict[str, TableInfo]):
        self.schemas.schema_from_vector_db = value
        
    @property
    def filtered_schema(self) -> Dict[str, TableInfo]:
        return dict(self.schemas.filtered_schema)
        
    @filtered_schema.setter
    def filtered_schema(self, value: Dict[str, TableInfo]):
        self.schemas.filtered_schema = value
        
    @property
    def enriched_schema(self) -> Dict[str, TableInfo]:
        return dict(self.schemas.enriched_schema)
        
    @enriched_schema.setter
    def enriched_schema(self, value: Dict[str, TableInfo]):
        self.schemas.enriched_schema = value
        
    @property
    def reduced_mschema(self) -> str:
        return self.schemas.reduced_mschema
        
    @reduced_mschema.setter
    def reduced_mschema(self, value: str):
        self.schemas.reduced_mschema = value
        
    @property
    def full_mschema(self) -> str:
        return self.schemas.full_mschema
    
    @full_mschema.setter
    def full_mschema(self, value: str):
        self.schemas.full_mschema = value
        
    @property
    def used_mschema(self) -> str:
        return self.schemas.used_mschema
    
    @used_mschema.setter
    def used_mschema(self, value: str):
        self.schemas.used_mschema = value
    
    # Generation results properties
    @property
    def generated_tests(self) -> List[Tuple[str, List[str]]]:
        return self.generation.generated_tests
        
    @generated_tests.setter
    def generated_tests(self, value: List[Tuple[str, List[str]]]):
        self.generation.generated_tests = value
        
    @property
    def generated_sqls(self) -> List[str]:
        return self.generation.generated_sqls
    
    @generated_sqls.setter
    def generated_sqls(self, value: List[str]):
        self.generation.generated_sqls = value
        
    @property
    def test_results(self) -> List[str]:
        return list(self.generation.test_results)
    
    @test_results.setter
    def test_results(self, value: List[str]):
        self.generation.test_results = value
        
    @property
    def final_evaluation(self) -> bool:
        return self.generation.final_evaluation
    
    @final_evaluation.setter
    def final_evaluation(self, value: bool):
        self.generation.final_evaluation = value
        
    @property
    def generated_tests_json(self) -> str:
        return self.generation.generated_tests_json
    
    @generated_tests_json.setter
    def generated_tests_json(self, value: str):
        self.generation.generated_tests_json = value
        
    @property
    def generated_sqls_json(self) -> str:
        return self.generation.generated_sqls_json
    
    @generated_sqls_json.setter
    def generated_sqls_json(self, value: str):
        self.generation.generated_sqls_json = value
        
    @property
    def evaluation_results(self) -> List[Tuple[str, List[str]]]:
        return self.generation.evaluation_results
    
    @evaluation_results.setter
    def evaluation_results(self, value: List[Tuple[str, List[str]]]):
        self.generation.evaluation_results = value
        
    @property
    def evaluation_results_json(self) -> str:
        return self.generation.evaluation_results_json
    
    @evaluation_results_json.setter
    def evaluation_results_json(self, value: str):
        self.generation.evaluation_results_json = value
        
    @property
    def generated_sql(self) -> Optional[str]:
        return self.generation.generated_sql
        
    @generated_sql.setter
    def generated_sql(self, value: Optional[str]):
        self.generation.generated_sql = value
        
    @property
    def successful_agent_name(self) -> Optional[str]:
        return self.generation.successful_agent_name
    
    @successful_agent_name.setter
    def successful_agent_name(self, value: Optional[str]):
        self.generation.successful_agent_name = value
        
    @property
    def selection_metrics(self) -> Optional[Dict[str, Any]]:
        return self.generation.selection_metrics
    
    @selection_metrics.setter
    def selection_metrics(self, value: Optional[Dict[str, Any]]):
        self.generation.selection_metrics = value
        
    @property
    def selection_metrics_json(self) -> str:
        return self.generation.selection_metrics_json
    
    @selection_metrics_json.setter
    def selection_metrics_json(self, value: str):
        self.generation.selection_metrics_json = value
        
    @property
    def sql_explanation(self) -> Optional[str]:
        return self.generation.sql_explanation
    
    @sql_explanation.setter
    def sql_explanation(self, value: Optional[str]):
        self.generation.sql_explanation = value
    
    # Execution state properties
    @property
    def last_SQL(self) -> str:
        return self.execution.last_SQL
        
    @last_SQL.setter
    def last_SQL(self, value: str):
        self.execution.last_SQL = value
        
    @property
    def last_execution_error(self) -> str:
        return self.execution.last_execution_error
    
    @last_execution_error.setter
    def last_execution_error(self, value: str):
        self.execution.last_execution_error = value
        
    @property
    def last_generation_success(self) -> bool:
        return self.execution.last_generation_success
    
    @last_generation_success.setter
    def last_generation_success(self, value: bool):
        self.execution.last_generation_success = value
        
    @property
    def sql_generation_failure_message(self) -> Optional[str]:
        return self.execution.sql_generation_failure_message
    
    @sql_generation_failure_message.setter
    def sql_generation_failure_message(self, value: Optional[str]):
        self.execution.sql_generation_failure_message = value
        
    @property
    def available_context_tokens(self) -> Optional[int]:
        return self.execution.available_context_tokens
    
    @available_context_tokens.setter
    def available_context_tokens(self, value: Optional[int]):
        self.execution.available_context_tokens = value
        
    @property
    def full_schema_tokens_count(self) -> Optional[int]:
        return self.execution.full_schema_tokens_count
    
    @full_schema_tokens_count.setter
    def full_schema_tokens_count(self, value: Optional[int]):
        self.execution.full_schema_tokens_count = value
        
    @property
    def schema_link_strategy(self) -> Optional[str]:
        return self.execution.schema_link_strategy
    
    @schema_link_strategy.setter
    def schema_link_strategy(self, value: Optional[str]):
        self.execution.schema_link_strategy = value
    
    # External services properties
    @property
    def vdbmanager(self) -> Any:
        return self.services.vdbmanager
        
    @property
    def agents_and_tools(self) -> Any:
        return self.services.agents_and_tools
        
    @property
    def sql_db_config(self) -> Any:
        return self.services.sql_db_config
        
    @property
    def number_of_tests_to_generate(self) -> int:
        return self.services.number_of_tests_to_generate
        
    @property
    def number_of_sql_to_generate(self) -> int:
        return self.services.number_of_sql_to_generate
        
    @property
    def workspace(self) -> dict:
        return self.services.workspace
    
    
    # ============================================================================
    # SCHEMA PROCESSING METHODS
    # 
    # These methods implement core schema processing logic and delegate to
    # specialized context objects where appropriate.
    # Schema creation methods
    # ============================================================================
    
    def create_enriched_schema(self) -> Dict[str, TableInfo]:
        """
        Creates an enriched schema that contains all tables and columns from full_schema,
        with examples merged from schema_with_examples where available.
        No filtering is applied - all tables and columns from full_schema are preserved.
        
        Returns:
            Dict[str, TableInfo]: A new schema with all tables/columns enriched with examples
        """
        enriched_schema: Dict[str, TableInfo] = {}
        
        # Optimize: Pre-fetch schema_with_examples for faster lookups
        examples_by_table = {
            table_name: table_data.get("columns", {})
            for table_name, table_data in self.schema_with_examples.items()
        }
        
        for table_name, table_info in self.full_schema.items():
            # Initialize the enriched table structure with full schema data
            enriched_table: TableInfo = {
                "table_description": table_info.get("table_description", ""),
                "columns": {}
            }
            
            full_columns = table_info.get("columns", {})
            examples_columns = examples_by_table.get(table_name, {})
            
            # Optimize: Process columns efficiently with dict comprehension when possible
            if not examples_columns:
                # Fast path: No examples to merge, just copy columns
                enriched_table["columns"] = {
                    column_name: dict(column_info)
                    for column_name, column_info in full_columns.items()
                }
            else:
                # Standard path: Merge with examples
                for column_name, column_info in full_columns.items():
                    # Start with a copy of the column info from full_schema
                    enriched_column_info = dict(column_info)
                    
                    # Merge additional information from schema_with_examples if available
                    examples_info = examples_columns.get(column_name)
                    if examples_info:
                        # Add examples if available
                        if "examples" in examples_info:
                            enriched_column_info["examples"] = examples_info["examples"]
                        
                        # Optimize: Merge efficiently using dict update for non-conflicting keys
                        for key, value in examples_info.items():
                            if key not in enriched_column_info or not enriched_column_info.get(key):
                                enriched_column_info[key] = value
                    
                    enriched_table["columns"][column_name] = enriched_column_info
            
            # Add all tables (no filtering applied)
            enriched_schema[table_name] = enriched_table
        
        # Update the system state through the schemas context
        self.schemas.enriched_schema = enriched_schema
        
        return enriched_schema

    def create_filtered_schema(self) -> Dict[str, TableInfo]:
        """
        Creates a new schema that contains only columns from full_schema that are present
        in at least one of the other two schemas (schema_with_examples or schema_from_vector_db).
        Always includes primary keys (pk_field) and foreign keys (fk_field) from every table,
        even if not present in the other schemas.
        
        Returns:
            Dict[str, TableInfo]: A new schema with the filtered columns
        """
        filtered_schema: Dict[str, TableInfo] = {}
        
        # Optimize: Pre-fetch nested dictionaries for faster lookups
        vector_by_table = {
            table_name: table_data.get("columns", {})
            for table_name, table_data in self.schema_from_vector_db.items()
        }
        examples_by_table = {
            table_name: table_data.get("columns", {})
            for table_name, table_data in self.schema_with_examples.items()
        }
        
        for table_name, table_info in self.full_schema.items():
            full_columns = table_info.get("columns", {})
            vector_columns = vector_by_table.get(table_name, {})
            examples_columns = examples_by_table.get(table_name, {})
            
            # Optimize: Pre-compute the set of columns to include (union of both schemas)
            columns_to_include = set(vector_columns.keys()) | set(examples_columns.keys())
            
            if not columns_to_include:
                # Fast path: No columns to filter, skip this table
                continue
            
            # Initialize the filtered table structure
            filtered_table: TableInfo = {
                "table_description": table_info.get("table_description", ""),
                "columns": {}
            }
            
            # Optimize: Only process columns that should be included
            for column_name in columns_to_include:
                if column_name not in full_columns:
                    continue  # Skip if not in full schema
                
                column_info = full_columns[column_name]
                # Create a copy of the column info from full_schema
                filtered_column_info = dict(column_info)
                
                # Merge additional information from other schemas if available
                examples_info = examples_columns.get(column_name)
                if examples_info and "examples" in examples_info:
                    filtered_column_info["examples"] = examples_info["examples"]
                
                vector_info = vector_columns.get(column_name)
                if vector_info and "column_description" in vector_info:
                    if not filtered_column_info.get("column_description"):
                        filtered_column_info["column_description"] = vector_info["column_description"]
                
                filtered_table["columns"][column_name] = filtered_column_info
            
            # Only add the table if it has columns
            if filtered_table["columns"]:
                filtered_schema[table_name] = filtered_table
        
        self.schemas.filtered_schema = filtered_schema
        return filtered_schema
    
    def add_connections_to_tentative_schema(self, dbmanager) -> None:
        """
        Add foreign key connections to the tentative schema using the database manager.
        
        This method delegates to the database manager to analyze and add relationship
        information (foreign keys, primary keys, etc.) to the tentative schema. This
        enhances the schema with connection metadata that helps with query generation.
        
        Args:
            dbmanager: Database manager instance that handles schema connection analysis
            
        Note:
            This method modifies the tentative_schema property in-place by adding
            relationship metadata discovered by the database manager.
        """
        dbmanager.add_connections_to_tentative_schema(self.tentative_schema)
    
    def get_database_schema_for_queries(
        self,
        dbmanager,
        queries: List[str],
        include_value_description: bool = True
    ) -> str:
        """
        Generate database schema information for a list of SQL queries.
        
        This method analyzes multiple SQL queries to extract the database schema
        information they require, then creates a unified schema string that includes
        all relevant tables and columns from the queries. The resulting schema can
        be used for SQL generation contexts.
        
        Args:
            dbmanager: Database manager instance for schema operations
            queries (List[str]): List of SQL query strings to analyze
            include_value_description (bool): Whether to include column value descriptions
                in the generated schema string. Defaults to True.
                
        Returns:
            str: A formatted database schema string containing all tables and columns
                referenced by the input queries, optionally enriched with examples
                and descriptions from the system state.
                
        Note:
            If any query fails to parse, an empty schema dict is used for that query
            but processing continues with the remaining queries. The final result
            represents the union of all successfully analyzed queries.
            
        Example:
            >>> queries = ["SELECT name FROM users", "SELECT * FROM orders"]
            >>> schema = state.get_database_schema_for_queries(dbmgr, queries)
            >>> # Returns formatted schema string for 'users' and 'orders' tables
        """
        schema_dict_list = []
        for query in queries:
            try:
                schema_dict_list.append(dbmanager.get_sql_columns_dict(query))
            except (DatabaseConnectionError, ValueError) as e:
                log_error(f"Error in getting database schema for query: {e}")
                schema_dict_list.append({})
            except Exception as e:
                # Unexpected error - log with more context
                log_error(f"Unexpected error in database schema query '{query}': {e}")
                schema_dict_list.append({})
        union_schema_dict = dbmanager.get_union_schema_dict(schema_dict_list)
        database_info = (dbmanager.get_database_schema_string(
            union_schema_dict,
            self.schema_with_examples,
            self.schema_with_descriptions,
            include_value_description=include_value_description
        ))
        return database_info
    
    def construct_history(self) -> str:
        """
        Constructs the history of the executing tool.
        
        Returns:
            str: The history of the previous question and SQL pairs.
        """
        history = ""
        
        # SQL_meta_infos is a list, not a dict
        for index in range(len(self.SQL_meta_infos) - 1):
            history += f"Step: {index + 1}\n"
            history += f"Original SQL: {self.remove_new_lines(self.SQL_meta_infos[index].SQL)}\n"
            history += f"Feedbacks: {self.remove_new_lines(self._get_feedback_string(self.SQL_meta_infos[index].feedbacks))}\n"
            history += f"Refined SQL: {self.remove_new_lines(self.SQL_meta_infos[index + 1].SQL)}\n"
            history += "\n"

        if not history:
            history = "No history available."

        return history
    
    def remove_new_lines(self, text: str) -> str:
        """
        Remove all newline characters from the given text.
        
        This utility method cleans text by removing both carriage returns (\\r)
        and line feeds (\\n) characters, making it suitable for single-line display
        or logging purposes.
        
        Args:
            text (str): The input text that may contain newline characters
            
        Returns:
            str: The text with all newline characters removed
            
        Example:
            >>> state.remove_new_lines("SELECT * FROM\\nusers\\r\\nWHERE id = 1")
            "SELECT * FROM users WHERE id = 1"
        """
        return re.sub(r'[\r\n]+', '', text)
    
    def _get_feedback_string(self, feedbacks: List[str]) -> str:
        """
        Returns a string representation of the feedbacks.
        
        Args:
            feedbacks (List[str]): The list of feedbacks.
        
        Returns:
            str: The string representation of the feedbacks.
        """
        feedback_string = ""
        for i, feedback in enumerate(feedbacks):
            feedback_string += f"--> {i+1}. {feedback}\n"
        return feedback_string

    def get_evidence_from_vector_db(self) -> tuple[bool, List[str], str]:
        """
        Retrieves the top 3 most relevant evidence based on keywords and formats them as a clean markdown list.

        Uses the keywords stored in self.keywords.

        Returns:
            tuple[bool, List[str], str]: (success, evidence_list, error_message)
                - success: True if operation succeeded, False otherwise
                - evidence_list: List of unique evidence strings
                - error_message: Detailed error message if operation failed
        """
        
        # Check if vdbmanager is available
        if not self.vdbmanager:
            error_msg = (
                "VECTOR DATABASE UNAVAILABLE\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "The vector database service is not accessible.\n\n"
                "Impact:\n"
                "• Cannot retrieve contextual hints and evidence\n"
                "• SQL generation will proceed without semantic context\n"
                "• Results may be less accurate\n\n"
                "Recommended Actions:\n"
                "1. Verify Qdrant service is running on the configured port\n"
                "2. Check network connectivity to the vector database\n"
                "3. Confirm vector database configuration in workspace settings\n"
            )
            logging.getLogger(__name__).warning("Vector DB manager not available - cannot retrieve evidence")
            self.semantic.evidence = []
            return False, [], error_msg
        
        # Convert keywords list to a search query string
        query = " ".join(self.keywords) if self.keywords else ""
        
        try:
            similar_evidence = self.vdbmanager.search_similar(
                query=query,
                doc_type=ThothType.EVIDENCE,
                top_k=3,
                score_threshold=0.35)

            if not similar_evidence:
                self.semantic.evidence = []
                return True, [], ""  # Success but no evidence found

            # Remove duplicates by content comparison and filter out white text evidence
            # Optimize: Use dict.fromkeys() for order-preserving deduplication
            unique_evidence = list(dict.fromkeys(
                evidence.evidence.strip()
                for evidence in similar_evidence
                if evidence.evidence and evidence.evidence.strip()
            ))
            self.semantic.evidence = unique_evidence
            return True, unique_evidence, ""
            
        except VectorDatabaseError as e:
            error_msg = f"Vector database error during evidence retrieval: {e}"
            log_error(error_msg)
            self.semantic.evidence = []
            return False, [], error_msg
            
        except Exception as e:
            error_msg = (
                f"UNEXPECTED ERROR in evidence retrieval\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Failed to retrieve evidence from vector database.\n\n"
                f"Error Details:\n"
                f"• {str(e)}\n\n"
                f"Impact:\n"
                f"• Cannot retrieve contextual hints\n"
                f"• SQL generation will proceed with reduced accuracy\n\n"
                f"The system will continue but results may be suboptimal.\n"
            )
            log_error(f"Unexpected error retrieving evidence: {e}")
            self.semantic.evidence = []
            return False, [], error_msg

    def get_sql_from_vector_db(self) -> tuple[bool, List[Tuple[str, str, str]], str]:
        """
        Retrieves the top 5 most relevant SQL examples based on keywords and extracts question, SQL, and hint values.

        Uses the keywords stored in self.keywords and the vdbmanager stored in self.vdbmanager.
        Also stores the results in self.sql_shots for later use.
        Now uses a more permissive similarity search to always get 5 examples.

        Returns:
            tuple[bool, List[Tuple[str, str, str]], str]: (success, sql_examples, error_message)
                - success: True if operation succeeded, False otherwise
                - sql_examples: List of tuples (question, sql, hint) with duplicates removed
                - error_message: Detailed error message if operation failed
        """
        
        # Check if vdbmanager is available
        if not self.vdbmanager:
            error_msg = (
                "VECTOR DATABASE UNAVAILABLE\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "The vector database service is not accessible.\n\n"
                "Impact:\n"
                "• Cannot retrieve similar SQL examples\n"
                "• SQL generation will proceed without reference examples\n"
                "• Generated SQL may be less idiomatic or optimized\n\n"
                "Recommended Actions:\n"
                "1. Verify Qdrant service is running on the configured port\n"
                "2. Check network connectivity to the vector database\n"
                "3. Confirm vector database configuration in workspace settings\n"
            )
            logging.getLogger(__name__).warning("Vector DB manager not available - cannot retrieve SQL examples")
            self.semantic.sql_shots = []
            self.semantic.sql_documents = []
            return False, [], error_msg
        
        # Convert keywords list to a search query string
        query = " ".join(self.keywords) if self.keywords else ""
        
        try:
            # Use a very low threshold to get more results, even if not closely related
            # We want to get at least 5 examples, so use a permissive threshold
            similar_sqls = self.vdbmanager.search_similar(
                query=query,
                doc_type=ThothType.SQL,
                top_k=5,
                score_threshold=0.1  # Much lower threshold for more permissive search
            )
            
            if not similar_sqls:
                self.semantic.sql_shots = []
                self.semantic.sql_documents = []
                return True, [], ""  # Success but no examples found
            
            # Remove duplicates by SQL content comparison and extract values
            seen_sqls = set()
            unique_sql_tuples = []
            for sql_doc in similar_sqls:
                # Use both question and SQL as unique identifier to avoid duplicates
                sql_key = f"{sql_doc.question.strip().lower()}||{sql_doc.sql.strip().lower()}"
                if sql_key not in seen_sqls:
                    seen_sqls.add(sql_key)
                    # Extract question, sql, and hint from the SqlDocument
                    question = sql_doc.question.strip() if hasattr(sql_doc, 'question') and sql_doc.question else ""
                    sql = sql_doc.sql.strip() if hasattr(sql_doc, 'sql') and sql_doc.sql else ""
                    hint = sql_doc.hint.strip() if hasattr(sql_doc, 'hint') and sql_doc.hint else ""
                    unique_sql_tuples.append((question, sql, hint))
            
            # Store the SQL shots in the system state for logging
            self.semantic.sql_shots = unique_sql_tuples
            
            # Also store the actual SqlDocument objects for template formatting
            # Only store unique ones based on the same key
            unique_sql_documents = []
            seen_keys = set()
            for sql_doc in similar_sqls:
                sql_key = f"{sql_doc.question.strip().lower()}||{sql_doc.sql.strip().lower()}"
                if sql_key not in seen_keys:
                    seen_keys.add(sql_key)
                    unique_sql_documents.append(sql_doc)
            
            self.semantic.sql_documents = unique_sql_documents[:5]  # Ensure we have at most 5
            
            return True, unique_sql_tuples, ""
            
        except Exception as e:
            error_msg = (
                f"VECTOR DATABASE ERROR\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Failed to retrieve SQL examples from vector database.\n\n"
                f"Error Details:\n"
                f"• {str(e)}\n\n"
                f"Impact:\n"
                f"• Cannot retrieve similar SQL patterns\n"
                f"• SQL generation will proceed without examples\n"
                f"• Generated SQL may not follow database conventions\n\n"
                f"The system will continue but SQL quality may be reduced.\n"
            )
            log_error(f"Error retrieving SQL examples: {e}")
            self.semantic.sql_shots = []
            self.semantic.sql_documents = []
            return False, [], error_msg

    def extract_schema_via_lsh(self) -> None:
        """
        Extracts schema using LSH similarity search and updates system state.
        
        Delegates to SchemaProcessor for actual processing.
        """
        self.schema_processor.extract_via_lsh(self)
    
    def extract_schema_from_vectordb(self) -> None:
        """
        Extracts schema from vector database using semantic similarity search.
        
        Delegates to SchemaProcessor for actual processing.
        """
        self.schema_processor.extract_from_vectordb(self)
    
    def update_directives_from_workspace(self, workspace_data: Dict[str, Any]) -> None:
        """
        Updates the directives field from workspace data.
        
        Delegates to SchemaProcessor for actual processing.
        """
        self.schema_processor.update_directives_from_workspace(self, workspace_data)

    async def run_question_validation_with_translation(self):
        """
        Run the enhanced question validation flow with language detection and translation coordination.
        This function implements a multi-agent system where the validator can call the translator.
        Returns ValidationResult with all necessary data.
        """
        from typing import Optional, NamedTuple
        from dataclasses import dataclass
        from helpers.template_preparation import TemplateLoader

        # Get logging level from environment
        logging_level = os.getenv('LOGGING_LEVEL', 'INFO').upper()
        level_mapping = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        log_level = level_mapping.get(logging_level, logging.INFO)
        
        logging.getLogger(__name__).setLevel(log_level)

        class TranslationResult(NamedTuple):
            """Result of translation operation with explicit data."""
            translated_question: str
            original_question: str
            original_language: str
            was_translated: bool

        class ValidationResult(NamedTuple):
            """Complete result of validation operation."""
            message: str
            is_valid: bool
            question: str
            original_question: Optional[str] = None
            original_language: Optional[str] = None

        @dataclass 
        class TranslationDeps:
            """Dependencies for question translation containing the necessary data for template injection."""
            question: str
            target_language: str
            scope: str

        # Note: scope and language are now set during initialization via RequestContext

        log_info(f"Starting question validation - Target language: {self.language}")

        # Create a combined agent that has both validator and translator capabilities
        # The validator agent gets access to the translator agent as a tool
        if not hasattr(self.agents_and_tools, 'question_validator_agent') or not hasattr(self.agents_and_tools, 'question_translator_agent'):
            # Fallback to simple validation if agents are not available
            log_info("Falling back to simple validation - agents not available")
            simple_result = await self._run_question_validation()
            return ValidationResult(
                message=simple_result[0],
                is_valid=simple_result[1],
                question=self.question
            )

        # Add the translator as a tool to the validator agent
        validator_agent = self.agents_and_tools.question_validator_agent
        translator_agent = self.agents_and_tools.question_translator_agent

        # Store translation result to return explicitly
        translation_result = None
        
        # Check if translator_tool is already registered to prevent duplicate registration
        existing_tool_names = [tool.name for tool in validator_agent._function_toolset.tools]
        
        if "translator_tool" not in existing_tool_names:
            # Register the translator agent as a tool for the validator (without state updates)
            @validator_agent.tool
            async def translator_tool(ctx: RunContext['SystemState'], question_to_translate: str, target_language: str, scope: str) -> str:
                """Translate a question to the target language and return translation info."""
                nonlocal translation_result
                try:
                    # Validate inputs
                    if not question_to_translate or not question_to_translate.strip():
                        return "Translation failed: Empty question provided"
                    
                    if not target_language or not target_language.strip():
                        return "Translation failed: No target language specified"
                    
                    # Create translation dependencies
                    translation_deps = TranslationDeps(
                        question=question_to_translate.strip(),
                        target_language=target_language.strip(),
                        scope=scope or ""
                    )
                    
                    # Get the translation template and run the translator agent
                    translation_template = TemplateLoader.format(
                        'user_translate',
                        question=question_to_translate.strip(), 
                        target_language=target_language.strip(), 
                        scope=scope or ""
                    )
                    translation_agent_result = await translator_agent.run(
                        translation_template,
                        deps=translation_deps,
                    )
                    
                    # Validate translation result
                    if not translation_agent_result:
                        return "Translation failed: Invalid translation result"
                    
                    # Store translation result for explicit return
                    translation_result = TranslationResult(
                        translated_question=translation_agent_result.output.translated_question,
                        original_question=question_to_translate,
                        original_language=translation_agent_result.output.detected_language,
                        was_translated=translation_agent_result.output.translated_question != question_to_translate
                    )
                    
                    log_info(f"Translation completed: {question_to_translate} -> {translation_result.translated_question}")
                    return f"Translation successful. Question translated from {translation_result.original_language} to {target_language}"
                    
                except AgentExecutionError as e:
                    error_msg = f"Translation agent error: {str(e)}"
                    log_error(error_msg)
                    return error_msg
                except Exception as e:
                    error_msg = f"Unexpected translation error: {str(e)}"
                    log_error(error_msg)
                    # Convert to specific exception for consistency
                    raise AgentExecutionError(f"Translation failed: {e}", agent_type="question_translation")

        # Prepare the enhanced validation template with language detection
        validation_template = TemplateLoader.format(
            'user_validate_lang',
            question=self.question,
            scope=self.scope,
            language=self.language
        )

        # Run the enhanced validator agent with translator access
        log_info("Running enhanced question validation with language detection...")
        
        try:
            check_result = await validator_agent.run(
                validation_template,
                deps=self,
            )

            if log_level <= logging.INFO:
                logging.getLogger(__name__).info(f"Validator agent execution completed")
            
            # Check if we got a valid result
            if not check_result or not hasattr(check_result, 'data'):
                log_error("Validator agent returned invalid result")
                simple_result = await self._run_question_validation()
                return ValidationResult(
                    message=simple_result[0],
                    is_valid=simple_result[1],
                    question=self.question
                )
            
            # Analyze the result
            outcome = check_result.output.outcome
            reasons = check_result.output.reasons
            detected_language = getattr(check_result.output, 'detected_language', 'unknown')
            translation_needed = getattr(check_result.output, 'translation_needed', False)
            
            # Log the detection results
            log_info(f"Language detection: {detected_language}, Translation needed: {translation_needed}")
            
        except ValidationError as e:
            error_msg = f"Validation error: {str(e)}"
            log_error(error_msg)
            # Fallback to simple validation
            log_info("Falling back to simple validation due to validation error")
            simple_result = await self._run_question_validation()
            return ValidationResult(
                message=simple_result[0],
                is_valid=simple_result[1],
                question=self.question
            )
        except AgentExecutionError as e:
            error_msg = f"Agent execution error during validation: {str(e)}"
            log_error(error_msg)
            # Fallback to simple validation
            log_info("Falling back to simple validation due to agent error")
            simple_result = await self._run_question_validation()
            return ValidationResult(
                message=simple_result[0],
                is_valid=simple_result[1],
                question=self.question
            )
        except Exception as e:
            error_msg = f"Unexpected error during enhanced validation: {str(e)}"
            log_error(error_msg)
            # Convert to specific exception for consistency
            raise ValidationError(f"Enhanced validation failed: {e}")

        if outcome != "OK":
            error_message = f"## Question Validation Failed\n\n"
            error_message += f"**Status**: {outcome}\n\n"
            error_message += f"**Explanation**: {reasons}\n\n"
            error_message += "### Please try:\n\n"
            error_message += "- Rephrasing your question more clearly\n"
            error_message += "- Ensuring your question relates to the database scope\n"
            error_message += "- Using proper grammar and complete sentences\n"
            error_message += "- Being more specific about what data you want to retrieve\n\n"
            error_message += "### Examples of good questions:\n\n"
            error_message += "- *What is the average salary of employees?*\n"
            error_message += "- *Show me all customers from Italy*\n"
            error_message += "- *How many orders were placed last month?*"

            log_error(f"Question validation failed: {outcome} - {reasons}")
            return ValidationResult(
                message=error_message,
                is_valid=False,
                question=self.question,
                original_question=translation_result.original_question if translation_result else None,
                original_language=translation_result.original_language if translation_result else None
            )
       
        success_msg = "THOTHLOG:Question validation passed"
        if translation_needed:
            success_msg += f" (translated from {detected_language} to {self.language})"
        success_msg += ", proceeding with keyword extraction"
        log_info(f"Enhanced validation completed successfully - {success_msg}")
        
        return ValidationResult(
            message=success_msg,
            is_valid=True,
            question=translation_result.translated_question if translation_result else self.question,
            original_question=translation_result.original_question if translation_result else None,
            original_language=translation_result.original_language if translation_result else None
        )

    async def _run_question_validation(self):
        """
        Run the original question validation flow (fallback version).
        Returns a tuple: (message_to_stream, is_valid).
        """
        from helpers.template_preparation import TemplateLoader

        # Get logging level from environment
        logging_level = os.getenv('LOGGING_LEVEL', 'INFO').upper()
        level_mapping = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        log_level = level_mapping.get(logging_level, logging.INFO)
        
        logging.getLogger(__name__).setLevel(log_level)

        # Get scope and language from workspace
        scope = self.workspace.get("sql_db", {}).get("scope", "")
        language = self.workspace.get("sql_db", {}).get("language", "English")

        # Log scope and language used by LLM (only if log level allows)
        if log_level <= logging.INFO:
            logging.getLogger(__name__).info(f"LLM using scope: '{scope}' and language: '{language}'")
        log_info(f"LLM using scope: '{scope}' and language: '{language}'")

        # Format the check question template with actual values
        check_template = TemplateLoader.format(
            'user_check_question',
            question=self.question,
            scope=scope,
            language=language
        )

        # Run the question validator agent with SystemState
        log_info("Running question validity check...")
        check_result = await self.agents_and_tools.question_validator_agent.run(
            check_template,
            deps=self,  # Use SystemState - the agent expects this
        )

        # Analyze the result - in PydanticAI 0.7.0, access via .output
        outcome = check_result.output.outcome
        reasons = check_result.output.reasons

        # Log outcome and reasons from question check
        if log_level <= logging.INFO:
            logging.getLogger(__name__).info(
                f"Question check result - outcome: '{outcome}', reasons: '{reasons}'"
            )
        log_info(f"Question check result - outcome: '{outcome}', reasons: '{reasons}'")

        log_info(f"Question check outcome: {outcome}")

        if outcome != "OK":
            # Question is not valid, return error message
            error_message = f"## Question Validation Failed\n\n"
            error_message += f"**Status**: {outcome}\n\n"
            error_message += f"**Explanation**: {reasons}\n\n"
            error_message += "### Please try:\n\n"
            error_message += "- Rephrasing your question more clearly\n"
            error_message += "- Ensuring your question relates to the database scope\n"
            error_message += "- Using proper grammar and complete sentences\n"
            error_message += "- Being more specific about what data you want to retrieve\n\n"
            error_message += "### Examples of good questions:\n\n"
            error_message += "- *What is the average salary of employees?*\n"
            error_message += "- *Show me all customers from Italy*\n"
            error_message += "- *How many orders were placed last month?*"

            log_error(f"Question validation failed: {outcome} - {reasons}")
            log_error(f"Question validation failed: {outcome} - {reasons}")
            return error_message, False

        # Question is valid, continue with workflow
        return "THOTHLOG:Question validation passed, proceeding with keyword extraction", True