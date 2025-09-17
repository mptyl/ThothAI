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
Test suite for progress views in thoth_ai_backend.
Tests async upload operations and progress checking functionality.
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

from thoth_core.models import Workspace, SqlDb, VectorDb, SqlTable, SqlColumn, Setting


class TestProgressViews(TestCase):
    """Test progress views with async operation mocks"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_class": "TestProgressViews",
            "errors": [],
            "warnings": [],
            "summary": {},
        }

        # Create test user
        self.user = User.objects.create_user(
            username="testuser_progress", password="testpass123", email="test-progress@example.com"
        )
        self.user.is_staff = True
        self.user.save()

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

        # Create test setting and attach to workspace
        self.setting = Setting.objects.create(name="Default Test Setting")
        self.workspace.setting = self.setting
        self.workspace.save()

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
        report_file = f"{report_dir}/test_progress_views_{timestamp}.json"

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

    @patch('thoth_ai_backend.views_progress.run_upload_in_background')
    def test_upload_evidences_async_view(self, mock_run_upload):
        """Test async evidence upload"""
        view_name = "upload_evidences_async"
        try:
            # Mock background upload task
            mock_task = Mock()
            mock_task.id = "test-evidence-task-id"
            mock_run_upload.return_value = mock_task

            # Test without authentication
            response = self.client.post(
                reverse("thoth_ai_backend:upload_evidences", args=[self.workspace.id])
            )
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(
                    view_name,
                    {
                        "message": f"Upload evidences async without auth returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.client.login(username="testuser", password="testpass123")
            response = self.client.post(
                reverse("thoth_ai_backend:upload_evidences", args=[self.workspace.id])
            )

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Upload evidences async returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            else:
                data = json.loads(response.content)
                if "task_id" not in data:
                    self._record_warning(
                        view_name,
                        {
                            "message": "Upload evidences async response missing task_id",
                            "response": data,
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.views_progress.run_upload_in_background')
    def test_upload_questions_async_view(self, mock_run_upload):
        """Test async questions upload"""
        view_name = "upload_questions_async"
        try:
            # Mock background upload task
            mock_task = Mock()
            mock_task.id = "test-questions-task-id"
            mock_run_upload.return_value = mock_task

            # Test without authentication
            response = self.client.post(
                reverse("thoth_ai_backend:upload_questions", args=[self.workspace.id])
            )
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(
                    view_name,
                    {
                        "message": f"Upload questions async without auth returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.client.login(username="testuser", password="testpass123")
            response = self.client.post(
                reverse("thoth_ai_backend:upload_questions", args=[self.workspace.id])
            )

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Upload questions async returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            else:
                data = json.loads(response.content)
                if "task_id" not in data:
                    self._record_warning(
                        view_name,
                        {
                            "message": "Upload questions async response missing task_id",
                            "response": data,
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.utils.progress_tracker.ProgressTracker.get_progress')
    def test_check_evidence_progress_view(self, mock_get_progress):
        """Test evidence upload progress check"""
        view_name = "check_evidence_progress"
        try:
            # Mock progress check
            mock_get_progress.return_value = {
                "status": "in_progress",
                "progress": 50,
                "processed": 500,
                "total": 1000,
                "message": "Processing evidence documents"
            }

            # Test without authentication
            response = self.client.get(
                reverse("thoth_ai_backend:check_evidence_progress", args=[self.workspace.id])
            )
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check evidence progress without auth returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.client.login(username="testuser", password="testpass123")
            response = self.client.get(
                reverse("thoth_ai_backend:check_evidence_progress", args=[self.workspace.id])
            )

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Check evidence progress returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with completed progress
            mock_get_progress.return_value = {
                "status": "completed",
                "progress": 100,
                "processed": 1000,
                "total": 1000,
                "message": "Evidence upload completed"
            }
            response = self.client.get(
                reverse("thoth_ai_backend:check_evidence_progress", args=[self.workspace.id])
            )
            if response.status_code != 200:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check evidence progress with completed status returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with failed progress
            mock_get_progress.return_value = {
                "status": "failed",
                "progress": 25,
                "processed": 250,
                "total": 1000,
                "error": "Upload failed due to invalid data"
            }
            response = self.client.get(
                reverse("thoth_ai_backend:check_evidence_progress", args=[self.workspace.id])
            )
            if response.status_code != 200:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check evidence progress with failed status returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.utils.progress_tracker.ProgressTracker.get_progress')
    def test_check_questions_progress_view(self, mock_get_progress):
        """Test questions upload progress check"""
        view_name = "check_questions_progress"
        try:
            # Mock progress check
            mock_get_progress.return_value = {
                "status": "in_progress",
                "progress": 75,
                "processed": 750,
                "total": 1000,
                "message": "Processing question documents"
            }

            # Test without authentication
            response = self.client.get(
                reverse("thoth_ai_backend:check_questions_progress", args=[self.workspace.id])
            )
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check questions progress without auth returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.client.login(username="testuser", password="testpass123")
            response = self.client.get(
                reverse("thoth_ai_backend:check_questions_progress", args=[self.workspace.id])
            )

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Check questions progress returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with not found progress
            mock_get_progress.return_value = {
                "status": "not_found",
                "progress": 0,
                "error": "No upload task found"
            }
            response = self.client.get(
                reverse("thoth_ai_backend:check_questions_progress", args=[self.workspace.id])
            )
            if response.status_code != 404:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check questions progress with not found status returned {response.status_code} instead of 404",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_upload_evidences_sync_fallback(self):
        """Test synchronous evidence upload fallback"""
        view_name = "upload_evidences_sync"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Create a simple CSV file in memory
            from io import BytesIO

            csv_content = b"evidence,context\nTest evidence,Test context\n"
            csv_file = BytesIO(csv_content)
            csv_file.name = "test_evidence.csv"

            with patch('thoth_ai_backend.views.upload_evidences') as mock_upload:
                mock_upload.return_value = {
                    "success": True,
                    "uploaded_count": 1,
                    "message": "Evidence uploaded successfully"
                }

                response = self.client.post(
                    reverse("thoth_ai_backend:upload_evidences_sync", args=[self.workspace.id]),
                    {"csv_file": csv_file},
                )

                if response.status_code not in [200, 302]:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Upload evidences sync returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_upload_questions_sync_fallback(self):
        """Test synchronous questions upload fallback"""
        view_name = "upload_questions_sync"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Create a simple CSV file in memory
            from io import BytesIO

            csv_content = b"question,sql_query\nTest question?,SELECT * FROM test_table;\n"
            csv_file = BytesIO(csv_content)
            csv_file.name = "test_questions.csv"

            with patch('thoth_ai_backend.views.upload_questions') as mock_upload:
                mock_upload.return_value = {
                    "success": True,
                    "uploaded_count": 1,
                    "message": "Questions uploaded successfully"
                }

                response = self.client.post(
                    reverse("thoth_ai_backend:upload_questions_sync", args=[self.workspace.id]),
                    {"csv_file": csv_file},
                )

                if response.status_code not in [200, 302]:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Upload questions sync returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"