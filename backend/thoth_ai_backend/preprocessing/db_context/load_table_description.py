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

import logging
from typing import Dict
from django.db.models import Prefetch
from thoth_core.models import SqlDb, SqlTable, SqlColumn

def load_tables_description(db_id: int, **kwargs) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Loads table descriptions directly from the Django models for a given database.

    Args:
        db_id (int): The id of the database.

    Returns:
        Dict[str, Dict[str, Dict[str, str]]]: A dictionary containing table descriptions.
    """
    table_description = {}

    try:
        # Get the SqlDb instance by the actual database name field
        db = SqlDb.objects.get(id=db_id)

        # Prefetch related SqlTables and SqlColumns to optimize queries
        tables = SqlTable.objects.filter(sql_db=db).prefetch_related(
            Prefetch('columns', queryset=SqlColumn.objects.all(), to_attr='prefetched_columns')
        )

        for table in tables:
            table_name = table.name.lower().strip()
            table_description[table_name] = {}

            for column in table.prefetched_columns:
                column_name = column.original_column_name.lower().strip()
                table_description[table_name][column_name] = {
                    "original_column_name": column.original_column_name,
                    "column_name": column.column_name or "",
                    "column_description": column.column_description or "",
                    "generated_comment": column.generated_comment or "",
                    "data_format": column.data_format or "",
                    "value_description": (
                        column.value_description or ""
                        if kwargs.get("use_value_description", True)
                        else ""
                    ),
                }

    except SqlDb.DoesNotExist:
        logging.error(f"Database with id '{db_id}' not found.")
    except Exception as e:
        logging.error(f"Error loading table descriptions: {e}")

    return table_description

def load_tables_concatenated_description(db_id: int, **kwargs) -> Dict[str, Dict[str, str]]:
    """
    Loads and concatenates table descriptions directly from the Django models for a given database.

    Args:
        db_id (int): The id of the database to retrieve information for.

    Returns:
        Dict[str, Dict[str, str]]: A nested dictionary where:
            - The outer dictionary keys are table names (str).
            - The inner dictionary keys are column names (str).
            - The inner dictionary values are concatenated descriptions (str)
              for each column, including the column name, column description,
              and value description, separated by commas.
    """
    concatenated_descriptions = {}

    try:
        # Get the SqlDb instance by the actual database name field
        db = SqlDb.objects.get(id=db_id)

        # Prefetch related SqlTables and SqlColumns to optimize queries
        tables = SqlTable.objects.filter(sql_db=db).prefetch_related(
            Prefetch('columns', queryset=SqlColumn.objects.all(), to_attr='prefetched_columns')
        )

        for table in tables:
            table_name = table.name.lower().strip()
            concatenated_descriptions[table_name] = {}

            for column in table.prefetched_columns:
                column_name = column.original_column_name.lower().strip()

                # Concatenate the descriptions
                description_parts = [
                    column.column_name or "",
                    column.generated_comment or "",
                    (
                        column.value_description or ""
                        if kwargs.get("use_value_description", True)
                        else ""
                    ),
                    ]

                concatenated_description = ", ".join(
                    part for part in description_parts if part
                ).strip()
                concatenated_description = concatenated_description.replace("  ", " ")

                concatenated_descriptions[table_name][column_name] = (
                    concatenated_description.strip(", ")
                )

    except SqlDb.DoesNotExist:
        logging.error(f"Database with id '{db_id}' not found.")
    except Exception as e:
        logging.error(f"Error loading concatenated table descriptions: {e}")

    return concatenated_descriptions
