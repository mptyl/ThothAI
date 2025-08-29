# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Utility per la gestione delle configurazioni del progetto
"""

def get_vectordb_config(db: dict) -> dict:
    """
    Ottiene la configurazione del database vettoriale
    
    Args:
        db (dict): Dizionario con le informazioni del database
        
    Returns:
        dict: Configurazione del database vettoriale
    """
    # Use vector database name as collection name instead of schema+db_name combination
    index = db["vector_db"]["name"]
    host = db["vector_db"]["host"]
    port = db["vector_db"]["port"]
    vect_type = db["vector_db"]["vect_type"]
    return {
        "vector_db_type": vect_type,
        "host": host,
        "port": port,
        "collection_name": index
    }
