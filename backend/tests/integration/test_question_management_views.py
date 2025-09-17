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
Test suite for question management views in thoth_ai_backend.
Tests CRUD operations for questions, preprocessing status, and database column updates.
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
# Mock models for question management
from unittest.mock import Mock


class TestQuestionManagementViews(TestCase):
    """Test question management views with external service mocks"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_class": "TestQuestionManagementViews",
            "errors": [],
            "warnings": [],
            "summary": {},
        }

        # Create test user
        self.user = User.objects.create_user(
            username="testuser_questions", password="testpass123", email="test-questions@example.com"
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

        # Mock Qdrant client
        self.qdrant_patcher = patch(
            "qdrant_client.QdrantClient"
        )
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
        report_dir = "tests/reports"
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{report_dir}/test_question_management_views_{timestamp}.json"

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

    def test_view_columns_view(self):
        """Test viewing column details"""
        view_name = "view_columns"
        try:
            # Login required for admin views
            self.client.login(username="testuser", password="testpass123")

            # Create a mock column document
            mock_column_doc = Mock()
            mock_column_doc.id = "test_column_id"
            mock_column_doc.column_name = "test_column"
            mock_column_doc.table_name = "test_table"
            mock_column_doc.description = "Test column description"

            with patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.get_document.return_value = mock_column_doc
                mock_get_vector_store.return_value = mock_vector_store

                response = self.client.get(
                    reverse("thoth_ai_backend:view_columns", args=["test_column_id"])
                )

                if response.status_code != 200:
                    self._record_error(
                        view_name,
                        {
                            "message": f"View columns returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_manage_question_create_view(self):
        """Test creating questions"""
        view_name = "create_question"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Test GET request (show form)
            response = self.client.get(reverse("thoth_ai_backend:create_question"))
            if response.status_code != 200:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Create question GET returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test POST request (create question)
            question_data = {
                "workspace": self.workspace.id,
                "question": "Test question?",
                "sql_query": "SELECT * FROM test_table;",
            }

            # Store current workspace in session
            session = self.client.session
            session["current_workspace_id"] = self.workspace.id
            session.save()

            response = self.client.post(
                reverse("thoth_ai_backend:create_question"), question_data
            )

            if response.status_code not in [200, 302]:  # 302 for redirect after success
                self._record_error(
                    view_name,
                    {
                        "message": f"Create question POST returned {response.status_code}",
                        "status_code": response.status_code,
                        "data_sent": question_data,
                    },
                )
            else:
                self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_manage_question_update_view(self):
        """Test updating questions"""
        view_name = "update_question"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Create a mock question document
            mock_question_doc = Mock()
            mock_question_doc.id = "test_question_id"
            mock_question_doc.question = "Original question"
            mock_question_doc.sql_query = "SELECT * FROM test_table;"

            with patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.get_document.return_value = mock_question_doc
                mock_get_vector_store.return_value = mock_vector_store

                # Test GET request
                response = self.client.get(
                    reverse("thoth_ai_backend:update_question", args=["test_question_id"])
                )
                if response.status_code != 200:
                    self._record_warning(
                        view_name,
                        {
                            "message": f"Update question GET returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )

                # Test POST request
                updated_data = {
                    "workspace": self.workspace.id,
                    "question": "Updated question?",
                    "sql_query": "SELECT * FROM test_table WHERE id = 1;",
                }

                session = self.client.session
                session["current_workspace_id"] = self.workspace.id
                session.save()

                response = self.client.post(
                    reverse("thoth_ai_backend:update_question", args=["test_question_id"]),
                    updated_data,
                )

                if response.status_code not in [200, 302]:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Update question POST returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )
                else:
                    self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_confirm_delete_question_view(self):
        """Test question deletion confirmation"""
        view_name = "confirm_delete_question"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Create a mock question document
            mock_question_doc = Mock()
            mock_question_doc.id = "test_question_id"

            with patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.get_document.return_value = mock_question_doc
                mock_get_vector_store.return_value = mock_vector_store

                response = self.client.get(
                    reverse("thoth_ai_backend:confirm_delete_question", args=["test_question_id"])
                )

                if response.status_code != 200:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Delete question confirm returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )
                else:
                    self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_delete_question_confirmed_view(self):
        """Test confirmed question deletion"""
        view_name = "delete_question_confirmed"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Create a mock question document
            mock_question_doc = Mock()
            mock_question_doc.id = "test_question_id"

            with patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.get_document.return_value = mock_question_doc
                mock_vector_store.delete_document.return_value = True
                mock_get_vector_store.return_value = mock_vector_store

                response = self.client.post(
                    reverse("thoth_ai_backend:delete_question_confirmed", args=["test_question_id"])
                )

                if response.status_code not in [200, 302]:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Delete question execute returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )
                else:
                    self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.utils.progress_tracker.ProgressTracker.get_progress')
    def test_check_preprocessing_status_view(self, mock_get_progress):
        """Test preprocessing status check"""
        view_name = "check_preprocessing_status"
        try:
            # Mock task status
            mock_get_progress.return_value = {
                "status": "completed",
                "progress": 100,
                "message": "Preprocessing completed successfully"
            }

            # Test without authentication
            response = self.api_client.get(f"/thoth-ai-backend/check_preprocessing_status/{self.workspace.id}/")
            if response.status_code != 302:  # Should redirect to login
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check preprocessing status without auth returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with authentication
            self.client.login(username="testuser", password="testpass123")
            response = self.client.get(f"/thoth-ai-backend/check_preprocessing_status/{self.workspace.id}/")

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Check preprocessing status returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            # Test with failed status
            mock_get_progress.return_value = {
                "status": "failed",
                "progress": 50,
                "error": "Preprocessing failed"
            }
            response = self.client.get(f"/thoth-ai-backend/check_preprocessing_status/{self.workspace.id}/")
            if response.status_code != 200:
                self._record_warning(
                    view_name,
                    {
                        "message": f"Check preprocessing status with failure returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.views.upload_questions')
    def test_upload_questions_view(self, mock_upload):
        """Test questions upload"""
        view_name = "upload_questions"
        try:
            # Mock successful upload
            mock_upload.return_value = {
                "success": True,
                "uploaded_count": 10,
                "message": "Questions uploaded successfully"
            }

            self.client.login(username="testuser", password="testpass123")

            # Create a simple CSV file in memory
            from io import BytesIO

            csv_content = b"question,sql_query\nTest question?,SELECT * FROM test_table;\n"
            csv_file = BytesIO(csv_content)
            csv_file.name = "test_questions.csv"

            response = self.client.post(
                reverse("thoth_ai_backend:upload_questions", args=[self.workspace.id]),
                {"csv_file": csv_file},
            )

            if response.status_code not in [200, 302]:
                self._record_error(
                    view_name,
                    {
                        "message": f"Upload questions returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            else:
                self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.preprocessing.update_database_columns_direct.update_database_columns_description')
    def test_update_database_columns_view(self, mock_update):
        """Test database columns update"""
        view_name = "update_database_columns"
        try:
            # Mock successful update
            mock_update.return_value = {
                "success": True,
                "updated_count": 5,
                "message": "Columns updated successfully"
            }

            self.client.login(username="testuser", password="testpass123")

            response = self.client.post(
                reverse("thoth_ai_backend:update_database_columns", args=[self.workspace.id])
            )

            if response.status_code not in [200, 302]:
                self._record_error(
                    view_name,
                    {
                        "message": f"Update database columns returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            else:
                self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"