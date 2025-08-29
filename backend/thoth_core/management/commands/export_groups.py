# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
import csv
import os

class Command(BaseCommand):
    help = 'Download Django auth groups to a CSV file'

    def handle(self, *args, **options):
        io_dir = os.getenv('IO_DIR', 'exports')
        file_path = os.path.join(io_dir, 'groups.csv')

        os.makedirs(io_dir, exist_ok=True)

        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['id', 'name'])

            for group in Group.objects.all():
                writer.writerow([group.id, group.name])

        self.stdout.write(self.style.SUCCESS(f'Successfully downloaded groups to {file_path}'))
