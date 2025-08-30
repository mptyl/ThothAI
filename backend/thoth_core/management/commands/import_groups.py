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
from django.contrib.auth.models import Group, Permission
from thoth_core.models import GroupProfile
import os
import csv

class Command(BaseCommand):
    help = 'Import Django auth groups from a CSV file and their associated group profiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='local',
            help='Source directory for CSV files (default: local)'
        )

    def parse_boolean(self, value):
        """Parse boolean values from CSV"""
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 't')
        return bool(value)

    def handle(self, *args, **options):
        source = options.get('source', 'local')
        io_dir = 'setup_csv'
        file_path = os.path.join(io_dir, 'groups.csv')
        
        # Check for source-specific file
        source_specific_path = os.path.join(io_dir, source, 'groups.csv')
        if os.path.exists(source_specific_path):
            file_path = source_specific_path
            self.stdout.write(f'Using source-specific file: {file_path}')
        else:
            self.stdout.write(f'Using default file: {file_path}')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        # Import groups with permissions
        groups_imported = 0
        groups_updated = 0
        permission_errors = 0
        
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    group, created = Group.objects.update_or_create(
                        id=row['id'],
                        defaults={'name': row['name']}
                    )
                    
                    # Handle permissions
                    permissions_field = row.get('permissions', '').strip()
                    if permissions_field:
                        try:
                            # Parse permission IDs from the CSV (comma-separated)
                            permission_ids = [int(pid.strip()) for pid in permissions_field.split(',') if pid.strip()]
                            
                            # Get the permission objects
                            permissions = Permission.objects.filter(id__in=permission_ids)
                            
                            # Set the permissions for the group
                            group.permissions.set(permissions)
                            
                            self.stdout.write(f'Set {permissions.count()} permissions for group: {group.name}')
                            
                        except (ValueError, Permission.DoesNotExist) as e:
                            permission_errors += 1
                            self.stdout.write(self.style.WARNING(
                                f'Error setting permissions for group {group.name}: {str(e)}'
                            ))
                    else:
                        # Clear permissions if none specified
                        group.permissions.clear()
                    
                    if created:
                        groups_imported += 1
                        self.stdout.write(self.style.SUCCESS(f'Created group: {group.name}'))
                    else:
                        groups_updated += 1
                        self.stdout.write(self.style.SUCCESS(f'Updated group: {group.name}'))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing group {row.get("name", "unknown")}: {str(e)}'))

        # Now import group profiles
        groupprofile_path = os.path.join(io_dir, 'groupprofile.csv')
        
        # Check for source-specific groupprofile file
        source_specific_groupprofile_path = os.path.join(io_dir, source, 'groupprofile.csv')
        if os.path.exists(source_specific_groupprofile_path):
            groupprofile_path = source_specific_groupprofile_path
            self.stdout.write(f'Using source-specific groupprofile file: {groupprofile_path}')
        else:
            self.stdout.write(f'Using default groupprofile file: {groupprofile_path}')

        profiles_imported = 0
        profiles_updated = 0
        profile_errors = 0

        if os.path.exists(groupprofile_path):
            self.stdout.write('Importing group profiles...')
            with open(groupprofile_path, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        group_id = row.get('group')
                        if not group_id:
                            self.stdout.write(self.style.WARNING(f"Missing group ID in row {reader.line_num}"))
                            profile_errors += 1
                            continue
                        
                        # Get the associated group
                        try:
                            group = Group.objects.get(id=group_id)
                        except Group.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f"Group with ID {group_id} not found"))
                            profile_errors += 1
                            continue
                        
                        # Parse boolean fields with defaults
                        show_sql = self.parse_boolean(row.get('show_sql', 'False'))
                        explain_generated_query = self.parse_boolean(row.get('explain_generated_query', 'True'))
                        
                        # Create or update group profile
                        model_id = row.get('id')
                        if model_id:
                            # Try to get existing group profile by ID or create new one with that ID
                            try:
                                group_profile = GroupProfile.objects.get(id=model_id)
                                # Update fields
                                group_profile.group = group
                                group_profile.show_sql = show_sql
                                group_profile.explain_generated_query = explain_generated_query
                                group_profile.save()
                                profiles_updated += 1
                                self.stdout.write(f"Updated GroupProfile for: {group.name}")
                            except GroupProfile.DoesNotExist:
                                # Create new group profile with specified ID
                                group_profile = GroupProfile.objects.create(
                                    id=model_id,
                                    group=group,
                                    show_sql=show_sql,
                                    explain_generated_query=explain_generated_query
                                )
                                profiles_imported += 1
                                self.stdout.write(f"Created GroupProfile for: {group.name}")
                        else:
                            # If no ID, use update_or_create with group
                            group_profile, created = GroupProfile.objects.update_or_create(
                                group=group,
                                defaults={
                                    'show_sql': show_sql,
                                    'explain_generated_query': explain_generated_query,
                                }
                            )
                            if created:
                                profiles_imported += 1
                                self.stdout.write(f"Created GroupProfile for: {group.name}")
                            else:
                                profiles_updated += 1
                                self.stdout.write(f"Updated GroupProfile for: {group.name}")
                    
                    except Exception as e:
                        profile_errors += 1
                        self.stdout.write(self.style.ERROR(f"Error processing GroupProfile for group ID {group_id}: {str(e)}"))
        else:
            self.stdout.write(self.style.WARNING(f'GroupProfile CSV file not found at {groupprofile_path}'))

        self.stdout.write(self.style.SUCCESS(
            f'Group import completed successfully. '
            f'Groups created: {groups_imported}, '
            f'Groups updated: {groups_updated}, '
            f'Profiles created: {profiles_imported}, '
            f'Profiles updated: {profiles_updated}, '
            f'Profile errors: {profile_errors}, '
            f'Permission errors: {permission_errors}'
        ))