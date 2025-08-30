# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Generic Template Loader

This module provides a unified template loading system to reduce code duplication.
"""

from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class TemplateLoader:
    """Generic template loader with caching support."""
    
    _cache: Dict[str, str] = {}
    
    @classmethod
    def get_template_path(cls, template_name: str, template_dir: str = "templates") -> Path:
        """
        Get the full path to a template file.
        
        Args:
            template_name: Name of the template file
            template_dir: Directory containing templates (relative to project root)
            
        Returns:
            Path object to the template file
        """
        from helpers.agents_utils import get_project_root
        project_root = get_project_root()
        return project_root / template_dir / template_name
    
    @classmethod
    def load_template(
        cls,
        template_name: str,
        template_dir: str = "templates",
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """
        Load a template file with optional variable substitution.
        
        Args:
            template_name: Name of the template file
            template_dir: Directory containing templates
            use_cache: Whether to use cached templates
            **kwargs: Variables to substitute in the template
            
        Returns:
            Template content with variables substituted
        """
        cache_key = f"{template_dir}/{template_name}"
        
        # Check cache first
        if use_cache and cache_key in cls._cache and not kwargs:
            logger.debug(f"Using cached template: {cache_key}")
            return cls._cache[cache_key]
        
        try:
            template_path = cls.get_template_path(template_name, template_dir)
            
            if not template_path.exists():
                logger.error(f"Template not found: {template_path}")
                return f"# Template {template_name} not found"
            
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Substitute variables if provided
            if kwargs:
                for key, value in kwargs.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in content:
                        content = content.replace(placeholder, str(value))
            
            # Cache if no variables were substituted
            if use_cache and not kwargs:
                cls._cache[cache_key] = content
                logger.debug(f"Cached template: {cache_key}")
            
            return content
            
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {str(e)}")
            return f"# Error loading template {template_name}: {str(e)}"
    
    @classmethod
    def clear_cache(cls):
        """Clear the template cache."""
        cls._cache.clear()
        logger.debug("Template cache cleared")


def load_system_template(template_name: str, **kwargs) -> str:
    """
    Load a system template from the system_templates directory.
    
    Args:
        template_name: Name of the template file
        **kwargs: Variables to substitute
        
    Returns:
        Template content
    """
    return TemplateLoader.load_template(
        template_name, 
        template_dir="templates/system_templates",
        **kwargs
    )


def load_user_template(template_name: str, **kwargs) -> str:
    """
    Load a user-facing template from the templates directory.
    
    Args:
        template_name: Name of the template file
        **kwargs: Variables to substitute
        
    Returns:
        Template content
    """
    return TemplateLoader.load_template(
        template_name,
        template_dir="templates",
        **kwargs
    )