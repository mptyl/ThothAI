# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.apps import AppConfig


class ThothBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'thoth_ai_backend'
