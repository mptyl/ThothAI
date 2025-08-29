# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Integration tests for thoth_core views.
Tests all views via their URLs without modifying any code.
Records all errors and issues in test reports.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from thoth_core.models import Workspace, SqlDb, VectorDb, SqlTable, SqlColumn


class TestCoreViews(TestCase):
    """Test all thoth_core views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'test_class': 'TestCoreViews',
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        # Create test user
        self.user = User.objects.create_user(
            username='coreuser',
            password='testpass123',
            email='core@example.com'
        )
        
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
    
    def tearDown(self):
        """Save test report after each test class"""
        report_dir = 'tests/reports'
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"{report_dir}/test_core_views_{timestamp}.json"
        
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
    
    def test_index_view(self):
        """Test the index view"""
        view_name = 'index'
        try:
            # Test without authentication
            response = self.client.get(reverse('index'))
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(view_name, {
                    'message': 'Index view accessible without authentication',
                    'status_code': response.status_code
                })
            
            # Test with authentication
            self.client.login(username='coreuser', password='testpass123')
            response = self.client.get(reverse('index'))
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Index view returned status {response.status_code}',
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
    
    def test_api_login_view(self):
        """Test the API login view"""
        view_name = 'api_login'
        try:
            # Test with valid credentials
            response = self.api_client.post(reverse('api_login'), {
                'username': 'coreuser',
                'password': 'testpass123'
            })
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'API login failed with status {response.status_code}',
                    'status_code': response.status_code,
                    'response': response.data
                })
            elif 'token' not in response.data:
                self._record_error(view_name, {
                    'message': 'API login response missing token',
                    'response': response.data
                })
            
            # Test with invalid credentials
            response = self.api_client.post(reverse('api_login'), {
                'username': 'coreuser',
                'password': 'wrongpass'
            })
            
            if response.status_code == 200:
                self._record_error(view_name, {
                    'message': 'API login succeeded with invalid credentials',
                    'status_code': response.status_code
                })
            
            # Test with missing credentials
            response = self.api_client.post(reverse('api_login'), {})
            if response.status_code != 400:
                self._record_warning(view_name, {
                    'message': f'API login with missing credentials returned {response.status_code} instead of 400',
                    'status_code': response.status_code
                })
            
            self.report_data['summary'][view_name] = 'PASS'
            
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_test_token_view(self):
        """Test the token validation view"""
        view_name = 'test_token'
        try:
            # Test without token
            response = self.api_client.get('/api/test_token')
            if response.status_code != 401:
                self._record_warning(view_name, {
                    'message': f'Token test without auth returned {response.status_code} instead of 401',
                    'status_code': response.status_code
                })
            
            # Test with valid token
            self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
            response = self.api_client.get('/api/test_token')
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Token test with valid token returned {response.status_code}',
                    'status_code': response.status_code
                })
            
            # Test with invalid token
            self.api_client.credentials(HTTP_AUTHORIZATION='Token invalid123')
            response = self.api_client.get('/api/test_token')
            
            if response.status_code != 401:
                self._record_warning(view_name, {
                    'message': f'Token test with invalid token returned {response.status_code} instead of 401',
                    'status_code': response.status_code
                })
            
            self.report_data['summary'][view_name] = 'PASS'
            
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_get_user_workspaces_view(self):
        """Test the get user workspaces view"""
        view_name = 'get_user_workspaces'
        try:
            # Test without authentication
            response = self.api_client.get('/api/workspaces')
            if response.status_code != 401:
                self._record_warning(view_name, {
                    'message': f'Workspaces endpoint without auth returned {response.status_code} instead of 401',
                    'status_code': response.status_code
                })
            
            # Test with token authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
            response = self.api_client.get('/api/workspaces')
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Workspaces endpoint returned {response.status_code}',
                    'status_code': response.status_code
                })
            elif not isinstance(response.data, list):
                self._record_error(view_name, {
                    'message': 'Workspaces response is not a list',
                    'response_type': type(response.data).__name__
                })
            elif len(response.data) == 0:
                self._record_warning(view_name, {
                    'message': 'No workspaces returned for test user',
                    'response': response.data
                })
            
            self.report_data['summary'][view_name] = 'PASS'
            
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_table_list_by_db_name_view(self):
        """Test the table list by database name view"""
        view_name = 'TableListByDbNameView'
        try:
            # Test without authentication
            response = self.api_client.get(f'/api/sqldb/{self.sql_db.name}/tables/')
            if response.status_code != 401:
                self._record_warning(view_name, {
                    'message': f'Tables endpoint without auth returned {response.status_code} instead of 401',
                    'status_code': response.status_code
                })
            
            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
            response = self.api_client.get(f'/api/sqldb/{self.sql_db.name}/tables/')
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Tables endpoint returned {response.status_code}',
                    'status_code': response.status_code,
                    'db_name': self.sql_db.name
                })
            
            # Test with non-existent database
            response = self.api_client.get('/api/sqldb/nonexistent_db/tables/')
            if response.status_code != 404:
                self._record_warning(view_name, {
                    'message': f'Tables endpoint with invalid DB returned {response.status_code} instead of 404',
                    'status_code': response.status_code
                })
            
            self.report_data['summary'][view_name] = 'PASS'
            
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_table_columns_detail_view(self):
        """Test the table columns detail view"""
        view_name = 'TableColumnsDetailView'
        try:
            # Test without authentication
            url = f'/api/sqldb/{self.sql_db.name}/table/{self.table.name}/columns/'
            response = self.api_client.get(url)
            if response.status_code != 401:
                self._record_warning(view_name, {
                    'message': f'Columns endpoint without auth returned {response.status_code} instead of 401',
                    'status_code': response.status_code
                })
            
            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
            response = self.api_client.get(url)
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Columns endpoint returned {response.status_code}',
                    'status_code': response.status_code,
                    'url': url
                })
            
            # Test with non-existent table
            bad_url = f'/api/sqldb/{self.sql_db.name}/table/nonexistent_table/columns/'
            response = self.api_client.get(bad_url)
            if response.status_code != 404:
                self._record_warning(view_name, {
                    'message': f'Columns endpoint with invalid table returned {response.status_code} instead of 404',
                    'status_code': response.status_code
                })
            
            self.report_data['summary'][view_name] = 'PASS'
            
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_set_workspace_session_view(self):
        """Test the set workspace session view"""
        view_name = 'set_workspace_session'
        try:
            # Test without authentication
            response = self.client.post(reverse('set_workspace'), {
                'workspace_id': self.workspace.id
            })
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(view_name, {
                    'message': 'Set workspace accessible without authentication',
                    'status_code': response.status_code
                })
            
            # Test with authentication
            self.client.login(username='coreuser', password='testpass123')
            response = self.client.post(reverse('set_workspace'), {
                'workspace_id': self.workspace.id
            })
            
            if response.status_code != 204:
                self._record_error(view_name, {
                    'message': f'Set workspace returned {response.status_code} instead of 204',
                    'status_code': response.status_code
                })
            
            # Test with missing workspace_id
            response = self.client.post(reverse('set_workspace'), {})
            if response.status_code != 400:
                self._record_warning(view_name, {
                    'message': f'Set workspace without ID returned {response.status_code} instead of 400',
                    'status_code': response.status_code
                })
            
            # Test with invalid workspace_id
            response = self.client.post(reverse('set_workspace'), {
                'workspace_id': 99999
            })
            if response.status_code != 403:
                self._record_warning(view_name, {
                    'message': f'Set invalid workspace returned {response.status_code} instead of 403',
                    'status_code': response.status_code
                })
            
            self.report_data['summary'][view_name] = 'PASS'
            
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'
    
    def test_get_tables_by_database_ajax(self):
        """Test the AJAX get tables by database view"""
        view_name = 'get_tables_by_database'
        try:
            # This is an admin AJAX endpoint, requires login
            self.client.login(username='coreuser', password='testpass123')
            
            # Test with valid database_id
            response = self.client.get(reverse('get_tables_by_database'), {
                'database_id': self.sql_db.id
            })
            
            if response.status_code != 200:
                self._record_error(view_name, {
                    'message': f'Get tables AJAX returned {response.status_code}',
                    'status_code': response.status_code
                })
            
            # Test without database_id
            response = self.client.get(reverse('get_tables_by_database'))
            if response.status_code != 200:
                self._record_warning(view_name, {
                    'message': f'Get tables without ID returned {response.status_code}',
                    'status_code': response.status_code
                })
            
            self.report_data['summary'][view_name] = 'PASS'
            
        except Exception as e:
            self._record_error(view_name, {
                'message': str(e),
                'exception_type': type(e).__name__
            })
            self.report_data['summary'][view_name] = 'FAIL'


def generate_summary_report():
    """Generate a summary report of all test runs"""
    report_dir = 'tests/reports'
    summary = {
        'total_tests': 0,
        'total_errors': 0,
        'total_warnings': 0,
        'views_with_errors': [],
        'views_with_warnings': [],
        'all_passes': []
    }
    
    if os.path.exists(report_dir):
        for filename in os.listdir(report_dir):
            if filename.endswith('.json') and filename.startswith('test_core_views_'):
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
                        summary['total_tests'] += 1
                        if status == 'PASS' and view not in summary['all_passes']:
                            summary['all_passes'].append(view)
    
    summary_file = f"{report_dir}/summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary report generated: {summary_file}")
    return summary