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
Agent pool management for organizing agents by functionality and level.
"""

from typing import List, Optional, Dict
from pydantic_ai import Agent
import random


class AgentPools:
    """
    Manages pools of agents organized by functionality and level.
    Supports Basic, Advanced, and Expert levels for both SQL and Test generation.
    """
    
    def __init__(self):
        # Legacy pools for backward compatibility
        self.test_unit_generation_agents_pool: List[Agent] = []
        self.sql_generation_agents_pool: List[Agent] = []
        
        # New level-based pools
        self.sql_pools: Dict[str, List[Agent]] = {
            'basic': [],
            'advanced': [],
            'expert': []
        }
        
        self.test_pools: Dict[str, List[Agent]] = {
            'basic': [],
            'advanced': [],
            'expert': []
        }
    
    # Legacy methods for backward compatibility
    def add_to_test_generation_pool(self, agent: Optional[Agent]):
        """Add an agent to the test generation pool (legacy)."""
        if agent is not None:
            self.test_unit_generation_agents_pool.append(agent)
    
    def get_test_generation_pool(self) -> List[Agent]:
        """Get the test generation agent pool (legacy)."""
        return self.test_unit_generation_agents_pool
    
    def add_to_sql_generation_pool(self, agent: Optional[Agent]):
        """Add an agent to the SQL generation pool (legacy).
        
        Args:
            agent: The agent to add to the SQL generation pool
        """
        if agent is not None:
            self.sql_generation_agents_pool.append(agent)
    
    def get_sql_generation_pool(self) -> List[Agent]:
        """Get the SQL generation agent pool (legacy).
        
        Returns:
            List[Agent]: List of SQL generation agents
        """
        return self.sql_generation_agents_pool
    
    # New level-based methods
    def add_sql_agent(self, agent: Agent, level: str):
        """
        Add an SQL agent to a specific level pool.
        
        Args:
            agent: The agent to add
            level: The level ("basic", "advanced", or "expert")
        """
        level_lower = level.lower()
        if level_lower in self.sql_pools and agent is not None:
            self.sql_pools[level_lower].append(agent)
            # Also add to legacy pool for compatibility
            self.sql_generation_agents_pool.append(agent)
    
    def add_test_agent(self, agent: Agent, level: str):
        """
        Add a test agent to a specific level pool.
        
        Args:
            agent: The agent to add
            level: The level ("basic", "advanced", or "expert")
        """
        level_lower = level.lower()
        if level_lower in self.test_pools and agent is not None:
            self.test_pools[level_lower].append(agent)
            # Also add to legacy pool for compatibility
            self.test_unit_generation_agents_pool.append(agent)
    
    def get_sql_agents_by_level(self, level: str) -> List[Agent]:
        """
        Get all SQL agents for a specific level.
        
        Args:
            level: The level ("basic", "advanced", or "expert")
            
        Returns:
            List of agents for the specified level
        """
        level_lower = level.lower()
        return self.sql_pools.get(level_lower, [])
    
    def get_test_agents_by_level(self, level: str) -> List[Agent]:
        """
        Get all test agents for a specific level.
        
        Args:
            level: The level ("basic", "advanced", or "expert")
            
        Returns:
            List of agents for the specified level
        """
        level_lower = level.lower()
        return self.test_pools.get(level_lower, [])
    
    def get_random_sql_agent(self, level: str) -> Optional[Agent]:
        """
        Get a random SQL agent from a specific level pool.
        
        Args:
            level: The level ("basic", "advanced", or "expert")
            
        Returns:
            A random agent from the pool or None if pool is empty
        """
        agents = self.get_sql_agents_by_level(level)
        return random.choice(agents) if agents else None
    
    def get_random_test_agent(self, level: str) -> Optional[Agent]:
        """
        Get a random test agent from a specific level pool.
        
        Args:
            level: The level ("basic", "advanced", or "expert")
            
        Returns:
            A random agent from the pool or None if pool is empty
        """
        agents = self.get_test_agents_by_level(level)
        return random.choice(agents) if agents else None
    
    def get_sql_agent_at_index(self, level: str, index: int) -> Optional[Agent]:
        """
        Get an SQL agent at a specific index from a level pool.
        
        Args:
            level: The level ("basic", "advanced", or "expert")
            index: The index in the pool
            
        Returns:
            The agent at the index or None if index is out of bounds
        """
        agents = self.get_sql_agents_by_level(level)
        if 0 <= index < len(agents):
            return agents[index]
        return None
    
    def get_test_agent_at_index(self, level: str, index: int) -> Optional[Agent]:
        """
        Get a test agent at a specific index from a level pool.
        
        Args:
            level: The level ("basic", "advanced", or "expert")
            index: The index in the pool
            
        Returns:
            The agent at the index or None if index is out of bounds
        """
        agents = self.get_test_agents_by_level(level)
        if 0 <= index < len(agents):
            return agents[index]
        return None
    
    def clear_all_pools(self):
        """Clear all agent pools."""
        self.test_unit_generation_agents_pool.clear()
        self.sql_generation_agents_pool.clear()
        for level in self.sql_pools:
            self.sql_pools[level].clear()
        for level in self.test_pools:
            self.test_pools[level].clear()
    
    def get_pool_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about the agent pools.
        
        Returns:
            Dictionary with counts for each pool and level
        """
        return {
            'sql': {
                'basic': len(self.sql_pools['basic']),
                'advanced': len(self.sql_pools['advanced']),
                'expert': len(self.sql_pools['expert']),
                'total': len(self.sql_generation_agents_pool)
            },
            'test': {
                'basic': len(self.test_pools['basic']),
                'advanced': len(self.test_pools['advanced']),
                'expert': len(self.test_pools['expert']),
                'total': len(self.test_unit_generation_agents_pool)
            }
        }
    
