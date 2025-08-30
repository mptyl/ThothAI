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
