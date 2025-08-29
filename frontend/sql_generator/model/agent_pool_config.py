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
Agent pool configuration models for dynamic agent management.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AIModelConfig(BaseModel):
    """Configuration for an AI model."""
    id: int
    name: str
    specific_model: str
    context_size: Optional[int] = None
    basic_model: Optional[Dict[str, Any]] = None


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    id: int
    name: str
    agent_type: str
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1280, gt=0)
    timeout: float = Field(default=45.0, gt=0)
    retries: int = Field(default=5, ge=0)
    ai_model: Optional[AIModelConfig] = None


class LevelPools(BaseModel):
    """Agent pools organized by level."""
    basic: List[AgentConfig] = Field(default_factory=list)
    advanced: List[AgentConfig] = Field(default_factory=list)
    expert: List[AgentConfig] = Field(default_factory=list)


class AgentPoolConfig(BaseModel):
    """Complete agent pool configuration from Django backend."""
    sql_generators: LevelPools = Field(default_factory=LevelPools)
    test_generators: LevelPools = Field(default_factory=LevelPools)
    
    def get_sql_agents_by_level(self, level: str) -> List[AgentConfig]:
        """
        Get SQL generator agents for a specific level.
        
        Args:
            level: "basic", "advanced", or "expert"
            
        Returns:
            List of agent configurations for the specified level
        """
        level_lower = level.lower()
        if level_lower == "basic":
            return self.sql_generators.basic
        elif level_lower == "advanced":
            return self.sql_generators.advanced
        elif level_lower == "expert":
            return self.sql_generators.expert
        else:
            return self.sql_generators.basic  # Default to basic
    
    def get_test_agents_by_level(self, level: str) -> List[AgentConfig]:
        """
        Get test generator agents for a specific level.
        
        Args:
            level: "basic", "advanced", or "expert"
            
        Returns:
            List of agent configurations for the specified level
        """
        level_lower = level.lower()
        if level_lower == "basic":
            return self.test_generators.basic
        elif level_lower == "advanced":
            return self.test_generators.advanced
        elif level_lower == "expert":
            return self.test_generators.expert
        else:
            return self.test_generators.basic  # Default to basic
    
    def has_agents_for_level(self, agent_type: str, level: str) -> bool:
        """
        Check if there are agents available for a specific type and level.
        
        Args:
            agent_type: "sql" or "test"
            level: "basic", "advanced", or "expert"
            
        Returns:
            True if agents are available, False otherwise
        """
        if agent_type.lower() == "sql":
            agents = self.get_sql_agents_by_level(level)
        elif agent_type.lower() == "test":
            agents = self.get_test_agents_by_level(level)
        else:
            return False
        
        return len(agents) > 0
    
    def get_agent_count_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get a summary of agent counts by type and level.
        
        Returns:
            Dictionary with counts for each type and level
        """
        return {
            "sql_generators": {
                "basic": len(self.sql_generators.basic),
                "advanced": len(self.sql_generators.advanced),
                "expert": len(self.sql_generators.expert)
            },
            "test_generators": {
                "basic": len(self.test_generators.basic),
                "advanced": len(self.test_generators.advanced),
                "expert": len(self.test_generators.expert)
            }
        }