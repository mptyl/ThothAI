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

from django.apps import AppConfig


class ThothCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "thoth_core"

    def ready(self):
        # Import dei signals per la registrazione dei receiver

        # Initialize database plugins using the new plugin discovery system
        try:
            from .utilities.utils import initialize_database_plugins

            available_plugins = initialize_database_plugins()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize database plugins: {e}")
