# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

class Command(BaseCommand):
    help = 'Delete all users from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        user_count = User.objects.count()

        if user_count == 0:
            self.stdout.write(self.style.WARNING('No users found in the database.'))
            return

        if not options['force']:
            confirm = input(f'Are you sure you want to delete all {user_count} users? This action cannot be undone. (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        try:
            with transaction.atomic():
                User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted all {user_count} users.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
