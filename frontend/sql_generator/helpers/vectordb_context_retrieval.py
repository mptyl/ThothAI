# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

"""
Helper functions for retrieving context from vector database.
Replaces the previous RetrieveContextTool class with simpler functions.
"""

from typing import Dict, List, Any
from helpers.vectordb_utils import query_vector_db_for_columns_data
from helpers.logging_config import get_logger
from helpers.dual_logger import log_info, log_error

logger = get_logger(__name__)


def retrieve_context_from_vectordb(
    question: str,
    evidence: str,
    keyword_list: List[str],
    vector_db,
    top_k: int = 10
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Retrieves context from vector database based on question, evidence and keywords.
    
    Args:
        question: The user's question
        evidence: Evidence or additional text
        keyword_list: List of keywords for search
        vector_db: Instance of the vector store to use for search
        top_k: Number of similar results to retrieve
        
    Returns:
        Dict[str, Dict[str, Dict[str, str]]]: Schema with retrieved descriptions
    """
    log_info("retrieve_context_from_vectordb called")
    logger.info(f"Executing context retrieval with {len(keyword_list)} keywords")
    
    try:
        # Find the most similar columns based on question, evidence, and keywords
        retrieved_columns = find_most_similar_columns(
            question=question,
            evidence=evidence,
            keywords=keyword_list,
            vector_db=vector_db,
            top_k=top_k
        )
        
        # Format the retrieved descriptions
        result = _format_retrieved_descriptions(retrieved_columns)
        log_info("retrieve_context_from_vectordb successfully executed")
        return result
    except Exception as e:
        log_error(f"retrieve_context_from_vectordb error: {str(e)}")
        raise


def find_relevant_columns(
    query: str,
    vector_db,
    top_k: int = 10
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Utility function to find relevant columns given a single query.
    
    Args:
        query: Search query
        vector_db: Instance of the vector store to use for search
        top_k: Number of results to return
        
    Returns:
        Dict[str, Dict[str, Dict[str, str]]]: Relevant columns with descriptions
    """
    try:
        retrieved = query_vector_db_for_columns_data(
            vector_db, query, top_k=top_k
        )
        return _format_retrieved_descriptions(retrieved)
    except Exception as e:
        logger.error(f"Error during search with query '{query}': {str(e)}")
        return {}


def find_most_similar_columns(
    question: str,
    evidence: str,
    keywords: List[str],
    vector_db,
    top_k: int
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Finds the most similar columns based on the question and evidence.
    
    Args:
        question: The user's question
        evidence: Evidence or additional text
        keywords: List of keywords for search
        vector_db: Instance of the vector store to use for search
        top_k: Number of similar columns to retrieve
        
    Returns:
        Dict[str, Dict[str, Dict[str, str]]]: Dictionary with the most similar columns and their descriptions
    """
    logger.debug("Searching for the most similar columns")
    tables_with_descriptions = {}
    
    for keyword in keywords:
        # Build the query with the keyword
        logger.debug(f"Search query: {keyword}")
        
        try:
            # Retrieve the columns most similar to the keyword
            retrieved_columns = query_vector_db_for_columns_data(
                vector_db, keyword, top_k=top_k
            )
            logger.debug(f"Retrieved {len(retrieved_columns)} columns for keyword '{keyword}'")
            for column in retrieved_columns:
                logger.debug(f"Column: {column}, Description: {retrieved_columns[column]}")
            
            # Add the retrieved descriptions
            tables_with_descriptions = _add_description(
                tables_with_descriptions, retrieved_columns
            )
            logger.debug(f"Added descriptions for keyword '{keyword}'")
            for table_name, columns in retrieved_columns.items():
                logger.debug(f"Table: {table_name}, Columns: {columns}")
        except Exception as e:
            logger.error(f"Error during search with keyword '{keyword}': {str(e)}")
    
    logger.debug(f"Found descriptions for {len(tables_with_descriptions)} tables")
    return tables_with_descriptions


def _add_description(
    tables_with_descriptions: Dict[str, Dict[str, Dict[str, str]]],
    retrieved_descriptions: Dict[str, Dict[str, Dict[str, str]]]
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Adds descriptions to tables from retrieved descriptions.
    
    Args:
        tables_with_descriptions: Current tables with descriptions
        retrieved_descriptions: Retrieved descriptions
        
    Returns:
        Updated tables with new descriptions
    """
    if retrieved_descriptions is None:
        logger.warning("No descriptions retrieved")
        return tables_with_descriptions
    
    for table_name, column_descriptions in retrieved_descriptions.items():
        if table_name not in tables_with_descriptions:
            tables_with_descriptions[table_name] = {}
        
        for column_name, description_info in column_descriptions.items():
            # Ensure description_info is a dictionary
            if not isinstance(description_info, dict):
                logger.warning(f"Description for {table_name}.{column_name} is not a dict, skipping: {description_info}")
                continue
            
            # Add 'table_name' and 'column_name' to the description_info if not present
            # This ensures the output format is consistent for the adapter check
            if "table_name" not in description_info:
                description_info["table_name"] = table_name
            if "column_name" not in description_info:
                description_info["column_name"] = column_name  # Ensure column_name is also part of the value
            
            if column_name not in tables_with_descriptions[table_name]:
                tables_with_descriptions[table_name][column_name] = description_info
            else:
                # If the column already exists, update only if the new score is higher
                current_score = tables_with_descriptions[table_name][column_name].get("score", 0)
                new_score = description_info.get("score", 0)
                
                current_score = 0 if current_score is None else current_score
                new_score = 0 if new_score is None else new_score
                
                if new_score > current_score:
                    tables_with_descriptions[table_name][column_name] = description_info
    
    return tables_with_descriptions


def _format_retrieved_descriptions(
    retrieved_columns: Dict[str, Dict[str, Dict[str, str]]]
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Formats the retrieved descriptions.
    Ensures 'table_name' and 'column_name' are present and removes the 'score' key.
    
    Args:
        retrieved_columns: Retrieved columns with descriptions
        
    Returns:
        Formatted descriptions
    """
    logger.debug("Formatting retrieved descriptions")
    for table_name, column_descriptions in retrieved_columns.items():
        logger.debug(f"Formatting descriptions for table {table_name}")
        for column_name, column_info in column_descriptions.items():
            if isinstance(column_info, dict):
                # Ensure standard keys are present for downstream tools
                if "table_name" not in column_info:
                    column_info["table_name"] = table_name
                if "column_name" not in column_info:
                    column_info["column_name"] = column_name
                column_info.pop("score", None)  # Remove score after potential use in _add_description
            else:
                logger.warning(f"column_info for {table_name}.{column_name} is not a dict during formatting: {column_info}")
    return retrieved_columns