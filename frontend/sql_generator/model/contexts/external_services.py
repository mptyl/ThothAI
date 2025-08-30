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
External services context for SystemState decomposition.

Contains references to external services and managers used throughout
the SQL generation workflow, including vector database, agents, and configurations.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ExternalServices(BaseModel):
    """
    External services and managers context.
    
    This context holds references to external services, managers, and configurations
    that are used throughout the SQL generation pipeline. These are typically
    initialized once and shared across different phases of execution.
    
    Services are grouped by type:
    - Vector Database: vdbmanager (for semantic search and context retrieval)
    - AI Agents: agents_and_tools (collection of PydanticAI agents)
    - Database Config: sql_db_config (connection and configuration details)
    - Processing Config: number_of_tests_to_generate, number_of_sql_to_generate
    - Request Flags: request_flags (sidebar configuration flags from the UI)
    """
    
    # Vector database manager for semantic search
    vdbmanager: Optional[Any] = Field(
        default=None,
        description="Vector database manager for semantic similarity search and context retrieval"
    )
    
    # AI agents collection
    agents_and_tools: Optional[Any] = Field(
        default=None,
        description="Collection of PydanticAI agents and tools for SQL generation workflow"
    )
    
    # Database configuration
    sql_db_config: Optional[Any] = Field(
        default=None,
        description="SQL database configuration and connection parameters"
    )
    
    # Generation parameters
    number_of_tests_to_generate: int = Field(
        default=5,
        description="Number of test cases to generate for SQL validation"
    )
    
    number_of_sql_to_generate: int = Field(
        default=10,
        description="Number of SQL candidates to generate for selection"
    )
    
    # Workspace data (for agent access)
    workspace: dict = Field(
        default_factory=dict,
        description="Complete workspace configuration data"
    )
    
    # Request flags from UI
    request_flags: Dict[str, bool] = Field(
        default_factory=dict,
        description="Sidebar configuration flags from the UI request"
    )
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True  # Allow external service objects
        validate_assignment = True  # Validate on field assignment
        
    def has_vector_db(self) -> bool:
        """
        Check if vector database manager is available.
        
        Returns:
            bool: True if vdbmanager is available
        """
        return self.vdbmanager is not None
        
    def has_agents(self) -> bool:
        """
        Check if AI agents are available.
        
        Returns:
            bool: True if agents_and_tools is available
        """
        return self.agents_and_tools is not None
        
    def has_db_config(self) -> bool:
        """
        Check if database configuration is available.
        
        Returns:
            bool: True if sql_db_config is available
        """
        return self.sql_db_config is not None
        
    def has_workspace(self) -> bool:
        """
        Check if workspace data is available.
        
        Returns:
            bool: True if workspace contains data
        """
        return len(self.workspace) > 0
        
    def get_vector_db_type(self) -> str:
        """
        Get vector database type if available.
        
        Returns:
            str: Vector database type or 'Unknown'
        """
        if not self.has_vector_db():
            return "Unknown"
            
        # Try to get type from vdbmanager if it has a type attribute
        if hasattr(self.vdbmanager, 'db_type'):
            return str(self.vdbmanager.db_type)
        elif hasattr(self.vdbmanager, '__class__'):
            return self.vdbmanager.__class__.__name__
        else:
            return "Vector DB"
            
    def get_workspace_name(self) -> str:
        """
        Get workspace name from workspace data.
        
        Returns:
            str: Workspace name or 'Unknown'
        """
        if not self.has_workspace():
            return "Unknown"
            
        # Try different possible keys for workspace name
        possible_keys = ['name', 'workspace_name', 'title', 'display_name']
        for key in possible_keys:
            if key in self.workspace and self.workspace[key]:
                return str(self.workspace[key])
                
        return "Unknown"
        
    def get_db_config_type(self) -> str:
        """
        Get database configuration type if available.
        
        Returns:
            str: Database config type or 'Unknown'
        """
        if not self.has_db_config():
            return "Unknown"
            
        # Try to get database type from config
        if hasattr(self.sql_db_config, 'db_type'):
            return str(self.sql_db_config.db_type)
        elif isinstance(self.sql_db_config, dict):
            return self.sql_db_config.get('db_type', 'Unknown')
        else:
            return "SQL DB Config"
            
    def get_agent_count(self) -> int:
        """
        Get number of available agents.
        
        Returns:
            int: Number of agents or 0 if not available
        """
        if not self.has_agents():
            return 0
            
        # Try to count agents if agents_and_tools has countable agents
        agent_attrs = [
            'keyword_extraction_agent', 'sql_generation_agents', 
            'test_generation_agent', 'evaluator_agent',
            'question_validator_agent', 'question_translator_agent',
            'sql_explanation_agent'
        ]
        
        count = 0
        for attr in agent_attrs:
            if hasattr(self.agents_and_tools, attr):
                agent = getattr(self.agents_and_tools, attr)
                if agent is not None:
                    if isinstance(agent, list):
                        count += len(agent)
                    else:
                        count += 1
                        
        return count
        
    def are_services_ready(self) -> bool:
        """
        Check if all critical services are ready.
        
        Returns:
            bool: True if essential services are available
        """
        # At minimum, we need agents to function
        return self.has_agents()
        
    def get_generation_config_summary(self) -> str:
        """
        Get summary of generation configuration.
        
        Returns:
            str: Configuration summary
        """
        return f"Tests: {self.number_of_tests_to_generate}, SQLs: {self.number_of_sql_to_generate}"
        
    def get_services_summary(self) -> str:
        """
        Get a summary of external services for logging/display.
        
        Returns:
            str: Human-readable services summary
        """
        summary_parts = []
        
        if self.has_agents():
            agent_count = self.get_agent_count()
            summary_parts.append(f"Agents: {agent_count}")
            
        if self.has_vector_db():
            vdb_type = self.get_vector_db_type()
            summary_parts.append(f"VectorDB: {vdb_type}")
            
        if self.has_db_config():
            db_type = self.get_db_config_type()
            summary_parts.append(f"Database: {db_type}")
            
        if self.has_workspace():
            workspace_name = self.get_workspace_name()
            summary_parts.append(f"Workspace: {workspace_name}")
            
        config_summary = self.get_generation_config_summary()
        summary_parts.append(f"Config: {config_summary}")
        
        if not summary_parts:
            return "No external services available"
            
        readiness = "ready" if self.are_services_ready() else "not ready"
        return f"External services ({readiness}): {', '.join(summary_parts)}"