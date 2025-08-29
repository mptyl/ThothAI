# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
SQL compatibility utilities for ensuring PostgreSQL syntax.

Requires: sqlglot (https://github.com/tobymao/sqlglot)
"""

import sqlglot
from sqlglot import transpile, parse_one, errors

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
