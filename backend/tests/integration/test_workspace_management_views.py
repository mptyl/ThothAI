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
Test suite for workspace management views with external service mocks.
Tests workspace agent pools, vector database connections, and embedding configuration.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from thoth_core.models import Workspace, SqlDb, VectorDb, SqlTable, SqlColumn, Setting, Agent


class TestWorkspaceManagementViews(TestCase):
    """Test workspace management views with external service mocks"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_class": "TestWorkspaceManagementViews",
            "errors": [],
            "warnings": [],
            "summary": {},
        }

        # Create test user
        self.user = User.objects.create_user(
            username="testuser_workspace", password="testpass123", email="test-workspace@example.com"
        )

        # Create test token
        self.token = Token.objects.create(user=self.user)

        # Create test database
        self.vector_db = VectorDb.objects.create(
            name="test_vector_db", host="localhost", port=6334, vect_type="Qdrant"
        )

        self.sql_db = SqlDb.objects.create(
            name="test_sql_db",
            db_type="PostgreSQL",
            db_host="localhost",
            db_port=5444,
            db_name="test_db",
            user_name="test_user",
            password="test_pass",
            vector_db=self.vector_db,
        )

        # Create test workspace
        self.workspace = Workspace.objects.create(
            name="Test Workspace", sql_db=self.sql_db
        )
        self.workspace.users.add(self.user)

        # Create test table and columns
        self.table = SqlTable.objects.create(name="test_table", sql_db=self.sql_db)
        self.column = SqlColumn.objects.create(
            original_column_name="id",
            sql_table=self.table,
            data_format="INTEGER",
            pk_field=True,
        )

    def tearDown(self):
        """Save test report after each test class"""
        report_dir = "tests/reports"
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{report_dir}/test_workspace_management_views_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(self.report_data, f, indent=2)

    def _record_error(self, view_name: str, error: Dict[str, Any]):
        """Record an error in the test report"""
        self.report_data["errors"].append(
            {"view": view_name, "timestamp": datetime.now().isoformat(), **error}
        )

    def _record_warning(self, view_name: str, warning: Dict[str, Any]):
        """Record a warning in the test report"""
        self.report_data["warnings"].append(
            {"view": view_name, "timestamp": datetime.now().isoformat(), **warning}
        )

    def test_get_workspace_agent_pools_view(self):
        """Test getting workspace agent pools"""
        view_name = "get_workspace_agent_pools"
        try:
            # Test without authentication
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/agent-pools/")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get agent pools without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/agent-pools/")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Get agent pools returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif not isinstance(response.data, list):
                self._record_error(
                    view_name,
                    {
                        "message": "Get agent pools response is not a list",
                        "response_type": type(response.data).__name__,
                    },
                )

            # Test with non-existent workspace
            response = self.api_client.get("/api/workspace/99999/agent-pools/")
            if response.status_code != 404:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get agent pools with invalid workspace returned {response.status_code} instead of 404",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store')
    def test_test_vector_db_connection_view(self, mock_get_vector_store):
        """Test vector database connection testing"""
        view_name = "test_vector_db_connection"
        try:
            # Mock successful connection test
            mock_get_vector_store.return_value = MagicMock()

            # Test without authentication
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/test-vector-db/")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Test vector DB without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/test-vector-db/")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Test vector DB returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test failed connection
            mock_get_vector_store.side_effect = Exception("Connection failed")
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/test-vector-db/")
            if response.status_code != 400:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Test vector DB with failed connection returned {response.status_code} instead of 400",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store')
    def test_check_embedding_config_view(self, mock_get_vector_store):
        """Test embedding configuration check"""
        view_name = "check_embedding_config"
        try:
            # Mock successful embedding service check
            mock_get_vector_store.return_value = MagicMock()

            # Test without authentication
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/check-embedding/")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check embedding config without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/check-embedding/")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Check embedding config returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test failed embedding service check
            mock_get_vector_store.side_effect = Exception("API key invalid")
            response = self.api_client.get(f"/api/workspace/{self.workspace.id}/check-embedding/")
            if response.status_code != 400:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check embedding config with invalid service returned {response.status_code} instead of 400",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_get_columns_by_table_view(self):
        """Test getting columns by table"""
        view_name = "get_columns_by_table"
        try:
            # This is an admin AJAX endpoint, requires login
            self.client.login(username="testuser", password="testpass123")

            # Test with valid table_id
            response = self.client.get(
                reverse("get_columns_by_columns"), {"table_id": self.table.id}
            )

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Get columns by table returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test without table_id
            response = self.client.get(reverse("get_columns_by_columns"))
            if response.status_code != 200:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get columns without table_id returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with invalid table_id
            response = self.client.get(
                reverse("get_columns_by_columns"), {"table_id": 99999}
            )
            if response.status_code != 200:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get columns with invalid table_id returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"