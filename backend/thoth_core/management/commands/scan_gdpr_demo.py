# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import json
from django.core.management.base import BaseCommand
from thoth_core.models import Workspace, SqlDb
from thoth_core.thoth_ai.thoth_workflow.gdpr_scanner import scan_database_for_gdpr, generate_gdpr_html
from thoth_core.utilities.shared_paths import get_export_path


class Command(BaseCommand):
    help = 'Scan demo workspace databases for GDPR-sensitive data (ID=1)'

    def handle(self, *args, **options):
        try:
            # Get the demo workspace (ID=1)
            workspace = Workspace.objects.get(id=1)
            self.stdout.write(f'Found demo workspace: {workspace.name}')
            
            # Get all databases in the workspace
            databases = SqlDb.objects.filter(workspace=workspace)
            
            if not databases.exists():
                self.stdout.write(
                    self.style.WARNING('No databases found in demo workspace')
                )
                return
            
            self.stdout.write(f'Scanning {databases.count()} database(s) for GDPR compliance...\n')
            
            # Process each database
            success_count = 0
            for db in databases:
                self.stdout.write(f'Scanning: {db.name}...')
                try:
                    # Perform GDPR scan
                    report = scan_database_for_gdpr(db.id)
                    
                    # Display summary
                    sensitive_tables = len(report.get('sensitive_tables', []))
                    total_fields = sum(
                        len(t.get('sensitive_columns', [])) 
                        for t in report.get('sensitive_tables', [])
                    )
                    
                    if sensitive_tables > 0:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  → Found {sensitive_tables} tables with {total_fields} sensitive fields'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f'  → No sensitive data detected')
                        )
                    
                    # Save to database
                    db.gdpr_scan_result = json.dumps(report, indent=2)
                    db.save()
                    
                    # Also save HTML report
                    html_content = generate_gdpr_html(report)
                    html_path = get_export_path(f'gdpr_scan_{db.name}_{db.id}.html')
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ GDPR scan completed for {db.name}')
                    )
                    self.stdout.write(f'  Report saved to: {html_path}')
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error scanning {db.name}: {str(e)}')
                    )
            
            # Overall summary
            self.stdout.write('\n' + '='*60)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Completed: {success_count} database(s) scanned successfully'
                )
            )
            
            # Display risk summary if any sensitive data found
            for db in databases:
                if db.gdpr_scan_result:
                    try:
                        report = json.loads(db.gdpr_scan_result)
                        risk_summary = report.get('risk_summary', {})
                        if any(risk_summary.values()):
                            self.stdout.write(f'\n{db.name} Risk Summary:')
                            for level, count in risk_summary.items():
                                if count > 0:
                                    style = (
                                        self.style.ERROR if level == 'HIGH' else 
                                        self.style.WARNING if level == 'MEDIUM' else 
                                        self.style.SUCCESS
                                    )
                                    self.stdout.write(style(f'  {level}: {count} fields'))
                    except:
                        pass
                        
        except Workspace.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Demo workspace (ID=1) not found. Please run load_defaults first.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )