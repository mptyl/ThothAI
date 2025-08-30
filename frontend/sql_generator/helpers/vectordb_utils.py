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
Utility per la gestione di operazioni vettoriali e database vettoriali

MIGRATED: Now uses native thoth-qdrant with multilingual support.
All embedding operations are handled transparently by the VectorStoreInterface.
"""

import logging
import os
from .dual_logger import log_info, log_error
from typing import Dict

from thoth_qdrant import VectorStoreInterface
from thoth_qdrant import ThothType


def query_vector_db_for_columns_data(
    document_store: VectorStoreInterface,
    query: str,
    top_k: int
) -> Dict[str, Dict[str,Dict[str,str]]]:
    """
    Interroga il database vettoriale per i documenti più rilevanti
    
    Args:
        document_store (ThothVectorBase): Database vettoriale
        query (str): Query di ricerca
        top_k (int): Numero di risultati da restituire
        
    Returns:
        Dict[str, List[Dict]]: Risultati della query con metadati
    """
    # Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-base-en-v1.5")
    try:
        # index = VectorStoreIndex.from_vector_store(document_store.vector_store)
        # retriever = VectorIndexRetriever(index=index, similarity_top_k=top_k)
        # query_engine = RetrieverQueryEngine(retriever=retriever)
        similar_columns=document_store.search_similar(query=query, doc_type=ThothType.COLUMN_NAME, top_k=top_k, score_threshold=0.35)
        #result = query_engine.query(query)
        log_info(f"Query executed successfully: {query}")

        table_description = {}
        for doc in similar_columns:
            table_name = doc.table_name.strip()
            original_column_name = doc.original_column_name.strip()
            column_name = doc.column_name.strip()
            column_description = doc.column_description.strip()
            value_description = doc.value_description.strip()

            if table_name not in table_description:
                table_description[table_name] = {}

            if original_column_name not in table_description[table_name]:
                table_description[table_name][original_column_name] = {
                    "column_name": column_name,
                    "original_column_name": original_column_name,
                    "column_description": column_description,
                    "value_description": value_description,
                    "score": doc.score if hasattr(doc, "score") else None,
                }

        log_info(f"Query results processed for query: {query}")
        return table_description

    except Exception as e:
        log_error(f"Error executing query: {query}, Error: {e}")
        raise e
