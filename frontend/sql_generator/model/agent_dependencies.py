# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Lightweight dependency classes for agents.

These classes provide focused, minimal dependencies for each agent type,
improving performance and reducing coupling compared to the full SystemState.
"""

from pydantic import BaseModel
from typing import List, Tuple, Dict, Any


class KeywordExtractionDeps(BaseModel):
    """
    Dependencies for keyword extraction agent.
    
    Contains only the essential information needed to extract keywords
    from user questions within the database scope.
    """
    question: str
    scope: str
    language: str


class ValidationDeps(BaseModel):
    """
    Dependencies for question validation agent.
    
    Contains information needed to validate if a question is appropriate
    for SQL generation within the given workspace context.
    """
    question: str
    scope: str
    language: str
    workspace: Dict[str, Any]


class TestGenerationDeps(BaseModel):
    """
    Dependencies for test generation agent.
    
    Contains information needed to generate test cases for SQL validation.
    """
    question: str
    schema_info: str
    evidence: List[str]
    sql_examples: List[Tuple[str, str, str]]  # (question, sql, hint)
    number_of_tests_to_generate: int = 5


class TranslationDeps(BaseModel):
    """
    Dependencies for question translation agent.
    
    Contains information needed to translate questions between languages.
    """
    question: str
    target_language: str
    scope: str


class SqlExplanationDeps(BaseModel):
    """
    Dependencies for SQL explanation agent.
    
    Contains information needed to explain generated SQL queries.
    """
    generated_sql: str
    question: str
    schema_info: str
    language: str = "English"


class AskHumanDeps(BaseModel):
    """
    Dependencies for ask human agent.
    
    Contains context needed when requesting human assistance.
    """
    question: str
    context: str
    issue_description: str