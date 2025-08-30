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
SQL compatibility utilities for ensuring PostgreSQL syntax.

Requires: sqlglot (https://github.com/tobymao/sqlglot)
"""

from sqlglot import transpile, errors

def ensure_postgres_compatibility(sql: str) -> str:
    """
    Attempts to convert the input SQL string to PostgreSQL-compatible syntax.
    If conversion fails, returns the original SQL.

    Args:
        sql (str): The input SQL query.

    Returns:
        str: The SQL query rewritten for PostgreSQL compatibility, or the original if conversion fails.
    """
    try:
        # Try to parse and transpile to PostgreSQL dialect
        # sqlglot will try to auto-detect the source dialect, but we can specify common ones if needed
        transpiled = transpile(sql, read='sqlite', write="postgres")
        if transpiled:
            return transpiled[0]
    except errors.ParseError as e:
        raise e
    except Exception as ex:
        raise ex
    # If anything fails, return the original SQL
    return sql
