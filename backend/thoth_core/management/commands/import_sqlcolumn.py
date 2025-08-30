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
from thoth_core.models import SqlColumn, SqlTable
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import SqlColumn data from CSV, preserving original IDs"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting SqlColumn CSV import"))

        csv_path = os.path.join(settings.BASE_DIR, "setup_csv", "sqlcolumn.csv")

        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f"SqlColumn CSV file not found at {csv_path}")
            )
            return

        imported_count = 0
        updated_count = 0
        error_count = 0

        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    # Estrai l'ID dal CSV
                    model_id = row.get("id")

                    # Ottieni la tabella SQL associata
                    sql_table = None
                    if row.get("sql_table"):
                        try:
                            sql_table = SqlTable.objects.get(id=row["sql_table"])
                        except (SqlTable.DoesNotExist, ValueError):
                            try:
                                # Try to get by name
                                sql_table = SqlTable.objects.filter(
                                    name=row["sql_table"]
                                ).first()
                            except Exception:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"SqlTable '{row['sql_table']}' not found for SqlColumn '{row.get('column_name', 'unknown')}'"
                                    )
                                )
                                continue  # Skip this row if we don't find the table
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing sql_table reference for SqlColumn '{row.get('column_name', 'unknown')}'"
                            )
                        )
                        continue  # Skip this row if there's no table reference

                    # Prepare values for boolean fields
                    pk_field = self.parse_boolean(row.get("pk_field", "False"))
                    fk_field = row.get(
                        "fk_field", ""
                    )  # This is a reference to another column, not a boolean

                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ID in row, using column_name and sql_table as key: {row.get('column_name')} in {sql_table.name if sql_table else 'unknown'}"
                            )
                        )
                        # If there's no ID, use column name and table as key
                        obj, created = SqlColumn.objects.update_or_create(
                            column_name=row["column_name"],
                            sql_table=sql_table,
                            defaults={
                                "original_column_name": row.get(
                                    "original_column_name", row["column_name"]
                                ),
                                "data_format": row.get("data_format", ""),
                                "column_description": row.get("column_description", ""),
                                "generated_comment": row.get("generated_comment", ""),
                                "value_description": row.get("value_description", ""),
                                "pk_field": pk_field,
                                "fk_field": fk_field,
                            },
                        )
                        if created:
                            imported_count += 1
                            self.stdout.write(
                                f"Created SqlColumn: {obj.column_name} in {sql_table.name}"
                            )
                        else:
                            updated_count += 1
                            self.stdout.write(
                                f"Updated SqlColumn: {obj.column_name} in {sql_table.name}"
                            )
                    else:
                        # If there's an ID, try to update the existing object or create a new one with that ID
                        try:
                            obj = SqlColumn.objects.get(id=model_id)
                            # Aggiorna i campi
                            obj.column_name = row["column_name"]
                            obj.original_column_name = row.get(
                                "original_column_name", row["column_name"]
                            )
                            obj.sql_table = sql_table
                            obj.data_format = row.get("data_format", "")
                            obj.column_description = row.get("column_description", "")
                            obj.generated_comment = row.get("generated_comment", "")
                            obj.value_description = row.get("value_description", "")
                            obj.pk_field = pk_field
                            obj.fk_field = fk_field
                            obj.save()
                            updated_count += 1
                            self.stdout.write(
                                f"Updated SqlColumn with ID {model_id}: {obj.column_name} in {sql_table.name}"
                            )
                        except SqlColumn.DoesNotExist:
                            # Crea un nuovo oggetto con l'ID specificato
                            obj = SqlColumn.objects.create(
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
                            self.stdout.write(
                                f"Created SqlColumn with ID {model_id}: {obj.column_name} in {sql_table.name}"
                            )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing SqlColumn {row.get('column_name', 'unknown')}: {str(e)}"
                        )
                    )
                    logger.error(
                        f"Error processing SqlColumn {row.get('column_name', 'unknown')}: {str(e)}",
                        exc_info=True,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"SqlColumn import completed. Created: {imported_count}, Updated: {updated_count}, Errors: {error_count}"
            )
        )

    def parse_boolean(self, value):
        """Parse a string to a boolean value"""
        if isinstance(value, bool):
            return value
        if not value:
            return False
        return value.lower() in ("true", "t", "yes", "y", "1")
