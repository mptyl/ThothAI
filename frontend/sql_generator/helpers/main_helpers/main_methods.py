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

import json
import logging
import os
import traceback
from typing import Dict, Any

import httpx
from thoth_dbmanager import ThothDbFactory
from thoth_qdrant import VectorStoreFactory

from ..vectordb_config_utils import (
    build_vector_db_params,
    extract_vector_db_config_from_workspace,
    get_supported_vector_backends,
)
from agents.core.agent_manager import ThothAgentManager
from thoth_dbmanager import get_available_databases

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_database_plugins_initialized = False
_database_plugins_availability: Dict[str, bool] | None = None

def _sanitize_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(cfg, dict):
        return {}
    redacted: Dict[str, Any] = {}
    for key, value in cfg.items():
        key_lower = str(key).lower()
        if key_lower in {"password", "api_key", "token", "connection_string"}:
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted

def _is_positive(status_text: str, manager_obj: Any) -> bool:
    """Validate that a manager is properly initialized.
    
    Args:
        status_text: Status message from manager initialization
        manager_obj: The manager object (dbmanager or vdbmanager)
    
    Returns:
        True if manager is properly initialized, False otherwise
    """
    try:
        # Check manager object exists
        if manager_obj is None:
            logger.error("Manager object is None")
            return False
        
        # Check status text indicates successful initialization
        if not isinstance(status_text, str):
            logger.error(f"Status text is not a string: {type(status_text)}")
            return False
        
        status_lower = status_text.lower()
        
        # Check for positive indicators
        if "initialized" in status_lower:
            return True
        
        # Check for known error indicators
        if any(error_term in status_lower for error_term in ["error", "failed", "unavailable", "not found"]):
            logger.error(f"Manager initialization failed: {status_text}")
            return False
        
        # If status doesn't contain clear indicators, log warning
        logger.warning(f"Unclear manager status: {status_text}")
        return False
        
    except Exception as e:
        logger.error(f"Exception in _is_positive validation: {e}")
        return False

def build_not_ready_error_details(
    workspace_name: str,
    workspace_config: Dict[str, Any],
    sql_db_config: Dict[str, Any],
    dbmanager_status: str,
    vdbmanager_status: str,
    dbmanager: Any,
    vdbmanager: Any,
) -> str:
    """
    Build a detailed error message describing which services are not ready and why.
    Returns a plain text string to be returned as response body.
    """

    # Determine which components failed
    db_ok = _is_positive(dbmanager_status, dbmanager)
    vdb_ok = _is_positive(vdbmanager_status, vdbmanager)

    db_params_lines: list[str] = []
    if not db_ok:
        sql_cfg_sanitized = _sanitize_config(sql_db_config or {})
        preferred_db_keys = [
            "db_type", "db_mode", "db_name", "schema", "db_host", "db_port", "user_name", "language"
        ]
        shown_keys: list[str] = []
        for key in preferred_db_keys:
            if key in sql_cfg_sanitized:
                db_params_lines.append(f"  - {key}: {sql_cfg_sanitized[key]}")
                shown_keys.append(key)
        for key, value in sql_cfg_sanitized.items():
            if key not in shown_keys:
                db_params_lines.append(f"  - {key}: {value}")

    vdb_params_lines: list[str] = []
    if not vdb_ok:
        try:
            vdb_cfg = extract_vector_db_config_from_workspace(workspace_config)
            vdb_cfg_sanitized = _sanitize_config(vdb_cfg or {})
            preferred_vdb_keys = ["vect_type", "name", "host", "port", "database", "user", "path", "url", "tenant"]
            shown_keys: list[str] = []
            for key in preferred_vdb_keys:
                if key in vdb_cfg_sanitized:
                    vdb_params_lines.append(f"  - {key}: {vdb_cfg_sanitized[key]}")
                    shown_keys.append(key)
            for key, value in vdb_cfg_sanitized.items():
                if key not in shown_keys:
                    vdb_params_lines.append(f"  - {key}: {value}")
        except ValueError as e:
            # If vector DB config is missing, add a message about it
            vdb_params_lines.append(f"  - Error: {str(e)}")

    # Build a clear header that reflects exactly which components are not ready
    if not db_ok and not vdb_ok:
        header_line = "ERROR: DB Manager and Vector DB Manager are not ready."
    elif not db_ok:
        header_line = "ERROR: DB Manager is not ready."
    elif not vdb_ok:
        header_line = "ERROR: Vector DB Manager is not ready."
    else:
        header_line = "ERROR: One or more services are not ready."

    details_sections = [
        header_line,
        "",
        f"Workspace: {workspace_name}",
        f"DB Manager Status: {dbmanager_status}",
        f"Vector DB Manager Status: {vdbmanager_status}",
    ]

    # Explicit summary of missing setups so both appear when both are failing
    missing_lines: list[str] = []
    if not db_ok:
        missing_lines.append("- DB Manager setup missing")
    if not vdb_ok:
        missing_lines.append("- Vector DB Manager setup missing")
    if missing_lines:
        details_sections.extend([
            "",
            "Missing setup summary:",
            *missing_lines,
        ])

    if db_params_lines:
        details_sections.extend([
            "",
            "DB setup parameters (failed):",
            *db_params_lines,
        ])

    if vdb_params_lines:
        details_sections.extend([
            "",
            "Vector DB setup parameters (failed):",
            *vdb_params_lines,
        ])

    details_sections.extend([
        "",
        "Actions: Verify database type/backends and dependencies are installed, then retry.",
    ])

    return "\n".join(details_sections)

def initialize_database_plugins():
    """
    Initialize available database plugins by importing the plugins module
    and discovering which databases have their dependencies installed.
    
    Returns:
        Dict[str, bool]: Dictionary mapping database names to availability status
    """
    try:
        global _database_plugins_initialized, _database_plugins_availability

        # Avoid re-importing and re-logging if already initialized
        if _database_plugins_initialized and _database_plugins_availability is not None:
            return _database_plugins_availability

        # Explicitly import known plugin modules to ensure registration (as done in thoth_sl)
        loaded_plugins = []
        failed_plugins = []
        for module_name in [
            "thoth_dbmanager.plugins.sqlite",
            "thoth_dbmanager.plugins.postgresql",
            "thoth_dbmanager.plugins.mysql",
            "thoth_dbmanager.plugins.mariadb",
            "thoth_dbmanager.plugins.sqlserver",
            "thoth_dbmanager.plugins.oracle",
            "thoth_dbmanager.plugins.supabase",
        ]:
            try:
                __import__(module_name)
                loaded_plugins.append(module_name.split(".")[-1])
            except Exception:
                failed_plugins.append(module_name.split(".")[-1])

        logger.info(
            "Database plugins modules imported: "
            + (", ".join(loaded_plugins) if loaded_plugins else "none")
        )
        if failed_plugins:
            logger.info(
                "Database plugins modules unavailable (missing deps): " + ", ".join(failed_plugins)
            )
        
        # Get available databases based on installed dependencies
        available_databases = get_available_databases()
        
        # Log available plugins
        available_list = [db for db, available in available_databases.items() if available]
        unavailable_list = [db for db, available in available_databases.items() if not available]
        
        if available_list:
            logger.info(f"Available database plugins: {', '.join(available_list)}")
        if unavailable_list:
            logger.info(f"Unavailable database plugins (missing dependencies): {', '.join(unavailable_list)}")
            
        # Cache results and mark initialized
        _database_plugins_availability = available_databases
        _database_plugins_initialized = True

        return _database_plugins_availability
        
    except Exception as e:
        logger.error(f"Error initializing database plugins: {str(e)}")
        return {}

def initialize_vectordb_backend_plugins():
    """
    Initialize available vector database plugins by discovering 
    which backends have their dependencies installed.
    
    Returns:
        Dict[str, bool]: Dictionary mapping backend names to availability status
    """
    try:
        # Ask the installed factory for currently loadable backends
        loadable_backends = set(VectorStoreFactory.list_backends())

        # Cross-check against supported backends defined in our config utils
        supported_backends = set(get_supported_vector_backends())

        # Build availability map: True if loadable (dependencies installed), False otherwise
        availability = {backend: (backend in loadable_backends) for backend in supported_backends}

        available_list = [b for b, ok in availability.items() if ok]
        unavailable_list = [b for b, ok in availability.items() if not ok]

        if available_list:
            logger.info(f"Available vector database backends: {', '.join(sorted(available_list))}")
        if unavailable_list:
            logger.info(
                f"Unavailable vector database backends (missing dependencies): {', '.join(sorted(unavailable_list))}"
            )

        return availability

    except Exception as e:
        logger.error(f"Error initializing vector database plugins: {str(e)}")
        return {}

def _initialize_vdbmanager(workspace_config, sql_db_config):
    vdbmanager = None
    vdbmanager_status = "Not initialized"
        
    try:
        # Debug logging for Docker issue
        logger.info(f"DEBUG: workspace_config = {workspace_config}")
        logger.info(f"DEBUG: sql_db in workspace = {workspace_config.get('sql_db', {})}")
        
        # Check if vector_db exists in the nested structure
        sql_db = workspace_config.get('sql_db', {})
        vector_db = sql_db.get('vector_db')
        
        if vector_db is None:
            logger.warning("No vector_db configuration found in workspace, using defaults")
            logger.info(f"Available sql_db keys: {list(sql_db.keys()) if isinstance(sql_db, dict) else 'Not a dict'}")
        
        # Extract vector DB config from workspace
        vector_db_config = extract_vector_db_config_from_workspace(workspace_config)
        logger.info(f"DEBUG: Extracted vector_db_config = {vector_db_config}")
        
        vect_type = vector_db_config.get('vect_type', 'qdrant')
        
        # Additional validation for empty vect_type
        if not vect_type or vect_type == '':
            logger.warning("vect_type is empty, using default 'qdrant'")
            vect_type = 'qdrant'
            vector_db_config['vect_type'] = 'qdrant'
            
        logger.info(f"Initializing vector database: {vect_type}")
            
        # Build parameters for vector DB
        factory_params = build_vector_db_params(vector_db_config, vect_type)
        
        # Fix for macOS Docker networking: use 127.0.0.1 instead of localhost
        if factory_params.get('host') == 'localhost':
            logger.info("Converting 'localhost' to '127.0.0.1' for better Docker compatibility on macOS")
            factory_params['host'] = '127.0.0.1'
        
        # Additional debug info
        logger.info(f"DEBUG: Connection details - host={factory_params.get('host')}, port={factory_params.get('port', 6333)}")
        logger.info(f"DEBUG: factory_params = {factory_params}")
        # Get available vector database backends from factory discovery
        available_backends = initialize_vectordb_backend_plugins()
        
        # Check if the requested vector database backend is available
        if vect_type not in available_backends:
            logger.error(f"Unknown vector database backend: {vect_type}. Available backends: {list(available_backends.keys())}")
            vdbmanager_status = f"Unknown vector database backend: {vect_type}"
            return vdbmanager, vdbmanager_status
            
        if not available_backends[vect_type]:
            logger.error(f"Vector database backend '{vect_type}' is not available (missing dependencies)")
            vdbmanager_status = f"Vector database backend '{vect_type}' unavailable - missing dependencies"
            return vdbmanager, vdbmanager_status
            
        # Create vdbmanager instance using the plugin-aware factory
        # Add a small delay to avoid connection issues with Docker-based Qdrant
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to {vect_type} at {factory_params.get('host')}:{factory_params.get('port')} (attempt {attempt + 1}/{max_retries})...")
                vdbmanager = VectorStoreFactory.create(**factory_params)
                vdbmanager_status = f"{vect_type} vdbmanager initialized for {sql_db_config.get('db_name')}"
                logger.info(f"VDBManager initialized successfully: vdbmanager={vdbmanager is not None}")
                break
            except Exception as conn_error:
                logger.error(f"Connection attempt {attempt + 1} failed: {conn_error}")
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying in 1 second...")
                    time.sleep(1)
                else:
                    logger.error(f"All {max_retries} connection attempts failed")
                    raise conn_error
    except Exception as e:
        logger.error(f"Error initializing vdbmanager: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        vdbmanager_status = f"Error: {str(e)}"
    return vdbmanager,vdbmanager_status

async def _get_workspace_config(workspace_id: int) -> Dict[str, Any]:
    """
    Fetch workspace configuration from Django backend.
    
    Args:
        workspace_id: The ID of the workspace to load configuration for
        
    Returns:
        Dict containing workspace configuration from Django API
    """
    try:
        django_server = os.getenv("DJANGO_SERVER", os.getenv("DJANGO_BACKEND_URL", "http://localhost:8200"))
        api_key = os.getenv("DJANGO_API_KEY")
        
        logger.info(f"[_get_workspace_config] Django server: {django_server}")
        logger.info(f"[_get_workspace_config] API key found: {bool(api_key)}")
        
        if not api_key:
            logger.warning("DJANGO_API_KEY not found, workspace configuration may be limited")
            return {"error": "API key not configured"}
        
        url = f"{django_server}/api/workspace/id/{workspace_id}"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        
        logger.info(f"[_get_workspace_config] Fetching workspace config from: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            workspace_config = response.json()
            logger.info(f"Successfully loaded workspace: {workspace_config.get('name', 'Unknown')}")
            
            return workspace_config
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching workspace {workspace_id}: {e.response.status_code} - {e.response.text}")
        return {"error": f"Backend HTTP error: {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Request error fetching workspace {workspace_id}: {str(e)}")
        return {"error": f"Backend connection failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error fetching workspace {workspace_id}: {str(e)}")
        return {"error": f"Configuration error: {str(e)}"}

def _initialize_dbmanager(sql_db_config):
    """
    Initialize database manager using the plugin discovery system.
    Use the sql_db_config present in the selected workspace
    
    Args:
        sql_db_config: Dictionary containing database configuration
        
    Returns:
        Tuple of (dbmanager, dbmanager_status)
    """
    dbmanager = None
    dbmanager_status = "Not initialized"
        
    try:
        db_type = sql_db_config.get('db_type', '').lower()
        db_root_path = os.getenv("DB_ROOT_PATH", "/data/databases")
        db_mode = sql_db_config.get('db_mode', 'dev')
        
        # Ensure plugins are initialized (this will import the plugins module and register them)
        initialize_database_plugins()
        
        # Get available databases from plugin discovery
        available_databases = get_available_databases()
        
        # Check if the requested database type is available
        if db_type not in available_databases:
            logger.error(f"Unknown database type: {db_type}. Available types: {list(available_databases.keys())}")
            dbmanager_status = f"Unknown database type: {db_type}"
            return dbmanager, dbmanager_status
            
        if not available_databases[db_type]:
            logger.error(f"Database type '{db_type}' is not available (missing dependencies)")
            dbmanager_status = f"Database type '{db_type}' unavailable - missing dependencies"
            return dbmanager, dbmanager_status
        
        # Prepare common parameters
        common_params = {
            'db_type': db_type,
            'db_root_path': db_root_path,
            'db_mode': db_mode,
            'language': sql_db_config.get('language', 'en'),
        }
        
        # Add database-specific parameters based on type
        if db_type == 'sqlite':
            common_params.update({
                'database_name': sql_db_config.get('db_name', 'california_schools'),
            })
        elif db_type == 'postgresql':
            common_params.update({
                'host': sql_db_config.get('db_host', 'localhost'),
                'port': sql_db_config.get('db_port', 5432),
                'database': sql_db_config.get('db_name', 'california_schools'),
                'user': sql_db_config.get('user_name', 'postgres'),
                'password': sql_db_config.get('password', ''),
                'schema': sql_db_config.get('schema', 'public'),
            })
        elif db_type == 'mariadb':
            common_params.update({
                'host': sql_db_config.get('db_host', 'localhost'),
                'port': sql_db_config.get('db_port', 3306),
                'database': sql_db_config.get('db_name', 'california_schools'),
                'user': sql_db_config.get('user_name', 'root'),
                'password': sql_db_config.get('password', ''),
            })
        elif db_type == 'sqlserver':
            common_params.update({
                'host': sql_db_config.get('db_host', 'localhost'),
                'port': sql_db_config.get('db_port', 1433),
                'database': sql_db_config.get('db_name', 'california_schools'),
                'user': sql_db_config.get('user_name', 'sa'),
                'password': sql_db_config.get('password', ''),
            })
        
        # Create the dbmanager using the factory (which uses the plugin system)
        dbmanager = ThothDbFactory.create_manager(**common_params)
        dbmanager_status = f"{db_type.upper()} dbmanager initialized for {sql_db_config.get('db_name', 'unknown')}"
        logger.info(dbmanager_status)
        
    except Exception as e:
        logger.error(f"Error initializing dbmanager for {db_type}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        dbmanager_status = f"Error: {str(e)}"
        
    return dbmanager, dbmanager_status

async def _get_agent_pools(workspace_id: int):
    """
    Fetch agent pool configuration from Django backend.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        Dictionary containing agent pool configuration or None if fetch fails
    """
    try:
        django_server = os.environ.get('DJANGO_SERVER', 'http://localhost:8040')
        django_api_key = os.environ.get('DJANGO_API_KEY', '')
        
        if not django_api_key:
            logger.warning("DJANGO_API_KEY not set, agent pool fetch may fail")
        
        url = f"{django_server}/api/workspace/{workspace_id}/agent-pools/"
        
        headers = {
            'X-API-KEY': django_api_key,
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                pool_config = response.json()
                logger.info(f"Successfully fetched agent pools for workspace {workspace_id}")
                
                # Convert to AgentPoolConfig model
                from model.agent_pool_config import AgentPoolConfig
                return AgentPoolConfig(**pool_config)
            else:
                logger.error(f"Failed to fetch agent pools: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error fetching agent pools: {e}")
        return None

async def _get_workspace(workspace_id):
    try:
        logger.info(f"[_get_workspace] Fetching workspace {workspace_id} from Django backend...")
        workspace_config = await _get_workspace_config(workspace_id)
        logger.info(f"[_get_workspace] Retrieved workspace config: {json.dumps(workspace_config, indent=2) if workspace_config else 'None'}")
            
        if "error" in workspace_config:
            error_msg = f"Failed to fetch workspace {workspace_id}: {workspace_config['error']}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Backend connection failed for workspace {workspace_id}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    logger.info(f"[_get_workspace] Final workspace config being used: {json.dumps(workspace_config, indent=2)}")
    return workspace_config

async def _setup_dbmanager_and_agents(workspace_id: int, request) -> Dict[str, Any]:
    """
    Setup dbmanager and agent pool based on workspace ID.
    
    Args:
        workspace_id: The ID of the workspace to load configuration for
        request: The original SQL generation request
        
    Returns:
        Dict containing initialized dbmanager, vdbmanager, and agent pool with workspace details
    """
    from helpers.dual_logger import log_error, log_info
    
    try:
        logger.info(f"Setting up dbmanager, vdbmanager and agents for workspace {workspace_id}...")
        
        # Step 1: Fetch workspace configuration from Django backend
        workspace_config = await _get_workspace(workspace_id)
        if not workspace_config:
            error_msg = f"Failed to fetch workspace configuration for workspace_id={workspace_id}"
            log_error(error_msg)
            raise ValueError(error_msg)
        
        # Step 2: Fetch agent pool configuration from Django backend
        agent_pool_config = await _get_agent_pools(workspace_id)
        if not agent_pool_config:
            log_info(f"Warning: No agent pool configuration found for workspace {workspace_id}, using defaults")
        
        # Step 3: Extract key configuration details
        workspace_name = workspace_config.get('name', 'Unknown')
        sql_db_config = workspace_config.get('sql_db', {})
        
        if not sql_db_config:
            error_msg = f"No SQL database configuration found in workspace {workspace_name}"
            log_error(error_msg)
            raise ValueError(error_msg)
        
        functionality_level = request.functionality_level   

        # Initialize database manager
        dbmanager, dbmanager_status = _initialize_dbmanager(sql_db_config)
        if not dbmanager:
            error_details = {
                "workspace_id": workspace_id,
                "workspace_name": workspace_name,
                "sql_db_config": _sanitize_config(sql_db_config),
                "status": dbmanager_status
            }
            log_error(f"Failed to initialize dbmanager: {json.dumps(error_details)}")
        
        # Initialize vector database manager
        vdbmanager, vdbmanager_status = _initialize_vdbmanager(workspace_config, sql_db_config)
        if not vdbmanager:
            error_details = {
                "workspace_id": workspace_id,
                "workspace_name": workspace_name,
                "status": vdbmanager_status
            }
            log_error(f"Failed to initialize vdbmanager: {json.dumps(error_details)}")
        
        # Initialize agent manager
        try:
            agent_manager = ThothAgentManager(workspace_config, dbmanager, agent_pool_config).initialize()
            if not agent_manager:
                log_error(f"Agent manager initialization returned None for workspace {workspace_id}")
        except Exception as e:
            error_details = {
                "workspace_id": workspace_id,
                "workspace_name": workspace_name,
                "error": str(e)
            }
            log_error(f"Failed to initialize agent manager: {json.dumps(error_details)}")
            agent_manager = None
        
        return {
            "workspace_name": workspace_name,
            "functionality_level": functionality_level,
            "dbmanager": dbmanager,
            "dbmanager_status": dbmanager_status,
            "vdbmanager": vdbmanager,
            "vdbmanager_status": vdbmanager_status,
            "agent_manager": agent_manager,
            "workspace_config": workspace_config,
            "sql_db_config": sql_db_config
        }
        
    except Exception as e:
        error_details = {
            "workspace_id": workspace_id,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        log_error(f"Critical error in _setup_dbmanager_and_agents: {json.dumps(error_details)}")
        raise