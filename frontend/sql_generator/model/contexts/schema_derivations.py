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
Schema derivations context for SystemState decomposition.

Contains various processed and filtered versions of the database schema
that are generated during the SQL generation workflow for different purposes.
"""

from typing import Dict, List
from pydantic import BaseModel, Field, validator
from frozendict import frozendict

# Import the type definition from centralized types module  
from ..types import TableInfo


class SchemaDerivations(BaseModel):
    """
    Processed and filtered schema variants for SQL generation.
    
    This context contains different versions of the database schema that are
    derived from the base full_schema through various filtering, enrichment,
    and processing operations. Each schema serves a specific purpose in the
    SQL generation pipeline.
    
    Schema Types:
    - similar_columns: LSH similarity search results (column recommendations)
    - schema_with_examples: Schema enriched with example values from LSH
    - schema_from_vector_db: Schema with descriptions from vector database
    - filtered_schema: Subset of relevant tables/columns for current question
    - enriched_schema: Full schema with all available enhancements
    - reduced_mschema: M-Schema string for filtered schema (LLM consumption)
    - full_mschema: M-Schema string for complete schema (reference)
    - used_mschema: Final M-Schema actually used by SQL generation
    """
    
    # LSH (Locality Sensitive Hashing) similarity search results
    similar_columns: Dict[str, List[str]] = Field(
        default_factory=lambda: frozendict({}),
        description="Column similarity mapping from LSH search: {table_name: [similar_column_names]}"
    )
    
    schema_with_examples: Dict[str, TableInfo] = Field(
        default_factory=lambda: frozendict({}),
        description="Schema structure with example values from LSH similarity search"
    )
    
    # Vector database schema enrichment
    schema_from_vector_db: Dict[str, TableInfo] = Field(
        default_factory=lambda: frozendict({}),
        description="Schema with column descriptions retrieved from vector database"
    )
    
    # Processed schema variants
    filtered_schema: Dict[str, TableInfo] = Field(
        default_factory=lambda: frozendict({}),
        description="Filtered schema containing only relevant columns for current question"
    )
    
    enriched_schema: Dict[str, TableInfo] = Field(
        default_factory=lambda: frozendict({}),
        description="Full schema enriched with examples and descriptions from all sources"
    )
    
    # M-Schema string representations (for LLM consumption)
    reduced_mschema: str = Field(
        default="",
        description="M-Schema string representation of filtered schema for LLM"
    )
    
    full_mschema: str = Field(
        default="",
        description="M-Schema string representation of complete database schema"
    )
    
    used_mschema: str = Field(
        default="",
        description="Final M-Schema string that was actually used for SQL generation"
    )
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True  # Allow frozendict
        validate_assignment = True  # Validate on field assignment
        
    @validator('similar_columns')
    def validate_similar_columns(cls, v):
        """Ensure similar_columns is properly formatted"""
        if v is None:
            return frozendict({})
        # Ensure all values are lists and remove empty entries
        cleaned = {}
        for table, columns in v.items():
            if isinstance(columns, list) and columns:
                cleaned[table] = [col for col in columns if col and col.strip()]
        return frozendict(cleaned)
        
    @validator('schema_with_examples', 'schema_from_vector_db', 'filtered_schema', 'enriched_schema')
    def validate_schema_dict(cls, v):
        """Validate schema dictionary structure"""
        if v is None:
            return frozendict({})
        # Basic validation that each table has the expected structure
        for table_name, table_info in v.items():
            if not isinstance(table_info, dict):
                continue
            if 'columns' not in table_info:
                continue  # Skip malformed entries
        return frozendict(v)
        
    def has_lsh_results(self) -> bool:
        """
        Check if LSH similarity search results are available.
        
        Returns:
            bool: True if LSH results exist
        """
        return len(self.similar_columns) > 0 or len(self.schema_with_examples) > 0
        
    def has_vector_db_results(self) -> bool:
        """
        Check if vector database results are available.
        
        Returns:
            bool: True if vector DB results exist
        """
        return len(self.schema_from_vector_db) > 0
        
    def has_filtered_schema(self) -> bool:
        """
        Check if filtered schema has been created.
        
        Returns:
            bool: True if filtered schema exists
        """
        return len(self.filtered_schema) > 0
        
    def has_enriched_schema(self) -> bool:
        """
        Check if enriched schema has been created.
        
        Returns:
            bool: True if enriched schema exists  
        """
        return len(self.enriched_schema) > 0
        
    def has_mschema(self) -> bool:
        """
        Check if M-Schema string has been generated.
        
        Returns:
            bool: True if at least one M-Schema variant exists
        """
        return bool(self.reduced_mschema or self.full_mschema or self.used_mschema)
        
    def get_filtered_table_names(self) -> List[str]:
        """
        Get list of table names in the filtered schema.
        
        Returns:
            List[str]: List of filtered table names
        """
        return list(self.filtered_schema.keys())
        
    def get_enriched_table_names(self) -> List[str]:
        """
        Get list of table names in the enriched schema.
        
        Returns:
            List[str]: List of enriched table names
        """
        return list(self.enriched_schema.keys())
        
    def get_similar_columns_for_table(self, table_name: str) -> List[str]:
        """
        Get similar columns for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List[str]: List of similar column names, empty if none found
        """
        return list(self.similar_columns.get(table_name, []))
        
    def count_filtered_columns(self) -> int:
        """
        Count total number of columns in filtered schema.
        
        Returns:
            int: Total column count across all filtered tables
        """
        total = 0
        for table_info in self.filtered_schema.values():
            columns = table_info.get('columns', {})
            total += len(columns)
        return total
        
    def count_enriched_columns(self) -> int:
        """
        Count total number of columns in enriched schema.
        
        Returns:
            int: Total column count across all enriched tables
        """
        total = 0
        for table_info in self.enriched_schema.values():
            columns = table_info.get('columns', {})
            total += len(columns)
        return total
        
    def get_schema_derivations_summary(self) -> str:
        """
        Get a summary of schema derivations for logging/display.
        
        Returns:
            str: Human-readable summary of schema derivations
        """
        summary_parts = []
        
        if self.has_lsh_results():
            lsh_tables = len(self.similar_columns) + len(self.schema_with_examples)
            summary_parts.append(f"LSH: {lsh_tables} tables")
            
        if self.has_vector_db_results():
            vdb_tables = len(self.schema_from_vector_db)
            summary_parts.append(f"VectorDB: {vdb_tables} tables")
            
        if self.has_filtered_schema():
            filtered_tables = len(self.filtered_schema)
            filtered_columns = self.count_filtered_columns()
            summary_parts.append(f"Filtered: {filtered_tables} tables, {filtered_columns} columns")
            
        if self.has_enriched_schema():
            enriched_tables = len(self.enriched_schema) 
            enriched_columns = self.count_enriched_columns()
            summary_parts.append(f"Enriched: {enriched_tables} tables, {enriched_columns} columns")
            
        if self.has_mschema():
            mschema_variants = sum([
                bool(self.reduced_mschema),
                bool(self.full_mschema), 
                bool(self.used_mschema)
            ])
            summary_parts.append(f"M-Schema: {mschema_variants} variants")
            
        if not summary_parts:
            return "No schema derivations available"
            
        return f"Schema derivations: {', '.join(summary_parts)}"