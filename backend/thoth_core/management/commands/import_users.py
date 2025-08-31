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
from django.contrib.auth.models import User, Group
import csv
import os


class Command(BaseCommand):
    help = "Import Django auth users from a CSV file"

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
        
        # setup_csv is part of the project, copied during Docker build
        from django.conf import settings
        io_dir = os.path.join(settings.BASE_DIR.parent, "setup_csv")
        file_path = os.path.join(io_dir, "users.csv")

        # Check for source-specific file
        source_specific_path = os.path.join(io_dir, source, "users.csv")
        if os.path.exists(source_specific_path):
            file_path = source_specific_path
            self.stdout.write(f"Using source-specific file: {file_path}")
        else:
            self.stdout.write(f"Using default file: {file_path}")

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with open(file_path, "r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                user, created = User.objects.update_or_create(
                    username=row["username"],
                    defaults={
                        "email": row["email"],
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "is_staff": row["is_staff"].lower() == "true",
                        "is_active": row["is_active"].lower() == "true",
                        "date_joined": row["date_joined"],
                    },
                )

                # Handle group relationships
                if row.get("groups"):
                    try:
                        group_ids = [
                            int(gid.strip())
                            for gid in row["groups"].split(",")
                            if gid.strip()
                        ]
                        groups = Group.objects.filter(id__in=group_ids)
                        user.groups.set(groups)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{'Created' if created else 'Updated'} user: {user.username} with groups: {list(groups.values_list('name', flat=True))}"
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Error setting groups for user {user.username}: {str(e)}"
                            )
                        )
                else:
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f"Created user: {user.username}")
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f"Updated user: {user.username}")
                        )

        self.stdout.write(self.style.SUCCESS("User import completed successfully"))
