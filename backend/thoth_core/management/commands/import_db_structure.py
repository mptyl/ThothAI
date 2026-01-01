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

from django.core.management.base import BaseCommand
from django.conf import settings
from thoth_core.models import SqlDb, SqlTable, SqlColumn, Relationship, VectorDb
import os
import csv
from datetime import datetime


class Command(BaseCommand):
    help = "Import database structure from CSV files, preserving original IDs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--import-dir",
            type=str,
            default="setup_csv",
            help="Directory containing CSV files to import",
        )
        parser.add_argument(
            "--source",
            type=str,
            choices=["local", "docker"],
            default="local",
            help="Source of CSV files to import (local or docker)",
        )

    def parse_datetime(self, datetime_str):
        """Parse datetime string or return None if empty"""
        if not datetime_str or datetime_str.strip() == "":
            return None
        try:
            return datetime.fromisoformat(datetime_str)
        except (ValueError, TypeError):
            return None

    def handle(self, *args, **options):
        # setup_csv is part of the project root, copied during Docker build
        source = options.get("source", "local")
        
        # Use helper for selected_dbs.csv
        from thoth_core.management.helpers import get_setup_csv_path
        selected_dbs_file = get_setup_csv_path("selected_dbs.csv", source)
        
        self.stdout.write(f"Using CSV file at: {selected_dbs_file}")
        
        # Determine base directory for subsequent files
        # We need the parent directory of selected_dbs.csv to find other files
        # get_setup_csv_path returns the full path including filename
        # so we take the parent to get the directory
        resolved_import_dir = os.path.dirname(selected_dbs_file)
        self.stdout.write(f"Base import directory resolved to: {resolved_import_dir}")

        if not os.path.exists(selected_dbs_file):
            self.stdout.write(
                self.style.ERROR(f"Selected DBs file not found: {selected_dbs_file}")
            )
            return

        imported_dbs = []
        imported_tables_count = 0
        imported_columns_count = 0
        imported_relationships_count = 0

        with open(selected_dbs_file, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                db_name = row["name"]
                imported_dbs.append(db_name)

                # Find the SqlDb record
                sql_db = None
                try:
                    sql_db = SqlDb.objects.get(name=db_name)
                    self.stdout.write(f"Found existing database: {db_name}")
                except SqlDb.DoesNotExist:
                    self.stdout.write(f"Creating new database: {db_name}")

                    # Handle db_port field - convert empty string to None
                    db_port = None
                    if row.get("db_port") and row.get("db_port").strip():
                        try:
                            db_port = int(row.get("db_port"))
                        except (ValueError, TypeError):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Invalid db_port value '{row.get('db_port')}' for SqlDb '{db_name}', setting to None"
                                )
                            )
                            db_port = None

                    # Normalize language to ISO code if csv provides names
                    lang = (row.get("language", "") or "").strip()
                    try:
                        from thoth_core.models import LanguageCode
                        valid_codes = {code for code, _ in LanguageCode.choices}
                        name_to_code = {label.lower(): code for code, label in LanguageCode.choices}
                        lang_lower = lang.lower()
                        if lang_lower in valid_codes:
                            norm_lang = lang_lower
                        elif lang_lower in name_to_code:
                            norm_lang = name_to_code[lang_lower]
                        else:
                            norm_lang = LanguageCode.EN
                    except Exception:
                        norm_lang = lang or "en"

                    sql_db = SqlDb.objects.create(
                        id=row["id"],
                        name=db_name,
                        db_host=row.get("db_host", ""),
                        db_type=row.get("db_type", "PostgreSQL"),
                        db_name=row.get("db_name", ""),
                        db_port=db_port,  # Use the processed db_port value
                        schema=row.get("schema", "public"),
                        user_name=row.get("user_name", ""),
                        password=row.get("password", ""),
                        db_mode=row.get("db_mode", ""),
                        language=norm_lang,
                    )
                # Find the VectorDb if specified
                vector_db = None
                if row.get("vector_db"):
                    try:
                        vector_db = VectorDb.objects.get(id=row["vector_db"])
                        # Check if this VectorDb is already assigned to another SqlDb
                        existing_sqldb_with_vectordb = (
                            SqlDb.objects.filter(vector_db=vector_db)
                            .exclude(id=sql_db.id)
                            .first()
                        )
                        if existing_sqldb_with_vectordb:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"VectorDb '{vector_db.name}' is already assigned to SqlDb '{existing_sqldb_with_vectordb.name}'. "
                                    f"Removing it from '{existing_sqldb_with_vectordb.name}' and assigning to '{sql_db.name}'"
                                )
                            )
                            existing_sqldb_with_vectordb.vector_db = None
                            existing_sqldb_with_vectordb.save()

                        sql_db.vector_db = vector_db
                        sql_db.save()
                    except VectorDb.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"VectorDb '{row['vector_db']}' not found"
                            )
                        )

                # Import tables, columns, and relationships for this database
                tables_count = self.import_tables(resolved_import_dir, db_name, sql_db, source)
                imported_tables_count += tables_count

                columns_count = self.import_columns(resolved_import_dir, db_name, sql_db, source)
                imported_columns_count += columns_count

                relationships_count = self.import_relationships(
                    resolved_import_dir, db_name, source
                )
                imported_relationships_count += relationships_count

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully imported {len(imported_dbs)} database(s) ({', '.join(imported_dbs)}) with "
                f"{imported_tables_count} tables, {imported_columns_count} columns, and "
                f"{imported_relationships_count} relationships"
            )
        )

    def import_tables(self, import_dir, db_name, sql_db, source="local"):
        """Import tables for a specific database, preserving original IDs"""
        # We already resolved the directory in handle(), so just construct the filename
        # Note: In handle() we resolved to the specific source directory (e.g. setup_csv/docker)
        # So we don't need to try source-specific vs default logic again here if we trust import_dir
        
        tables_file = os.path.join(import_dir, f"{db_name}_tables.csv")
        self.stdout.write(f"Looking for tables file at: {tables_file}")

        if not os.path.exists(tables_file):
            self.stdout.write(
                self.style.WARNING(
                    f"Tables file not found for {db_name}: {tables_file}"
                )
            )
            return 0

        imported_count = 0
        updated_count = 0

        with open(tables_file, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Extract the ID from CSV
                    model_id = row.get("id")

                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ID for table {row.get('name', 'unknown')} in {db_name}, skipping"
                            )
                        )
                        continue

                    # Try to get existing table by ID or create new one with that ID
                    try:
                        table = SqlTable.objects.get(id=model_id)
                        # Update fields
                        table.name = row["name"]
                        table.sql_db = sql_db
                        table.description = row.get("description", "")
                        table.generated_comment = row.get("generated_comment", "")
                        table.save()
                        updated_count += 1
                    except SqlTable.DoesNotExist:
                        # Create new table with specified ID
                        table = SqlTable.objects.create(
                            id=model_id,
                            name=row["name"],
                            sql_db=sql_db,
                            description=row.get("description", ""),
                            generated_comment=row.get("generated_comment", ""),
                        )
                        imported_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing table {row.get('name', 'unknown')} in {db_name}: {str(e)}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_count} tables and updated {updated_count} tables for database: {db_name}"
            )
        )
        return imported_count + updated_count

    def import_columns(self, import_dir, db_name, sql_db, source="local"):
        """Import columns for a specific database, preserving original IDs"""
        columns_file = os.path.join(import_dir, f"{db_name}_columns.csv")
        self.stdout.write(f"Looking for columns file at: {columns_file}")

        if not os.path.exists(columns_file):
            self.stdout.write(
                self.style.WARNING(
                    f"Columns file not found for {db_name}: {columns_file}"
                )
            )
            return 0

        imported_count = 0
        updated_count = 0

        with open(columns_file, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Extract the ID from CSV
                    model_id = row.get("id")

                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ID for column {row.get('column_name', 'unknown')} in {db_name}, skipping"
                            )
                        )
                        continue

                    # Get the table for this column using only ID
                    sql_table = None
                    table_id = row.get("sql_table_id")
                    if not table_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing table ID for column {row.get('column_name', 'unknown')} in {db_name}, skipping"
                            )
                        )
                        continue

                    try:
                        sql_table = SqlTable.objects.get(id=table_id)
                    except SqlTable.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Table with ID {table_id} not found for column {row.get('column_name', 'unknown')}"
                            )
                        )
                        continue

                    # Get string values directly from CSV
                    pk_field = row.get("pk_field", "")
                    fk_field = row.get("fk_field", "")

                    # Try to get existing column by ID or create new one with that ID
                    try:
                        column = SqlColumn.objects.get(id=model_id)
                        # Update fields
                        column.column_name = row["column_name"]
                        column.original_column_name = row.get(
                            "original_column_name", row["column_name"]
                        )
                        column.sql_table = sql_table
                        column.data_format = row.get("data_format", "")
                        column.column_description = row.get("column_description", "")
                        column.generated_comment = row.get("generated_comment", "")
                        column.value_description = row.get("value_description", "")
                        column.pk_field = pk_field
                        column.fk_field = fk_field
                        column.save()
                        updated_count += 1
                    except SqlColumn.DoesNotExist:
                        # Create new column with specified ID
                        column = SqlColumn.objects.create(
                            id=model_id,
                            column_name=row["column_name"],
                            original_column_name=row.get(
                                "original_column_name", row["column_name"]
                            ),
                            sql_table=sql_table,
                            data_format=row.get("data_format", ""),
                            column_description=row.get("column_description", ""),
                            generated_comment=row.get("generated_comment", ""),
                            value_description=row.get("value_description", ""),
                            pk_field=pk_field,
                            fk_field=fk_field,
                        )
                        imported_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing column {row.get('column_name', 'unknown')} in {db_name}: {str(e)}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_count} columns and updated {updated_count} columns for database: {db_name}"
            )
        )
        return imported_count + updated_count

    def import_relationships(self, import_dir, db_name, source="local"):
        """Import relationships for a specific database, preserving original IDs"""
        relationships_file = os.path.join(import_dir, f"{db_name}_relationships.csv")
        self.stdout.write(f"Looking for relationships file at: {relationships_file}")

        if not os.path.exists(relationships_file):
            self.stdout.write(
                self.style.WARNING(
                    f"Relationships file not found for {db_name}: {relationships_file}"
                )
            )
            return 0

        imported_count = 0
        updated_count = 0

        with open(relationships_file, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Extract the ID from CSV
                    model_id = row.get("id")

                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ID for relationship in {db_name}, skipping"
                            )
                        )
                        continue

                    # Get the source and target tables and columns
                    source_table = None
                    target_table = None
                    source_column = None
                    target_column = None

                    # Get source table using only ID
                    source_table_id = row.get("source_table")
                    if not source_table_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing source table ID for relationship in {db_name}, skipping"
                            )
                        )
                        continue

                    try:
                        source_table = SqlTable.objects.get(id=source_table_id)
                    except SqlTable.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Source table with ID {source_table_id} not found"
                            )
                        )
                        continue

                    # Get target table using only ID
                    target_table_id = row.get("target_table")
                    if not target_table_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing target table ID for relationship in {db_name}, skipping"
                            )
                        )
                        continue

                    try:
                        target_table = SqlTable.objects.get(id=target_table_id)
                    except SqlTable.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Target table with ID {target_table_id} not found"
                            )
                        )
                        continue

                    # Get source column using only ID
                    source_column_id = row.get("source_column")
                    if not source_column_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing source column ID for relationship in {db_name}, skipping"
                            )
                        )
                        continue

                    try:
                        source_column = SqlColumn.objects.get(id=source_column_id)
                    except SqlColumn.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Source column with ID {source_column_id} not found"
                            )
                        )
                        continue

                    # Get target column using only ID
                    target_column_id = row.get("target_column")
                    if not target_column_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing target column ID for relationship in {db_name}, skipping"
                            )
                        )
                        continue

                    try:
                        target_column = SqlColumn.objects.get(id=target_column_id)
                    except SqlColumn.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Target column with ID {target_column_id} not found"
                            )
                        )
                        continue

                    # Try to get existing relationship by ID or create new one with that ID
                    try:
                        relationship = Relationship.objects.get(id=model_id)
                        # Update fields
                        relationship.source_table = source_table
                        relationship.source_column = source_column
                        relationship.target_table = target_table
                        relationship.target_column = target_column
                        relationship.save()
                        updated_count += 1
                    except Relationship.DoesNotExist:
                        # Create new relationship with specified ID
                        relationship = Relationship.objects.create(
                            id=model_id,
                            source_table=source_table,
                            source_column=source_column,
                            target_table=target_table,
                            target_column=target_column,
                        )
                        imported_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing relationship in {db_name}: {str(e)}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_count} relationships and updated {updated_count} relationships for database: {db_name}"
            )
        )
        return imported_count + updated_count
