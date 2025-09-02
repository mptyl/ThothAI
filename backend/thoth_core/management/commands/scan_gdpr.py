# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from thoth_core.models import SqlDb, Workspace
from thoth_core.thoth_ai.thoth_workflow.gdpr_scanner import scan_database_for_gdpr


class Command(BaseCommand):
    help = 'Scan databases for GDPR-sensitive data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace',
            type=int,
            help='Workspace ID to use for scanning'
        )
        parser.add_argument(
            '--database',
            type=str,
            help='Database name to scan'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Scan all databases'
        )

    def handle(self, *args, **options):
        workspace_id = options.get('workspace')
        database_name = options.get('database')
        scan_all = options.get('all')

        if not workspace_id:
            self.stdout.write(self.style.ERROR('Workspace ID is required'))
            raise CommandError('Please specify --workspace')

        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            raise CommandError(f'Workspace with ID {workspace_id} does not exist')

        # Build queryset
        if scan_all:
            databases = SqlDb.objects.all()
            self.stdout.write(f'Scanning all {databases.count()} databases for GDPR compliance...')
        elif database_name:
            try:
                databases = SqlDb.objects.filter(name=database_name)
                if not databases.exists():
                    raise CommandError(f'Database "{database_name}" not found')
            except SqlDb.DoesNotExist:
                raise CommandError(f'Database "{database_name}" not found')
        else:
            # Default to workspace database
            databases = SqlDb.objects.filter(id=workspace.sql_db.id)
            self.stdout.write(f'Scanning workspace database for GDPR: {workspace.sql_db.name}')

        # Process each database
        success_count = 0
        error_count = 0
        
        for db in databases:
            try:
                self.stdout.write(f'Scanning database "{db.name}"...')
                
                # Perform GDPR scan
                report = scan_database_for_gdpr(db.id)
                
                if "error" in report:
                    self.stdout.write(
                        self.style.ERROR(f'Error scanning "{db.name}": {report["error"]}')
                    )
                    error_count += 1
                    continue
                
                # Save report to database
                with transaction.atomic():
                    db.gdpr_report = report
                    db.gdpr_scan_date = timezone.now()
                    db.save(update_fields=["gdpr_report", "gdpr_scan_date"])
                
                # Display summary
                summary = report["summary"]
                risk_score = report.get("risk_score", {})
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Database "{db.name}": Found {summary["sensitive_columns"]} sensitive columns '
                        f'in {summary["tables_with_sensitive_data"]} tables. '
                        f'Risk: {risk_score.get("level", "N/A")} ({risk_score.get("score", 0)}/100)'
                    )
                )
                
                if summary["critical_findings"] > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [CRITICAL] {summary["critical_findings"]} critical findings need attention!'
                        )
                    )
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error scanning "{db.name}": {str(e)}')
                )
                error_count += 1
        
        # Final summary
        self.stdout.write('')
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully scanned {success_count} database(s) for GDPR compliance'
                )
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'{error_count} database(s) failed to scan')
            )