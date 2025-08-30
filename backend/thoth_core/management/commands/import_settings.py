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
from thoth_core.models import Setting, AiModel
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import Setting data from CSV, preserving original IDs"

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
        self.stdout.write(self.style.SUCCESS("Starting Setting CSV import"))

        csv_path = os.path.join(settings.BASE_DIR, "setup_csv", "setting.csv")
        source_specific_path = os.path.join(
            settings.BASE_DIR, "setup_csv", source, "setting.csv"
        )

        if os.path.exists(source_specific_path):
            csv_path = source_specific_path
            self.stdout.write(f"Using source-specific file: {csv_path}")
        else:
            self.stdout.write(f"Using default file: {csv_path}")

        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f"Setting CSV file not found at {csv_path}")
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
                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ID in row, using name as key: {row.get('name')}"
                            )
                        )
                        # If there's no ID, use name as key
                        obj, created = Setting.objects.update_or_create(
                            name=row["name"], defaults=self.get_defaults_from_row(row)
                        )
                        if created:
                            imported_count += 1
                            self.stdout.write(f"Created Setting: {obj.name}")
                        else:
                            updated_count += 1
                            self.stdout.write(f"Updated Setting: {obj.name}")
                    else:
                        # If there's an ID, try to update the existing object or create a new one with that ID
                        try:
                            obj = Setting.objects.get(id=model_id)
                            # Aggiorna i campi
                            for key, value in self.get_defaults_from_row(row).items():
                                setattr(obj, key, value)
                            # Assicurati che il nome sia aggiornato
                            obj.name = row["name"]
                            obj.save()
                            updated_count += 1
                            self.stdout.write(
                                f"Updated Setting with ID {model_id}: {obj.name}"
                            )
                        except Setting.DoesNotExist:
                            # Crea un nuovo oggetto con l'ID specificato
                            obj = Setting(
                                id=model_id,
                                name=row["name"],
                                **self.get_defaults_from_row(row),
                            )
                            obj.save()
                            imported_count += 1
                            self.stdout.write(
                                f"Created Setting with ID {model_id}: {obj.name}"
                            )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing Setting {row.get('name', 'unknown')}: {str(e)}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Setting import completed. Created: {imported_count}, Updated: {updated_count}, Errors: {error_count}"
            )
        )

    def get_defaults_from_row(self, row):
        """Extract default values from CSV row"""
        # Get related AiModel if specified
        comment_model = None
        if row.get("comment_model"):
            try:
                comment_model = AiModel.objects.get(id=row["comment_model"])
            except (AiModel.DoesNotExist, ValueError):
                try:
                    # Try to get by name instead
                    comment_model = AiModel.objects.get(name=row["comment_model"])
                except AiModel.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"AiModel '{row['comment_model']}' not found for Setting '{row['name']}'"
                        )
                    )

        defaults = {
            "theme": row.get("theme", ""),
            "language": row.get("language", "English"),
            "comment_model": comment_model,
            "system_prompt": row.get("system_prompt", ""),
        }

        # Handle numeric fields
        if "example_rows_for_comment" in row and row["example_rows_for_comment"]:
            try:
                defaults["example_rows_for_comment"] = int(
                    row["example_rows_for_comment"]
                )
            except (ValueError, TypeError):
                defaults["example_rows_for_comment"] = 5  # Default value

        if "signature_size" in row and row["signature_size"]:
            try:
                defaults["signature_size"] = int(row["signature_size"])
            except (ValueError, TypeError):
                defaults["signature_size"] = 30  # Default value

        if "n_grams" in row and row["n_grams"]:
            try:
                defaults["n_grams"] = int(row["n_grams"])
            except (ValueError, TypeError):
                defaults["n_grams"] = 3  # Default value

        if "threshold" in row and row["threshold"]:
            try:
                defaults["threshold"] = float(row["threshold"])
            except (ValueError, TypeError):
                defaults["threshold"] = 0.01  # Default value

        # Handle boolean fields
        if "verbose" in row:
            defaults["verbose"] = self.parse_boolean(row["verbose"])

        if "use_value_description" in row:
            defaults["use_value_description"] = self.parse_boolean(
                row["use_value_description"]
            )

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
