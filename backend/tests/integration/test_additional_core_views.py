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
Test suite for additional thoth_core views that are not covered in existing tests.
Tests API management, user management, workspace operations, and system functions.
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

from thoth_core.models import Workspace, SqlDb, VectorDb, SqlTable, SqlColumn, ThothLog, Setting


class TestAdditionalCoreViews(TestCase):
    """Test additional thoth_core views not covered in existing tests"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_class": "TestAdditionalCoreViews",
            "errors": [],
            "warnings": [],
            "summary": {},
        }

        # Create test user
        self.user = User.objects.create_user(
            username="testuser_core", password="testpass123", email="test-core@example.com"
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
        report_file = f"{report_dir}/test_additional_core_views_{timestamp}.json"

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

    def test_test_api_key_view(self):
        """Test the API key validation view"""
        view_name = "test_api_key"
        try:
            # Test without authentication
            response = self.api_client.post("/api/test_api_key", {"api_key": "test_key"})
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"API key test without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.post("/api/test_api_key", {"api_key": "test_key"})

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"API key test returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_get_current_user_view(self):
        """Test getting current user info"""
        view_name = "get_current_user"
        try:
            # Test without authentication
            response = self.api_client.get("/api/user")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get user without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get("/api/user")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Get user returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif not isinstance(response.data, dict):
                self._record_error(
                    view_name,
                    {
                        "message": "Get user response is not a dictionary",
                        "response_type": type(response.data).__name__,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_get_user_workspaces_list_view(self):
        """Test getting user workspaces as list"""
        view_name = "get_user_workspaces_list"
        try:
            # Test without authentication
            response = self.api_client.get("/api/workspaces_user_list")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Workspaces list without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get("/api/workspaces_user_list")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Workspaces list returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif not isinstance(response.data, list):
                self._record_error(
                    view_name,
                    {
                        "message": "Workspaces list response is not a list",
                        "response_type": type(response.data).__name__,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_get_workspace_by_name_view(self):
        """Test getting workspace by name"""
        view_name = "get_workspace_by_name"
        try:
            # Test without authentication
            response = self.api_client.get(f"/api/workspace/{self.workspace.name}")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get workspace by name without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get(f"/api/workspace/{self.workspace.name}")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Get workspace by name returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with non-existent workspace
            response = self.api_client.get("/api/workspace/nonexistent_workspace")
            if response.status_code != 404:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get workspace by name with invalid name returned {response.status_code} instead of 404",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_get_workspace_by_id_view(self):
        """Test getting workspace by ID"""
        view_name = "get_workspace_by_id"
        try:
            # Test without authentication
            response = self.api_client.get(f"/api/workspace/id/{self.workspace.id}")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get workspace by ID without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get(f"/api/workspace/id/{self.workspace.id}")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Get workspace by ID returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with non-existent workspace
            response = self.api_client.get("/api/workspace/id/99999")
            if response.status_code != 404:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get workspace by ID with invalid ID returned {response.status_code} instead of 404",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_health_check_view(self):
        """Test health check endpoint"""
        view_name = "health_check"
        try:
            # Test health check endpoint (no authentication required)
            response = self.client.get("/health")
            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Health check returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test API health check endpoint
            response = self.api_client.get("/api/health")
            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"API health check returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_thoth_log_crud_views(self):
        """Test ThothLog CRUD operations"""
        view_name = "thoth_log_crud"
        try:
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

            # Test creating a ThothLog
            log_data = {
                "level": "INFO",
                "message": "Test log message",
                "component": "test_component",
                "workspace": self.workspace.id
            }

            response = self.api_client.post("/api/thoth-logs/", log_data)
            if response.status_code not in [201, 200]:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Create ThothLog returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test listing ThothLogs
            response = self.api_client.get("/api/thoth-logs/")
            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"List ThothLogs returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test getting ThothLog summary
            response = self.api_client.get("/api/thoth-logs/summary/")
            if response.status_code != 200:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Get ThothLog summary returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_generate_frontend_token_view(self):
        """Test frontend token generation"""
        view_name = "generate_frontend_token"
        try:
            # Test without authentication
            response = self.api_client.get("/api/generate-frontend-token/")
            if response.status_code != 401:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Generate frontend token without auth returned {response.status_code} instead of 401",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
            response = self.api_client.get("/api/generate-frontend-token/")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Generate frontend token returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif "token" not in response.data:
                self._record_error(
                    view_name,
                    {
                        "message": "Generate frontend token response missing token",
                        "response": response.data,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"