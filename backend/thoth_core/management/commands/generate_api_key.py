# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import secrets
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Generate a new API key for authentication'

    def handle(self, *args, **kwargs):
        api_key = secrets.token_urlsafe(32)
        self.stdout.write(self.style.SUCCESS(f'Generated API Key: {api_key}'))