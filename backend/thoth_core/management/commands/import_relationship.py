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
from thoth_core.models import Relationship, SqlTable
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import Relationship data from CSV, preserving original IDs"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting Relationship CSV import"))

        csv_path = os.path.join(settings.BASE_DIR, "setup_csv", "relationship.csv")

        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f"Relationship CSV file not found at {csv_path}")
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

                    # Ottieni le tabelle SQL associate
                    parent_table = None
                    child_table = None

                    if row.get("parent_table"):
                        try:
                            parent_table = SqlTable.objects.get(id=row["parent_table"])
                        except (SqlTable.DoesNotExist, ValueError):
                            try:
                                # Try to get by name
                                parent_table = SqlTable.objects.filter(
                                    name=row["parent_table"]
                                ).first()
                            except Exception:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Parent SqlTable '{row['parent_table']}' not found for Relationship"
                                    )
                                )
                                continue  # Skip this row if we don't find the parent table
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                "Missing parent_table reference for Relationship"
                            )
                        )
                        continue  # Skip this row if there's no reference to the parent table

                    if row.get("child_table"):
                        try:
                            child_table = SqlTable.objects.get(id=row["child_table"])
                        except (SqlTable.DoesNotExist, ValueError):
                            try:
                                # Try to get by name
                                child_table = SqlTable.objects.filter(
                                    name=row["child_table"]
                                ).first()
                            except Exception:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Child SqlTable '{row['child_table']}' not found for Relationship"
                                    )
                                )
                                continue  # Skip this row if we don't find the child table
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                "Missing child_table reference for Relationship"
                            )
                        )
                        continue  # Skip this row if there's no reference to the child table

                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                "Missing ID in row, using parent and child tables as key"
                            )
                        )
                        # If there's no ID, use parent and child tables as key
                        obj, created = Relationship.objects.update_or_create(
                            parent_table=parent_table,
                            child_table=child_table,
                            defaults={
                                "parent_column": row.get("parent_column", ""),
                                "child_column": row.get("child_column", ""),
                                "relationship_type": row.get(
                                    "relationship_type", "ONE_TO_MANY"
                                ),
                            },
                        )
                        if created:
                            imported_count += 1
                            self.stdout.write(
                                f"Created Relationship: {parent_table.name} -> {child_table.name}"
                            )
                        else:
                            updated_count += 1
                            self.stdout.write(
                                f"Updated Relationship: {parent_table.name} -> {child_table.name}"
                            )
                    else:
                        # If there's an ID, try to update the existing object or create a new one with that ID
                        try:
                            obj = Relationship.objects.get(id=model_id)
                            # Aggiorna i campi
                            obj.parent_table = parent_table
                            obj.child_table = child_table
                            obj.parent_column = row.get("parent_column", "")
                            obj.child_column = row.get("child_column", "")
                            obj.relationship_type = row.get(
                                "relationship_type", "ONE_TO_MANY"
                            )
                            obj.save()
                            updated_count += 1
                            self.stdout.write(
                                f"Updated Relationship with ID {model_id}: {parent_table.name} -> {child_table.name}"
                            )
                        except Relationship.DoesNotExist:
                            # Crea un nuovo oggetto con l'ID specificato
                            obj = Relationship.objects.create(
                                id=model_id,
                                parent_table=parent_table,
                                child_table=child_table,
                                parent_column=row.get("parent_column", ""),
                                child_column=row.get("child_column", ""),
                                relationship_type=row.get(
                                    "relationship_type", "ONE_TO_MANY"
                                ),
                            )
                            imported_count += 1
                            self.stdout.write(
                                f"Created Relationship with ID {model_id}: {parent_table.name} -> {child_table.name}"
                            )
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error processing row {row}: {str(e)}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed. Imported: {imported_count}, Updated: {updated_count}, Errors: {error_count}"
            )
        )
