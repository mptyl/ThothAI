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
from django.contrib.auth.models import Group
import csv
import os


class Command(BaseCommand):
    help = "Download Django auth groups to a CSV file"

    def handle(self, *args, **options):
        io_dir = os.getenv("IO_DIR", "exports")
        file_path = os.path.join(io_dir, "groups.csv")

        os.makedirs(io_dir, exist_ok=True)

        with open(file_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["id", "name"])

            for group in Group.objects.all():
                writer.writerow([group.id, group.name])

        self.stdout.write(
            self.style.SUCCESS(f"Successfully downloaded groups to {file_path}")
        )
