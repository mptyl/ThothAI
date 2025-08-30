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
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib

from pydantic import BaseModel, Field
from helpers.dual_logger import log_error

logger = logging.getLogger(__name__)


class PaginationRequest(BaseModel):
    """Request model for paginated query execution"""
    workspace_id: int
    sql: str
    page: int = Field(default=0, ge=0)
    page_size: int = Field(default=10, ge=1, le=1000)  # Increased for export operations
    sort_model: Optional[List[Dict[str, Any]]] = None
    filter_model: Optional[Dict[str, Any]] = None


class PaginationResponse(BaseModel):
    """Response model for paginated query results"""
    data: List[Dict[str, Any]]
    total_rows: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    columns: List[str]
    error: Optional[str] = None


@dataclass
class QueryCacheEntry:
    """Cache entry for query results"""
    result: Any
    timestamp: datetime
    ttl: timedelta = timedelta(minutes=5)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.timestamp + self.ttl


class PaginatedQueryService:
    """Service for executing paginated SQL queries with caching and optimization"""
    
    def __init__(self, dbmanager):
        """
        Initialize the paginated query service
        
        Args:
            dbmanager: Database manager instance with connection info
        """
        self.dbmanager = dbmanager
        self._query_cache: Dict[str, QueryCacheEntry] = {}
        self._count_cache: Dict[str, QueryCacheEntry] = {}
        
    def _get_cache_key(self, sql: str, workspace_id: int, **kwargs) -> str:
        """Generate a cache key for a query"""
        cache_data = f"{workspace_id}:{sql}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _extract_columns_from_sql(self, sql: str) -> List[str]:
        """Extract column names from SQL SELECT statement"""
        columns = []
        
        # Check if it's a simple COUNT(*) query without other columns
        if re.match(r'^\s*SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM', sql, re.IGNORECASE):
            return ['count']
            
        # Try to extract columns from SELECT clause
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            columns_str = match.group(1)
            
            # Parse columns respecting quotes and parentheses
            current_col = ""
            paren_depth = 0
            quote_char = None
            i = 0
            
            while i < len(columns_str):
                char = columns_str[i]
                
                # Handle quotes - anything inside quotes is part of a field name
                if quote_char is None and char in ['"', "'"]:
                    quote_char = char
                    current_col += char
                elif quote_char and char == quote_char:
                    quote_char = None
                    current_col += char
                elif quote_char:
                    # Inside quotes - just add the character
                    current_col += char
                elif char == '(':
                    paren_depth += 1
                    current_col += char
                elif char == ')':
                    paren_depth -= 1
                    current_col += char
                elif char == ',' and paren_depth == 0:
                    # Found a column separator at the top level
                    if current_col.strip():
                        columns.append(self._process_column_definition(current_col.strip()))
                    current_col = ""
                else:
                    current_col += char
                
                i += 1
            
            # Don't forget the last column
            if current_col.strip():
                columns.append(self._process_column_definition(current_col.strip()))
        
        return columns if columns else ['column_1']
    
    def _process_column_definition(self, col_def: str) -> str:
        """Process a single column definition to extract the column name or alias"""
        col_def = col_def.strip()
        
        # Check for alias with AS
        if ' AS ' in col_def.upper():
            # Find the last occurrence of AS (case-insensitive)
            as_index = col_def.upper().rfind(' AS ')
            alias = col_def[as_index + 4:].strip()
            # Remove quotes from alias if present
            return alias.strip('"').strip("'")
        
        # Check for implicit alias (expression followed by identifier without AS)
        # This is tricky and we'll skip complex detection
        
        # For quoted field names (like T1."Field Name"), extract just the field name
        if '"' in col_def:
            # Extract content between the last pair of quotes
            import re
            quoted_pattern = r'"([^"]+)"'
            matches = re.findall(quoted_pattern, col_def)
            if matches:
                # Return the last quoted string (the field name)
                return matches[-1]
        
        # For expressions with table prefixes (T1.field)
        if '.' in col_def and not any(op in col_def for op in ['(', '/', '*', '+', '-']):
            # Simple table.column reference
            parts = col_def.split('.')
            # Return the last part (column name), removing quotes
            return parts[-1].strip().strip('"').strip("'")
        
        # For functions or complex expressions without alias
        if any(func in col_def.upper() for func in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN(', 'CAST(']):
            # This is a function without an alias - use a generic name
            return 'result'
        
        # For arithmetic expressions without alias
        if any(op in col_def for op in ['/', '*', '+', '-']) and '(' in col_def:
            return 'result'
        
        # Default: return as-is, removing quotes
        return col_def.strip('"').strip("'")
    
    def _apply_sorting(self, sql: str, sort_model: Optional[List[Dict[str, Any]]]) -> str:
        """Apply sorting to SQL query based on AG-Grid sort model"""
        # If no sort_model from AG-Grid, return SQL unchanged
        if not sort_model or len(sort_model) == 0:
            return sql
        
        # Check if SQL already has an ORDER BY clause
        # This regex captures the ORDER BY content more accurately
        order_by_match = re.search(r'\s+ORDER\s+BY\s+(.+?)(?=\s+LIMIT|\s*$)', sql, flags=re.IGNORECASE | re.DOTALL)
        
        if order_by_match:
            # SQL already has ORDER BY - we need to modify it based on AG-Grid sorting
            # Parse existing ORDER BY to understand current sorting
            # For now, we'll replace the entire ORDER BY with AG-Grid's sorting
            # This is because AG-Grid manages the complete sort state
            
            sql_without_order = re.sub(r'\s+ORDER\s+BY\s+.+?(?=\s+LIMIT|\s*$)', '', sql, flags=re.IGNORECASE | re.DOTALL)
            
            # Build new ORDER BY based on sort_model from AG-Grid
            order_by_parts = []
            for sort_item in sort_model:
                col_id = sort_item.get('colId', '')
                sort_direction = sort_item.get('sort', 'asc').upper()
                if col_id and col_id not in ['', 'undefined', '__selection__']:
                    # Handle column names with spaces or special characters
                    if ' ' in col_id or '-' in col_id:
                        col_id_safe = f'"{col_id}"'
                    else:
                        col_id_safe = re.sub(r'[^\w\.]', '', col_id)
                    
                    # Add NULLS LAST for consistency with original query
                    nulls_clause = 'NULLS LAST' if sort_direction == 'ASC' else 'NULLS FIRST'
                    order_by_parts.append(f"{col_id_safe} {sort_direction} {nulls_clause}")
            
            if order_by_parts:
                if ' LIMIT ' in sql_without_order.upper():
                    parts = re.split(r'(\s+LIMIT\s+)', sql_without_order, flags=re.IGNORECASE)
                    sql = parts[0] + f" ORDER BY {', '.join(order_by_parts)}" + ''.join(parts[1:])
                else:
                    sql_without_order = sql_without_order.strip()
                    if sql_without_order.endswith(';'):
                        # Insert ORDER BY before the semicolon
                        sql = sql_without_order[:-1] + f" ORDER BY {', '.join(order_by_parts)};"
                    else:
                        sql = f"{sql_without_order} ORDER BY {', '.join(order_by_parts)}"
            else:
                # No sorting from AG-Grid, keep original ORDER BY
                sql = sql
        else:
            # No existing ORDER BY, add new one if we have sort_model
            order_by_parts = []
            for sort_item in sort_model:
                col_id = sort_item.get('colId', '')
                sort_direction = sort_item.get('sort', 'asc').upper()
                if col_id and col_id not in ['', 'undefined', '__selection__']:
                    if ' ' in col_id or '-' in col_id:
                        col_id_safe = f'"{col_id}"'
                    else:
                        col_id_safe = re.sub(r'[^\w\.]', '', col_id)
                    
                    # Add NULLS LAST for consistency
                    nulls_clause = 'NULLS LAST' if sort_direction == 'ASC' else 'NULLS FIRST'
                    order_by_parts.append(f"{col_id_safe} {sort_direction} {nulls_clause}")
            
            if order_by_parts:
                if ' LIMIT ' in sql.upper():
                    parts = re.split(r'(\s+LIMIT\s+)', sql, flags=re.IGNORECASE)
                    sql = parts[0] + f" ORDER BY {', '.join(order_by_parts)}" + ''.join(parts[1:])
                else:
                    sql = sql.strip()
                    if sql.endswith(';'):
                        # Insert ORDER BY before the semicolon
                        sql = sql[:-1] + f" ORDER BY {', '.join(order_by_parts)};"
                    else:
                        sql = f"{sql} ORDER BY {', '.join(order_by_parts)}"
        
        return sql
    
    def _apply_filters(self, sql: str, filter_model: Optional[Dict[str, Any]]) -> str:
        """Apply filters to SQL query based on AG-Grid filter model"""
        if not filter_model or len(filter_model) == 0:
            return sql
        
        # Build WHERE conditions for filters
        filter_conditions = []
        for column, filter_config in filter_model.items():
            if isinstance(filter_config, dict) and column != '__selection__':
                filter_type = filter_config.get('type', 'contains')
                filter_value = filter_config.get('filter', '')
                
                if filter_value:
                    # Handle column names with spaces or special characters
                    if ' ' in column or '-' in column:
                        # Quote the column name for SQL
                        column_safe = f'"{column}"'
                    else:
                        # Sanitize column name
                        column_safe = re.sub(r'[^\w\.]', '', column)
                    
                    # Escape single quotes in filter value
                    filter_value = filter_value.replace("'", "''")
                    
                    # Build condition based on filter type
                    if filter_type == 'contains':
                        filter_conditions.append(f"{column_safe} LIKE '%{filter_value}%'")
                    elif filter_type == 'equals':
                        filter_conditions.append(f"{column_safe} = '{filter_value}'")
                    elif filter_type == 'notEquals':
                        filter_conditions.append(f"{column_safe} != '{filter_value}'")
                    elif filter_type == 'startsWith':
                        filter_conditions.append(f"{column_safe} LIKE '{filter_value}%'")
                    elif filter_type == 'endsWith':
                        filter_conditions.append(f"{column_safe} LIKE '%{filter_value}'")
        
        if filter_conditions:
            # Check if SQL already has WHERE clause
            if 'WHERE' in sql.upper():
                # Add conditions to existing WHERE clause
                sql = sql.replace('WHERE', f"WHERE ({' AND '.join(filter_conditions)}) AND ", 1)
            else:
                if 'ORDER BY' in sql.upper():
                    sql = re.sub(r'(\s+ORDER\s+BY)', f" WHERE {' AND '.join(filter_conditions)}\\1", sql, flags=re.IGNORECASE)
                elif 'LIMIT' in sql.upper():
                    sql = re.sub(r'(\s+LIMIT)', f" WHERE {' AND '.join(filter_conditions)}\\1", sql, flags=re.IGNORECASE)
                else:
                    sql = sql.strip()
                    if sql.endswith(';'):
                        # Insert WHERE before the semicolon
                        sql = sql[:-1] + f" WHERE {' AND '.join(filter_conditions)};"
                    else:
                        sql = f"{sql} WHERE {' AND '.join(filter_conditions)}"
        
        return sql
    
    def _extract_limit_from_sql(self, sql: str) -> Optional[int]:
        """Extract LIMIT value from SQL query if present"""
        limit_match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            return int(limit_match.group(1))
        return None
    
    def _apply_pagination(self, sql: str, page: int, page_size: int, original_limit: Optional[int] = None) -> Tuple[str, int]:
        """Apply LIMIT and OFFSET to SQL query for pagination.
        
        Returns:
            Tuple of (paginated_sql, effective_limit)
        """
        offset = page * page_size
        
        def _insert_pagination_clause(sql_query: str, limit_clause: str) -> str:
            """Helper function to insert LIMIT/OFFSET before the final semicolon if present"""
            sql_query = sql_query.strip()
            if sql_query.endswith(';'):
                return sql_query[:-1] + f" {limit_clause};"
            else:
                # No semicolon, just append
                return f"{sql_query} {limit_clause}"
        
        if original_limit is not None:
            if offset >= original_limit:
                # Return a query that will return no results
                sql_without_limit = re.sub(r'\s+LIMIT\s+\d+(\s+OFFSET\s+\d+)?', '', sql, flags=re.IGNORECASE)
                paginated_sql = _insert_pagination_clause(sql_without_limit, "LIMIT 0")
                return paginated_sql, 0
            
            effective_limit = min(page_size, original_limit - offset)
            
            sql_without_limit = re.sub(r'\s+LIMIT\s+\d+(\s+OFFSET\s+\d+)?', '', sql, flags=re.IGNORECASE)
            paginated_sql = _insert_pagination_clause(sql_without_limit, f"LIMIT {effective_limit} OFFSET {offset}")
            return paginated_sql, effective_limit
        else:
            sql = re.sub(r'\s+LIMIT\s+\d+(\s+OFFSET\s+\d+)?', '', sql, flags=re.IGNORECASE)
            paginated_sql = _insert_pagination_clause(sql, f"LIMIT {page_size} OFFSET {offset}")
            return paginated_sql, page_size
    
    def _get_total_count(self, sql: str, workspace_id: int, original_limit: Optional[int] = None) -> int:
        """Get total count of rows for a query, respecting original LIMIT if present"""
        # Check cache first
        cache_key = self._get_cache_key(sql, workspace_id, operation='count')
        if cache_key in self._count_cache:
            entry = self._count_cache[cache_key]
            if not entry.is_expired():
                logger.debug(f"Using cached count for query: {entry.result} rows")
                return entry.result
        
        if original_limit is not None and original_limit <= 1000:
            try:
                result = self.dbmanager.execute_sql(
                    sql=sql,
                    params={},
                    fetch="all"
                )
                total = len(result) if result else 0
                
                # Cache the result
                self._count_cache[cache_key] = QueryCacheEntry(
                    result=total,
                    timestamp=datetime.now()
                )
                return total
            except Exception as e:
                log_error(f"Error getting count for limited query: {e}")
                return 0
        
        sql_for_count = re.sub(r'\s+LIMIT\s+\d+(\s+OFFSET\s+\d+)?', '', sql, flags=re.IGNORECASE)
        
        # Create count query
        count_sql = f"SELECT COUNT(*) as total FROM ({sql_for_count}) AS count_subquery"
        
        try:
            # Execute count query
            result = self.dbmanager.execute_sql(
                sql=count_sql,
                params={},
                fetch=1
            )
            
            if result and len(result) > 0:
                # Handle different result formats
                first_row = result[0]
                
                # Handle SQLAlchemy Row objects
                if hasattr(first_row, '__getitem__'):
                    # Can be accessed by index (tuple-like or Row object)
                    total = first_row[0]
                elif isinstance(first_row, dict):
                    # Try different possible keys
                    total = first_row.get('total', first_row.get('count', first_row.get('COUNT(*)', 0)))
                else:
                    total = int(first_row) if first_row else 0
                
                # Ensure it's an integer
                total = int(total) if total is not None else 0
                
                if original_limit is not None and original_limit > 1000:
                    total = min(total, original_limit)
                
                # Cache the result
                self._count_cache[cache_key] = QueryCacheEntry(
                    result=total,
                    timestamp=datetime.now()
                )
                
                return total
            
            logger.warning(f"Count query returned no results")
            return 0
            
        except Exception as e:
            log_error(f"Error getting total count: {e}")
            return 0
    
    def execute_paginated_query(self, request: PaginationRequest) -> PaginationResponse:
        """
        Execute a SQL query with pagination support
        
        Args:
            request: Pagination request with query details
            
        Returns:
            PaginationResponse with paginated results
        """
        try:
            original_limit = self._extract_limit_from_sql(request.sql)
            logger.debug(f"Detected original LIMIT: {original_limit}")
            
            # Apply filters first
            filtered_sql = self._apply_filters(request.sql, request.filter_model)
            
            # Apply sorting
            sorted_sql = self._apply_sorting(filtered_sql, request.sort_model)
            
            if original_limit is not None and original_limit <= 1000:
                logger.debug(f"Using in-memory pagination for LIMIT {original_limit}")
                return self._execute_with_memory_pagination(
                    sorted_sql, request, original_limit
                )
            else:
                return self._execute_with_sql_pagination(
                    sorted_sql, request, original_limit
                )
                
        except Exception as e:
            log_error(f"Error in execute_paginated_query: {e}")
            return PaginationResponse(
                data=[],
                total_rows=0,
                page=request.page,
                page_size=request.page_size,
                has_next=False,
                has_previous=False,
                columns=[],
                error=str(e)
            )
    
    def _execute_with_memory_pagination(self, sql: str, request: PaginationRequest, 
                                      original_limit: int) -> PaginationResponse:
        """
        Execute query with in-memory pagination for queries with LIMIT <= 1000
        """
        try:
            logger.debug(f"Executing query with in-memory pagination (LIMIT {original_limit})")
            
            # Check cache
            cache_key = self._get_cache_key(
                sql, request.workspace_id,
                operation='memory_pagination',
                limit=original_limit
            )
            
            if cache_key in self._query_cache:
                entry = self._query_cache[cache_key]
                if not entry.is_expired():
                    logger.debug(f"Using cached results for in-memory pagination")
                    all_results = entry.result['data']
                    columns = entry.result['columns']
                else:
                    all_results = None
                    columns = None
            else:
                all_results = None
                columns = None
            
            if all_results is None:
                # Execute query to get all results
                execution_result = self.dbmanager.execute_sql(
                    sql=sql,
                    params={},
                    fetch="all"
                )
                
                # Extract columns
                columns = self._extract_columns_from_sql(sql)
                
                # Convert to list of dictionaries
                all_results = []
                if execution_result and isinstance(execution_result, list):
                    for row in execution_result:
                        row_dict = {}
                        if hasattr(row, '_asdict'):
                            row_dict = dict(row._asdict())
                        elif hasattr(row, 'keys'):
                            row_dict = dict(row)
                        else:
                            for i, value in enumerate(row):
                                col_name = columns[i] if i < len(columns) else f"column_{i+1}"
                                if value is None:
                                    row_dict[col_name] = None
                                elif isinstance(value, (int, float, bool)):
                                    row_dict[col_name] = value
                                else:
                                    row_dict[col_name] = str(value)
                        all_results.append(row_dict)
                
                # Cache the results
                self._query_cache[cache_key] = QueryCacheEntry(
                    result={'data': all_results, 'columns': columns},
                    timestamp=datetime.now()
                )
            
            # Apply pagination in memory
            total_rows = len(all_results)
            start_idx = request.page * request.page_size
            end_idx = start_idx + request.page_size
            
            # Slice the results
            paginated_results = all_results[start_idx:end_idx]
            
            return PaginationResponse(
                data=paginated_results,
                total_rows=total_rows,
                page=request.page,
                page_size=request.page_size,
                has_next=(request.page + 1) * request.page_size < total_rows,
                has_previous=request.page > 0,
                columns=columns
            )
            
        except Exception as e:
            log_error(f"Error in memory pagination: {e}")
            return PaginationResponse(
                data=[],
                total_rows=0,
                page=request.page,
                page_size=request.page_size,
                has_next=False,
                has_previous=False,
                columns=[],
                error=str(e)
            )
    
    def _execute_with_sql_pagination(self, sql: str, request: PaginationRequest,
                                    original_limit: Optional[int]) -> PaginationResponse:
        """
        Execute query with SQL-based pagination for queries without LIMIT or with LIMIT > 1000
        """
        try:
            total_rows = self._get_total_count(sql, request.workspace_id, original_limit)
            
            # Apply pagination to SQL
            paginated_sql, effective_limit = self._apply_pagination(
                sql, 
                request.page, 
                request.page_size,
                original_limit
            )
            
            # Check query cache
            cache_key = self._get_cache_key(
                paginated_sql, 
                request.workspace_id,
                page=request.page,
                page_size=request.page_size,
                sort_model=str(request.sort_model),
                filter_model=str(request.filter_model)
            )
            
            if cache_key in self._query_cache:
                entry = self._query_cache[cache_key]
                if not entry.is_expired():
                    logger.debug(f"Using cached results for page {request.page}")
                    cached_data = entry.result
                    return PaginationResponse(
                        data=cached_data['data'],
                        total_rows=total_rows,
                        page=request.page,
                        page_size=request.page_size,
                        has_next=(request.page + 1) * request.page_size < total_rows,
                        has_previous=request.page > 0,
                        columns=cached_data['columns']
                    )
            
            # Execute paginated query
            logger.debug(f"Executing paginated query for page {request.page}, size {request.page_size}")
            execution_result = self.dbmanager.execute_sql(
                sql=paginated_sql,
                params={},
                fetch=request.page_size
            )
            
            # Extract columns from original SQL (not the modified one)
            columns = self._extract_columns_from_sql(request.sql)
            
            # If SELECT * was used, we need to get actual column names from the result
            if columns == ['*'] and execution_result and len(execution_result) > 0:
                # Try to get column names from the result metadata
                first_row = execution_result[0]
                if hasattr(first_row, '_fields'):  # SQLAlchemy Row object
                    columns = list(first_row._fields)
                elif hasattr(first_row, 'keys'):  # Dict-like object
                    columns = list(first_row.keys())
                else:
                    # Fall back to generic column names based on row length
                    columns = [f"column_{i+1}" for i in range(len(first_row))]
                logger.debug(f"Detected columns from SELECT *: {columns}")
            
            # Convert result to list of dictionaries
            formatted_results = []
            if execution_result and isinstance(execution_result, list):
                for row in execution_result:
                    row_dict = {}
                    # Handle different row types
                    if hasattr(row, '_asdict'):  # NamedTuple or SQLAlchemy Row
                        row_dict = dict(row._asdict())
                    elif hasattr(row, 'keys'):  # Dict-like object
                        row_dict = dict(row)
                    else:  # Tuple or list
                        for i, value in enumerate(row):
                            col_name = columns[i] if i < len(columns) else f"column_{i+1}"
                            # Convert value to JSON-serializable format
                            if value is None:
                                row_dict[col_name] = None
                            elif isinstance(value, (int, float, bool)):
                                row_dict[col_name] = value
                            else:
                                row_dict[col_name] = str(value)
                    formatted_results.append(row_dict)
            
            # Cache the results
            cache_data = {
                'data': formatted_results,
                'columns': columns
            }
            self._query_cache[cache_key] = QueryCacheEntry(
                result=cache_data,
                timestamp=datetime.now()
            )
            
            # Return paginated response
            return PaginationResponse(
                data=formatted_results,
                total_rows=total_rows,
                page=request.page,
                page_size=request.page_size,
                has_next=(request.page + 1) * request.page_size < total_rows,
                has_previous=request.page > 0,
                columns=columns
            )
            
        except Exception as e:
            log_error(f"Error executing paginated query: {e}")
            return PaginationResponse(
                data=[],
                total_rows=0,
                page=request.page,
                page_size=request.page_size,
                has_next=False,
                has_previous=False,
                columns=[],
                error=str(e)
            )
    
    def clear_cache(self, workspace_id: Optional[int] = None):
        """Clear query cache, optionally for a specific workspace"""
        if workspace_id:
            # Clear only cache entries for specific workspace
            keys_to_remove = [
                key for key in self._query_cache.keys()
                if key.startswith(f"{workspace_id}:")
            ]
            for key in keys_to_remove:
                del self._query_cache[key]
                
            keys_to_remove = [
                key for key in self._count_cache.keys()
                if key.startswith(f"{workspace_id}:")
            ]
            for key in keys_to_remove:
                del self._count_cache[key]
        else:
            # Clear all cache
            self._query_cache.clear()
            self._count_cache.clear()
            
        logger.debug(f"Cache cleared for workspace: {workspace_id or 'all'}")
    
    def cleanup_expired_cache(self):
        """Remove expired entries from cache"""
        # Clean query cache
        expired_keys = [
            key for key, entry in self._query_cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._query_cache[key]
            
        # Clean count cache
        expired_keys = [
            key for key, entry in self._count_cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._count_cache[key]
            
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")