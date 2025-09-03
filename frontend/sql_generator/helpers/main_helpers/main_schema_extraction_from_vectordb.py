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

# Unless required by applicable law or agreed to in writing, software
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
Helper functions for schema extraction from vector database
"""

from typing import Dict, Any
from model.system_state import SystemState
from helpers.vectordb_context_retrieval import find_most_similar_columns
from helpers.logging_config import get_logger

logger = get_logger(__name__)


def extract_schema_via_vector_db(state: SystemState) -> Dict[str, Dict[str, Any]]:
    """
    Estrae schema usando similarity search del database vettoriale.
    
    Utilizza le funzioni helper per trovare le colonne più simili basandosi su:
    - Question dell'utente
    - Evidences concatenate 
    - Keywords estratte
    
    Args:
        state: SystemState contenente question, keywords, evidences e vdbmanager
        
    Returns:
        Dict con schema estratto dal database vettoriale nel formato:
        {
            "table_name": {
                "table_description": "",  # Vector DB non fornisce questo
                "columns": {
                    "column_name": {
                        "original_column_name": str, 
                        "column_description": str,
                        "value_description": str
                    }
                }
            }
        }
    """
    logger.info("Starting schema extraction via vector database similarity search")
    
    # Log header at DEBUG level
    logger.debug("="*60)
    logger.debug("VECTOR SIMILARITY SEARCH STARTED")
    logger.debug("="*60)
    
    # Concatena le tre evidences come specificato nei requirements
    evidence = " ".join(state.evidence) if state.evidence else ""
    logger.debug(f"Question: {state.question}")
    logger.debug(f"Keywords: {state.keywords}")
    logger.debug(f"Concatenated evidence: {evidence[:200]}..." if len(evidence) > 200 else f"Concatenated evidence: {evidence}")
    
    # Parametri per la ricerca
    top_k = 10  # Numero di risultati simili da recuperare
    
    try:
        logger.debug("-"*60)
        logger.debug(f"Configuration:")
        logger.debug(f"  - Top K Results: {top_k}")
        logger.debug(f"  - Number of keywords: {len(state.keywords)}")
        logger.debug("-"*60)
        logger.debug(f"\nStarting vector DB search...")
        
        # Chiama la funzione helper per trovare le colonne più simili
        raw_schema_dict = find_most_similar_columns(
            question=state.question,
            evidence=evidence,
            keywords=state.keywords,
            vector_db=state.vdbmanager,
            top_k=top_k
        )
        
        # Converti il formato alla nuova struttura
        # Da: {"table": {"column": {info}}} 
        # A: {"table": {"table_description": "", "columns": {"column": {info}}}}
        schema_dict = {}
        total_columns = 0
        
        logger.debug("\nProcessing similarity search results:")
        
        for table_name, columns in raw_schema_dict.items():
            schema_dict[table_name] = {
                "table_description": "",  # Vector DB non fornisce table descriptions
                "columns": {}
            }
            
            logger.debug(f"\n  Table: {table_name}")
            
            for column_name, column_info in columns.items():
                # Mantieni solo le info disponibili dal vector DB
                cleaned_info = {
                    "original_column_name": column_info.get("original_column_name", column_name),
                    "column_description": column_info.get("column_description", ""),
                    "value_description": column_info.get("value_description", "")
                }
                schema_dict[table_name]["columns"][column_name] = cleaned_info
                total_columns += 1
                
                # Log column details at DEBUG level
                logger.debug(f"    ✓ {column_name}")
                if cleaned_info["column_description"]:
                    logger.debug(f"        Description: {cleaned_info['column_description'][:100]}{'...' if len(cleaned_info['column_description']) > 100 else ''}")
                if cleaned_info["value_description"]:
                    logger.debug(f"        Values: {cleaned_info['value_description'][:100]}{'...' if len(cleaned_info['value_description']) > 100 else ''}")
        
        logger.info(f"Schema extraction completed. Found {len(schema_dict)} tables")
        
        # Log summary at DEBUG level
        logger.debug("="*60)
        logger.debug("VECTOR SIMILARITY SEARCH COMPLETE")
        logger.debug(f"Total tables found: {len(schema_dict)}")
        logger.debug(f"Total columns retrieved: {total_columns}")
        logger.debug("="*60)
        
        return schema_dict
        
    except Exception as e:
        logger.error(f"Error during vector database schema extraction: {str(e)}")
        # Ritorna dizionario vuoto in caso di errore per non bloccare il flusso
        return {}


def format_schema_for_display(schema_dict: Dict[str, Dict[str, Any]]) -> str:
    """
    Formatta il dizionario dello schema in una stringa human-readable.
    
    Args:
        schema_dict: Dizionario dello schema da formattare
        
    Returns:
        Stringa formattata per visualizzazione
    """
    if not schema_dict:
        return "(none)"
    
    lines = []
    for table_name, table_info in schema_dict.items():
        lines.append(f"- Table: {table_name}")
        
        # Add table description if available
        table_description = table_info.get('table_description', '')
        if table_description:
            lines.append(f"  Description: {table_description}")
        
        columns_dict = table_info.get("columns", {})
        for column_name, column_info in columns_dict.items():
            lines.append(f"  - Column: {column_name}")
            
            if isinstance(column_info, dict):
                if column_info.get("column_description"):
                    lines.append(f"    Description: {column_info['column_description']}")
                if column_info.get("value_description"):
                    lines.append(f"    Values: {column_info['value_description']}")
                # Handle examples if present (for schema_with_examples)
                if "examples" in column_info and column_info["examples"]:
                    for example in column_info["examples"][:5]:  # Show max 5 examples
                        lines.append(f"    Example: {example}")
            
    return "\n".join(lines)