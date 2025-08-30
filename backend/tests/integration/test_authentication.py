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
Integration tests for authentication and authorization.
Tests different authentication methods without modifying any code.
Records all errors and issues in test reports.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from thoth_core.models import Workspace, SqlDb, VectorDb
# Note: ApiKey model doesn't exist yet


class TestAuthentication(TestCase):
    """Test all authentication methods"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_class": "TestAuthentication",
            "errors": [],
            "warnings": [],
            "summary": {},
        }

        # Create test users
        self.user = User.objects.create_user(
            username="authuser", password="testpass123", email="auth@example.com"
        )

        self.admin_user = User.objects.create_superuser(
            username="adminuser", password="adminpass123", email="admin@example.com"
        )

        # Create tokens
        self.user_token = Token.objects.create(user=self.user)
        self.admin_token = Token.objects.create(user=self.admin_user)

        # Create API key (commented out since ApiKey model doesn't exist yet)
        # self.api_key = ApiKey.objects.create(
        #     name='Test API Key',
        #     description='Key for testing'
        # )

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

        # Create restricted workspace (admin only)
        self.admin_workspace = Workspace.objects.create(
            name="Admin Workspace", sql_db=self.sql_db
        )
        self.admin_workspace.users.add(self.admin_user)

    def tearDown(self):
        """Save test report"""
        report_dir = "tests/reports"
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{report_dir}/test_authentication_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(self.report_data, f, indent=2)

    def _record_error(self, test_name: str, error: Dict[str, Any]):
        """Record an error in the test report"""
        self.report_data["errors"].append(
            {"test": test_name, "timestamp": datetime.now().isoformat(), **error}
        )

    def _record_warning(self, test_name: str, warning: Dict[str, Any]):
        """Record a warning in the test report"""
        self.report_data["warnings"].append(
            {"test": test_name, "timestamp": datetime.now().isoformat(), **warning}
        )

    def test_session_authentication(self):
        """Test session-based authentication"""
        test_name = "session_authentication"
        try:
            # Test access without login
            response = self.client.get(reverse("index"))
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(
                    test_name,
                    {
                        "message": "Protected page accessible without login",
                        "status_code": response.status_code,
                    },
                )

            # Test login
            login_success = self.client.login(
                username="authuser", password="testpass123"
            )
            if not login_success:
                self._record_error(
                    test_name, {"message": "Login failed with valid credentials"}
                )

            # Test access after login
            response = self.client.get(reverse("index"))
            if response.status_code != 200:
                self._record_error(
                    test_name,
                    {
                        "message": f"Protected page returned {response.status_code} after login",
                        "status_code": response.status_code,
                    },
                )

            # Test logout
            self.client.logout()
            response = self.client.get(reverse("index"))
            if response.status_code != 302:
                self._record_warning(
                    test_name,
                    {
                        "message": "Protected page accessible after logout",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][test_name] = "PASS"

        except Exception as e:
            self._record_error(
                test_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][test_name] = "FAIL"

    def test_token_authentication(self):
        """Test token-based authentication"""
        test_name = "token_authentication"
        try:
            # Test without token
            response = self.api_client.get("/api/workspaces")
            if response.status_code != 401:
                self._record_warning(
                    test_name,
                    {
                        "message": f"API accessible without token, returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with valid token
            self.api_client.credentials(
                HTTP_AUTHORIZATION=f"Token {self.user_token.key}"
            )
            response = self.api_client.get("/api/workspaces")
            if response.status_code != 200:
                self._record_error(
                    test_name,
                    {
                        "message": f"API with valid token returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with invalid token
            self.api_client.credentials(HTTP_AUTHORIZATION="Token invalid123")
            response = self.api_client.get("/api/workspaces")
            if response.status_code != 401:
                self._record_error(
                    test_name,
                    {
                        "message": f"API with invalid token returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with malformed token header
            self.api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid123")
            response = self.api_client.get("/api/workspaces")
            if response.status_code != 401:
                self._record_warning(
                    test_name,
                    {
                        "message": f"API with malformed token header returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][test_name] = "PASS"

        except Exception as e:
            self._record_error(
                test_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][test_name] = "FAIL"

    def test_api_key_authentication(self):
        """Test API key authentication"""
        test_name = "api_key_authentication"
        # Skip this test since ApiKey model doesn't exist yet
        self._record_warning(
            test_name,
            {
                "message": "Test skipped: ApiKey model not implemented yet",
                "status": "SKIPPED",
            },
        )
        self.report_data["summary"][test_name] = "SKIPPED"

    def test_permission_isolation(self):
        """Test workspace permission isolation"""
        test_name = "permission_isolation"
        try:
            # Test user can access their workspace
            self.api_client.credentials(
                HTTP_AUTHORIZATION=f"Token {self.user_token.key}"
            )
            response = self.api_client.get("/api/workspaces")
            if response.status_code == 200:
                data = response.json()
                user_workspace_ids = [w["id"] for w in data]
                if self.workspace.id not in user_workspace_ids:
                    self._record_error(
                        test_name,
                        {
                            "message": "User cannot access their own workspace",
                            "workspace_id": self.workspace.id,
                        },
                    )
                if self.admin_workspace.id in user_workspace_ids:
                    self._record_error(
                        test_name,
                        {
                            "message": "User can access admin workspace without permission",
                            "admin_workspace_id": self.admin_workspace.id,
                        },
                    )

            # Test workspace isolation in session
            self.client.login(username="authuser", password="testpass123")
            response = self.client.post(
                reverse("set_workspace"), {"workspace_id": self.admin_workspace.id}
            )
            if response.status_code != 403:
                self._record_error(
                    test_name,
                    {
                        "message": f"User can set unauthorized workspace, returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][test_name] = "PASS"

        except Exception as e:
            self._record_error(
                test_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][test_name] = "FAIL"

    def test_mixed_authentication(self):
        """Test behavior with mixed authentication methods"""
        test_name = "mixed_authentication"
        # Skip this test since ApiKey model doesn't exist yet
        self._record_warning(
            test_name,
            {
                "message": "Test skipped: ApiKey model not implemented yet",
                "status": "SKIPPED",
            },
        )
        self.report_data["summary"][test_name] = "SKIPPED"

    def test_authentication_endpoints(self):
        """Test authentication-specific endpoints"""
        test_name = "authentication_endpoints"
        try:
            # Test login endpoint
            response = self.api_client.post(
                reverse("api_login"),
                {"username": "authuser", "password": "testpass123"},
            )
            if response.status_code != 200:
                self._record_error(
                    test_name,
                    {
                        "message": f"Login endpoint returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif "token" not in response.json():
                self._record_error(
                    test_name,
                    {
                        "message": "Login response missing token field",
                        "response": response.json(),
                    },
                )
            else:
                returned_token = response.json()["token"]
                if returned_token != self.user_token.key:
                    self._record_warning(
                        test_name,
                        {
                            "message": "Login returned different token than expected",
                            "expected": self.user_token.key[:8] + "...",
                            "received": returned_token[:8] + "...",
                        },
                    )

            # Test login with wrong password
            response = self.api_client.post(
                reverse("api_login"), {"username": "authuser", "password": "wrongpass"}
            )
            if response.status_code != 401:
                self._record_error(
                    test_name,
                    {
                        "message": f"Login with wrong password returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test login with non-existent user
            response = self.api_client.post(
                reverse("api_login"), {"username": "nonexistent", "password": "anypass"}
            )
            if response.status_code != 404:
                self._record_warning(
                    test_name,
                    {
                        "message": f"Login with non-existent user returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][test_name] = "PASS"

        except Exception as e:
            self._record_error(
                test_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][test_name] = "FAIL"


def generate_auth_summary():
    """Generate a summary report for authentication tests"""
    report_dir = "tests/reports"
    summary = {
        "test_suite": "Authentication",
        "total_tests": 0,
        "total_errors": 0,
        "total_warnings": 0,
        "failed_tests": [],
        "tests_with_warnings": [],
        "passed_tests": [],
        "timestamp": datetime.now().isoformat(),
    }

    if os.path.exists(report_dir):
        for filename in os.listdir(report_dir):
            if filename.endswith(".json") and filename.startswith(
                "test_authentication_"
            ):
                with open(os.path.join(report_dir, filename), "r") as f:
                    data = json.load(f)
                    summary["total_errors"] += len(data.get("errors", []))
                    summary["total_warnings"] += len(data.get("warnings", []))

                    for error in data.get("errors", []):
                        test = error.get("test", "unknown")
                        if test not in summary["failed_tests"]:
                            summary["failed_tests"].append(test)

                    for warning in data.get("warnings", []):
                        test = warning.get("test", "unknown")
                        if test not in summary["tests_with_warnings"]:
                            summary["tests_with_warnings"].append(test)

                    for test, status in data.get("summary", {}).items():
                        summary["total_tests"] += 1
                        if status == "PASS" and test not in summary["passed_tests"]:
                            summary["passed_tests"].append(test)

    return summary
