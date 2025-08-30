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
Base class for agent management functionality.
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

class BaseAgentManager(ABC):
    """
    Abstract base class for agent management.
    Provides common functionality for agent initialization and configuration.
    """
    
    def __init__(self, workspace: Dict[str, Any]):
        self.workspace = workspace
        self.agents = {}
        
    @staticmethod
    def get_retries(agent_config: Optional[Dict[str, Any]], default: int = 3) -> int:
        """
        Get retries value from agent config, with fallback to default.
        
        Args:
            agent_config: Agent configuration dictionary
            default: Default number of retries
            
        Returns:
            Number of retries to use
        """
        if agent_config and 'retries' in agent_config and agent_config['retries'] is not None:
            return agent_config['retries']
        return default
    
    @abstractmethod
    def initialize(self):
        """Initialize all agents and configure their tools and validators."""
        pass
    
    @abstractmethod
    def _configure_tools_and_validators(self):
        """Configure tools and validators for the agents."""
        pass
