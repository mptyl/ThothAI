# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from enum import Enum
from typing import List, Optional

class GeneratorType(Enum):
    """
    Enum that defines the different types of SQL generators available.
    
    Each generator type has a display name and a preferred pool index,
    which determines the starting position in the agents pool.
    """
    BASIC = ("Basic", 0)
    ADVANCED = ("Advanced", 1) 
    EXPERT = ("Expert", 2)
    
    def __init__(self, display_name: str, pool_index: int):
        self.display_name = display_name
        self.pool_index = pool_index
    
    @classmethod
    def from_string(cls, generator_name: str) -> 'GeneratorType':
        """
        Converts a string to the corresponding GeneratorType.
        
        Args:
            generator_name: Name of the generator as string
            
        Returns:
            GeneratorType: The corresponding generator type
        """
        if generator_name is None:
            return cls.BASIC
            
        # Handle both string and non-string inputs gracefully
        generator_str = str(generator_name).strip()
        
        for generator in cls:
            if generator.display_name == generator_str:
                return generator
        return cls.BASIC  # Safe default fallback
    
    def get_start_index(self, pool_size: int) -> int:
        """
        Calculates a safe starting index for the pool.
        
        Args:
            pool_size: Size of the agents pool
            
        Returns:
            int: Valid starting index (always < pool_size)
        """
        if pool_size <= 0:
            return 0
        return min(self.pool_index, pool_size - 1)
    
    def reorder_pool(self, agents_pool: List) -> List:
        """
        Reorders the agents pool based on the selected generator.
        
        Args:
            agents_pool: List of agents to reorder
            
        Returns:
            List: Reordered pool with preferred agent first
        """
        if not agents_pool:
            return agents_pool
            
        start_index = self.get_start_index(len(agents_pool))
        return agents_pool[start_index:] + agents_pool[:start_index]
    
    def __str__(self) -> str:
        """String representation returns the display name."""
        return self.display_name
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"GeneratorType.{self.name}('{self.display_name}', {self.pool_index})"
    
    def get_next_level(self) -> Optional['GeneratorType']:
        """Get the next escalation level."""
        escalation_chain = [GeneratorType.BASIC, GeneratorType.ADVANCED, GeneratorType.EXPERT]
        try:
            current_index = escalation_chain.index(self)
            if current_index < len(escalation_chain) - 1:
                return escalation_chain[current_index + 1]
            return None
        except ValueError:
            return None
    
    def can_escalate(self) -> bool:
        """Check if this level can escalate to a higher level."""
        return self.get_next_level() is not None
    
    def get_escalation_priority(self) -> int:
        """Get escalation priority (higher number = higher priority)."""
        return self.pool_index
