# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Base class for agent management functionality.
"""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from pydantic_ai import Agent

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
