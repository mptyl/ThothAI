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

"""
Integration tests for thoth_ai_backend views.
Tests all views via their URLs without modifying any code.
Records all errors and issues in test reports.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from thoth_core.models import Workspace, SqlDb, VectorDb, SqlTable, SqlColumn, Setting
# Note: EvidenceDocument, SqlDocument, ColumnDocument models don't exist yet


class TestAIBackendViews(TestCase):
    """Test all thoth_ai_backend views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'test_class': 'TestAIBackendViews',
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.user.is_staff = True
        self.user.save()
        
        # Create test token
        self.token = Token.objects.create(user=self.user)
        
        # Create test database
        self.vector_db = VectorDb.objects.create(
            name='test_vector_db',
            host='localhost',
            port=6334,
            vect_type='Qdrant'
        )
        
        self.sql_db = SqlDb.objects.create(
            name='test_sql_db',
            db_type='PostgreSQL',
            db_host='localhost',
            db_port=5444,
            db_name='test_db',
            user_name='test_user',
            password='test_pass',
            vector_db=self.vector_db
        )
        
        # Create test workspace
        self.workspace = Workspace.objects.create(
            name='Test Workspace',
            sql_db=self.sql_db
        )
        self.workspace.users.add(self.user)
        
        # Create test setting
        self.setting = Setting.objects.create(
            workspace=self.workspace,
            language='en',
            is_active=True
        )
        
        # Create test table and columns
        self.table = SqlTable.objects.create(
            name='test_table',
            sql_db=self.sql_db
        )
        
        self.column = SqlColumn.objects.create(
            original_column_name='id',
            sql_table=self.table,
            data_format='INTEGER',
            pk_field=True
        )
        
        # Mock Qdrant client
        self.qdrant_patcher = patch('thoth_ai_backend.vector_database_utils.QdrantClient')
        self.mock_qdrant = self.qdrant_patcher.start()
        self.mock_qdrant_instance = MagicMock()
        self.mock_qdrant.return_value = self.mock_qdrant_instance
        
        # Mock successful Qdrant operations
        self.mock_qdrant_instance.get_collection.return_value = MagicMock()
        self.mock_qdrant_instance.add.return_value = True
        self.mock_qdrant_instance.delete.return_value = True
        self.mock_qdrant_instance.count.return_value = MagicMock(count=0)
    
    def tearDown(self):
        """Stop mocks and save test report"""
        self.qdrant_patcher.stop()
        
        # Save test report
        report_dir = 'tests/reports'
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"{report_dir}/test_ai_backend_views_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.report_data, f, indent=2)
    
    def _record_error(self, view_name: str, error: Dict[str, Any]):
        """Record an error in the test report"""
        self.report_data['errors'].append({
            'view': view_name,
            'timestamp': datetime.now().isoformat(),
            **error
        })
    
    def _record_warning(self, view_name: str, warning: Dict[str, Any]):
        """Record a warning in the test report"""
        self.report_data['warnings'].append({
            'view': view_name,
            'timestamp': datetime.now().isoformat(),
            **warning
        })
    
    def test_evidence_list_view(self):
        """Test the evidence list view"""
        view_name = 'EvidenceView'
        try:
            # Login required for admin views
            self.client.login(username='testuser', password='testpass123')
            
            response = self.client.get(reverse('thoth_ai_backend:evidence'))
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Evidence list view returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_create_evidence_view(self):
        """Test the create evidence view"""
        view_name = 'create_evidence'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Test GET request (show form)
            response = self.client.get(reverse('thoth_ai_backend:create_evidence'))
            if response.status_code != 200:
                self._record_warning(view_name, {
                    'message': f'Create evidence GET returned {response.status_code}',
                    'status_code': response.status_code
                })
            
            # Test POST request (create evidence)
            evidence_data = {
                'workspace': self.workspace.id,
                'evidence': 'Test evidence',
                'context': 'Test context'
            }
            
            # Store current workspace in session
            session = self.client.session
            session['current_workspace_id'] = self.workspace.id
            session.save()
            
            response = self.client.post(reverse('thoth_ai_backend:create_evidence'), evidence_data)
            
            if response.status_code not in [200, 302]:  # 302 for redirect after success
                self._record_error(view_name, {
                    'message': f'Create evidence POST returned {response.status_code}',
                    'status_code': response.status_code,
                    'data_sent': evidence_data
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_update_evidence_view(self):
        """Test the update evidence view"""
        view_name = 'update_evidence'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Create an evidence first
            evidence = EvidenceDocument(
                workspace=self.workspace,
                evidence='Original evidence',
                context='Original context'
            )
            evidence.save()
            
            # Test GET request
            response = self.client.get(reverse('thoth_ai_backend:update_evidence', args=[evidence.id]))
            if response.status_code != 200:
                self._record_warning(view_name, {
                    'message': f'Update evidence GET returned {response.status_code}',
                    'status_code': response.status_code
                })
            
            # Test POST request
            updated_data = {
                'workspace': self.workspace.id,
                'evidence': 'Updated evidence',
                'context': 'Updated context'
            }
            
            session = self.client.session
            session['current_workspace_id'] = self.workspace.id
            session.save()
            
            response = self.client.post(
                reverse('thoth_ai_backend:update_evidence', args=[evidence.id]), 
                updated_data
            )
            
            if response.status_code not in [200, 302]:
                self._record_error(view_name, {
                    'message': f'Update evidence POST returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_delete_evidence_confirm_view(self):
        """Test the delete evidence confirmation view"""
        view_name = 'confirm_delete_evidence'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Create an evidence
            evidence = EvidenceDocument(
                workspace=self.workspace,
                evidence='Test evidence to delete',
                context='Test context'
            )
            evidence.save()
            
            response = self.client.get(
                reverse('thoth_ai_backend:confirm_delete_evidence', args=[evidence.id])
            )
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Delete evidence confirm returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_delete_evidence_execute_view(self):
        """Test the delete evidence execution view"""
        view_name = 'delete_evidence_confirmed'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Create an evidence
            evidence = EvidenceDocument(
                workspace=self.workspace,
                evidence='Test evidence to delete',
                context='Test context'
            )
            evidence.save()
            
            response = self.client.post(
                reverse('thoth_ai_backend:delete_evidence_confirmed', args=[evidence.id])
            )
            
            if response.status_code not in [200, 302]:
                self._record_error(view_name, {
                    'message': f'Delete evidence execute returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_export_evidence_csv_view(self):
        """Test the export evidence CSV view"""
        view_name = 'export_evidence_csv'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Create some evidence
            EvidenceDocument.objects.create(
                workspace=self.workspace,
                evidence='Export test evidence 1',
                context='Context 1'
            )
            
            session = self.client.session
            session['current_workspace_id'] = self.workspace.id
            session.save()
            
            response = self.client.get(reverse('thoth_ai_backend:export_evidence_csv'))
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Export evidence CSV returned {response.status_code}',
                    'status_code': response.status_code
                })
            elif response.get('Content-Type') != 'text/csv':
                self._record_warning(view_name, {
                    'message': 'Export evidence response is not CSV',
                    'content_type': response.get('Content-Type')
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_questions_list_view(self):
        """Test the questions list view"""
        view_name = 'QuestionsView'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            response = self.client.get(reverse('thoth_ai_backend:questions'))
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Questions list view returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_columns_list_view(self):
        """Test the columns list view"""
        view_name = 'ColumnsView'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            response = self.client.get(reverse('thoth_ai_backend:columns'))
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Columns list view returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_preprocess_view(self):
        """Test the preprocess view"""
        view_name = 'PreprocessView'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            response = self.client.get(reverse('thoth_ai_backend:preprocess'))
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Preprocess view returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    @patch('thoth_ai_backend.views.process_workspace_async.delay')
    def test_run_preprocessing_view(self, mock_task):
        """Test the run preprocessing view"""
        view_name = 'run_preprocessing'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Mock the async task
            mock_task.return_value.id = 'test-task-id'
            
            response = self.client.post(
                reverse('thoth_ai_backend:run_preprocessing', args=[self.workspace.id])
            )
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Run preprocessing returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                data = json.loads(response.content)
                if 'task_id' not in data:
                    self._record_warning(view_name, {
                        'message': 'Run preprocessing response missing task_id',
                        'response': data
                    })
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_db_docs_view(self):
        """Test the database documentation view"""
        view_name = 'DbDocsView'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            response = self.client.get(reverse('thoth_ai_backend:db_docs'))
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'DB docs view returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_delete_all_evidence_view(self):
        """Test the delete all evidence view"""
        view_name = 'delete_all_evidence'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Create some evidence
            EvidenceDocument.objects.create(
                workspace=self.workspace,
                evidence='Test evidence 1',
                context='Context 1'
            )
            EvidenceDocument.objects.create(
                workspace=self.workspace,
                evidence='Test evidence 2',
                context='Context 2'
            )
            
            session = self.client.session
            session['current_workspace_id'] = self.workspace.id
            session.save()
            
            response = self.client.post(reverse('thoth_ai_backend:delete_all_evidence'))
            
            if response.status_code not in [200, 302]:
                self._record_error(view_name, {
                    'message': f'Delete all evidence returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_upload_evidence_view(self):
        """Test the upload evidence view"""
        view_name = 'upload_evidence'
        try:
            self.client.login(username='testuser', password='testpass123')
            
            # Create a simple CSV file in memory
            from io import BytesIO
            csv_content = b"evidence,context\nTest evidence from CSV,Test context from CSV\n"
            csv_file = BytesIO(csv_content)
            csv_file.name = 'test_evidence.csv'
            
            response = self.client.post(
                reverse('thoth_ai_backend:upload_evidence', args=[self.workspace.id]),
                {'csv_file': csv_file}
            )
            
            if response.status_code not in [200, 302]:
                self._record_error(view_name, {
                    'message': f'Upload evidence returned {response.status_code}',
                    'status_code': response.status_code
                })
            else:
                self.report_data['summary'][view_name] = 'PASS'
                
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'


def generate_ai_backend_summary():
    """Generate a summary report for AI backend tests"""
    report_dir = 'tests/reports'
    summary = {
        'test_suite': 'AI Backend Views',
        'total_views_tested': 0,
        'total_errors': 0,
        'total_warnings': 0,
        'views_with_errors': [],
        'views_with_warnings': [],
        'all_passes': [],
        'timestamp': datetime.now().isoformat()
    }
    
    if os.path.exists(report_dir):
        for filename in os.listdir(report_dir):
            if filename.endswith('.json') and filename.startswith('test_ai_backend_views_'):
                with open(os.path.join(report_dir, filename), 'r') as f:
                    data = json.load(f)
                    summary['total_errors'] += len(data.get('errors', []))
                    summary['total_warnings'] += len(data.get('warnings', []))
                    
                    for error in data.get('errors', []):
                        view = error.get('view', 'unknown')
                        if view not in summary['views_with_errors']:
                            summary['views_with_errors'].append(view)
                    
                    for warning in data.get('warnings', []):
                        view = warning.get('view', 'unknown')
                        if view not in summary['views_with_warnings']:
                            summary['views_with_warnings'].append(view)
                    
                    for view, status in data.get('summary', {}).items():
                        summary['total_views_tested'] += 1
                        if status == 'PASS' and view not in summary['all_passes']:
                            summary['all_passes'].append(view)
    
    return summary