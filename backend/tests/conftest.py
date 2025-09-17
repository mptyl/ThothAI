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
Pytest configuration and shared fixtures for tests.
Provides mock services and test data generators.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Configure Django settings for tests
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings")

# Setup Django before importing test modules
import django
django.setup()

import pytest
from django.conf import settings
from django.test import override_settings, TestCase

# Test database configuration - override for tests if needed
TEST_DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {"NAME": ":memory:"},
    }
}

@pytest.fixture(scope="session")
def django_db_setup():
    """Override Django database setup for tests"""
    settings.DATABASES = TEST_DATABASES


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.
    This eliminates the need to mark every test with @pytest.mark.django_db
    """
    pass


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for vector database operations"""
    with patch("thoth_ai_backend.vector_database_utils.QdrantClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        # Mock common Qdrant operations
        mock_instance.get_collection.return_value = MagicMock(
            vectors_count=0, points_count=0
        )
        mock_instance.search.return_value = []
        mock_instance.add.return_value = True
        mock_instance.delete.return_value = True
        mock_instance.update.return_value = True
        mock_instance.count.return_value = MagicMock(count=0)

        yield mock_instance


@pytest.fixture
def mock_celery_task():
    """Mock Celery tasks for async operations"""
    with patch("thoth_ai_backend.tasks.process_workspace_async.delay") as mock_task:
        mock_task.return_value = MagicMock(
            id="mock-task-id", state="SUCCESS", result={"status": "completed"}
        )
        yield mock_task


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for AI operations"""
    with patch(
        "thoth_core.thoth_ai.thoth_workflow.comment_generation_utils.setup_default_comment_llm_model"
    ) as mock_llm:
        mock_instance = MagicMock()
        mock_llm.return_value = mock_instance

        # Mock LLM responses
        mock_instance.run.return_value = {
            "generator": {
                "replies": [MagicMock(content='{"comment": "Test generated comment"}')]
            }
        }

        yield mock_instance


@pytest.fixture
def test_user(django_user_model):
    """Create a test user"""
    user = django_user_model.objects.create_user(
        username="testuser_conf", password="testpass123", email="test-conf@example.com"
    )
    return user


@pytest.fixture
def admin_user(django_user_model):
    """Create a test admin user"""
    user = django_user_model.objects.create_superuser(
        username="adminuser", password="adminpass123", email="admin@example.com"
    )
    return user


@pytest.fixture
def api_client():
    """Create a DRF API client"""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, test_user):
    """Create an authenticated API client"""
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def test_workspace(test_user):
    """Create a test workspace with database"""
    from thoth_core.models import Workspace, SqlDb, VectorDb

    vector_db = VectorDb.objects.create(
        name="test_vector_db", host="localhost", port=6334, db_type="qdrant"
    )

    sql_db = SqlDb.objects.create(
        name="test_sql_db",
        db_type="postgresql",
        host="localhost",
        port=5444,
        database="test_db",
        username="test_user",
        password="test_pass",
        vector_db=vector_db,
    )

    workspace = Workspace.objects.create(name="Test Workspace", sql_db=sql_db)
    workspace.users.add(test_user)

    return workspace


@pytest.fixture
def test_table(test_workspace):
    """Create a test table with columns"""
    from thoth_core.models import SqlTable, SqlColumn

    table = SqlTable.objects.create(name="test_table", sql_db=test_workspace.sql_db)

    # Create columns
    SqlColumn.objects.create(
        original_column_name="id", sql_table=table, data_format="INTEGER", pk_field=True
    )

    SqlColumn.objects.create(
        original_column_name="name", sql_table=table, data_format="VARCHAR(255)"
    )

    SqlColumn.objects.create(
        original_column_name="created_at", sql_table=table, data_format="TIMESTAMP"
    )

    return table


# Settings override is handled by Django's test framework


@pytest.fixture
def capture_test_reports():
    """Capture and save test reports"""
    reports = []

    def _capture_report(report_data):
        reports.append(report_data)

    yield _capture_report

    # Save all reports at the end
    if reports:
        import json
        from datetime import datetime

        report_dir = Path("tests/reports")
        report_dir.mkdir(exist_ok=True)

        summary_file = (
            report_dir
            / f"test_run_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(summary_file, "w") as f:
            json.dump(
                {
                    "test_run": datetime.now().isoformat(),
                    "total_reports": len(reports),
                    "reports": reports,
                },
                f,
                indent=2,
            )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest - Django is already configured by settings module"""
    pass


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add django_db marker to all tests
        item.add_marker(pytest.mark.django_db)

        # Add appropriate markers based on test location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


# Test environment variables
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    test_env = {
        "DJANGO_SETTINGS_MODULE": "Thoth.settings",
        "DATABASE_URL": "sqlite://:memory:",
        "QDRANT_URL": "http://localhost:6334",
        "CELERY_TASK_ALWAYS_EAGER": "True",
        "TESTING": "True",
    }

    for key, value in test_env.items():
        os.environ[key] = value

    yield

    # Clean up
    for key in test_env:
        os.environ.pop(key, None)
