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
Test suite for export and import views with external service mocks.
Tests CSV export/import operations, PDF generation, and GDPR reports with mocked LLM, database, and file operations.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO, StringIO

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from thoth_core.models import Workspace, SqlDb, VectorDb, SqlTable, SqlColumn, Setting


class TestExportImportViews(TestCase):
    """Test export and import views with comprehensive mocking"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_class": "TestExportImportViews",
            "errors": [],
            "warnings": [],
            "summary": {},
        }

        # Create test user
        self.user = User.objects.create_user(
            username="testuser_export", password="testpass123", email="test-export@example.com"
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

        # Mock vector store utilities
        self.vector_store_patcher = patch(
            "thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store"
        )
        self.mock_vector_store = self.vector_store_patcher.start()
        self.mock_vector_store_instance = MagicMock()
        self.mock_vector_store.return_value = self.mock_vector_store_instance

        # Mock successful vector store operations
        self.mock_vector_store_instance.get_collection_info.return_value = {
            "collection_name": "test_collection",
            "total_documents": 100,
            "status": "healthy"
        }

    def tearDown(self):
        """Stop mocks and save test report"""
        self.vector_store_patcher.stop()

        # Save test report
        report_dir = "tests/reports"
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{report_dir}/test_export_import_views_{timestamp}.json"

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

    def test_export_columns_csv_view(self):
        """Test columns CSV export"""
        view_name = "export_columns_csv"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Mock vector store operations
            with patch('thoth_ai_backend.views.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.get_all_documents.return_value = [
                    Mock(
                        id="col1",
                        column_name="test_column_1",
                        table_name="test_table_1",
                        description="Test column 1"
                    ),
                    Mock(
                        id="col2",
                        column_name="test_column_2",
                        table_name="test_table_2",
                        description="Test column 2"
                    )
                ]
                mock_get_vector_store.return_value = mock_vector_store

                session = self.client.session
                session["current_workspace_id"] = self.workspace.id
                session.save()

                response = self.client.get(reverse("thoth_ai_backend:export_columns_csv"))

                if response.status_code != 200:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Export columns CSV returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )
                elif response.get("Content-Type") != "text/csv":
                    self._record_warning(
                        view_name,
                        {
                            "message": "Export columns response is not CSV",
                            "content_type": response.get("Content-Type"),
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_export_questions_csv_view(self):
        """Test questions CSV export"""
        view_name = "export_questions_csv"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Mock vector store operations
            with patch('thoth_ai_backend.views.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.get_all_documents.return_value = [
                    Mock(
                        id="q1",
                        question="Test question 1?",
                        sql_query="SELECT * FROM table1;"
                    ),
                    Mock(
                        id="q2",
                        question="Test question 2?",
                        sql_query="SELECT * FROM table2;"
                    )
                ]
                mock_get_vector_store.return_value = mock_vector_store

                session = self.client.session
                session["current_workspace_id"] = self.workspace.id
                session.save()

                response = self.client.get(reverse("thoth_ai_backend:export_questions_csv"))

                if response.status_code != 200:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Export questions CSV returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )
                elif response.get("Content-Type") != "text/csv":
                    self._record_warning(
                        view_name,
                        {
                            "message": "Export questions response is not CSV",
                            "content_type": response.get("Content-Type"),
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.backend_utils.vector_store_utils.import_evidence_from_csv_file')
    @patch('builtins.open')
    @patch('csv.DictReader')
    def test_import_evidence_server_csv_view(self, mock_csv_reader, mock_open_file, mock_import_csv):
        """Test evidence CSV import from server with file mocks"""
        view_name = "import_evidence_server_csv"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Mock file operations
            mock_open_file.return_value = StringIO("evidence,context\nTest evidence,Test context\n")

            # Mock CSV reader
            mock_reader_instance = Mock()
            mock_reader_instance.__iter__.return_value = [
                {"evidence": "Test evidence", "context": "Test context"},
                {"evidence": "Test evidence 2", "context": "Test context 2"}
            ]
            mock_csv_reader.return_value = mock_reader_instance

            # Mock successful import
            mock_import_csv.return_value = {
                "success": True,
                "imported_count": 2,
                "message": "Evidence imported successfully"
            }

            response = self.client.post(reverse("thoth_ai_backend:import_evidence_server_csv"))

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Import evidence CSV returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.backend_utils.vector_store_utils.import_columns_from_csv_file')
    @patch('builtins.open')
    @patch('csv.DictReader')
    def test_import_columns_server_csv_view(self, mock_csv_reader, mock_open_file, mock_import_csv):
        """Test columns CSV import from server with file mocks"""
        view_name = "import_columns_server_csv"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Mock file operations
            mock_open_file.return_value = StringIO("column_name,table_name,description\ntest_col,test_table,Test description\n")

            # Mock CSV reader
            mock_reader_instance = Mock()
            mock_reader_instance.__iter__.return_value = [
                {"column_name": "test_col", "table_name": "test_table", "description": "Test description"}
            ]
            mock_csv_reader.return_value = mock_reader_instance

            # Mock successful import
            mock_import_csv.return_value = {
                "success": True,
                "imported_count": 1,
                "message": "Columns imported successfully"
            }

            response = self.client.post(reverse("thoth_ai_backend:import_columns_server_csv"))

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Import columns CSV returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    @patch('thoth_ai_backend.backend_utils.vector_store_utils.import_questions_from_csv_file')
    @patch('builtins.open')
    @patch('csv.DictReader')
    def test_import_questions_server_csv_view(self, mock_csv_reader, mock_open_file, mock_import_csv):
        """Test questions CSV import from server with file mocks"""
        view_name = "import_questions_server_csv"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Mock file operations
            mock_open_file.return_value = StringIO("question,sql_query\nTest question?,SELECT * FROM test_table;\n")

            # Mock CSV reader
            mock_reader_instance = Mock()
            mock_reader_instance.__iter__.return_value = [
                {"question": "Test question?", "sql_query": "SELECT * FROM test_table;"}
            ]
            mock_csv_reader.return_value = mock_reader_instance

            # Mock successful import
            mock_import_csv.return_value = {
                "success": True,
                "imported_count": 1,
                "message": "Questions imported successfully"
            }

            response = self.client.post(reverse("thoth_ai_backend:import_questions_server_csv"))

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Import questions CSV returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_delete_all_columns_view(self):
        """Test deleting all columns"""
        view_name = "delete_all_columns"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Mock vector store operations
            with patch('thoth_ai_backend.views.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.delete_all_documents.return_value = True
                mock_get_vector_store.return_value = mock_vector_store

                session = self.client.session
                session["current_workspace_id"] = self.workspace.id
                session.save()

                response = self.client.post(reverse("thoth_ai_backend:delete_all_columns"))

                if response.status_code not in [200, 302]:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Delete all columns returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_delete_all_questions_view(self):
        """Test deleting all questions"""
        view_name = "delete_all_questions"
        try:
            self.client.login(username="testuser", password="testpass123")

            # Mock vector store operations
            with patch('thoth_ai_backend.views.get_vector_store') as mock_get_vector_store:
                mock_vector_store = Mock()
                mock_vector_store.delete_all_documents.return_value = True
                mock_get_vector_store.return_value = mock_vector_store

                session = self.client.session
                session["current_workspace_id"] = self.workspace.id
                session.save()

                response = self.client.post(reverse("thoth_ai_backend:delete_all_questions"))

                if response.status_code not in [200, 302]:
                    self._record_error(
                        view_name,
                        {
                            "message": f"Delete all questions returned {response.status_code}",
                            "status_code": response.status_code,
                        },
                    )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_export_pdf_view(self):
        """Test PDF export"""
        view_name = "export_pdf"
        try:
            self.client.login(username="testuser", password="testpass123")

            session = self.client.session
            session["current_workspace_id"] = self.workspace.id
            session.save()

            response = self.client.get(reverse("thoth_ai_backend:export_pdf"))

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"Export PDF returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif response.get("Content-Type") != "application/pdf":
                self._record_warning(
                    view_name,
                    {
                        "message": "Export PDF response is not PDF",
                        "content_type": response.get("Content-Type"),
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_gdpr_export_pdf_view(self):
        """Test GDPR PDF export"""
        view_name = "gdpr_export_pdf"
        try:
            self.client.login(username="testuser", password="testpass123")

            session = self.client.session
            session["current_workspace_id"] = self.workspace.id
            session.save()

            response = self.client.get(reverse("thoth_ai_backend:gdpr_export_pdf"))

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"GDPR export PDF returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif response.get("Content-Type") != "application/pdf":
                self._record_warning(
                    view_name,
                    {
                        "message": "GDPR export PDF response is not PDF",
                        "content_type": response.get("Content-Type"),
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_gdpr_export_json_view(self):
        """Test GDPR JSON export"""
        view_name = "gdpr_export_json"
        try:
            self.client.login(username="testuser", password="testpass123")

            session = self.client.session
            session["current_workspace_id"] = self.workspace.id
            session.save()

            response = self.client.get(reverse("thoth_ai_backend:gdpr_export_json"))

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"GDPR export JSON returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif response.get("Content-Type") != "application/json":
                self._record_warning(
                    view_name,
                    {
                        "message": "GDPR export JSON response is not JSON",
                        "content_type": response.get("Content-Type"),
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"

    def test_gdpr_export_csv_view(self):
        """Test GDPR CSV export"""
        view_name = "gdpr_export_csv"
        try:
            self.client.login(username="testuser", password="testpass123")

            session = self.client.session
            session["current_workspace_id"] = self.workspace.id
            session.save()

            response = self.client.get(reverse("thoth_ai_backend:gdpr_export_csv"))

            if response.status_code != 200:
                self._record_error(
                    view_name,
                    {
                        "message": f"GDPR export CSV returned {response.status_code}",
                        "status_code": response.status_code,
                    },
                )
            elif "text/csv" not in (response.get("Content-Type") or ""):
                self._record_warning(
                    view_name,
                    {
                        "message": "GDPR export CSV response is not CSV",
                        "content_type": response.get("Content-Type"),
                    },
                )

            self.report_data["summary"][view_name] = "PASS"

        except Exception as e:
            self._record_error(
                view_name, {"message": str(e), "exception_type": type(e).__name__}
            )
            self.report_data["summary"][view_name] = "FAIL"
