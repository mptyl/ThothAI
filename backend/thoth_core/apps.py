# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.apps import AppConfig


class ThothCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'thoth_core'

    def ready(self):
        # Import dei signals per la registrazione dei receiver
        import thoth_core.signals
        
        # Initialize database plugins using the new plugin discovery system
        try:
            from .utilities.utils import initialize_database_plugins
            available_plugins = initialize_database_plugins()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize database plugins: {e}")
