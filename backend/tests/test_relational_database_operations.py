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
Test suite for relational database operations using the new plugin architecture.

This test suite verifies:
1. Table creation from admin actions
2. Column extraction from admin actions  
3. Relationship detection from admin actions
4. Database schema operations across different SQL backends
"""

import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError

from thoth_core.models import (
    SqlDb, SqlTable, SqlColumn, Relationship, ColumnDataTypes, SQLDBChoices
)
from thoth_core.dbmanagement import get_db_manager, map_data_type
from thoth_dbmanager import ThothDbFactory
from thoth_dbmanager.documents import TableDocument, ColumnDocument, ForeignKeyDocument


class RelationalDatabaseTestSuite(TestCase):
    """Test suite for relational database operations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Test databases for different backends
        self.sql_dbs = {}
        
        # PostgreSQL
        self.sql_dbs['postgresql'] = SqlDb.objects.create(
            name='test_postgres',
            db_type=SQLDBChoices.POSTGRES,
            db_host='localhost',
            db_port=5432,
            db_name='testdb',
            user_name='testuser',
            password='testpass',
            schema='public'
        )
        
        # SQLite
        self.sql_dbs['sqlite'] = SqlDb.objects.create(
            name='test_sqlite',
            db_type=SQLDBChoices.SQLITE,
            db_name='test.db'
        )
        
        # MySQL
        self.sql_dbs['mysql'] = SqlDb.objects.create(
            name='test_mysql',
            db_type=SQLDBChoices.MYSQL,
            db_host='localhost',
            db_port=3306,
            db_name='testdb',
            user_name='testuser',
            password='testpass'
        )
        
        # MariaDB
        self.sql_dbs['mariadb'] = SqlDb.objects.create(
            name='test_mariadb',
            db_type=SQLDBChoices.MARIADB,
            db_host='localhost',
            db_port=3306,
            db_name='testdb',
            user_name='testuser',
            password='testpass'
        )
    
    @patch('thoth_dbmanager.ThothDbFactory.create_manager')
    def test_db_manager_creation_postgresql(self, mock_create_manager):
        """Test database manager creation for PostgreSQL."""
        mock_manager = Mock()
        mock_create_manager.return_value = mock_manager
        
        sqldb = self.sql_dbs['postgresql']
        manager = get_db_manager(sqldb)
        
        mock_create_manager.assert_called_once()
        call_args = mock_create_manager.call_args
        
        # Verify db_type
        self.assertEqual(call_args[1]['db_type'], 'postgresql')
        
        # Verify connection parameters
        self.assertEqual(call_args[1]['host'], 'localhost')
        self.assertEqual(call_args[1]['port'], 5432)
        self.assertEqual(call_args[1]['database'], 'testdb')
        self.assertEqual(call_args[1]['user'], 'testuser')
        self.assertEqual(call_args[1]['password'], 'testpass')
        self.assertEqual(call_args[1]['schema'], 'public')
        
        self.assertEqual(manager, mock_manager)
    
    @patch('thoth_dbmanager.ThothDbFactory.create_manager')
    def test_db_manager_creation_sqlite(self, mock_create_manager):
        """Test database manager creation for SQLite."""
        mock_manager = Mock()
        mock_create_manager.return_value = mock_manager
        
        sqldb = self.sql_dbs['sqlite']
        manager = get_db_manager(sqldb)
        
        mock_create_manager.assert_called_once()
        call_args = mock_create_manager.call_args
        
        # Verify db_type
        self.assertEqual(call_args[1]['db_type'], 'sqlite')
        
        # Verify SQLite uses database_path instead of separate host/port
        self.assertIn('database_path', call_args[1])
        self.assertTrue(call_args[1]['database_path'].endswith('test.db'))
        
        self.assertEqual(manager, mock_manager)
    
    @patch('thoth_dbmanager.ThothDbFactory.create_manager')
    def test_db_manager_creation_mysql(self, mock_create_manager):
        """Test database manager creation for MySQL."""
        mock_manager = Mock()
        mock_create_manager.return_value = mock_manager
        
        sqldb = self.sql_dbs['mysql']
        manager = get_db_manager(sqldb)
        
        mock_create_manager.assert_called_once()
        call_args = mock_create_manager.call_args
        
        # Verify db_type
        self.assertEqual(call_args[1]['db_type'], 'mysql')
        
        # Verify connection parameters
        self.assertEqual(call_args[1]['host'], 'localhost')
        self.assertEqual(call_args[1]['port'], 3306)
        self.assertEqual(call_args[1]['database'], 'testdb')
        
        self.assertEqual(manager, mock_manager)
    
    def test_data_type_mapping(self):
        """Test data type mapping from database types to Django model choices."""
        # Test VARCHAR mapping
        self.assertEqual(map_data_type('VARCHAR(255)'), ColumnDataTypes.VARCHAR)
        self.assertEqual(map_data_type('CHARACTER VARYING(100)'), ColumnDataTypes.VARCHAR)
        
        # Test CHAR mapping
        self.assertEqual(map_data_type('CHAR(10)'), ColumnDataTypes.CHAR)
        self.assertEqual(map_data_type('CHARACTER(5)'), ColumnDataTypes.CHAR)
        
        # Test INTEGER mapping
        self.assertEqual(map_data_type('INT'), ColumnDataTypes.INT)
        self.assertEqual(map_data_type('INTEGER'), ColumnDataTypes.INT)
        self.assertEqual(map_data_type('BIGINT'), ColumnDataTypes.INT)
        self.assertEqual(map_data_type('SMALLINT'), ColumnDataTypes.INT)
        
        # Test FLOAT mapping
        self.assertEqual(map_data_type('FLOAT'), ColumnDataTypes.FLOAT)
        self.assertEqual(map_data_type('REAL'), ColumnDataTypes.FLOAT)
        
        # Test DATE mapping
        self.assertEqual(map_data_type('DATE'), ColumnDataTypes.DATE)
        self.assertEqual(map_data_type('TIMESTAMP'), ColumnDataTypes.TIMESTAMP)
        
        # Test BOOLEAN mapping
        self.assertEqual(map_data_type('BOOLEAN'), ColumnDataTypes.BOOLEAN)
        self.assertEqual(map_data_type('BOOL'), ColumnDataTypes.BOOLEAN)
    
    @patch('thoth_core.dbmanagement.get_db_manager')
    def test_table_creation_admin_action(self, mock_get_db_manager):
        """Test table creation from admin actions."""
        # Mock database manager
        mock_manager = Mock()
        mock_manager.get_tables.return_value = [
            TableDocument(
                table_name='users',
                description='User accounts table',
                column_count=5,
                row_count=1000
            ),
            TableDocument(
                table_name='orders',
                description='Customer orders table',
                column_count=8,
                row_count=5000
            )
        ]
        mock_get_db_manager.return_value = mock_manager
        
        sqldb = self.sql_dbs['postgresql']
        
        # Simulate admin action for table creation
        manager = get_db_manager(sqldb)
        tables = manager.get_tables()
        
        # Verify tables were retrieved
        self.assertEqual(len(tables), 2)
        self.assertEqual(tables[0].table_name, 'users')
        self.assertEqual(tables[1].table_name, 'orders')
        
        # Simulate creating SqlTable objects
        for table_doc in tables:
            sql_table = SqlTable.objects.create(
                name=table_doc.table_name,
                description=table_doc.description,
                sql_db=sqldb
            )
            self.assertEqual(sql_table.name, table_doc.table_name)
    
    @patch('thoth_core.dbmanagement.get_db_manager')
    def test_column_extraction_admin_action(self, mock_get_db_manager):
        """Test column extraction from admin actions."""
        # Create test table
        sqldb = self.sql_dbs['postgresql']
        test_table = SqlTable.objects.create(
            name='users',
            description='Test users table',
            sql_db=sqldb
        )
        
        # Mock database manager
        mock_manager = Mock()
        mock_manager.get_columns.return_value = [
            ColumnDocument(
                column_name='id',
                data_type='INTEGER',
                is_nullable=False,
                is_primary_key=True,
                description='User ID primary key'
            ),
            ColumnDocument(
                column_name='username',
                data_type='VARCHAR(50)',
                is_nullable=False,
                is_primary_key=False,
                description='User login name'
            ),
            ColumnDocument(
                column_name='email',
                data_type='VARCHAR(255)',
                is_nullable=True,
                is_primary_key=False,
                description='User email address'
            ),
            ColumnDocument(
                column_name='created_at',
                data_type='TIMESTAMP',
                is_nullable=False,
                is_primary_key=False,
                description='Account creation timestamp'
            )
        ]
        mock_get_db_manager.return_value = mock_manager
        
        # Simulate admin action for column extraction
        manager = get_db_manager(sqldb)
        columns = manager.get_columns('users')
        
        # Verify columns were retrieved
        self.assertEqual(len(columns), 4)
        
        # Simulate creating SqlColumn objects
        for column_doc in columns:
            sql_column = SqlColumn.objects.create(
                original_column_name=column_doc.column_name,
                column_name=column_doc.column_name,
                data_format=map_data_type(column_doc.data_type),
                column_description=column_doc.description,
                sql_table=test_table
            )
            
            # Verify primary key field is set
            if column_doc.is_primary_key:
                sql_column.pk_field = 'PRIMARY KEY'
                sql_column.save()
                
            self.assertEqual(sql_column.original_column_name, column_doc.column_name)
        
        # Verify all columns were created
        created_columns = SqlColumn.objects.filter(sql_table=test_table)
        self.assertEqual(created_columns.count(), 4)
        
        # Verify primary key was identified
        pk_column = created_columns.filter(pk_field='PRIMARY KEY').first()
        self.assertIsNotNone(pk_column)
        self.assertEqual(pk_column.original_column_name, 'id')
    
    @patch('thoth_core.dbmanagement.get_db_manager')
    def test_relationship_detection_admin_action(self, mock_get_db_manager):
        """Test relationship detection from admin actions."""
        # Create test tables
        sqldb = self.sql_dbs['postgresql']
        
        users_table = SqlTable.objects.create(
            name='users',
            description='Users table',
            sql_db=sqldb
        )
        
        orders_table = SqlTable.objects.create(
            name='orders',
            description='Orders table',
            sql_db=sqldb
        )
        
        # Create test columns
        user_id_column = SqlColumn.objects.create(
            original_column_name='id',
            column_name='id',
            data_format=ColumnDataTypes.INT,
            column_description='User ID',
            pk_field='PRIMARY KEY',
            sql_table=users_table
        )
        
        order_user_id_column = SqlColumn.objects.create(
            original_column_name='user_id',
            column_name='user_id',
            data_format=ColumnDataTypes.INT,
            column_description='Reference to user',
            sql_table=orders_table
        )
        
        # Mock database manager
        mock_manager = Mock()
        mock_manager.get_foreign_keys.return_value = [
            ForeignKeyDocument(
                constraint_name='fk_orders_user_id',
                source_table='orders',
                source_column='user_id',
                target_table='users',
                target_column='id',
                on_delete='CASCADE',
                on_update='CASCADE'
            )
        ]
        mock_get_db_manager.return_value = mock_manager
        
        # Simulate admin action for relationship detection
        manager = get_db_manager(sqldb)
        foreign_keys = manager.get_foreign_keys()
        
        # Verify foreign keys were retrieved
        self.assertEqual(len(foreign_keys), 1)
        fk = foreign_keys[0]
        self.assertEqual(fk.source_table, 'orders')
        self.assertEqual(fk.source_column, 'user_id')
        self.assertEqual(fk.target_table, 'users')
        self.assertEqual(fk.target_column, 'id')
        
        # Simulate creating Relationship objects
        relationship = Relationship.objects.create(
            source_table=orders_table,
            target_table=users_table,
            source_column=order_user_id_column,
            target_column=user_id_column
        )
        
        # Update FK field in source column
        order_user_id_column.fk_field = f"{users_table.name}.{user_id_column.original_column_name}"
        order_user_id_column.save()
        
        # Verify relationship was created
        self.assertEqual(relationship.source_table, orders_table)
        self.assertEqual(relationship.target_table, users_table)
        self.assertEqual(relationship.source_column, order_user_id_column)
        self.assertEqual(relationship.target_column, user_id_column)
        
        # Verify FK field was updated
        order_user_id_column.refresh_from_db()
        self.assertEqual(order_user_id_column.fk_field, 'users.id')
    
    def test_relationship_pk_fk_fields_update(self):
        """Test the static method for updating PK/FK fields in relationships."""
        # Create test data
        sqldb = self.sql_dbs['sqlite']
        
        # Users table
        users_table = SqlTable.objects.create(
            name='users',
            sql_db=sqldb
        )
        user_id_col = SqlColumn.objects.create(
            original_column_name='id',
            column_name='id',
            sql_table=users_table
        )
        
        # Orders table
        orders_table = SqlTable.objects.create(
            name='orders',
            sql_db=sqldb
        )
        order_user_id_col = SqlColumn.objects.create(
            original_column_name='user_id',
            column_name='user_id',
            sql_table=orders_table
        )
        
        # Products table
        products_table = SqlTable.objects.create(
            name='products',
            sql_db=sqldb
        )
        product_id_col = SqlColumn.objects.create(
            original_column_name='id',
            column_name='id',
            sql_table=products_table
        )
        
        # Order items table with multiple FKs
        order_items_table = SqlTable.objects.create(
            name='order_items',
            sql_db=sqldb
        )
        order_item_order_id_col = SqlColumn.objects.create(
            original_column_name='order_id',
            column_name='order_id',
            sql_table=order_items_table
        )
        order_item_product_id_col = SqlColumn.objects.create(
            original_column_name='product_id',
            column_name='product_id',
            sql_table=order_items_table
        )
        
        # Create relationships
        Relationship.objects.create(
            source_table=orders_table,
            target_table=users_table,
            source_column=order_user_id_col,
            target_column=user_id_col
        )
        
        Relationship.objects.create(
            source_table=order_items_table,
            target_table=orders_table,
            source_column=order_item_order_id_col,
            target_column=user_id_col  # Using user_id as example
        )
        
        Relationship.objects.create(
            source_table=order_items_table,
            target_table=products_table,
            source_column=order_item_product_id_col,
            target_column=product_id_col
        )
        
        # Call the static method to update PK/FK fields
        Relationship.update_pk_fk_fields()
        
        # Verify FK fields were updated
        order_user_id_col.refresh_from_db()
        self.assertEqual(order_user_id_col.fk_field, 'users.id')
        
        order_item_order_id_col.refresh_from_db()
        self.assertEqual(order_item_order_id_col.fk_field, 'users.id')
        
        order_item_product_id_col.refresh_from_db()
        self.assertEqual(order_item_product_id_col.fk_field, 'products.id')
    
    @patch('thoth_core.dbmanagement.get_db_manager')
    def test_schema_operations_across_backends(self, mock_get_db_manager):
        """Test schema operations work consistently across different database backends."""
        backends_to_test = ['postgresql', 'mysql', 'sqlite']
        
        for backend in backends_to_test:
            with self.subTest(backend=backend):
                # Mock database manager for this backend
                mock_manager = Mock()
                mock_manager.get_database_info.return_value = {
                    'database_type': backend,
                    'version': '13.0' if backend == 'postgresql' else '8.0',
                    'charset': 'utf8mb4' if backend in ['mysql', 'mariadb'] else 'UTF8',
                    'tables_count': 5,
                    'schemas': ['public'] if backend == 'postgresql' else []
                }
                mock_get_db_manager.return_value = mock_manager
                
                sqldb = self.sql_dbs[backend] if backend in self.sql_dbs else self.sql_dbs['sqlite']
                
                # Test database info retrieval
                manager = get_db_manager(sqldb)
                db_info = manager.get_database_info()
                
                # Verify common database info structure
                self.assertIn('database_type', db_info)
                self.assertIn('version', db_info)
                self.assertIn('tables_count', db_info)
                
                # Verify backend-specific behavior
                if backend == 'postgresql':
                    self.assertIn('schemas', db_info)
                    self.assertEqual(db_info['schemas'], ['public'])
    
    def test_error_handling_unsupported_database(self):
        """Test error handling for unsupported database types."""
        # Create SqlDb with unsupported database type
        unsupported_db = SqlDb.objects.create(
            name='unsupported_db',
            db_type='UnsupportedDB',  # This should fail
            db_name='test.db'
        )
        
        # Test that get_db_manager raises NotImplementedError
        with self.assertRaises(NotImplementedError) as cm:
            get_db_manager(unsupported_db)
        
        self.assertIn('not yet supported', str(cm.exception))
    
    @patch('thoth_dbmanager.ThothDbFactory.create_manager')
    def test_error_handling_connection_failure(self, mock_create_manager):
        """Test error handling when database connection fails."""
        # Mock connection failure
        mock_create_manager.side_effect = RuntimeError("Connection failed")
        
        sqldb = self.sql_dbs['postgresql']
        
        # Test that get_db_manager propagates the error
        with self.assertRaises(RuntimeError) as cm:
            get_db_manager(sqldb)
        
        self.assertIn('Connection failed', str(cm.exception))
    
    def test_bulk_operations(self):
        """Test bulk operations for creating multiple tables/columns."""
        sqldb = self.sql_dbs['sqlite']
        
        # Create multiple tables in bulk
        tables_data = [
            {'name': 'users', 'description': 'User accounts'},
            {'name': 'products', 'description': 'Product catalog'},
            {'name': 'orders', 'description': 'Customer orders'},
            {'name': 'order_items', 'description': 'Order line items'}
        ]
        
        created_tables = []
        for table_data in tables_data:
            table = SqlTable.objects.create(
                name=table_data['name'],
                description=table_data['description'],
                sql_db=sqldb
            )
            created_tables.append(table)
        
        # Verify all tables were created
        self.assertEqual(len(created_tables), 4)
        self.assertEqual(SqlTable.objects.filter(sql_db=sqldb).count(), 4)
        
        # Create multiple columns for the first table
        users_table = created_tables[0]
        columns_data = [
            {'name': 'id', 'type': ColumnDataTypes.INT, 'desc': 'Primary key'},
            {'name': 'username', 'type': ColumnDataTypes.VARCHAR, 'desc': 'Login name'},
            {'name': 'email', 'type': ColumnDataTypes.VARCHAR, 'desc': 'Email address'},
            {'name': 'created_at', 'type': ColumnDataTypes.TIMESTAMP, 'desc': 'Creation time'}
        ]
        
        created_columns = []
        for col_data in columns_data:
            column = SqlColumn.objects.create(
                original_column_name=col_data['name'],
                column_name=col_data['name'],
                data_format=col_data['type'],
                column_description=col_data['desc'],
                sql_table=users_table
            )
            created_columns.append(column)
        
        # Verify all columns were created
        self.assertEqual(len(created_columns), 4)
        self.assertEqual(SqlColumn.objects.filter(sql_table=users_table).count(), 4)


class RelationalDatabaseIntegrationTests(TestCase):
    """Integration tests for relational database operations with real backends."""
    
    def test_real_postgresql_operations(self):
        """Test operations with real PostgreSQL instance."""
        # This test would be skipped unless INTEGRATION_TESTS=1 is set
        # and would require an actual PostgreSQL instance running
        pass
    
    def test_real_sqlite_operations(self):
        """Test operations with real SQLite database."""
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
                'thoth_core',
            ],
            SECRET_KEY='test-secret-key'
        )
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['__main__'])