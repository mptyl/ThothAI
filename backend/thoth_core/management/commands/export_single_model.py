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
from django.apps import apps
import csv
import os


class Command(BaseCommand):
    help = "Export a single model data to a CSV file in IO_DIR"

    def add_arguments(self, parser):
        parser.add_argument("model_name", type=str, help="Name of the model to export")

    def handle(self, *args, **options):
        # Use data_exchange directory
        if os.getenv("IS_DOCKER"):
            io_dir = "/app/data_exchange"
        else:
            from django.conf import settings
            io_dir = os.path.join(settings.BASE_DIR.parent, "data_exchange")
        
        model_name = options["model_name"]
        
        # Ensure directory exists
        os.makedirs(io_dir, exist_ok=True)

        try:
            Model = apps.get_model("toth_be", model_name)
        except LookupError:
            self.stdout.write(self.style.ERROR(f"Model {model_name} not found"))
            return

        file_path = os.path.join(io_dir, f"{model_name.lower()}.csv")

        with open(file_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            fields = [f.original_column_name for f in Model._meta.fields]
            m2m_fields = [f.original_column_name for f in Model._meta.many_to_many]
            writer.writerow(fields + m2m_fields)

            for obj in Model.objects.all():
                row = []
                for field in fields:
                    value = getattr(obj, field)
                    if field.endswith("_id"):
                        row.append(value)
                    elif hasattr(value, "pk"):
                        row.append(value.pk)
                    else:
                        row.append(value)
                for m2m_field in m2m_fields:
                    related_objects = getattr(obj, m2m_field).all()
                    row.append(",".join(str(related.pk) for related in related_objects))
                writer.writerow(row)

        self.stdout.write(self.style.SUCCESS(f"Exported {model_name} to {file_path}"))
