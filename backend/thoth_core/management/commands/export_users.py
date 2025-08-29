# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import csv
import os

class Command(BaseCommand):
    help = 'Download Django auth users to a CSV file'

    def handle(self, *args, **options):
        io_dir = os.getenv('IO_DIR', 'exports')
        file_path = os.path.join(io_dir, 'users.csv')

        os.makedirs(io_dir, exist_ok=True)

        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined'])

            for user in User.objects.all():
                writer.writerow([
                    user.id,
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    user.is_staff,
                    user.is_active,
                    user.date_joined
                ])

        self.stdout.write(self.style.SUCCESS(f'Successfully downloaded users to {file_path}'))
