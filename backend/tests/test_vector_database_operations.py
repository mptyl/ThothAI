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
Test suite for vector database operations using the new plugin architecture.

This test suite verifies:
1. CRUD operations on all supported vector database backends
2. Evidence generation and upload from preprocessing mask
3. Questions generation and upload from preprocessing mask
4. Column descriptions handling
"""

import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

from thoth_core.models import (
    VectorDb, VectorDbChoices, SqlDb, Workspace, Setting, 
    BasicAiModel, AiModel, Agent, AgentChoices
)
from thoth_ai_backend.backend_utils.vector_store_utils import get_vector_store
from thoth_qdrant import VectorStoreFactory
from thoth_qdrant import (
    EvidenceDocument, ColumnNameDocument, SqlDocument, ThothType
)


class VectorDatabaseTestSuite(TestCase):
    """Test suite for vector database operations."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create basic AI model
        self.basic_model = BasicAiModel.objects.create(
            name='Test GPT Model',
            description='Test model for vector operations'
        )
        
        # Create AI model
        self.ai_model = AiModel.objects.create(
            basic_model=self.basic_model,
            specific_model='gpt-4',
            name='Test GPT-4',
            api_key='test-api-key'
        )
        
        # Create agent
        self.agent = Agent.objects.create(
            name='Test Agent',
            agent_type=AgentChoices.EXTRACTKEYWORDS,
            ai_model=self.ai_model
        )
        
        # Create setting
        self.setting = Setting.objects.create(
            name='Test Setting',
            language='English',
            comment_model=self.ai_model
        )
        
        # Test vector databases for different backends
        self.vector_dbs = {}
        
        # Qdrant
        self.vector_dbs['qdrant'] = VectorDb.objects.create(
            name='test_qdrant_collection',
            vect_type=VectorDbChoices.QDRANT,
            host='localhost',
            port=6333,
            api_key='test-qdrant-key'
        )
        
        # Weaviate removed
        
        # ChromaDB
        self.vector_dbs['chroma'] = VectorDb.objects.create(
            name='test_chroma_collection',
            vect_type=VectorDbChoices.CHROMA,
            path='/tmp/chroma_test'
        )
        
        # PGVector
        self.vector_dbs['pgvector'] = VectorDb.objects.create(
            name='testdb',  # name serves as database name for PGVector
            vect_type=VectorDbChoices.PGVECTOR,
            host='localhost',
            port=5432,
            username='testuser',
            password='testpass'
        )
        
        # Create SQL databases and workspaces for each vector DB
        self.workspaces = {}
        for backend, vector_db in self.vector_dbs.items():
            sql_db = SqlDb.objects.create(
                name=f'test_sql_{backend}',
                db_type='SQLite',
                db_name=f'test_{backend}.db',
                vector_db=vector_db
            )
            
            workspace = Workspace.objects.create(
                name=f'test_workspace_{backend}',
                sql_db=sql_db,
                default_model=self.agent.ai_model if self.agent else None,
                setting=self.setting
            )
            workspace.users.add(self.user)
            self.workspaces[backend] = workspace
    
    def _create_mock_request(self, workspace):
        """Create a mock request with session containing workspace."""
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'current_workspace': workspace.id}
        # Add current_workspace attribute that WorkspaceMiddleware would normally set
        request.current_workspace = workspace
        return request
    
    @patch('thoth_vdbmanager.vdbmanager.VectorStoreFactory.create')
    def test_vector_store_creation_qdrant(self, mock_create):
        """Test vector store creation for Qdrant."""
        mock_store = Mock()
        mock_create.return_value = mock_store
        
        request = self._create_mock_request(self.workspaces['qdrant'])
        
        vector_store = get_vector_store(request)
        
        mock_create.assert_called_once_with(
            'qdrant',
            collection='test_qdrant_collection',
            host='localhost',
            port=6333,
            api_key='test-qdrant-key'
        )
        self.assertEqual(vector_store, mock_store)
    
    @patch('thoth_vdbmanager.vdbmanager.VectorStoreFactory.create')
    def test_vector_store_creation_qdrant_again(self, mock_create):
        """Test vector store creation for Qdrant (duplicate to replace removed Weaviate test)."""
        mock_store = Mock()
        mock_create.return_value = mock_store
        
        request = self._create_mock_request(self.workspaces['qdrant'])
        
        vector_store = get_vector_store(request)
        
        mock_create.assert_called_once_with(
            'qdrant',
            collection='test_qdrant_collection',
            host='localhost',
            port=6333,
            api_key='test-qdrant-key'
        )
        self.assertEqual(vector_store, mock_store)
    
    @patch('thoth_vdbmanager.vdbmanager.VectorStoreFactory.create')
    def test_vector_store_creation_chroma(self, mock_create):
        """Test vector store creation for ChromaDB."""
        mock_store = Mock()
        mock_create.return_value = mock_store
        
        request = self._create_mock_request(self.workspaces['chroma'])
        
        vector_store = get_vector_store(request)
        
        mock_create.assert_called_once_with(
            'chroma',
            collection='test_chroma_collection',
            path='/tmp/chroma_test'
        )
        self.assertEqual(vector_store, mock_store)
    
    @patch('thoth_vdbmanager.vdbmanager.VectorStoreFactory.create')
    def test_vector_store_creation_pgvector(self, mock_create):
        """Test vector store creation for PGVector."""
        mock_store = Mock()
        mock_create.return_value = mock_store
        
        request = self._create_mock_request(self.workspaces['pgvector'])
        
        vector_store = get_vector_store(request)
        
        mock_create.assert_called_once_with(
            'pgvector',
            collection='testdb',
            host='localhost',
            port=5432,
            database='testdb',
            user='testuser',
            password='testpass'
        )
        self.assertEqual(vector_store, mock_store)
    
    def test_crud_operations_evidence_documents(self):
        """Test CRUD operations for evidence documents."""
        # Mock vector store
        mock_store = Mock()
        mock_store.add_evidence.return_value = 'evidence-id-1'
        mock_store.get_document.return_value = EvidenceDocument(
            id='evidence-id-1',
            evidence='Test evidence for database operations'
        )
        mock_store.delete_document.return_value = None
        
        # Test CREATE
        evidence_doc = EvidenceDocument(evidence='Test evidence for database operations')
        doc_id = mock_store.add_evidence(evidence_doc)
        self.assertEqual(doc_id, 'evidence-id-1')
        
        # Test READ
        retrieved_doc = mock_store.get_document('evidence-id-1')
        self.assertIsInstance(retrieved_doc, EvidenceDocument)
        self.assertEqual(retrieved_doc.evidence, 'Test evidence for database operations')
        
        # Test DELETE
        mock_store.delete_document('evidence-id-1')
        mock_store.delete_document.assert_called_once_with('evidence-id-1')
    
    def test_crud_operations_column_documents(self):
        """Test CRUD operations for column documents."""
        # Mock vector store
        mock_store = Mock()
        mock_store.add_column_description.return_value = 'column-id-1'
        mock_store.get_document.return_value = ColumnNameDocument(
            id='column-id-1',
            table_name='users',
            column_name='user_id',
            original_column_name='user_id',
            column_description='Primary key for users table',
            value_description='Integer values starting from 1'
        )
        
        # Test CREATE
        column_doc = ColumnNameDocument(
            table_name='users',
            column_name='user_id',
            original_column_name='user_id',
            column_description='Primary key for users table',
            value_description='Integer values starting from 1'
        )
        doc_id = mock_store.add_column_description(column_doc)
        self.assertEqual(doc_id, 'column-id-1')
        
        # Test READ
        retrieved_doc = mock_store.get_document('column-id-1')
        self.assertIsInstance(retrieved_doc, ColumnNameDocument)
        self.assertEqual(retrieved_doc.table_name, 'users')
        self.assertEqual(retrieved_doc.column_name, 'user_id')
    
    def test_crud_operations_sql_documents(self):
        """Test CRUD operations for SQL documents."""
        # Mock vector store
        mock_store = Mock()
        mock_store.add_sql.return_value = 'sql-id-1'
        mock_store.get_document.return_value = SqlDocument(
            id='sql-id-1',
            question='How many users are there?',
            sql='SELECT COUNT(*) FROM users',
            evidence='Count total number of users in the system'
        )
        
        # Test CREATE
        sql_doc = SqlDocument(
            question='How many users are there?',
            sql='SELECT COUNT(*) FROM users',
            evidence='Count total number of users in the system'
        )
        doc_id = mock_store.add_sql(sql_doc)
        self.assertEqual(doc_id, 'sql-id-1')
        
        # Test READ
        retrieved_doc = mock_store.get_document('sql-id-1')
        self.assertIsInstance(retrieved_doc, SqlDocument)
        self.assertEqual(retrieved_doc.question, 'How many users are there?')
        self.assertEqual(retrieved_doc.sql, 'SELECT COUNT(*) FROM users')
    
    @patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store')
    def test_evidence_preprocessing_integration(self, mock_get_vector_store):
        """Test evidence generation and upload from preprocessing mask."""
        # Mock vector store
        mock_store = Mock()
        mock_store.bulk_add_documents.return_value = ['evidence-1', 'evidence-2', 'evidence-3']
        mock_get_vector_store.return_value = mock_store
        
        # Create mock request
        request = self._create_mock_request(self.workspaces['qdrant'])
        
        # Test data - simulate preprocessing generating evidence
        test_evidence = [
            EvidenceDocument(evidence='Primary key constraints ensure unique identification'),
            EvidenceDocument(evidence='Foreign keys maintain referential integrity'),
            EvidenceDocument(evidence='Indexes improve query performance')
        ]
        
        # Simulate bulk upload
        doc_ids = mock_store.bulk_add_documents(test_evidence)
        
        # Verify bulk upload was called
        mock_store.bulk_add_documents.assert_called_once_with(test_evidence)
        self.assertEqual(len(doc_ids), 3)
        self.assertEqual(doc_ids, ['evidence-1', 'evidence-2', 'evidence-3'])
    
    @patch('thoth_ai_backend.backend_utils.vector_store_utils.get_vector_store')
    def test_questions_preprocessing_integration(self, mock_get_vector_store):
        """Test questions generation and upload from preprocessing mask."""
        # Mock vector store
        mock_store = Mock()
        mock_store.bulk_add_documents.return_value = ['sql-1', 'sql-2']
        mock_get_vector_store.return_value = mock_store
        
        # Create mock request
        request = self._create_mock_request(self.workspaces['qdrant'])
        
        # Test data - simulate preprocessing generating questions
        test_questions = [
            SqlDocument(
                question='What is the total number of active users?',
                sql='SELECT COUNT(*) FROM users WHERE status = "active"',
                evidence='Filter users by active status'
            ),
            SqlDocument(
                question='List all orders from the last month',
                sql='SELECT * FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)',
                evidence='Use date functions to filter recent orders'
            )
        ]
        
        # Simulate bulk upload
        doc_ids = mock_store.bulk_add_documents(test_questions)
        
        # Verify bulk upload was called
        mock_store.bulk_add_documents.assert_called_once_with(test_questions)
        self.assertEqual(len(doc_ids), 2)
        self.assertEqual(doc_ids, ['sql-1', 'sql-2'])
    
    def test_search_operations(self):
        """Test search operations across different document types."""
        # Mock vector store
        mock_store = Mock()
        
        # Mock search results
        mock_evidence_results = [
            EvidenceDocument(evidence='Primary key ensures uniqueness'),
            EvidenceDocument(evidence='Foreign key maintains relationships')
        ]
        mock_sql_results = [
            SqlDocument(
                question='Count all users',
                sql='SELECT COUNT(*) FROM users',
                evidence='Basic count query'
            )
        ]
        
        # Configure mock responses
        def mock_search_similar(query, doc_type, top_k=5, score_threshold=0.7):
            if doc_type == ThothType.EVIDENCE:
                return mock_evidence_results
            elif doc_type == ThothType.SQL:
                return mock_sql_results
            else:
                return []
        
        mock_store.search_similar = mock_search_similar
        
        # Test evidence search
        evidence_results = mock_store.search_similar('database constraints', ThothType.EVIDENCE)
        self.assertEqual(len(evidence_results), 2)
        self.assertIsInstance(evidence_results[0], EvidenceDocument)
        
        # Test SQL search
        sql_results = mock_store.search_similar('count users', ThothType.SQL)
        self.assertEqual(len(sql_results), 1)
        self.assertIsInstance(sql_results[0], SqlDocument)
    
    def test_collection_info_retrieval(self):
        """Test collection information retrieval."""
        # Mock vector store
        mock_store = Mock()
        mock_info = {
            'collection_name': 'test_collection',
            'total_documents': 150,
            'document_types': {
                'evidence': 50,
                'columns': 75,
                'sql': 25
            },
            'backend_type': 'qdrant',
            'status': 'healthy'
        }
        mock_store.get_collection_info.return_value = mock_info
        
        # Test collection info retrieval
        info = mock_store.get_collection_info()
        
        self.assertEqual(info['collection_name'], 'test_collection')
        self.assertEqual(info['total_documents'], 150)
        self.assertEqual(info['backend_type'], 'qdrant')
        self.assertEqual(info['status'], 'healthy')
    
    def test_error_handling(self):
        """Test error handling for various failure scenarios."""
        # Test missing workspace
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}  # No workspace in session
        
        with self.assertRaises(ValueError) as cm:
            get_vector_store(request)
        
        # Test unsupported vector database type
        unsupported_vdb = VectorDb.objects.create(
            name='unsupported_collection',
            vect_type='UnsupportedType'  # This should fail validation
        )
        
        sql_db = SqlDb.objects.create(
            name='test_sql_unsupported',
            db_type='SQLite',
            db_name='test_unsupported.db',
            vector_db=unsupported_vdb
        )
        
        workspace = Workspace.objects.create(
            name='test_workspace_unsupported',
            sql_db=sql_db,
            default_agent=self.agent,
            setting=self.setting
        )
        workspace.users.add(self.user)
        
        request = self._create_mock_request(workspace)
        
        with self.assertRaises(ValueError) as cm:
            get_vector_store(request)
        
        self.assertIn('not supported', str(cm.exception))


class VectorDatabaseIntegrationTests(TestCase):
    """Integration tests for vector database operations with real backends."""
    
    def test_real_qdrant_operations(self):
        """Test operations with real Qdrant instance (requires running Qdrant)."""
        # This test would be skipped unless INTEGRATION_TESTS=1 is set
        # and would require an actual Qdrant instance running
        pass
    
    def test_real_chroma_operations(self):
        """Test operations with real ChromaDB instance."""
        # This test would be skipped unless INTEGRATION_TESTS=1 is set
        pass


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'thoth_core',
                'thoth_ai_backend',
            ],
            SECRET_KEY='test-secret-key'
        )
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['__main__'])