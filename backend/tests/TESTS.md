# Tests Documentation

This document provides comprehensive documentation for all tests in the ThothAI backend project, including test organization, purpose, and execution instructions.

## Test Structure Overview

The test suite is organized into the following categories:

- **Integration Tests** (`tests/integration/`) - API endpoint testing with mocked external services
- **Unit Tests** (`tests/`) - Individual component testing
- **Conftest** (`tests/conftest.py`) - Shared fixtures and test configuration

## Integration Tests

### `test_additional_core_views.py`
**Purpose:** Tests core API management functions including authentication, user management, and workspace operations.

**Functions Tested:**
- `generate_frontend_token_view` - Frontend token generation
- `get_current_user_view` - Current user retrieval
- `get_user_workspaces_list_view` - User workspace listing
- `get_workspace_by_id_view` - Workspace retrieval by ID
- `get_workspace_by_name_view` - Workspace retrieval by name
- `health_check_view` - System health monitoring
- `test_api_key_view` - API key validation
- Thoth log CRUD operations

**Key Features:**
- Mocks external API services and LLM calls
- Tests token-based authentication
- Validates workspace management operations
- Error handling and edge case coverage

**Running:**
```bash
uv run pytest tests/integration/test_additional_core_views.py -v
```

---

### `test_ai_backend_views.py`
**Purpose:** Tests AI workflow operations including evidence management, preprocessing, and question handling.

**Functions Tested:**
- `columns_list_view` - Database column listing
- `create_evidence_view` - Evidence creation
- `db_docs_view` - Database documentation
- `delete_all_evidence_view` - Bulk evidence deletion
- `delete_evidence_confirm_view` - Evidence deletion confirmation
- `delete_evidence_execute_view` - Evidence deletion execution
- `evidence_list_view` - Evidence listing
- `export_evidence_csv_view` - Evidence CSV export
- `preprocess_view` - Data preprocessing
- `questions_list_view` - Question listing
- `run_preprocessing_view` - Preprocessing execution
- `update_evidence_view` - Evidence updates
- `upload_evidence_view` - Evidence upload

**Key Features:**
- Comprehensive AI workflow testing
- Vector store operations with mocks
- File upload and processing
- CSV export functionality

**Running:**
```bash
uv run pytest tests/integration/test_ai_backend_views.py -v
```

---

### `test_authentication.py`
**Purpose:** Tests authentication mechanisms including token-based and session-based authentication.

**Functions Tested:**
- `test_api_key_authentication` - API key validation
- `test_authentication_endpoints` - Auth endpoint functionality
- `test_mixed_authentication` - Multiple auth methods
- `test_permission_isolation` - Access control validation
- `test_session_authentication` - Session-based auth
- `test_token_authentication` - Token-based auth

**Key Features:**
- Multiple authentication strategy testing
- Permission boundary validation
- Security access control verification

**Running:**
```bash
uv run pytest tests/integration/test_authentication.py -v
```

---

### `test_core_views.py`
**Purpose:** Tests core Django views and basic functionality.

**Functions Tested:**
- `test_api_login_view` - API login functionality
- `test_get_tables_by_database_ajax` - AJAX table retrieval
- `test_get_user_workspaces_view` - User workspace access
- `test_index_view` - Main index page
- `test_set_workspace_session_view` - Session workspace setting
- `test_table_columns_detail_view` - Table column details
- `test_table_list_by_db_name_view` - Database table listing
- `test_test_token_view` - Token validation

**Key Features:**
- Basic Django view functionality
- Session management
- AJAX endpoint testing

**Running:**
```bash
uv run pytest tests/integration/test_core_views.py -v
```

---

### `test_export_import_views.py`
**Purpose:** Tests export and import operations including CSV handling, PDF generation, and GDPR compliance.

**Functions Tested:**
- `export_columns_csv_view` - Column CSV export
- `export_questions_csv_view` - Question CSV export
- `import_evidence_server_csv_view` - Evidence CSV import
- `import_columns_server_csv_view` - Column CSV import
- `import_questions_server_csv_view` - Question CSV import
- `delete_all_columns_view` - Bulk column deletion
- `delete_all_questions_view` - Bulk question deletion
- `export_pdf_view` - PDF report generation
- `gdpr_export_pdf_view` - GDPR PDF export
- `gdpr_export_json_view` - GDPR JSON export

**Key Features:**
- File I/O operations with proper mocking
- PDF generation testing
- GDPR compliance validation
- CSV import/export functionality

**Running:**
```bash
uv run pytest tests/integration/test_export_import_views.py -v
```

---

### `test_frontend_auth.py`
**Purpose:** Tests frontend authentication integration.

**Functions Tested:**
- Frontend login/logout functionality
- Session management
- Authentication state verification

**Key Features:**
- Frontend-backend authentication integration
- Session persistence testing

**Running:**
```bash
uv run pytest tests/integration/test_frontend_auth.py -v
```

---

### `test_progress_views.py`
**Purpose:** Tests asynchronous operation progress tracking and task management.

**Functions Tested:**
- `get_upload_progress_view` - Upload progress monitoring
- `cancel_upload_view` - Upload cancellation
- `pause_upload_view` - Upload pausing
- `resume_upload_view` - Upload resumption
- `get_task_status_view` - Task status checking
- `restart_task_view` - Task restart functionality

**Key Features:**
- Async operation testing
- Progress tracking validation
- Task lifecycle management
- Background task mocking

**Running:**
```bash
uv run pytest tests/integration/test_progress_views.py -v
```

---

### `test_question_management_views.py`
**Purpose:** Tests question CRUD operations and preprocessing management.

**Functions Tested:**
- Question creation, editing, and deletion
- Question validation and sanitization
- Preprocessing status tracking
- Question-sql pair management
- Bulk question operations

**Key Features:**
- Question lifecycle testing
- Preprocessing workflow validation
- Vector store integration with mocks

**Running:**
```bash
uv run pytest tests/integration/test_question_management_views.py -v
```

---

### `test_workspace_management_views.py`
**Purpose:** Tests workspace management functions including agent pools and database connections.

**Functions Tested:**
- `get_workspace_agent_pools_view` - Workspace agent pool retrieval
- `test_vector_db_connection_view` - Vector database connection testing
- `check_embedding_config_view` - Embedding configuration validation
- `get_columns_by_table_view` - Table column retrieval

**Key Features:**
- Workspace configuration testing
- Vector database connection validation
- Embedding service configuration
- Agent pool management

**Running:**
```bash
uv run pytest tests/integration/test_workspace_management_views.py -v
```

---

## Unit Tests

### `test_relational_database_operations.py`
**Purpose:** Tests relational database operations across different backends.

**Functions Tested:**
- Database manager creation for various backends (MySQL, SQLite, PostgreSQL)
- Schema operations and relationship detection
- Column extraction and table creation
- Admin action functionality

**Key Features:**
- Multi-database backend support
- Schema introspection testing
- Relationship detection validation

**Running:**
```bash
uv run pytest tests/test_relational_database_operations.py -v
```

---

### `test_vector_database_operations.py`
**Purpose:** Tests vector database operations and CRUD functionality.

**Functions Tested:**
- Vector store creation for different backends (Qdrant, Chroma, PGVector)
- CRUD operations for evidence, column, and SQL documents
- Search operations across document types
- Collection information retrieval
- Error handling and validation

**Key Features:**
- Multi-vector-database backend support
- Document lifecycle testing
- Search functionality validation
- Error handling scenarios

**Running:**
```bash
uv run pytest tests/test_vector_database_operations.py -v
```

---

## Test Execution

### Prerequisites

1. **Environment Setup:**
   ```bash
   # Install dependencies
   uv sync

   # Set up environment (copy _env.template to _env)
   cp _env.template _env
   # Configure _env with your settings
   ```

2. **Database Setup:**
   ```bash
   # Run migrations
   uv run python manage.py migrate
   ```

### Running Tests

**Quick Test Run:**
```bash
# Run all tests
uv run pytest tests/

# Run with verbose output
uv run pytest tests/ -v

# Run with short traceback
uv run pytest tests/ --tb=short
```

**Specific Test Categories:**
```bash
# Run only integration tests
uv run pytest tests/integration/

# Run only unit tests
uv run pytest tests/test_*.py

# Run specific test file
uv run pytest tests/integration/test_core_views.py

# Run specific test method
uv run pytest tests/integration/test_core_views.py::TestCoreViews::test_index_view
```

**Test Coverage:**
```bash
# Run tests with coverage report
uv run pytest tests/ --cov=thoth_core --cov=thoth_ai_backend --cov-report=html
```

### Test Scripts

The project provides convenient test scripts:

**Quick Tests:**
```bash
./scripts/run-tests-local.sh quick      # Quick smoke tests
./scripts/run-tests-local.sh full       # Full test suite with coverage
./scripts/run-tests-local.sh views      # View tests only
./scripts/run-tests-local.sh security   # Security tests only
```

**Direct pytest commands:**
```bash
uv run pytest tests/                    # All tests
uv run pytest tests/ -m unit            # Unit tests only
uv run pytest tests/ -m integration     # Integration tests
uv run pytest -v --tb=short            # Verbose with short traceback
```

## Test Configuration

### Fixtures (`tests/conftest.py`)

**Available Fixtures:**
- `django_db_setup` - Database configuration override
- `enable_db_access_for_all_tests` - Automatic database access
- `mock_qdrant_client` - Mocked Qdrant vector database
- `mock_celery_task` - Mocked Celery async tasks
- `mock_llm_client` - Mocked LLM service client
- `test_user` - Basic test user
- `admin_user` - Test admin user
- `api_client` - DRF API client
- `authenticated_api_client` - Authenticated API client
- `test_workspace` - Test workspace with database
- `test_table` - Test table with columns

### Test Markers

**Available Markers:**
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.django_db` - Database access (auto-enabled)

## Mocking Strategy

### External Services

**LLM Services:**
- All functions using external LLM providers are mocked
- Mock objects return realistic responses
- Error scenarios are tested with mock exceptions

**Database Operations:**
- Vector database operations use mocked clients
- Relational database operations use test database
- Connection pooling and error handling are mocked

**File Operations:**
- CSV I/O operations use `unittest.mock.mock_open`
- PDF generation uses mocked file objects
- File system operations are properly isolated

### Mock Examples

```python
# Mock vector store operations
@patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store')
def test_vector_operation(self, mock_get_vector_store):
    mock_store = Mock()
    mock_store.get_collection_info.return_value = {
        "collection_name": "test_collection",
        "total_documents": 100,
        "status": "healthy"
    }
    mock_get_vector_store.return_value = mock_store

    # Test your functionality
```

```python
# Mock file operations
@patch('builtins.open', new_callable=mock_open, read_data="test,data\nvalue1,value2")
@patch('csv.DictReader')
def test_csv_import(self, mock_csv_reader, mock_open_file):
    mock_reader = Mock()
    mock_reader.__iter__.return_value = [{"test": "data", "value": "value1"}]
    mock_csv_reader.return_value = mock_reader

    # Test your functionality
```

## Test Data Management

### User Management
- Each test class uses unique usernames to prevent conflicts
- Test users are created with consistent patterns: `testuser_[purpose]`
- Admin users are created for permission testing

### Database Isolation
- Tests use separate database instances when possible
- Transactions are rolled back after each test
- Test data is cleaned up in tearDown methods

### Workspace Management
- Test workspaces are created with associated databases
- Vector database collections are mocked for consistency
- Settings and configurations are properly isolated

## Error Handling

### Test Reports
- Failed tests generate detailed error reports
- Reports are saved to `tests/reports/` directory
- Error information includes timestamps and stack traces

### Common Issues
**Database Integrity Errors:**
- Ensure unique usernames across test classes
- Use proper transaction management
- Clean up test data in tearDown methods

**Mock Path Errors:**
- Verify mock paths match actual import locations
- Check function signatures and return values
- Use proper patch decorators for class methods

**Import Errors:**
- Verify model imports and field names
- Check for circular dependencies
- Ensure proper Django app configuration

## Best Practices

### Test Organization
- Group related tests in logical files
- Use descriptive test method names
- Follow Django testing conventions
- Implement proper setUp/tearDown methods

### Mock Usage
- Mock external services, not internal logic
- Use realistic mock return values
- Test both success and failure scenarios
- Clean up mocks in tearDown methods

### Performance Considerations
- Use database transactions for faster tests
- Mock expensive external calls
- Avoid unnecessary test data creation
- Use fixtures for shared test data

## Continuous Integration

### Test Requirements
- All tests must pass before code changes
- Coverage should be maintained or improved
- New features must include corresponding tests
- Mock external dependencies consistently

### Running in CI
```bash
# Full test suite with coverage
uv run pytest tests/ --cov=. --cov-report=xml

# Security-focused tests
uv run pytest tests/ -m security

# Integration tests only
uv run pytest tests/integration/ -v
```

This documentation provides a comprehensive overview of the test suite structure, execution procedures, and maintenance guidelines for the ThothAI backend project.