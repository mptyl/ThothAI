# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from typing import List, Tuple
from thoth_qdrant import VectorStoreInterface, ThothType



def get_evidence_from_vector_db(keywords: List[str], vector_db: VectorStoreInterface) -> List[str]:
    """
    Retrieves the top 3 most relevant evidence based on keywords and formats them as a clean markdown list.

    Args:
        keywords (list): List of keywords extracted from the question
        vector_db (VectorStoreInterface): The vector database instance

    Returns:
        str: Formatted evidence as a clean markdown list
    """
    # Convert keywords list to a search query string
    query = " ".join(keywords) if keywords else ""
    
    similar_evidences = vector_db.search_similar(
        query=query,
        doc_type=ThothType.EVIDENCE,
        top_k=3,
        score_threshold=0.35)

    if not similar_evidences:
        return []

    # Remove duplicates by content comparison and filter out white text evidence
    seen_evidences = set()
    seen_normalized = set()  # Track normalized versions for better duplicate detection
    unique_evidences = []
    
    def normalize_evidence(text):
        """Normalize evidence text for duplicate detection"""
        # Remove extra whitespaces and convert to lowercase for comparison
        normalized = ' '.join(text.lower().split())
        # Remove trailing semicolons and punctuation that don't affect meaning
        normalized = normalized.rstrip(';.,')
        return normalized
    
    for evidence in similar_evidences:
        # evidence is already another EvidenceDocument from search_similar
        evidence_text = evidence.evidence.strip()  # Use evidence property directly
        # Skip evidence that are blank, null, or contain only white text
        if not evidence_text or evidence_text == "":
            continue
            
        # Check for duplicates using normalized version
        normalized = normalize_evidence(evidence_text)
        
        # Check if this is a substring of an existing evidence or vice versa
        is_duplicate = False
        for existing_norm in seen_normalized:
            if normalized in existing_norm or existing_norm in normalized:
                is_duplicate = True
                break
        
        if not is_duplicate and evidence_text not in seen_evidences:
            seen_evidences.add(evidence_text)
            seen_normalized.add(normalized)
            unique_evidences.append(evidence_text)

    return unique_evidences

def get_sql_from_vector_db(keywords: List[str], vector_db: VectorStoreInterface) -> List[Tuple[str, str, str]]:
    """
    Retrieves the top 5 most relevant SQL examples based on keywords and extracts question, SQL, and hint values.

    Args:
        keywords (list): List of keywords extracted from the question
        vector_db (VectorStoreInterface): The vector database instance

    Returns:
        list: List of tuples (question, sql, hint) with duplicates removed
    """
    # Convert keywords list to a search query string
    query = " ".join(keywords) if keywords else ""
    
    similar_sqls = vector_db.search_similar(
        query=query,
        doc_type=ThothType.SQL,
        top_k=5,
        score_threshold=0.45
    )
    
    if not similar_sqls:
        return []
    
    # Remove duplicates by SQL content comparison and extract values
    seen_sqls = set()
    unique_sql_tuples = []
    for sql_doc in similar_sqls:
        # Use both question and SQL as unique identifier to avoid duplicates
        sql_key = f"{sql_doc.question.strip().lower()}||{sql_doc.sql.strip().lower()}"
        if sql_key not in seen_sqls:
            seen_sqls.add(sql_key)
            # Extract question, sql, and hint from the SqlDocument
            question = sql_doc.question.strip() if hasattr(sql_doc, 'question') and sql_doc.question else ""
            sql = sql_doc.sql.strip() if hasattr(sql_doc, 'sql') and sql_doc.sql else ""
            hint = sql_doc.hint.strip() if hasattr(sql_doc, 'hint') and sql_doc.hint else ""
            unique_sql_tuples.append((question, sql, hint))
    
    return unique_sql_tuples
