# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Unified template management system for ThothAI SQL Generator.
Provides a single, clean interface for loading and formatting all templates.
"""

import os
import itertools
from typing import Dict

from .agents_utils import get_project_root


class TemplateLoader:
    """
    Centralized template management system.
    All templates are accessed through this single class.
    """
    
    # Cache for loaded templates
    _cache: Dict[str, str] = {}
    
    @classmethod
    def load(cls, template_path: str) -> str:
        """
        Load a template by its path relative to the templates directory.
        
        Args:
            template_path: The path to the template file (relative to templates/)
            
        Returns:
            str: The raw template content
            
        Raises:
            FileNotFoundError: If the template file doesn't exist
        """
        if template_path in cls._cache:
            return cls._cache[template_path]
        
        full_path = os.path.join(get_project_root(), "templates", template_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Template not found: {full_path}")
        
        with open(full_path, "r") as file:
            content = file.read()
            cls._cache[template_path] = content
            return content
    
    @classmethod
    def format(cls, template_path: str, safe: bool = False, **kwargs) -> str:
        """
        Load and format a template with provided parameters.
        
        Args:
            template_path: The path to the template file (relative to templates/)
            safe: If True, use safe formatting that handles JSON blocks
            **kwargs: Parameters to substitute in the template
            
        Returns:
            str: The formatted template
        """
        template = cls.load(template_path)
        
        if safe:
            # For templates with JSON blocks or complex braces
            return cls._format_safe(template, list(kwargs.keys()), **kwargs)
        else:
            # Simple format for most templates
            return template.format(**kwargs)
    
    @classmethod
    def _format_safe(cls, template: str, placeholders: list, **kwargs) -> str:
        """
        Safely format a template with brace escaping for JSON blocks.
        
        Args:
            template: The raw template string
            placeholders: List of placeholder names to format
            **kwargs: Values to substitute
            
        Returns:
            str: The safely formatted template
        """
        # Step 1: escape all braces
        escaped = template.replace("{", "{{").replace("}", "}}")
        
        # Step 2: unescape only allowed placeholders
        for placeholder in placeholders:
            # Handle nested placeholders like dbmanager.db_type
            escaped = escaped.replace("{{" + placeholder + "}}", "{" + placeholder + "}")
        
        # Step 3: format with provided kwargs
        return escaped.format(**kwargs)
    
    @classmethod
    def clear_cache(cls):
        """Clear the template cache."""
        cls._cache.clear()


# =============================================================================
# UTILITY FUNCTIONS (keep these as they have complex logic)
# =============================================================================

def format_example_shots(selected_sqls) -> str:
    """
    Formats example shots for SQL generation templates using SqlDocuments from vector DB.
    
    Args:
        selected_sqls: List of SqlDocument objects from vector DB
    
    Returns:
        str: Formatted examples for LLM consumption (up to 5 examples)
    """
    examples = []
    
    for i, sql_doc in enumerate(selected_sqls[:5], 1):
        example = f"""### Example {i}

**Question**
{sql_doc.question if hasattr(sql_doc, 'question') and sql_doc.question else ''}

**Evidence**
{sql_doc.hint if hasattr(sql_doc, 'hint') and sql_doc.hint else ''}

**Answer**
{sql_doc.sql if hasattr(sql_doc, 'sql') and sql_doc.sql else ''}"""
        examples.append(example)
    
    if not examples:
        return "No SQL examples available from the vector database."
    
    return "\n\n".join(examples)


def clean_template_for_llm(raw_template: str) -> str:
    """
    Cleans and normalizes template text to make it more digestible for LLMs.
    
    Args:
        raw_template: The raw template string
        
    Returns:
        str: Cleaned template text
    """
    lines = raw_template.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        # Skip empty lines or lines with just decorative characters
        if not line or all(c in '=#-.*/' for c in line):
            continue

        # Remove redundant markdown headers if they don't add value
        if line.startswith('#') and len(line) < 5:
            continue

        # Normalize whitespace between sections
        if line.startswith('#'):
            if cleaned_lines:
                cleaned_lines.append('')

        # Remove redundant backticks from code block markers
        if line.startswith('```') and len(line) <= 4:
            cleaned_lines.append('```')
        else:
            cleaned_lines.append(line)

    # Join lines with proper spacing
    cleaned_text = '\n'.join(cleaned_lines)

    # Remove multiple consecutive blank lines
    cleaned_text = '\n'.join(line for line, _ in itertools.groupby(cleaned_text.splitlines()))

    return cleaned_text