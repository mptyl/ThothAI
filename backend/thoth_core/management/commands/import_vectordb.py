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
from thoth_core.models import VectorDb
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import VectorDb data from CSV, preserving original IDs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            choices=["local", "docker"],
            default="local",
            help="Source of CSV files to import (local or docker)",
        )

    def handle(self, *args, **options):
        source = options.get("source", "local")
        self.stdout.write(self.style.SUCCESS("Starting VectorDb CSV import"))

        csv_path = os.path.join(settings.BASE_DIR.parent, "setup_csv", "vectordb.csv")
        source_specific_path = os.path.join(
            settings.BASE_DIR.parent, "setup_csv", source, "vectordb.csv"
        )

        if os.path.exists(source_specific_path):
            csv_path = source_specific_path
            self.stdout.write(f"Using source-specific file: {csv_path}")
        else:
            self.stdout.write(f"Using default file: {csv_path}")

        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f"VectorDb CSV file not found at {csv_path}")
            )
            return

        imported_count = 0
        updated_count = 0
        error_count = 0

        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    # Estrai l'ID dal CSV - richiesto obbligatoriamente
                    model_id = row.get("id")
                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ID for VectorDb {row.get('name', 'unknown')}, skipping"
                            )
                        )
                        continue

                    # Cerca di aggiornare l'oggetto esistente o creane uno nuovo con quell'ID
                    try:
                        obj = VectorDb.objects.get(id=model_id)
                        # Aggiorna i campi
                        for key, value in self.get_defaults_from_row(row).items():
                            setattr(obj, key, value)
                        # Assicurati che il nome sia aggiornato
                        obj.name = row["name"]
                        obj.save()
                        updated_count += 1
                        self.stdout.write(
                            f"Updated VectorDb with ID {model_id}: {obj.name}"
                        )
                    except VectorDb.DoesNotExist:
                        # Crea un nuovo oggetto con l'ID specificato
                        obj = VectorDb(
                            id=model_id,
                            name=row["name"],
                            **self.get_defaults_from_row(row),
                        )
                        obj.save()
                        imported_count += 1
                        self.stdout.write(
                            f"Created VectorDb with ID {model_id}: {obj.name}"
                        )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing VectorDb {row.get('name', 'unknown')}: {str(e)}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"VectorDb import completed. Created: {imported_count}, Updated: {updated_count}, Errors: {error_count}"
            )
        )

    def get_defaults_from_row(self, row):
        """Extract default values from CSV row"""
        defaults = {
            "vect_type": row.get("vect_type", "Qdrant"),
            "host": row.get("host", "localhost"),
            "username": row.get("username", ""),
            "password": row.get("password", ""),
            "path": row.get("path", ""),
            "tenant": row.get("tenant", ""),
        }

        # Handle port field
        if "port" in row and row["port"]:
            try:
                defaults["port"] = int(row["port"])
            except (ValueError, TypeError):
                defaults["port"] = 6333  # Default Qdrant port
        else:
            defaults["port"] = 6333

        # Add datetime fields if present
        if "created_at" in row and row["created_at"]:
            defaults["created_at"] = self.parse_datetime(row["created_at"])
        if "updated_at" in row and row["updated_at"]:
            defaults["updated_at"] = self.parse_datetime(row["updated_at"])

        return defaults

    def parse_datetime(self, datetime_str):
        """Parse a datetime string to a datetime object"""
        if not datetime_str or datetime_str.lower() in ("null", "none", ""):
            return None

        try:
            from django.utils.dateparse import parse_datetime

            return parse_datetime(datetime_str)
        except Exception:
            self.stdout.write(
                self.style.WARNING(f"Could not parse datetime: {datetime_str}")
            )
            return None

    def parse_boolean(self, value):
        """Parse a string to a boolean value"""
        if isinstance(value, bool):
            return value
        if value.lower() in ("true", "yes", "1", "t", "y"):
            return True
        return False
