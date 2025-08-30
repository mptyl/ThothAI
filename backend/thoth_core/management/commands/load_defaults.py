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
from django.core.management import call_command
from django.utils import timezone
import time
import gc
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Import default system values in 5 sequential levels:
    
LEVEL 1: Base System Defaults (No Dependencies)
- Groups: Default user groups and permissions
- Users: System users and admin accounts
- BasicAiModels: Foundation AI model configurations
- VectorDbs: Vector database connections and settings

LEVEL 2: AI Model Dependencies
- AiModels: Advanced AI model configurations (depends on BasicAiModel)

LEVEL 3: Application Components
- Agents: AI agent definitions (depends on AiModel)
- Settings: System settings and configurations (depends on AiModel)

LEVEL 4: Database Structure
- Database schema: Tables, columns, and relationships for SQL databases

LEVEL 5: Workspace Configuration
- Workspaces: Complete workspace setups with all dependencies (SQL DB, Settings, AI Models, Agents, Users)

Usage Examples:
  python manage.py import_defaults          # Import all levels
  python manage.py import_defaults --only-level 1  # Import only base defaults
  python manage.py import_defaults --skip-level 2 3  # Skip levels 2 and 3
"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-level",
            type=int,
            nargs="*",
            help="Skip specific levels (1-5). Example: --skip-level 1 2",
        )
        parser.add_argument(
            "--only-level", type=int, help="Run only a specific level (1-5)"
        )
        parser.add_argument(
            "--no-cache-clear",
            action="store_true",
            help="Skip cache clearing between imports (faster but may cause issues)",
        )
        parser.add_argument(
            "--source",
            type=str,
            choices=["local", "docker"],
            default="docker",
            help="Source of CSV files to import (local or docker)",
        )
        # Selective cleaning options
        parser.add_argument(
            "--clean-db-structure",
            action="store_true",
            help="Clean SqlDbs and related tables (SqlTable, SqlColumn, Relationship) before import",
        )
        parser.add_argument(
            "--clean-workspaces",
            action="store_true",
            help="Clean Workspaces before import",
        )
        parser.add_argument(
            "--clean-ai-config",
            action="store_true",
            help="Clean AI configurations (AiModels, Agents, Settings) before import",
        )
        parser.add_argument(
            "--clean-vector-dbs",
            action="store_true",
            help="Clean VectorDbs before import",
        )
        parser.add_argument(
            "--clean-users",
            action="store_true",
            help="Clean Users and Groups before import (WARNING: This will delete all users including superusers!)",
        )
        parser.add_argument(
            "--clean-all",
            action="store_true",
            help="Clean ALL data before import (equivalent to using all --clean-* flags)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting default values import process"))
        self.stdout.write("=" * 80)

        skip_levels = options.get("skip_level", [])
        only_level = options.get("only_level")
        clear_cache = not options.get("no_cache_clear", False)
        source = options.get("source", "docker")

        # Handle cleaning options
        clean_all = options.get("clean_all", False)
        clean_db_structure = options.get("clean_db_structure", False) or clean_all
        clean_workspaces = options.get("clean_workspaces", False) or clean_all
        clean_ai_config = options.get("clean_ai_config", False) or clean_all
        clean_vector_dbs = options.get("clean_vector_dbs", False) or clean_all
        clean_users = options.get("clean_users", False) or clean_all

        # Clean existing data if requested
        if any(
            [
                clean_db_structure,
                clean_workspaces,
                clean_ai_config,
                clean_vector_dbs,
                clean_users,
            ]
        ):
            self.clean_existing_data(
                clean_db_structure=clean_db_structure,
                clean_workspaces=clean_workspaces,
                clean_ai_config=clean_ai_config,
                clean_vector_dbs=clean_vector_dbs,
                clean_users=clean_users,
            )

        self.stdout.write(f"Importing default values from: {source}")

        # Define import levels with their dependencies
        levels = {
            1: {
                "name": "Base System Defaults (No Dependencies)",
                "commands": [
                    "import_groups",
                    "import_users",
                    "import_basicaimodels",
                    "import_vectordb",
                ],
            },
            2: {"name": "AI Model Dependencies", "commands": ["import_aimodels"]},
            3: {
                "name": "Application Components",
                "commands": ["import_agents", "import_settings"],
            },
            4: {"name": "Database Structure", "commands": ["import_db_structure"]},
            5: {"name": "Workspace Configuration", "commands": ["import_workspace"]},
        }

        start_time = timezone.now()
        total_errors = 0

        for level_num in sorted(levels.keys()):
            # Skip level if requested
            if skip_levels and level_num in skip_levels:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Level {level_num}: {levels[level_num]['name']}"
                    )
                )
                continue

            # Run only specific level if requested
            if only_level and level_num != only_level:
                continue

            level_info = levels[level_num]
            self.stdout.write(
                f"\n{'=' * 20} LEVEL {level_num}: {level_info['name']} {'=' * 20}"
            )

            level_start_time = timezone.now()
            level_errors = 0

            for command in level_info["commands"]:
                try:
                    self.stdout.write(f"\n--- Executing: {command} ---")
                    command_start_time = timezone.now()

                    # Execute the command with source parameter
                    call_command(command, verbosity=1, source=source)

                    command_duration = timezone.now() - command_start_time
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {command} completed in {command_duration.total_seconds():.2f}s"
                        )
                    )

                    # Clear cache after each command to prevent issues
                    if clear_cache:
                        self.clear_all_caches()

                except Exception as e:
                    level_errors += 1
                    total_errors += 1
                    self.stdout.write(self.style.ERROR(f"✗ {command} failed: {str(e)}"))
                    logger.error(f"Command {command} failed: {str(e)}", exc_info=True)

            level_duration = timezone.now() - level_start_time

            if level_errors == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Level {level_num} completed successfully in {level_duration.total_seconds():.2f}s"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"\n✗ Level {level_num} completed with {level_errors} errors in {level_duration.total_seconds():.2f}s"
                    )
                )

            # Pause between levels for stabilization
            if clear_cache and level_num < max(levels.keys()):
                self.stdout.write("Pausing for system stabilization...")
                time.sleep(2)

        total_duration = timezone.now() - start_time

        self.stdout.write("\n" + "=" * 80)
        if total_errors == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"🎉 All default values imported successfully in {total_duration.total_seconds():.2f}s"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"[WARNING] Default values import completed with {total_errors} errors in {total_duration.total_seconds():.2f}s"
                )
            )

        # Final verification
        self.verify_imports()

    def clean_existing_data(
        self,
        clean_db_structure=False,
        clean_workspaces=False,
        clean_ai_config=False,
        clean_vector_dbs=False,
        clean_users=False,
    ):
        """Selectively clean existing data based on flags to avoid ID conflicts"""
        self.stdout.write(
            self.style.WARNING("\n--- Cleaning existing data before import ---")
        )

        from django.contrib.auth.models import User, Group
        from thoth_core.models import (
            Workspace,
            SqlDb,
            SqlTable,
            SqlColumn,
            Relationship,
            AiModel,
            BasicAiModel,
            Agent,
            Setting,
            VectorDb,
        )

        total_deleted = 0

        # Clean Workspaces (should be done first as they reference many other models)
        if clean_workspaces:
            count = Workspace.objects.count()
            if count > 0:
                Workspace.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} Workspace(s)")

        # Clean AI configurations
        if clean_ai_config:
            # Delete Agents first (they reference AiModels)
            count = Agent.objects.count()
            if count > 0:
                Agent.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} Agent(s)")

            # Delete Settings (they reference AiModels)
            count = Setting.objects.count()
            if count > 0:
                Setting.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} Setting(s)")

            # Delete AiModels (they reference BasicAiModels)
            count = AiModel.objects.count()
            if count > 0:
                AiModel.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} AiModel(s)")

            # Delete BasicAiModels
            count = BasicAiModel.objects.count()
            if count > 0:
                BasicAiModel.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} BasicAiModel(s)")

        # Clean database structure
        if clean_db_structure:
            # Delete Relationships first
            count = Relationship.objects.count()
            if count > 0:
                Relationship.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} Relationship(s)")

            # Delete Columns
            count = SqlColumn.objects.count()
            if count > 0:
                SqlColumn.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} SqlColumn(s)")

            # Delete Tables
            count = SqlTable.objects.count()
            if count > 0:
                SqlTable.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} SqlTable(s)")

            # Delete SqlDbs
            count = SqlDb.objects.count()
            if count > 0:
                SqlDb.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} SqlDb(s)")

        # Clean VectorDbs
        if clean_vector_dbs:
            count = VectorDb.objects.count()
            if count > 0:
                VectorDb.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} VectorDb(s)")

        # Clean Users and Groups (WARNING: This is destructive!)
        if clean_users:
            self.stdout.write(
                self.style.WARNING(
                    "  WARNING: Deleting all users including superusers!"
                )
            )

            # Delete Users first (they reference Groups)
            count = User.objects.count()
            if count > 0:
                User.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} User(s)")

            # Delete Groups
            count = Group.objects.count()
            if count > 0:
                Group.objects.all().delete()
                total_deleted += count
                self.stdout.write(f"  Deleted {count} Group(s)")

        if total_deleted > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Data cleanup completed successfully. Total records deleted: {total_deleted}"
                )
            )
        else:
            self.stdout.write("  No data to clean")

        # Clear caches after deletion
        self.clear_all_caches()
        self.stdout.write("")

    def clear_all_caches(self):
        """Clear all caches to ensure fresh data access"""
        import time

        # Close all database connections
        from django.db import connections

        for conn in connections.all():
            conn.close()

        # Clear Django cache
        from django.core.cache import cache

        cache.clear()

        # Reset queries
        from django.db import reset_queries

        reset_queries()

        # Force garbage collection
        gc.collect()

        # Small delay for Docker environment to ensure transaction visibility
        time.sleep(0.2)

        self.stdout.write("  Cache cleared")

    def verify_imports(self):
        """Verify that imports were successful by checking record counts"""
        self.stdout.write("\n--- Import Verification ---")

        try:
            from django.contrib.auth.models import User, Group
            from thoth_core.models import (
                BasicAiModel,
                VectorDb,
                AiModel,
                SqlDb,
                Agent,
                Setting,
                Workspace,
                SqlColumn,
                Relationship,
            )

            models_to_check = [
                (Group, "Groups"),
                (User, "Users"),
                (BasicAiModel, "BasicAiModels"),
                (VectorDb, "VectorDbs"),
                (AiModel, "AiModels"),
                (SqlDb, "SqlDbs"),
                (Agent, "Agents"),
                (Setting, "Settings"),
                (Workspace, "Workspaces"),
                (SqlColumn, "SqlColumns"),
                (Relationship, "Relationships"),
            ]

            for model, name in models_to_check:
                try:
                    count = model.objects.count()
                    if count > 0:
                        self.stdout.write(f"✓ {name}: {count} records")
                    else:
                        self.stdout.write(self.style.WARNING(f"⚠ {name}: 0 records"))
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"✗ {name}: Error counting - {str(e)}")
                    )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Verification failed: {str(e)}"))

    def get_level_description(self, level_num):
        """Get a description of what each level imports"""
        descriptions = {
            1: "Base system defaults: Groups, Users, BasicAiModels, VectorDbs",
            2: "AI model configurations: AiModels (depends on BasicAiModel)",
            3: "Application components: Agents, Settings (both depend on AiModel)",
            4: "Database structure: Complete SQL database schema setup",
            5: "Workspace setup: Full workspace configurations with all dependencies",
        }
        return descriptions.get(level_num, "Unknown level")
