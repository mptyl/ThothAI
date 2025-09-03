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
Schema processor for handling database schema operations.

This module provides the SchemaProcessor class which encapsulates all schema-related
operations including LSH similarity search, vector database extraction, and workspace
directive updates. This reduces the complexity of the SystemState class by extracting
schema processing logic into a dedicated, focused class.
"""

import logging
from typing import Dict, Any, List, Tuple
from helpers.dual_logger import log_error
from .exceptions import SchemaProcessingError, VectorDatabaseError


class SchemaProcessor:
    """
    Handles all schema processing operations for SystemState.
    
    This processor encapsulates schema-related operations including:
    - LSH (Locality Sensitive Hashing) similarity search for schema extraction
    - Vector database semantic search for column descriptions
    - Workspace directive management
    - Schema aggregation and formatting operations
    
    The processor works with SystemState instances but encapsulates the complex
    schema processing logic to improve maintainability and testability.
    """
    
    def __init__(self):
        """Initialize the schema processor."""
        self.logger = logging.getLogger(__name__)
    
    def extract_via_lsh(self, system_state) -> None:
        """
        Extract schema using LSH (Locality Sensitive Hashing) similarity search.
        
        This method uses the helper function that reads configurable parameters from workspace settings
        to perform LSH similarity search and extract relevant schema information.
        
        Args:
            system_state: SystemState instance to update with LSH results
            
        Raises:
            SchemaProcessingError: If LSH extraction fails
        """
        from helpers.main_helpers.main_schema_extraction_from_lsh import extract_schema_via_lsh as extract_lsh_helper
        
        try:
            # Use the helper function that reads configurable parameters from workspace settings
            similar_columns, schema_with_examples = extract_lsh_helper(system_state)
            
            # Store the results in system state
            system_state.schemas.similar_columns = similar_columns
            system_state.schemas.schema_with_examples = schema_with_examples
            
            self.logger.info(f"Schema extraction completed using configurable LSH parameters. "
                           f"Found {len(similar_columns)} tables with similar columns")
            
        except SchemaProcessingError as e:
            log_error(f"Schema processing error during LSH extraction: {e}")
            # Fallback to empty results to prevent application crash
            system_state.schemas.similar_columns = {}
            system_state.schemas.schema_with_examples = {}
            self.logger.warning("Using empty schema as fallback due to extraction error")
        except Exception as e:
            log_error(f"Unexpected error during LSH schema extraction: {e}")
            # Convert to specific exception type for consistency
            raise SchemaProcessingError(f"LSH schema extraction failed: {e}", operation="LSH extraction")
    
    def extract_from_vectordb(self, system_state) -> None:
        """
        Extract schema from vector database using semantic similarity search.
        
        This method populates schema_from_vector_db with table structure including
        column descriptions retrieved through vector similarity search.
        
        Args:
            system_state: SystemState instance to update with vector DB results
            
        Raises:
            VectorDatabaseError: If vector database operations fail
            SchemaProcessingError: If schema processing fails
        """
        from helpers.vectordb_context_retrieval import find_relevant_columns
        
        try:
            # Initialize aggregated schema dictionary
            aggregated_schema = {}
            
            def merge_results(target_dict: Dict, source_results):
                """Helper function to merge vector DB results into aggregated schema"""
                # Handle both dict and list formats
                if isinstance(source_results, dict):
                    # source_results is Dict[table_name, Dict[column_name, column_info]]
                    for table_name, columns in source_results.items():
                        if not table_name or not isinstance(columns, dict):
                            continue
                        
                        if table_name not in target_dict:
                            target_dict[table_name] = {}
                        
                        for column_name, column_info in columns.items():
                            if column_name and isinstance(column_info, dict):
                                # Ensure table_name and column_name are in the info
                                column_info['table_name'] = table_name
                                column_info['column_name'] = column_name
                                target_dict[table_name][column_name] = column_info
                                
                elif isinstance(source_results, list):
                    # Legacy format: List of dicts with table_name and column_name keys
                    for result in source_results:
                        if not isinstance(result, dict):
                            continue
                            
                        table_name = result.get('table_name', '')
                        column_name = result.get('column_name', '')
                        
                        if not table_name or not column_name:
                            continue
                        
                        if table_name not in target_dict:
                            target_dict[table_name] = {}
                        
                        target_dict[table_name][column_name] = result
                else:
                    # Unexpected format, log warning
                    self.logger.warning(f"Unexpected source_results format: {type(source_results)}")
            
            # Get evidence for concatenated search
            evidence = " ".join(system_state.semantic.evidence) if system_state.semantic.evidence else ""
            
            self.logger.info(f"Starting vector DB schema extraction with {len(system_state.semantic.keywords)} keywords")
            
            # 1. Search for each keyword individually (top_k=3 each)
            for keyword in system_state.semantic.keywords:
                if keyword and keyword.strip():
                    self.logger.debug(f"Searching vector DB for keyword: {keyword}")
                    try:
                        keyword_results = find_relevant_columns(
                            query=keyword.strip(),
                            vector_db=system_state.services.vdbmanager,
                            top_k=3
                        )
                        merge_results(aggregated_schema, keyword_results)
                        self.logger.debug(f"Found {len(keyword_results)} tables for keyword '{keyword}'")
                    except VectorDatabaseError as e:
                        self.logger.warning(f"Vector database error searching for keyword '{keyword}': {e}")
                    except Exception as e:
                        self.logger.warning(f"Unexpected error searching for keyword '{keyword}': {e}")
                        # Convert to specific exception for consistency
                        raise VectorDatabaseError(f"Keyword search failed: {e}", operation="keyword search", query=keyword)
            
            # 2. Search for the full question (top_k=10)
            if system_state.question and system_state.question.strip():
                self.logger.debug(f"Searching vector DB for full question")
                try:
                    question_results = find_relevant_columns(
                        query=system_state.question.strip(),
                        vector_db=system_state.services.vdbmanager,
                        top_k=10
                    )
                    merge_results(aggregated_schema, question_results)
                    self.logger.debug(f"Found {len(question_results)} tables for question")
                except VectorDatabaseError as e:
                    self.logger.warning(f"Vector database error searching for question: {e}")
                except Exception as e:
                    self.logger.warning(f"Unexpected error searching for question: {e}")
                    # Convert to specific exception for consistency
                    raise VectorDatabaseError(f"Question search failed: {e}", operation="question search", query=system_state.question)
            
            # 3. Search for concatenated evidence if available (top_k=5)
            if evidence and evidence.strip():
                self.logger.debug(f"Searching vector DB for evidence")
                try:
                    evidence_results = find_relevant_columns(
                        query=evidence.strip(),
                        vector_db=system_state.services.vdbmanager,
                        top_k=5
                    )
                    merge_results(aggregated_schema, evidence_results)
                    self.logger.debug(f"Found {len(evidence_results)} tables for evidence")
                except VectorDatabaseError as e:
                    self.logger.warning(f"Vector database error searching for evidence: {e}")
                except Exception as e:
                    self.logger.warning(f"Unexpected error searching for evidence: {e}")
                    # Convert to specific exception for consistency
                    raise VectorDatabaseError(f"Evidence search failed: {e}", operation="evidence search", query=evidence)
            
            # Format results to match expected structure
            schema_from_vector_db = self._format_vector_results(aggregated_schema)
            
            self.logger.info(f"Vector DB schema extraction completed. Found {len(schema_from_vector_db)} tables")
            
            # Update system state
            system_state.schemas.schema_from_vector_db = schema_from_vector_db
            
        except VectorDatabaseError as e:
            log_error(f"Vector database error during schema extraction: {str(e)}")
            # Set empty schema on error to not block the flow
            system_state.schemas.schema_from_vector_db = {}
        except Exception as e:
            log_error(f"Unexpected error during vector database schema extraction: {str(e)}")
            # Convert to specific exception type for consistency
            raise VectorDatabaseError(f"Vector DB schema extraction failed: {e}", operation="schema extraction")
    
    def update_directives_from_workspace(self, system_state, workspace_data: Dict[str, Any]) -> None:
        """
        Update the directives field from workspace data.
        
        Uses default directive if workspace directives are empty.
        
        Args:
            system_state: SystemState instance to update
            workspace_data: Dictionary containing workspace information including sqldb data
        """
        try:
            # Extract SQL database configuration from workspace data
            sql_db_data = workspace_data.get("sql_db", {}) if workspace_data else {}
            
            # Get directives from workspace, use default if empty
            workspace_directives = sql_db_data.get("directives", "").strip()
            
            if workspace_directives:
                system_state.database.directives = workspace_directives
                self.logger.info(f"Updated directives from workspace: {workspace_directives[:100]}...")
            else:
                # Use default directive
                default_directive = "Use only existing field names and table names"
                system_state.database.directives = default_directive
                self.logger.info(f"Using default directives: {default_directive}")
                
        except Exception as e:
            log_error(f"Error updating directives from workspace: {str(e)}")
            # Use default directive on error
            default_directive = "Use only existing field names and table names"
            system_state.database.directives = default_directive
            self.logger.warning(f"Using default directives due to error: {default_directive}")
    
    def _format_vector_results(self, aggregated_schema: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Format vector database results to match expected schema structure.
        
        Removes scores and ensures proper structure for schema consumption.
        
        Args:
            aggregated_schema: Raw results from vector database searches
            
        Returns:
            Dict: Formatted schema dictionary
        """
        schema_from_vector_db = {}
        
        for table_name, columns in aggregated_schema.items():
            schema_from_vector_db[table_name] = {
                "table_description": "",  # Vector DB doesn't provide table descriptions
                "columns": {}
            }
            
            for column_name, column_info in columns.items():
                if not isinstance(column_info, dict):
                    continue
                
                # Clean the column info by removing score and maintaining structure
                clean_info = {
                    "original_column_name": column_info.get("original_column_name", column_name),
                    "column_description": column_info.get("column_description", ""),
                    "value_description": column_info.get("value_description", "")
                }
                
                # Add any other metadata that's not the score
                for key, value in column_info.items():
                    if key not in ["score", "table_name", "column_name", "original_column_name", 
                                   "column_description", "value_description"]:
                        clean_info[key] = value
                
                schema_from_vector_db[table_name]["columns"][column_name] = clean_info
        
        return schema_from_vector_db