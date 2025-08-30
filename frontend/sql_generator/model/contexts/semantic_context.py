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
Semantic context for SystemState decomposition.

Contains data extracted through semantic analysis of the user's question,
including keywords, evidence, and SQL examples retrieved from vector databases.
"""

from typing import Any, List, Tuple
from pydantic import BaseModel, Field, validator
from frozenlist import FrozenList


class SemanticContext(BaseModel):
    """
    Semantic analysis results and context retrieval data.
    
    This context contains information extracted through AI-powered analysis
    of the user's question and similarity searches against vector databases.
    This data provides contextual hints and examples to guide SQL generation.
    
    Fields are grouped by their source:
    - Keyword Extraction: keywords (extracted from question analysis)
    - Vector DB Evidence: evidence, evidence_for_template (contextual hints)
    - Vector DB SQL Examples: sql_shots, sql_documents (similar SQL examples)
    """
    
    # Extracted keywords from question analysis
    keywords: List[str] = Field(
        default_factory=lambda: FrozenList([]),
        description="Keywords and entities extracted from the user's question"
    )
    
    # Evidence from vector database similarity search
    evidence: List[str] = Field(
        default_factory=lambda: FrozenList([]),
        description="Contextual evidence retrieved from vector database based on keywords"
    )
    
    evidence_for_template: str = Field(
        default="",
        description="Formatted evidence string ready for template injection"
    )
    
    # SQL examples from vector database similarity search
    sql_shots: List[Tuple[str, str, str]] = Field(
        default_factory=lambda: FrozenList([]),
        description="Similar SQL examples as tuples of (question, sql, hint)"
    )
    
    sql_documents: List[Any] = Field(
        default_factory=lambda: FrozenList([]),
        description="Actual SqlDocument objects from vector DB for template formatting"
    )
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True  # Allow SqlDocument objects and FrozenList
        validate_assignment = True  # Validate on field assignment
        
    @validator('keywords')
    def validate_keywords(cls, v):
        """Ensure keywords list doesn't contain empty strings"""
        if v is None:
            return FrozenList([])
        # Filter out empty or whitespace-only keywords
        cleaned = [kw.strip() for kw in v if kw and kw.strip()]
        return FrozenList(cleaned)
        
    @validator('evidence')
    def validate_evidence(cls, v):
        """Ensure evidence list doesn't contain empty strings"""
        if v is None:
            return FrozenList([])
        # Filter out empty or whitespace-only evidence
        cleaned = [ev.strip() for ev in v if ev and ev.strip()]
        return FrozenList(cleaned)
        
    @validator('sql_shots')
    def validate_sql_shots(cls, v):
        """Ensure SQL shots are properly formatted tuples"""
        if v is None:
            return FrozenList([])
        # Validate each tuple has exactly 3 elements and no empty strings
        validated = []
        for shot in v:
            if not isinstance(shot, tuple) or len(shot) != 3:
                continue  # Skip malformed tuples
            question, sql, hint = shot
            if question and sql:  # Require at least question and SQL
                validated.append((
                    question.strip(), 
                    sql.strip(), 
                    hint.strip() if hint else ""
                ))
        return FrozenList(validated)
        
    def has_keywords(self) -> bool:
        """
        Check if keywords have been extracted.
        
        Returns:
            bool: True if keywords are available
        """
        return len(self.keywords) > 0
        
    def has_evidence(self) -> bool:
        """
        Check if evidence has been retrieved.
        
        Returns:
            bool: True if evidence is available
        """
        return len(self.evidence) > 0
        
    def has_sql_examples(self) -> bool:
        """
        Check if SQL examples have been retrieved.
        
        Returns:
            bool: True if SQL examples are available
        """
        return len(self.sql_shots) > 0
        
    def get_keywords_string(self) -> str:
        """
        Get keywords as a space-separated string for vector DB queries.
        
        Returns:
            str: Space-separated keywords
        """
        return " ".join(self.keywords)
        
    def get_evidence_count(self) -> int:
        """
        Get the number of evidence items retrieved.
        
        Returns:
            int: Number of evidence items
        """
        return len(self.evidence)
        
    def get_sql_examples_count(self) -> int:
        """
        Get the number of SQL examples retrieved.
        
        Returns:
            int: Number of SQL examples
        """
        return len(self.sql_shots)
        
    def format_evidence_for_template(self) -> str:
        """
        Format evidence list as a clean markdown string for template use.
        
        Returns:
            str: Formatted evidence string
        """
        if not self.has_evidence():
            return ""
            
        formatted_items = []
        for i, evidence in enumerate(self.evidence, 1):
            formatted_items.append(f"- {evidence}")
            
        return "\n".join(formatted_items)
        
    def get_semantic_summary(self) -> str:
        """
        Get a summary of semantic context for logging/display.
        
        Returns:
            str: Human-readable semantic context summary
        """
        summary_parts = []
        
        if self.has_keywords():
            summary_parts.append(f"{len(self.keywords)} keywords")
            
        if self.has_evidence():
            summary_parts.append(f"{len(self.evidence)} evidence items")
            
        if self.has_sql_examples():
            summary_parts.append(f"{len(self.sql_shots)} SQL examples")
            
        if not summary_parts:
            return "No semantic context available"
            
        return f"Semantic context: {', '.join(summary_parts)}"