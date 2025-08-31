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
from thoth_core.models import AiModel, BasicAiModel
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import AI models from CSV file"

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
        self.stdout.write(self.style.SUCCESS("Starting AI Model CSV import"))

        csv_path = os.path.join(settings.BASE_DIR.parent, "setup_csv", "aimodel.csv")
        source_specific_path = os.path.join(
            settings.BASE_DIR.parent, "setup_csv", source, "aimodel.csv"
        )

        if os.path.exists(source_specific_path):
            csv_path = source_specific_path
            self.stdout.write(f"Using source-specific file: {csv_path}")
        else:
            self.stdout.write(f"Using default file: {csv_path}")

        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f"AI Model CSV file not found at {csv_path}")
            )
            return

        imported_count = 0
        updated_count = 0
        error_count = 0

        # Get valid model fields, excluding foreign key fields that need special handling
        model_fields = [
            field.name
            for field in AiModel._meta.get_fields()
            if not field.is_relation or field.name == "id"
        ]

        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    # Filter out fields that don't exist in the model
                    valid_fields = {}
                    skip_record = False

                    for key, value in row.items():
                        if key == "basic_model" and value:
                            # Handle foreign key relationship to BasicAiModel
                            try:
                                basic_model = BasicAiModel.objects.get(id=value)
                                valid_fields["basic_model"] = basic_model
                            except BasicAiModel.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"BasicAiModel with ID {value} not found for AiModel {row.get('name', 'unknown')}"
                                    )
                                )
                                # Skip this record if the referenced BasicAiModel doesn't exist
                                skip_record = True
                                break
                        elif key in model_fields and value is not None and value != "":
                            valid_fields[key] = value

                    # Skip this record if BasicAiModel was not found
                    if skip_record:
                        continue

                    # Estrai l'ID dal CSV - richiesto obbligatoriamente
                    model_id = row.get("id")
                    if not model_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing ID for AiModel {row.get('name', 'unknown')}, skipping"
                            )
                        )
                        continue

                    # Cerca di aggiornare l'oggetto esistente o creane uno nuovo con quell'ID
                    try:
                        obj = AiModel.objects.get(id=model_id)
                        # Aggiorna i campi
                        for key, value in valid_fields.items():
                            setattr(obj, key, value)
                        obj.save()
                        updated_count += 1
                        self.stdout.write(
                            f"Updated AiModel with ID {model_id}: {obj.name}"
                        )
                    except AiModel.DoesNotExist:
                        # Crea un nuovo oggetto con l'ID specificato
                        valid_fields["id"] = model_id
                        obj = AiModel.objects.create(**valid_fields)
                        imported_count += 1
                        self.stdout.write(
                            f"Created AiModel with ID {model_id}: {obj.name}"
                        )

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing AiModel {row.get('name', 'unknown')}: {str(e)}"
                        )
                    )
                    logger.error(
                        f"Error processing AiModel {row.get('name', 'unknown')}: {str(e)}",
                        exc_info=True,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"AiModel import completed. Created: {imported_count}, Updated: {updated_count}, Errors: {error_count}"
            )
        )

    def get_defaults_from_row(self, row):
        """Extract default values from CSV row"""
        defaults = {
            "specific_model": row.get("specific_model", ""),
            "name": row.get("name", ""),
            "url": row.get("url", ""),
            "temperature_allowed": row.get("temperature_allowed", "True").lower()
            == "true",
        }

        # Handle numeric fields
        if "temperature" in row and row["temperature"]:
            try:
                defaults["temperature"] = float(row["temperature"])
            except (ValueError, TypeError):
                defaults["temperature"] = 0.7  # Default value

        if "top_p" in row and row["top_p"]:
            try:
                defaults["top_p"] = float(row["top_p"])
            except (ValueError, TypeError):
                defaults["top_p"] = 0.95  # Default value

        if "max_tokens" in row and row["max_tokens"]:
            try:
                defaults["max_tokens"] = int(row["max_tokens"])
            except (ValueError, TypeError):
                defaults["max_tokens"] = 1024  # Default value

        if "timeout" in row and row["timeout"]:
            try:
                defaults["timeout"] = float(row["timeout"])
            except (ValueError, TypeError):
                defaults["timeout"] = 45.0  # Default value

        if "context_size" in row and row["context_size"]:
            try:
                defaults["context_size"] = int(row["context_size"])
            except (ValueError, TypeError):
                defaults["context_size"] = 4096  # Default value

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
        """Parse a string value to boolean"""
        if isinstance(value, bool):
            return value
        if not value:
            return False
        return str(value).lower() in ("true", "yes", "1", "t", "y")
