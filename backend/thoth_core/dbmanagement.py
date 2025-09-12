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

import logging
import os
from django.db import IntegrityError
from django.contrib import messages
from .models import SqlTable, SqlColumn, ColumnDataTypes, Relationship

# New plugin-based imports
from thoth_dbmanager import ThothDbFactory, get_available_databases
from .utilities.utils import initialize_database_plugins

# Get a logger for this module
logger = logging.getLogger(__name__)


def get_db_manager(sqldb):
    """
    Factory function to get the appropriate ThothDbManager instance based on db_type using plugin discovery system.
    """
    try:
        # Ensure plugins are initialized (this will import the plugins module and register them)
        initialize_database_plugins()

        # Map Django model db_type to plugin identifiers
        db_type_mapping = {
            "PostgreSQL": "postgresql",
            "SQLite": "sqlite",
            "MySQL": "mysql",
            "MariaDB": "mariadb",
            "SQLServer": "sqlserver",
            "Oracle": "oracle",
            # 'Supabase': 'supabase'  # Temporarily removed due to dependency conflicts
        }

        plugin_db_type = db_type_mapping.get(sqldb.db_type)
        if not plugin_db_type:
            raise NotImplementedError(
                f"Database type '{sqldb.db_type}' is not yet supported."
            )

        # Get available databases from plugin discovery
        available_databases = get_available_databases()

        # Check if the requested database type is available
        if plugin_db_type not in available_databases:
            available_types = list(available_databases.keys())
            raise NotImplementedError(
                f"Database type '{plugin_db_type}' is not known to the plugin system. Available types: {available_types}"
            )

        if not available_databases[plugin_db_type]:
            raise NotImplementedError(
                f"Database type '{plugin_db_type}' is not available - missing dependencies. Install with: pip install thoth-dbmanager[{plugin_db_type}]"
            )

        # Get DB_ROOT_PATH from environment or use default
        db_root_path = os.environ.get("DB_ROOT_PATH", "data")

        # Prepare common parameters
        common_params = {
            "db_type": plugin_db_type,
            "db_root_path": db_root_path,
            "db_mode": sqldb.db_mode,
        }

        # Add database-specific parameters based on type
        if plugin_db_type == "sqlite":
            # SQLite uses database_path instead of separate host/port/database
            # Construct path following the same pattern as other database plugins: db_root_path/db_mode_databases/db_name/db_name.sqlite
            sqlite_dir = os.path.join(
                db_root_path, f"{sqldb.db_mode}_databases", sqldb.db_name
            )
            common_params["database_path"] = os.path.join(
                sqlite_dir, f"{sqldb.db_name}.sqlite"
            )
        elif plugin_db_type == "postgresql":
            common_params.update(
                {
                    "host": sqldb.db_host,
                    "port": sqldb.db_port,
                    "database": sqldb.db_name,
                    "user": sqldb.user_name,
                    "password": sqldb.password,
                    "schema": sqldb.schema or "public",
                }
            )
        elif plugin_db_type in ["mysql", "mariadb"]:
            common_params.update(
                {
                    "host": sqldb.db_host,
                    "port": sqldb.db_port,
                    "database": sqldb.db_name,
                    "user": sqldb.user_name,
                    "password": sqldb.password,
                }
            )
        elif plugin_db_type == "sqlserver":
            common_params.update(
                {
                    "host": sqldb.db_host,
                    "port": sqldb.db_port,
                    "database": sqldb.db_name,
                    "user": sqldb.user_name,
                    "password": sqldb.password,
                    "schema": sqldb.schema
                    or "dbo",  # SQL Server default schema is 'dbo'
                }
            )
        elif plugin_db_type == "oracle":
            common_params.update(
                {
                    "host": sqldb.db_host,
                    "port": sqldb.db_port,
                    "database": sqldb.db_name,
                    "user": sqldb.user_name,
                    "password": sqldb.password,
                }
            )

        # Create manager using new factory (which uses the plugin system)
        manager = ThothDbFactory.create_manager(**common_params)

        logger.info(f"Successfully created {plugin_db_type} manager for {sqldb.name}")
        return manager

    except Exception as e:
        logger.error(f"Failed to create database manager for {sqldb.name}: {e}")
        raise


 


def map_data_type(data_type):
    data_type = data_type.upper()
    if data_type.startswith("VARCHAR") or data_type.startswith("CHARACTER VARYING"):
        return ColumnDataTypes.VARCHAR
    elif data_type.startswith("CHAR") or data_type.startswith("CHARACTER"):
        return ColumnDataTypes.CHAR
    elif data_type in ["INT", "INTEGER", "BIGINT", "SMALLINT"]:
        return ColumnDataTypes.INT
    elif data_type in ["FLOAT", "REAL"]:
        return ColumnDataTypes.FLOAT
    elif data_type == "DOUBLE PRECISION":
        return ColumnDataTypes.DOUBLE
    elif data_type == "DECIMAL" or data_type.startswith("NUMERIC"):
        return ColumnDataTypes.DECIMAL
    elif data_type == "DATE":
        return ColumnDataTypes.DATE
    elif data_type == "TIME":
        return ColumnDataTypes.TIME
    elif data_type in [
        "TIMESTAMP",
        "TIMESTAMP WITHOUT TIME ZONE",
        "TIMESTAMP WITH TIME ZONE",
    ]:
        return ColumnDataTypes.TIMESTAMP
    elif data_type in ["BOOLEAN", "BOOL"]:
        return ColumnDataTypes.BOOLEAN
    elif data_type == "ENUM":
        return ColumnDataTypes.ENUM
    else:
        return ColumnDataTypes.VARCHAR  # Default to VARCHAR for unknown types


def get_column_names_and_comments(sqldb, table_name):
    try:
        db_manager = get_db_manager(sqldb)

        # Prefer adapter documents
        columns_info = None
        adapter = getattr(db_manager, "adapter", None)
        if adapter and hasattr(adapter, "get_columns_as_documents"):
            try:
                docs = adapter.get_columns_as_documents(table_name)
                columns_info = [
                    {
                        "name": d.column_name,
                        "data_type": d.data_type,
                        "comment": d.comment,
                        "is_pk": d.is_pk,
                    }
                    for d in docs
                ]
            except Exception:
                # Fallback to manager method below
                columns_info = None

        if columns_info is None:
            columns_info = db_manager.get_columns(table_name)

        result = []
        for col_data in columns_info:
            column_name = col_data["name"]
            data_type = col_data["data_type"]
            comment = col_data.get("comment", "")
            is_pk = col_data.get("is_pk", False)
            result.append((column_name, data_type, comment, is_pk))

        if not result:
            logger.warning(f"No columns found for table {table_name}")

        return result

    except NotImplementedError as e:
        logger.error(f"Database type not supported: {e}")
        raise Exception(f"Database type '{sqldb.db_type}' is not supported")
    except Exception as e:
        logger.exception(
            f"Error retrieving column names and comments for table {table_name}: {str(e)}"
        )
        raise Exception(f"Connection error: {str(e)}")


def create_sql_columns(sql_table, column_info):
    created_columns = []
    skipped_columns = []

    for column_data in column_info:
        column_name = column_data[0]
        data_type = column_data[1]
        comment = column_data[2] if len(column_data) > 2 else None
        is_pk = column_data[3] if len(column_data) > 3 else False

        # Check if the column already exists
        if SqlColumn.objects.filter(
            sql_table=sql_table, original_column_name=column_name
        ).exists():
            skipped_columns.append((column_name, data_type, comment))
            continue

        # Map the data type
        mapped_data_type = map_data_type(data_type)

        # Create the column
        column = SqlColumn(
            sql_table=sql_table,
            original_column_name=column_name,
            column_name=column_name,
            data_format=mapped_data_type,
            column_description=comment or "",
            pk_field="PK" if is_pk else "",  # Set 'PK' if the column is a primary key
        )
        column.save()

        created_columns.append((column_name, data_type, comment))

    return created_columns, skipped_columns


def create_columns(modeladmin, request, queryset):
    total_tables = queryset.count()
    total_success = 0
    total_failed = 0
    failed_tables = []

    for sql_table in queryset:
        try:
            logger.info(f"SqlTable: {sql_table.name}")
            logger.info(f"SqlDb: {sql_table.sql_db.name}")

            # Get column names and comments
            column_info = get_column_names_and_comments(
                sql_table.sql_db, sql_table.name
            )

            if not column_info:
                error_msg = f"No columns found or error occurred for table '{sql_table.name}' in database '{sql_table.sql_db.name}'"
                messages.error(request, error_msg)
                failed_tables.append(
                    (
                        sql_table.name,
                        sql_table.sql_db.name,
                        "No columns found or connection error",
                    )
                )
                total_failed += 1
                continue

            logger.info("Columns found:")
            for column, data_type, comment, is_pk in column_info:
                logger.info(
                    f"- {column} ({data_type}) (Comment: {comment or 'None'}) (PK: {'Yes' if is_pk else 'No'})"
                )

            # Create SqlColumn records
            created_columns, skipped_columns = create_sql_columns(
                sql_table, column_info
            )

            logger.info("Columns created:")
            for column, data_type, comment in created_columns:
                logger.info(f"- {column} (Comment: {comment or 'None'})")

            logger.info("Columns skipped (already existing):")
            for column, data_type, comment in skipped_columns:
                logger.info(f"- {column} (Comment: {comment or 'None'})")

            logger.info("--------------------")

            # Success message
            messages.success(
                request,
                f"Successfully processed table '{sql_table.name}' in database '{sql_table.sql_db.name}': {len(created_columns)} columns created, {len(skipped_columns)} columns skipped",
            )
            total_success += 1

        except Exception as e:
            error_msg = f"Failed to process table '{sql_table.name}' in database '{sql_table.sql_db.name}': {str(e)}"
            logger.error(error_msg)
            messages.error(request, error_msg)
            failed_tables.append((sql_table.name, sql_table.sql_db.name, str(e)))
            total_failed += 1

    # Summary message
    if total_failed > 0:
        messages.warning(
            request,
            f"Task completed with {total_success} successes and {total_failed} failures out of {total_tables} tables",
        )
    else:
        messages.success(request, f"Successfully processed all {total_tables} tables")


create_columns.short_description = "Create columns for selected tables"


def get_table_names_and_comments(sqldb):
    try:
        db_manager = get_db_manager(sqldb)

        # Prefer adapter documents
        adapter = getattr(db_manager, "adapter", None)
        if adapter and hasattr(adapter, "get_tables_as_documents"):
            docs = adapter.get_tables_as_documents()
            result = [(d.table_name, getattr(d, "comment", "")) for d in docs]
        else:
            # Fallback to backward-compatible API (schema info not available here)
            tables_info = db_manager.get_tables()
            result = []
            for table_data in tables_info:
                table_name = table_data["name"]
                comment = table_data.get("comment", "")
                result.append((table_name, comment))

        return result

    except NotImplementedError as e:
        logger.error(f"Database type not supported: {e}")
        raise Exception(f"Database type '{sqldb.db_type}' is not supported")
    except Exception as e:
        logger.exception(f"Error retrieving table names and comments: {str(e)}")
        raise Exception(f"Connection error: {str(e)}")


def create_sql_tables(sqldb, table_info):
    created_tables = []
    skipped_tables = []

    for table_name, description in table_info:
        try:
            sql_table, created = SqlTable.objects.get_or_create(
                name=table_name,
                sql_db=sqldb,
                defaults={"description": description or ""},
            )
            if created:
                created_tables.append((table_name, description))
            else:
                # Update the comment if the table already exists
                if sql_table.description != description:
                    sql_table.description = description
                    sql_table.save()
                skipped_tables.append((table_name, description))
        except IntegrityError:
            skipped_tables.append((table_name, description))

    return created_tables, skipped_tables


def create_relationships(modeladmin, request, queryset):
    if not hasattr(queryset, "__iter__"):
        sqldb_list = [queryset]
    else:
        sqldb_list = queryset

    total_databases = len(sqldb_list)
    total_success = 0
    total_failed = 0
    failed_databases = []
    total_relationships_created = 0

    for sqldb in sqldb_list:
        try:
            db_manager = get_db_manager(sqldb)
            # Prefer adapter docs to keep schema_name; fallback to manager API
            adapter = getattr(db_manager, "adapter", None)
            if adapter and hasattr(adapter, "get_foreign_keys_as_documents"):
                fk_docs = adapter.get_foreign_keys_as_documents()
                relationships_info = [
                    {
                        "source_table_name": d.source_table_name,
                        "source_column_name": d.source_column_name,
                        "target_table_name": d.target_table_name,
                        "target_column_name": d.target_column_name,
                    }
                    for d in fk_docs
                ]
            else:
                relationships_info = db_manager.get_foreign_keys()

            if not relationships_info:
                messages.warning(
                    request,
                    f"No foreign key relationships found in database '{sqldb.name}'",
                )
                total_success += 1
                continue

            relationships_created = 0
            relationships_failed = 0

            # Limit to relationships whose tables exist in our catalog
            existing_tables = set(
                SqlTable.objects.filter(sql_db=sqldb).values_list("name", flat=True)
            )
            relationships_info = [
                r
                for r in relationships_info
                if r.get("source_table_name") in existing_tables
                and r.get("target_table_name") in existing_tables
            ]

            for rel_data in relationships_info:
                source_table_name = rel_data["source_table_name"]
                source_column_name = rel_data["source_column_name"]
                target_table_name = rel_data["target_table_name"]
                target_column_name = rel_data["target_column_name"]

                try:
                    source_table = SqlTable.objects.get(
                        name=source_table_name, sql_db=sqldb
                    )
                    target_table = SqlTable.objects.get(
                        name=target_table_name, sql_db=sqldb
                    )
                    # Ensure source/target columns exist; create on-the-fly if missing
                    try:
                        source_column = SqlColumn.objects.get(
                            original_column_name=source_column_name,
                            sql_table=source_table,
                        )
                    except SqlColumn.DoesNotExist:
                        try:
                            col_info = get_column_names_and_comments(
                                sqldb, source_table.name
                            )
                            create_sql_columns(source_table, col_info)
                            source_column = SqlColumn.objects.get(
                                original_column_name=source_column_name,
                                sql_table=source_table,
                            )
                        except Exception:
                            raise
                    try:
                        target_column = SqlColumn.objects.get(
                            original_column_name=target_column_name,
                            sql_table=target_table,
                        )
                    except SqlColumn.DoesNotExist:
                        try:
                            col_info = get_column_names_and_comments(
                                sqldb, target_table.name
                            )
                            create_sql_columns(target_table, col_info)
                            target_column = SqlColumn.objects.get(
                                original_column_name=target_column_name,
                                sql_table=target_table,
                            )
                        except Exception:
                            raise

                    relationship, created = Relationship.objects.get_or_create(
                        source_table=source_table,
                        target_table=target_table,
                        source_column=source_column,
                        target_column=target_column,
                    )
                    if created:
                        relationships_created += 1
                    logger.info(
                        f"Created/Updated relationship: {source_table_name}.{source_column_name} -> {target_table_name}.{target_column_name}"
                    )
                except SqlTable.DoesNotExist:
                    error_msg = f"Table not found in database '{sqldb.name}' - Source: {source_table_name} or Target: {target_table_name}"
                    logger.error(error_msg)
                    relationships_failed += 1
                except Exception as e:
                    error_msg = f"Error creating relationship in database '{sqldb.name}': {str(e)}"
                    logger.error(error_msg)
                    relationships_failed += 1

            Relationship.update_pk_fk_fields()
            logger.info("Relationships created and pk_field/fk_field updated.")

            # Success message
            messages.success(
                request,
                f"Successfully processed relationships for database '{sqldb.name}': {relationships_created} relationships created",
            )
            total_relationships_created += relationships_created
            total_success += 1

        except NotImplementedError as e:
            error_msg = f"Database type not supported for '{sqldb.name}': {str(e)}"
            logger.error(error_msg)
            messages.error(request, error_msg)
            failed_databases.append((sqldb.name, str(e)))
            total_failed += 1
        except Exception as e:
            error_msg = f"Error retrieving foreign key relationships for database '{sqldb.name}': {str(e)}"
            logger.error(error_msg)
            messages.error(request, error_msg)
            failed_databases.append((sqldb.name, str(e)))
            total_failed += 1

    # Summary message
    if total_failed > 0:
        messages.warning(
            request,
            f"Task completed with {total_success} successes and {total_failed} failures out of {total_databases} databases. Total relationships created: {total_relationships_created}",
        )
    else:
        messages.success(
            request,
            f"Successfully processed all {total_databases} databases. Total relationships created: {total_relationships_created}",
        )


def create_tables(modeladmin, request, queryset):
    total_databases = queryset.count()
    total_success = 0
    total_failed = 0
    failed_databases = []

    for sqldb in queryset:
        try:
            logger.info(f"SqlDb: {sqldb.name}")
            logger.info(f"  Host: {sqldb.db_host}")
            logger.info(f"  Type: {sqldb.db_type}")
            logger.info(f"  Database Name: {sqldb.db_name}")
            logger.info(f"  Port: {sqldb.db_port}")
            logger.info(f"  Schema: {sqldb.schema}")
            logger.info(f"  Username: {sqldb.user_name}")
            logger.info(f"  Password: {'*' * len(sqldb.password)}")
            logger.info(f"  Vector DB: {sqldb.vector_db}")

            # Retrieve table names and comments
            table_info = get_table_names_and_comments(sqldb)

            if not table_info:
                error_msg = f"Failed to retrieve tables from database '{sqldb.name}' - connection error or no tables found"
                messages.error(request, error_msg)
                failed_databases.append(
                    (sqldb.name, "Connection error or no tables found")
                )
                total_failed += 1
                continue

            logger.info("  Tables found:")
            for table, comment in table_info:
                logger.info(f"    - {table} (Comment: {comment or 'None'})")
            logger.info("--------------------")

            # Create SqlTable records
            created_tables, skipped_tables = create_sql_tables(sqldb, table_info)

            logger.info("  Tables created:")
            for table, comment in created_tables:
                logger.info(f"    - {table} (Comment: {comment or 'None'})")

            logger.info("  Tables skipped (already existing):")
            for table, comment in skipped_tables:
                logger.info(f"    - {table} (Comment: {comment or 'None'})")

            logger.info("--------------------")
            logger.info("====================")

            # Success message
            messages.success(
                request,
                f"Successfully processed database '{sqldb.name}': {len(created_tables)} tables created, {len(skipped_tables)} tables skipped",
            )
            total_success += 1

        except Exception as e:
            error_msg = f"Failed to process database '{sqldb.name}': {str(e)}"
            logger.error(error_msg)
            messages.error(request, error_msg)
            failed_databases.append((sqldb.name, str(e)))
            total_failed += 1

    # Summary message
    if total_failed > 0:
        messages.warning(
            request,
            f"Task completed with {total_success} successes and {total_failed} failures out of {total_databases} databases",
        )
    else:
        messages.success(
            request, f"Successfully processed all {total_databases} databases"
        )


def create_db_elements(modeladmin, request, queryset):
    total_databases = queryset.count()
    total_success = 0
    total_failed = 0
    failed_databases = []

    for sqldb in queryset:
        try:
            logger.info(f"Processing SqlDb: {sqldb.name}")

            # Step 1: Create all tables
            logger.info("Step 1: Creating tables")
            table_info = get_table_names_and_comments(sqldb)
            if not table_info:
                raise Exception("Failed to retrieve table information")

            created_tables, skipped_tables = create_sql_tables(sqldb, table_info)

            logger.info("Tables created:")
            for table, comment in created_tables:
                logger.info(f"  - {table} (Comment: {comment or 'None'})")
            logger.info("Tables skipped (already existing):")
            for table, comment in skipped_tables:
                logger.info(f"  - {table} (Comment: {comment or 'None'})")

            # Step 2: Create columns for each table
            logger.info("\nStep 2: Creating columns for each table")
            tables_processed = 0
            tables_failed = 0

            for sql_table in SqlTable.objects.filter(sql_db=sqldb):
                try:
                    logger.info(f"Processing table: {sql_table.name}")
                    column_info = get_column_names_and_comments(sqldb, sql_table.name)
                    if not column_info:
                        logger.warning(f"No columns found for table {sql_table.name}")
                        continue

                    created_columns, skipped_columns = create_sql_columns(
                        sql_table, column_info
                    )
                    tables_processed += 1
                except Exception as e:
                    logger.error(f"Error processing table {sql_table.name}: {str(e)}")
                    tables_failed += 1

            # Step 3: Create foreign key relationships
            logger.info("\nStep 3: Creating foreign key relationships")
            try:
                db_manager = get_db_manager(sqldb)
                adapter = getattr(db_manager, "adapter", None)
                if adapter and hasattr(adapter, "get_foreign_keys_as_documents"):
                    fk_docs = adapter.get_foreign_keys_as_documents()
                    relationships_info = [
                        {
                            "source_table_name": d.source_table_name,
                            "source_column_name": d.source_column_name,
                            "target_table_name": d.target_table_name,
                            "target_column_name": d.target_column_name,
                        }
                        for d in fk_docs
                    ]
                else:
                    relationships_info = db_manager.get_foreign_keys()

                # Limit to relationships whose tables exist in our catalog
                existing_tables = set(
                    SqlTable.objects.filter(sql_db=sqldb).values_list("name", flat=True)
                )
                relationships_info = [
                    r
                    for r in relationships_info
                    if r.get("source_table_name") in existing_tables
                    and r.get("target_table_name") in existing_tables
                ]

                relationships_created = 0
                for rel_data in relationships_info:
                    source_table_name = rel_data["source_table_name"]
                    source_column_name = rel_data["source_column_name"]
                    target_table_name = rel_data["target_table_name"]
                    target_column_name = rel_data["target_column_name"]

                    try:
                        source_table = SqlTable.objects.get(
                            name=source_table_name, sql_db=sqldb
                        )
                        target_table = SqlTable.objects.get(
                            name=target_table_name, sql_db=sqldb
                        )
                        # Ensure columns exist; create on-the-fly if missing
                        try:
                            source_column = SqlColumn.objects.get(
                                original_column_name=source_column_name,
                                sql_table=source_table,
                            )
                        except SqlColumn.DoesNotExist:
                            try:
                                col_info = get_column_names_and_comments(
                                    sqldb, source_table.name
                                )
                                create_sql_columns(source_table, col_info)
                                source_column = SqlColumn.objects.get(
                                    original_column_name=source_column_name,
                                    sql_table=source_table,
                                )
                            except Exception:
                                raise
                        try:
                            target_column = SqlColumn.objects.get(
                                original_column_name=target_column_name,
                                sql_table=target_table,
                            )
                        except SqlColumn.DoesNotExist:
                            try:
                                col_info = get_column_names_and_comments(
                                    sqldb, target_table.name
                                )
                                create_sql_columns(target_table, col_info)
                                target_column = SqlColumn.objects.get(
                                    original_column_name=target_column_name,
                                    sql_table=target_table,
                                )
                            except Exception:
                                raise

                        relationship, created = Relationship.objects.get_or_create(
                            source_table=source_table,
                            target_table=target_table,
                            source_column=source_column,
                            target_column=target_column,
                        )
                        if created:
                            relationships_created += 1
                    except Exception as e:
                        logger.warning(f"Error creating relationship: {str(e)}")

                Relationship.update_pk_fk_fields()
                logger.info("Relationships created and pk_field/fk_field updated.")

                # Success message
                messages.success(
                    request,
                    f"Successfully processed database '{sqldb.name}': {len(created_tables)} tables, {tables_processed} tables with columns, {relationships_created} relationships",
                )
                total_success += 1

            except Exception as e:
                raise Exception(f"Error creating relationships: {str(e)}")

        except Exception as e:
            error_msg = f"Failed to process database '{sqldb.name}': {str(e)}"
            logger.error(error_msg)
            messages.error(request, error_msg)
            failed_databases.append((sqldb.name, str(e)))
            total_failed += 1

    # Summary message
    if total_failed > 0:
        messages.warning(
            request,
            f"Task completed with {total_success} successes and {total_failed} failures out of {total_databases} databases",
        )
        for db_name, error in failed_databases:
            messages.error(request, f"  - {db_name}: {error}")
    else:
        messages.success(
            request, f"Successfully processed all {total_databases} databases"
        )


create_db_elements.short_description = (
    "Create all the database elements (tables, columns, and relationships)"
)
