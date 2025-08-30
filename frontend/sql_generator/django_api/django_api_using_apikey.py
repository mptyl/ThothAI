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
Django API functions for database schema operations
"""

import os
import logging
import httpx
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def get_db_tables(db_name: str = None) -> List[Dict[str, Any]]:
    """
    Get database tables from Django API
    
    Args:
        db_name: Database name
        
    Returns:
        List of tables with structure: [{"name": "table_name"}, ...]
    """
    try:
        django_server = os.getenv("DJANGO_SERVER", "http://localhost:8200")
        api_key = os.getenv("DJANGO_API_KEY")
        
        if not api_key:
            logger.warning("DJANGO_API_KEY not found, cannot fetch tables")
            return []
            
        if not db_name:
            logger.warning("No database name provided")
            return []
        
        url = f"{django_server}/api/sqldb/{db_name}/tables/"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        
        logger.info(f"Fetching tables from: {url}")
        
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            tables = response.json()
            logger.info(f"Successfully fetched {len(tables)} tables for database: {db_name}")
            return tables
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching tables for {db_name}: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        logger.error(f"Request error fetching tables for {db_name}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching tables for {db_name}: {str(e)}")
        return []

def get_table_info(db_name: str, table_name: str) -> Dict[str, Any]:
    """
    Get table information including description from Django API
    
    Args:
        db_name: Database name
        table_name: Table name
        
    Returns:
        Dictionary with table information including description
    """
    try:
        django_server = os.getenv("DJANGO_SERVER", "http://localhost:8200")
        api_key = os.getenv("DJANGO_API_KEY")
        
        if not api_key:
            logger.warning("DJANGO_API_KEY not found, cannot fetch table info")
            return {}
            
        if not db_name or not table_name:
            logger.warning(f"Missing parameters: db_name={db_name}, table_name={table_name}")
            return {}
        
        url = f"{django_server}/api/sqldb/{db_name}/table/{table_name}/"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        
        logger.info(f"Fetching table info from: {url}")
        
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            table_info = response.json()
            logger.info(f"Successfully fetched table info for: {db_name}.{table_name}")
            return table_info
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching table info for {db_name}.{table_name}: {e.response.status_code} - {e.response.text}")
        return {}
    except httpx.RequestError as e:
        logger.error(f"Request error fetching table info for {db_name}.{table_name}: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching table info for {db_name}.{table_name}: {str(e)}")
        return {}

def get_table_columns(db_name: str, table_name: str) -> List[Dict[str, Any]]:
    """
    Get table columns from Django API
    
    Args:
        db_name: Database name
        table_name: Table name
        
    Returns:
        List of columns with full column information
    """
    try:
        django_server = os.getenv("DJANGO_SERVER", "http://localhost:8200")
        api_key = os.getenv("DJANGO_API_KEY")
        
        if not api_key:
            logger.warning("DJANGO_API_KEY not found, cannot fetch columns")
            return []
            
        if not db_name or not table_name:
            logger.warning(f"Missing parameters: db_name={db_name}, table_name={table_name}")
            return []
        
        url = f"{django_server}/api/sqldb/{db_name}/table/{table_name}/columns/"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        
        logger.info(f"Fetching columns from: {url}")
        
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            columns = response.json()
            logger.info(f"Successfully fetched {len(columns)} columns for table: {db_name}.{table_name}")
            return columns
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching columns for {db_name}.{table_name}: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        logger.error(f"Request error fetching columns for {db_name}.{table_name}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching columns for {db_name}.{table_name}: {str(e)}")
        return []
