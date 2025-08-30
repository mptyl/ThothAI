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

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from thoth_core.models import Workspace
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reset table comment status for workspaces stuck in RUNNING state"

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspace-id",
            type=int,
            help="Specific workspace ID to reset (optional)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Reset all workspaces with RUNNING status",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reset without confirmation",
        )

    def handle(self, *args, **options):
        workspace_id = options.get("workspace_id")
        reset_all = options.get("all")
        force = options.get("force")

        if not workspace_id and not reset_all:
            raise CommandError("You must specify either --workspace-id or --all")

        # Get workspaces to reset
        if workspace_id:
            try:
                workspaces = Workspace.objects.filter(id=workspace_id)
                if not workspaces.exists():
                    raise CommandError(f"Workspace with ID {workspace_id} not found")
            except ValueError:
                raise CommandError(f"Invalid workspace ID: {workspace_id}")
        else:
            workspaces = Workspace.objects.filter(
                table_comment_status=Workspace.PreprocessingStatus.RUNNING
            )

        if not workspaces.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No workspaces found with RUNNING table comment status"
                )
            )
            return

        # Show what will be reset
        self.stdout.write(f"Found {workspaces.count()} workspace(s) to reset:")
        for workspace in workspaces:
            self.stdout.write(f"  - {workspace.name} (ID: {workspace.id})")
            if workspace.table_comment_start_time:
                self.stdout.write(f"    Started: {workspace.table_comment_start_time}")
            if workspace.table_comment_task_id:
                self.stdout.write(f"    Task ID: {workspace.table_comment_task_id}")

        # Confirmation
        if not force:
            confirm = input("\nDo you want to proceed with the reset? (yes/no): ")
            if confirm.lower() not in ["yes", "y"]:
                self.stdout.write(self.style.WARNING("Operation cancelled"))
                return

        # Perform the reset
        reset_count = 0
        for workspace in workspaces:
            try:
                old_status = workspace.table_comment_status
                old_task_id = workspace.table_comment_task_id

                workspace.table_comment_status = Workspace.PreprocessingStatus.IDLE
                workspace.table_comment_task_id = None
                workspace.table_comment_log = (
                    f"Status reset manually via management command at {timezone.now()}"
                )
                workspace.table_comment_end_time = timezone.now()
                workspace.save()

                reset_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Reset workspace "{workspace.name}" (ID: {workspace.id})'
                    )
                )

                # Log the action
                logger.info(
                    f"Table comment status reset for workspace {workspace.id} "
                    f"(was: {old_status}, task_id: {old_task_id})"
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to reset workspace "{workspace.name}" (ID: {workspace.id}): {e}'
                    )
                )
                logger.error(
                    f"Failed to reset workspace {workspace.id}: {e}", exc_info=True
                )

        if reset_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\nSuccessfully reset {reset_count} workspace(s)")
            )
        else:
            self.stdout.write(self.style.WARNING("No workspaces were reset"))
