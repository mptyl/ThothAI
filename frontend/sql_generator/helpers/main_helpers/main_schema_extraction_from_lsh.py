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
Helper module for schema extraction phase (Phase 4) of the SQL generation process.
This module contains all methods related to schema extraction via LSH, vector similarity, and full schema retrieval.

MIGRATION STATUS: This file contains legacy code that uses direct embedding operations.
These should be migrated to use VectorStoreInterface for consistency with thoth-qdrant.
Current embedding calls will be deprecated in future versions.
"""

import logging
import difflib
import numpy as np
from typing import Dict, List, Any, Optional

from model.system_state import SystemState
from ..db_info import get_db_schema

logger = logging.getLogger(__name__)


def format_full_schema_for_display(full_schema: Dict[str, Dict[str, Any]]) -> str:
    """
    Format the full_schema state into a human-readable string.
    
    Args:
        full_schema: The complete schema dictionary from the database
                    With structure: {"table": {"table_description": str, "columns": {...}}}
        
    Returns:
        Formatted string for human-readable display
    """
    if not full_schema:
        return "(no schema available)"
    
    lines = []
    
    for table_name, table_info in full_schema.items():
        lines.append(f"\nTable: {table_name}")
        
        # Add table description if available
        table_description = table_info.get('table_description', '')
        if table_description:
            lines.append(f"  Description: {table_description}")
        
        columns_dict = table_info.get("columns", {})
        if not columns_dict:
            lines.append("  (no columns)")
            continue
            
        for column_name, column_info in columns_dict.items():
            column_display = f"  • {column_name}"
            
            # Add data type if available
            data_format = column_info.get('data_format', '')
            if data_format:
                column_display += f" ({data_format})"
            
            # Add primary key indicator
            if column_info.get('pk_field'):
                column_display += " [PK]"
                
            # Add foreign key indicator with details
            fk_field = column_info.get('fk_field', '')
            if fk_field:
                column_display += f" [FK] → {fk_field}"
                
            lines.append(column_display)
            
            # Add column description if available
            description = column_info.get('column_description', '')
            if description:
                lines.append(f"    Description: {description}")
                
            # Add value description if available
            value_desc = column_info.get('value_description', '')
            if value_desc:
                lines.append(f"    Values: {value_desc}")
    
    return "\n".join(lines)


def extract_schema_via_lsh(state: SystemState) -> tuple[Dict[str, List[str]], Dict[str, Dict[str, Any]]]:
    """
    Estrae schema usando similarity search LSH con parametri configurabili.
    
    Args:
        state: SystemState contenente keywords, evidences, dbmanager, workspace
        
    Returns:
        tuple: (similar_columns, schema_with_examples)
            schema_with_examples: {"table_name": {"table_description": "", "columns": {"col_name": {"examples": ["val1", ...]}}}} 
    """
    # Get configurable parameters from workspace settings
    setting = {}
    if isinstance(getattr(state, "workspace", None), dict):
        setting = state.workspace.get("setting", {}) or {}
    
    # Extract LSH configuration with improved defaults
    signature_size = setting.get("signature_size", 50)  # Better default than 30
    lsh_top_n = setting.get("lsh_top_n", 25)  # Better default than 10
    edit_distance_threshold = setting.get("edit_distance_threshold", 0.2)  # Better default than 0.3
    embedding_similarity_threshold = setting.get("embedding_similarity_threshold", 0.4)  # Better default than 0.6
    max_examples_per_column = setting.get("max_examples_per_column", 10)  # Better default than 5
    
    # Log configuration at DEBUG level with human-friendly formatting
    logger.debug("="*60)
    logger.debug("LSH SCHEMA EXTRACTION STARTED")
    logger.debug("="*60)
    logger.debug("Configuration:")
    logger.debug(f"  - Signature Size: {signature_size}")
    logger.debug(f"  - Top N Results: {lsh_top_n}")
    logger.debug(f"  - Edit Distance Threshold: {edit_distance_threshold:.1%}")
    logger.debug(f"  - Embedding Similarity Threshold: {embedding_similarity_threshold:.1%}")
    logger.debug(f"  - Max Examples per Column: {max_examples_per_column}")
    logger.debug("-"*60)
    
    logger.info(f"LSH Configuration from settings: signature_size={signature_size}, top_n={lsh_top_n}, "
                f"edit_distance={edit_distance_threshold:.2f}, embedding_similarity={embedding_similarity_threshold:.2f}, "
                f"max_examples={max_examples_per_column}")
    
    # Concatena le tre evidence come specificato nelle istruzioni
    evidence = " ".join(state.evidence) if state.evidence else ""
    
    # Get the schema from dbmanager using the correct function
    tentative_schema = get_db_schema(state.dbmanager.db_id, state.dbmanager.schema)
    
    # Semplifica lo schema per uso interno (copia da RetrieveEntityTool._simplify_schema)
    simplified_schema = {}
    for table_name, table_info in tentative_schema.items():
        simplified_schema[table_name] = list(table_info["columns"].keys())
    
    # Get embedding function from state's vdbmanager
    # VDB Manager is required for LSH-based schema extraction
    if not state.vdbmanager:
        error_msg = "VDB Manager not initialized. Cannot perform LSH-based schema extraction."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Create a wrapper to make vdbmanager compatible with the LSH code expectations
    class VDBEmbeddingWrapper:
        def __init__(self, vdb_manager):
            self.vdb_manager = vdb_manager
            # Access the embedding_manager directly from the QdrantNativeAdapter
            if hasattr(vdb_manager, 'embedding_manager'):
                self.embedding_manager = vdb_manager.embedding_manager
            else:
                raise ValueError("VDB Manager does not have an embedding_manager attribute")
            
        def encode(self, texts, **kwargs):
            """Encode texts using the configured VDB manager's embedding manager."""
            try:
                # Use the embedding_manager's encode method directly
                # It already handles both single strings and lists properly
                return self.embedding_manager.encode(texts, **kwargs)
            except Exception as e:
                error_msg = f"Failed to generate embeddings via vdbmanager: {e}"
                logger.error(error_msg)
                raise ValueError(error_msg)
    
    embedding_function = VDBEmbeddingWrapper(state.vdbmanager)
    
    # Parameters are now configured from workspace settings (see above)
    
    # 1. Get similar_columns (copy from _get_similar_columns)
    similar_columns = _get_similar_columns_lsh(
        keywords=state.keywords, 
        question=state.question, 
        evidence=evidence,
        simplified_schema=simplified_schema,
        embedding_function=embedding_function
    )
    
    # 2. Get schema_with_examples with configurable parameters
    logger.debug("\nPhase 2: Extracting example values via LSH...")
    logger.debug(f"Keywords to search: {state.keywords}")
    
    raw_schema_with_examples = _get_similar_entities_lsh(
        keywords=state.keywords,
        dbmanager=state.dbmanager,
        signature_size=signature_size,
        lsh_top_n=lsh_top_n,
        edit_distance_threshold=edit_distance_threshold,
        embedding_similarity_threshold=embedding_similarity_threshold,
        max_examples_per_column=max_examples_per_column,
        embedding_function=embedding_function
    )
    
    # Convert to new structure - LSH doesn't provide table descriptions, so leave empty
    schema_with_examples = {}
    total_columns_found = 0
    total_examples_found = 0
    
    for table_name, columns in raw_schema_with_examples.items():
        schema_with_examples[table_name] = {
            "table_description": "",  # LSH doesn't provide table descriptions
            "columns": {}
        }
        
        for column_name, examples_list in columns.items():
            # Store only examples - LSH doesn't provide other column metadata
            schema_with_examples[table_name]["columns"][column_name] = {
                "examples": examples_list
            }
            total_columns_found += 1
            total_examples_found += len(examples_list)
            
            # Log the found examples at DEBUG level
            if examples_list:
                logger.debug(f"  ✓ {table_name}.{column_name}:")
                # Show first 3 examples for brevity
                examples_to_show = examples_list[:3]
                examples_str = ", ".join([f'"{ex}"' if isinstance(ex, str) else str(ex) for ex in examples_to_show])
                if len(examples_list) > 3:
                    examples_str += f" ... ({len(examples_list)} total)"
                logger.debug(f"      Examples: [{examples_str}]")
    
    # Log extraction summary
    logger.debug("="*60)
    logger.debug("LSH EXTRACTION COMPLETE")
    logger.debug(f"Total tables found: {len(schema_with_examples)}")
    logger.debug(f"Total columns with examples: {total_columns_found}")
    logger.debug(f"Total example values extracted: {total_examples_found}")
    logger.debug("="*60)
    
    return similar_columns, schema_with_examples


def _get_similar_columns_lsh(
    keywords: List[str], 
    question: str, 
    evidence: str,
    simplified_schema: Dict[str, List[str]],
    embedding_function
) -> Dict[str, List[str]]:
    """
    Trova le colonne simili alle parole chiave date in base alla domanda e all'evidence.
    Copiato da RetrieveEntityTool._get_similar_columns sostituendo hint con evidence.
    """
    selected_columns = {}
    similar_columns = _get_similar_column_names_lsh(
        keywords=keywords, question=question, evidence=evidence,
        simplified_schema=simplified_schema, embedding_function=embedding_function
    )
    for table_name, column_name in similar_columns:
        if table_name not in selected_columns:
            selected_columns[table_name] = []
        if column_name not in selected_columns[table_name]:
            selected_columns[table_name].append(column_name)
    return selected_columns


def _get_similar_columns_no_embed_lsh(
    keywords: List[str],
    question: str,
    evidence: str,
    simplified_schema: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    Variante senza embedding: seleziona colonne usando solo matching testuale
    tra parole chiave/parti della domanda/evidence e nomi colonna.
    """
    schema = simplified_schema or {}
    if not schema:
        return {}
    # Prepara potenziali nomi da confrontare
    potential_column_names: List[str] = []
    all_tokens_sources = [
        *(keywords or []),
        *(question.split() if question else []),
        *(evidence.split() if evidence else []),
    ]
    for token in all_tokens_sources:
        token = token.strip()
        if not token:
            continue
        potential_column_names.append(token)
        column, value = _column_value_lsh(token)
        if column:
            potential_column_names.append(column)
        potential_column_names.extend(_extract_paranthesis_lsh(token))
        if " " in token:
            potential_column_names.extend(part.strip() for part in token.split())

    # Seleziona colonne con semplice matching
    selected_columns: Dict[str, List[str]] = {}
    for table, columns in schema.items():
        for column_name in columns:
            for candidate in potential_column_names:
                if _does_keyword_match_column_lsh(candidate, column_name):
                    selected_columns.setdefault(table, [])
                    if column_name not in selected_columns[table]:
                        selected_columns[table].append(column_name)
                    break
    return selected_columns


def _column_value_lsh(string: str) -> tuple[Optional[str], Optional[str]]:
    """
    Split a string into column and value parts if it contains '='.
    Copied from RetrieveEntityTool._column_value
    """
    if "=" in string:
        left_equal = string.find("=")
        first_part = string[:left_equal].strip()
        second_part = (
            string[left_equal + 1 :].strip()
            if len(string) > left_equal + 1
            else None
        )
        return first_part, second_part
    return None, None


def _extract_paranthesis_lsh(string: str) -> List[str]:
    """
    Estrae stringhe tra parentesi da una stringa data.
    Copiato da RetrieveEntityTool._extract_paranthesis
    """
    paranthesis_matches = []
    open_paranthesis = []
    for i, char in enumerate(string):
        if char == "(":
            open_paranthesis.append(i)
        elif char == ")" and open_paranthesis:
            start = open_paranthesis.pop()
            found_string = string[start : i + 1]
            if found_string:
                paranthesis_matches.append(found_string)
    return paranthesis_matches


def _does_keyword_match_column_lsh(
    keyword: str, column_name: str, threshold: float = 0.9
) -> bool:
    """
    Check if a keyword matches a column name based on similarity.
    Copied from RetrieveEntityTool._does_keyword_match_column
    """
    keyword = keyword.lower().replace(" ", "").replace("_", "").rstrip("s")
    column_name = column_name.lower().replace(" ", "").replace("_", "").rstrip("s")
    similarity = difflib.SequenceMatcher(None, column_name, keyword).ratio()
    return similarity >= threshold


def _get_similar_column_names_lsh(
    keywords: List[str], question: str, evidence: str,
    simplified_schema: Dict[str, List[str]], embedding_function
) -> List[tuple[str, str]]:
    """
    Trova nomi di colonne simili alle parole chiave date in base alla domanda e all'evidence.
    Copiato da RetrieveEntityTool._get_similar_column_names sostituendo hint con evidence.
    """
    schema = simplified_schema
    if not schema:
        return []  # Return an empty list if the schema is empty

    potential_column_names = []
    for keyword in keywords:
        keyword = keyword.strip()
        potential_column_names.append(keyword)

        column, value = _column_value_lsh(keyword)
        if column:
            potential_column_names.append(column)

        potential_column_names.extend(_extract_paranthesis_lsh(keyword))

        if " " in keyword:
            potential_column_names.extend(part.strip() for part in keyword.split())

    # Prepara la lista di stringhe da incorporare
    column_strings = [
        f"`{table}`.`{column}`"
        for table, columns in schema.items()
        for column in columns
    ]

    if not column_strings:
        return []  # Return an empty list if no columns were found

    question_evidence_string = f"{question} {evidence}"

    to_embed_strings = column_strings + [question_evidence_string]

    # Get the embeddings
    embeddings = embedding_function.encode(to_embed_strings)

    # Separa gli embedding
    column_embeddings = embeddings[:-1]  # Tutti tranne l'ultimo
    question_evidence_embedding = embeddings[-1]  # L'ultimo

    # Calcola le similarità
    similar_column_names = []
    for i, column_embedding in enumerate(column_embeddings):
        if i >= len(column_strings):  # Aggiungi controllo di sicurezza
            break
        table, column = column_strings[i].split(".")[0].strip("`"), column_strings[
            i
        ].split(".")[1].strip("`")
        for potential_column_name in potential_column_names:
            if _does_keyword_match_column_lsh(potential_column_name, column):
                similarity_score = np.dot(column_embedding, question_evidence_embedding)
                similar_column_names.append((table, column, similarity_score))

    similar_column_names.sort(key=lambda x: x[2], reverse=True)
    table_column_pairs = list(
        set([(table, column) for table, column, _ in similar_column_names])
    )
    return table_column_pairs


def _get_similar_entities_lsh(
    keywords: List[str], 
    dbmanager,
    signature_size: int,
    lsh_top_n: int,
    edit_distance_threshold: float,
    embedding_similarity_threshold: float,
    max_examples_per_column: int,
    embedding_function
) -> Dict[str, Dict[str, List[str]]]:
    """
    Get similar entities using LSH with configurable parameters.
    """
    to_search_values = _get_to_search_values_lsh(keywords)
    similar_entities_via_LSH = _get_similar_entities_via_LSH_lsh(
        to_search_values, dbmanager, signature_size, lsh_top_n
    )
    similar_entities_via_edit_distance = _get_similar_entities_via_edit_distance_lsh(
        similar_entities_via_LSH, edit_distance_threshold
    )
    similar_entities_via_embedding = _get_similar_entities_via_embedding_lsh(
        similar_entities_via_edit_distance, embedding_similarity_threshold, embedding_function
    )
    selected_values = {}
    for entity in similar_entities_via_embedding:
        table_name = entity["table_name"]
        column_name = entity["column_name"]
        if table_name not in selected_values:
            selected_values[table_name] = {}
        if column_name not in selected_values[table_name]:
            selected_values[table_name][column_name] = []
        selected_values[table_name][column_name].append(entity)    
    
    for table_name, column_data_map in selected_values.items():
        for column_name, entities_list in column_data_map.items():
            if not entities_list:
                selected_values[table_name][column_name] = []
                continue

            sorted_entities = sorted(
                entities_list,
                key=lambda x: (x.get("embedding_similarity", 0.0), x.get("edit_distance_similarity", 0.0)),
                reverse=True
            )
            
            top_n_examples = []
            seen_values = set()
            for entity in sorted_entities:
                if len(top_n_examples) >= max_examples_per_column:
                    break
                value = entity["similar_value"]
                if value not in seen_values:
                    top_n_examples.append(value)
                    seen_values.add(value)
            selected_values[table_name][column_name] = top_n_examples
            
    return selected_values


def _get_to_search_values_lsh(keywords: List[str]) -> List[Dict[str, str]]:
    """
    Estrae i valori da cercare dalle parole chiave.
    Copiato da RetrieveEntityTool._get_to_search_values
    """
    def get_substring_packet(keyword: str, substring: str) -> Dict[str, str]:
        return {"keyword": keyword, "substring": substring}

    to_search_values = []
    for keyword in keywords:
        keyword = keyword.strip()
        to_search_values.append(get_substring_packet(keyword, keyword))
        if " " in keyword:
            for i in range(len(keyword)):
                if keyword[i] == " ":
                    first_part = keyword[:i]
                    second_part = keyword[i + 1 :]
                    to_search_values.append(
                        get_substring_packet(keyword, first_part)
                    )
                    to_search_values.append(
                        get_substring_packet(keyword, second_part)
                    )
        evidence_column, evidence_value = _column_value_lsh(keyword)
        if evidence_value:
            to_search_values.append(get_substring_packet(keyword, evidence_value))
    to_search_values.sort(
        key=lambda x: (x["keyword"], len(x["substring"]), x["substring"]),
        reverse=True,
    )
    return to_search_values


def _get_similar_entities_via_LSH_lsh(
    substring_packets: List[Dict[str, str]], 
    dbmanager,
    signature_size: int,
    lsh_top_n: int
) -> List[Dict[str, Any]]:
    """
    Get similar entities via LSH with configurable parameters.
    """
    similar_entities_via_LSH = []
    
    logger.debug("\nStarting LSH queries...")
    logger.debug(f"Total keywords to search: {len(substring_packets)}")
    
    for packet in substring_packets:
        keyword = packet["keyword"]
        substring = packet["substring"]
        unique_similar_values = {}  # Initialize as empty
        
        logger.debug(f"\nSearching LSH for: '{substring}' (from keyword: '{keyword}')")
        
        try:
            unique_similar_values = dbmanager.query_lsh(
                keyword=substring, 
                signature_size=signature_size,  # Use configurable value
                top_n=lsh_top_n  # Use configurable value
            )
            
            # Log the results at DEBUG level
            if unique_similar_values:
                total_values = sum(len(values) for column_values in unique_similar_values.values() 
                                 for values in column_values.values())
                logger.debug(f"  Found {len(unique_similar_values)} tables with {total_values} matching values")
                
                for table_name, column_values in unique_similar_values.items():
                    for column_name, values in column_values.items():
                        logger.debug(f"    ✓ {table_name}.{column_name}: {len(values)} values")
                        # Show first few values
                        if values:
                            sample_values = values[:3]
                            values_str = ", ".join([f'"{v}"' if isinstance(v, str) else str(v) for v in sample_values])
                            if len(values) > 3:
                                values_str += f" ... ({len(values)} total)"
                            logger.debug(f"        Values: [{values_str}]")
            else:
                logger.debug("  No matches found")
                
        except Exception as e:
            logger.warning(f"Failed to query LSH for keyword '{substring}' (from '{keyword}'): {e}. Skipping LSH-based entity retrieval for this keyword.")
            logger.debug(f"  Error details: {str(e)}")
            continue  # Skip to next keyword instead of processing empty results

        for table_name, column_values in unique_similar_values.items():
            for column_name, values in column_values.items():
                for value in values:
                    similar_entities_via_LSH.append(
                        {
                            "keyword": keyword,
                            "substring": substring,
                            "table_name": table_name,
                            "column_name": column_name,
                            "similar_value": value,
                        }
                    )
    
    logger.debug(f"\nLSH query phase complete. Total entities found: {len(similar_entities_via_LSH)}")
    return similar_entities_via_LSH


def _get_similar_entities_via_edit_distance_lsh(
    similar_entities_via_LSH: List[Dict[str, Any]], edit_distance_threshold: float
) -> List[Dict[str, Any]]:
    """
    Filtra entità per edit distance.
    Copiato da RetrieveEntityTool._get_similar_entities_via_edit_distance
    """
    similar_entities_via_edit_distance_similarity = []
    for entity_packet in similar_entities_via_LSH:
        edit_distance_similarity = difflib.SequenceMatcher(
            None,
            entity_packet["substring"].lower(),
            entity_packet["similar_value"].lower(),
        ).ratio()
        if edit_distance_similarity >= edit_distance_threshold:
            entity_packet["edit_distance_similarity"] = edit_distance_similarity
            similar_entities_via_edit_distance_similarity.append(entity_packet)
    return similar_entities_via_edit_distance_similarity


def _get_similar_entities_via_embedding_lsh(
    similar_entities_via_edit_distance: List[Dict[str, Any]], 
    embedding_similarity_threshold: float, embedding_function
) -> List[Dict[str, Any]]:
    """
    Filtra entità per embedding similarity.
    Copiato da RetrieveEntityTool._get_similar_entities_via_embedding
    """
    logger.debug(f"\nFiltering by embedding similarity (threshold: {embedding_similarity_threshold:.1%})...")
    logger.debug(f"Candidates to evaluate: {len(similar_entities_via_edit_distance)}")
    
    similar_values_dict = {}
    to_embed_strings = []
    for entity_packet in similar_entities_via_edit_distance:
        keyword = entity_packet["keyword"]
        substring = entity_packet["substring"]
        similar_value = entity_packet["similar_value"]
        if keyword not in similar_values_dict:
            similar_values_dict[keyword] = {}
        if substring not in similar_values_dict[keyword]:
            similar_values_dict[keyword][substring] = []
            to_embed_strings.append(substring)
        similar_values_dict[keyword][substring].append(entity_packet)
        to_embed_strings.append(similar_value)

    all_embeddings = embedding_function.encode(to_embed_strings)
    similar_entities_via_embedding_similarity = []
    index = 0
    
    # Track statistics for logging
    passed_count = 0
    failed_count = 0
    
    for keyword, substring_dict in similar_values_dict.items():
        for substring, entity_packets in substring_dict.items():
            substring_embedding = all_embeddings[index]
            index += 1
            similar_values_embeddings = all_embeddings[
                                        index : index + len(entity_packets)
                                        ]
            index += len(entity_packets)
            similarities = np.dot(similar_values_embeddings, substring_embedding)
            
            # Log similarity scores for this substring
            logger.debug(f"\n  Embedding similarity for '{substring}':")
            
            for i, entity_packet in enumerate(entity_packets):
                sim_score = similarities[i]
                passed = sim_score >= embedding_similarity_threshold
                
                if passed:
                    entity_packet["embedding_similarity"] = sim_score
                    similar_entities_via_embedding_similarity.append(entity_packet)
                    passed_count += 1
                    logger.debug(f"    ✓ {entity_packet['table_name']}.{entity_packet['column_name']} = "
                               f"'{entity_packet['similar_value'][:30]}{'...' if len(entity_packet['similar_value']) > 30 else ''}' "
                               f"(similarity: {sim_score:.3f})")
                else:
                    failed_count += 1
                    
    logger.debug(f"\nEmbedding similarity filtering complete:")
    logger.debug(f"  - Passed: {passed_count} entities")
    logger.debug(f"  - Filtered out: {failed_count} entities")
    
    return similar_entities_via_embedding_similarity