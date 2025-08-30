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

import os
import django
import logging
from typing import List, Dict

# Import new vector store plugin architecture
from thoth_qdrant import BaseThothDocument, ThothType, VectorStoreInterface

# Configure logging
logger = logging.getLogger(__name__)

# Configura l'ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ThothBE.settings")
django.setup()

from thoth_core.models import SqlDb


def query_vector_db(
    document_store: VectorStoreInterface, query: str, top_k: int
) -> List[BaseThothDocument]:
    """
    Queries the vector database for the most relevant documents based on the query.

    Args:
        document_store (ThothQdrant): The vector database to query.
        query (str): The query string to search for.
        top_k (int): The number of top results to return.

    Returns:
        List[BaseThothDocument]: A list of documents containing query results and metadata.
    """
    similars = document_store.search_similar(
        query=query, doc_type=ThothType.COLUMN_NAME, top_k=top_k, score_threshold=0.5
    )
    return similars


def get_vector_db_config(db: SqlDb) -> Dict:
    """
    Generates vector database configuration from SqlDb object.
    """
    vector_db = db.vector_db
    if not vector_db:
        raise ValueError(f"No vector database associated with SqlDb '{db.name}'")

    # Get collection name based on schema and db_name
    collection_name = db.get_collection_name()

    return {
        "collection_name": collection_name,
        "host": vector_db.host,
        "port": vector_db.port,
        "vector_db_type": vector_db.vect_type,
        # Add other necessary fields from your VectorDb model
    }


if __name__ == "__main__":
    db_name = "california_schools"
    try:
        # Get the SqlDb object from the database
        db = SqlDb.objects.get(name=db_name)

        # Get vector database configuration
        vector_db_config = get_vector_db_config(db)

        # Initialize the vector store using the new plugin system
        from thoth_qdrant import VectorStoreFactory

        document_store = VectorStoreFactory.create(
            "qdrant",
            collection=vector_db_config["collection_name"],
            host=vector_db_config["host"],
            port=vector_db_config["port"],
        )

        # Execute the query
        query = "schools"
        results = query_vector_db(document_store, query, 5)

        # Log results
        logger.info(f"\nRisultati per la query: '{query}'\n")
        for i, doc in enumerate(results, 1):
            logger.info(f"Risultato #{i}")
            logger.info(f"Tabella: {doc.table_name}")
            logger.info(f"Nome originale colonna: {doc.original_column_name}")
            logger.info(f"Colonna: {doc.column_name}")
            if doc.column_description:
                logger.info(f"Descrizione colonna: {doc.column_description}")
            if doc.value_description:
                logger.info(f"Descrizione valori: {doc.value_description}")
            if hasattr(doc, "score"):
                logger.info(f"Score: {doc.score:.4f}")
            logger.info("-" * 50)
    except SqlDb.DoesNotExist:
        logger.error(f"Database '{db_name}' non trovato.")
    except Exception as e:
        logger.error(f"Si è verificato un errore: {str(e)}", exc_info=True)
