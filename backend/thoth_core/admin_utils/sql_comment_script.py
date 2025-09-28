"""Utilities to build SQL comment synchronization scripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from django.utils import timezone
from django.utils.text import slugify

from thoth_core.models import SQLDBChoices, SqlColumn, SqlDb, SqlTable
from thoth_core.utilities.shared_paths import get_data_exchange_path


@dataclass(frozen=True)
class CommentScript:
    """Container for generated SQL script details."""

    content: str
    filename: str
    absolute_path: Path


def build_comment_script(
    sql_db: SqlDb,
    tables: Sequence[SqlTable],
) -> CommentScript:
    """Create SQL comment script for the given database/tables.

    Currently supports PostgreSQL; other database engines will be added later.
    """

    if not tables:
        raise ValueError("No tables provided for comment script generation.")

    for table in tables:
        if table.sql_db_id != sql_db.id:
            raise ValueError(
                "All tables must belong to the provided SqlDb when generating the comment script."
            )

    if sql_db.db_type == SQLDBChoices.POSTGRES:
        return _build_postgres_comment_script(sql_db, tables)
    if sql_db.db_type == SQLDBChoices.SQLSERVER:
        return _build_sqlserver_comment_script(sql_db, tables)
    if sql_db.db_type in (SQLDBChoices.MARIADB, SQLDBChoices.MYSQL):
        return _build_mysql_comment_script(sql_db, tables)

    raise NotImplementedError(
        f"Comment script generation not yet implemented for database type '{sql_db.db_type}'."
    )


def _build_postgres_comment_script(
    sql_db: SqlDb,
    tables: Sequence[SqlTable],
) -> CommentScript:
    schema = sql_db.schema.strip() if sql_db.schema else "public"
    schema_ident = _quote_ident(schema)
    generated_at = timezone.now()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S%f")

    header_lines: List[str] = [
        "-- ThothAI SQL comment synchronization script",
        f"-- Database: {sql_db.name}",
        f"-- Schema: {schema}",
        f"-- Generated at: {generated_at.isoformat(timespec='seconds')}",
        "",
    ]

    statements: List[str] = []

    ordered_tables = sorted(tables, key=lambda table: table.name or "")

    for table in ordered_tables:
        table_name = table.name
        table_ident = f"{schema_ident}.{_quote_ident(table_name)}"

        description = (table.description or "").strip()
        if description:
            statements.append(
                f"COMMENT ON TABLE {table_ident} IS {_quote_literal(description)};"
            )

        # Iterate over concrete SqlColumn records for the table
        for column in _iter_columns(table):
            column_description = (column.column_description or "").strip()
            if not column_description:
                continue
            column_ident = f"{table_ident}.{_quote_ident(column.original_column_name)}"
            statements.append(
                f"COMMENT ON COLUMN {column_ident} IS {_quote_literal(column_description)};"
            )

    if not statements:
        raise ValueError(
            "No comments found for the selected tables/columns; script would be empty."
        )

    body = "\n".join(statements)
    content = "\n".join(header_lines) + body + "\n"

    filename = _build_filename(sql_db, tables, timestamp)
    absolute_path = _write_to_data_exchange(content, filename)

    return CommentScript(content=content, filename=filename, absolute_path=absolute_path)


def _iter_columns(table: SqlTable) -> Iterable[SqlColumn]:
    # Prefetch_related ensures this doesn't hit the database per column when available.
    columns = list(table.columns.all())
    columns.sort(key=lambda column: column.original_column_name or "")
    return columns


def _quote_ident(identifier: str) -> str:
    escaped = identifier.replace("\"", "\"\"")
    return f'"{escaped}"'


def _quote_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _build_sqlserver_comment_script(
    sql_db: SqlDb,
    tables: Sequence[SqlTable],
) -> CommentScript:
    schema = sql_db.schema.strip() if sql_db.schema else "dbo"
    generated_at = timezone.now()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S%f")

    header_lines: List[str] = [
        "-- ThothAI SQL comment synchronization script",
        f"-- Database: {sql_db.name}",
        f"-- Schema: {schema}",
        f"-- Generated at: {generated_at.isoformat(timespec='seconds')}",
        "-- Database Type: SQL Server",
        "",
    ]

    statements: List[str] = []

    ordered_tables = sorted(tables, key=lambda table: table.name or "")

    for table in ordered_tables:
        table_name = table.name
        description = (table.description or "").strip()
        if description:
            statements.append(
                _sqlserver_extended_property_statement(
                    schema=schema,
                    table=table_name,
                    description=description,
                    column=None,
                )
            )

        for column in _iter_columns(table):
            column_description = (column.column_description or "").strip()
            if not column_description:
                continue
            statements.append(
                _sqlserver_extended_property_statement(
                    schema=schema,
                    table=table_name,
                    column=column.original_column_name,
                    description=column_description,
                )
            )

    if not statements:
        raise ValueError(
            "No comments found for the selected tables/columns; script would be empty."
        )

    body = "\nGO\n\n".join(statements) + "\nGO\n"
    content = "\n".join(header_lines) + body

    filename = _build_filename(sql_db, tables, timestamp)
    absolute_path = _write_to_data_exchange(content, filename)

    return CommentScript(content=content, filename=filename, absolute_path=absolute_path)


def _sqlserver_extended_property_statement(
    *,
    schema: str,
    table: str,
    description: str,
    column: str | None,
) -> str:
    level_params = [
        "@level0type = N'SCHEMA', @level0name = {schema_name}",
        "@level1type = N'TABLE', @level1name = {table_name}",
    ]

    if column is not None:
        level_params.append("@level2type = N'COLUMN', @level2name = {column_name}")

    level_mapping = {
        "schema_name": _sqlserver_literal(schema),
        "table_name": _sqlserver_literal(table),
        "column_name": _sqlserver_literal(column) if column is not None else "",
    }

    level_fragment = ",\n        ".join(
        param.format(**level_mapping) for param in level_params
    )

    value_literal = _sqlserver_literal(description)

    update_block = (
        "EXEC sys.sp_updateextendedproperty\n"
        "        @name = N'MS_Description',\n"
        f"        @value = {value_literal},\n"
        f"        {level_fragment};"
    )

    add_block = (
        "EXEC sys.sp_addextendedproperty\n"
        "        @name = N'MS_Description',\n"
        f"        @value = {value_literal},\n"
        f"        {level_fragment};"
    )

    return (
        "BEGIN TRY\n"
        f"    {update_block}\n"
        "END TRY\n"
        "BEGIN CATCH\n"
        f"    {add_block}\n"
        "END CATCH"
    )


def _sqlserver_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"N'{escaped}'"


def _build_mysql_comment_script(
    sql_db: SqlDb,
    tables: Sequence[SqlTable],
) -> CommentScript:
    generated_at = timezone.now()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S%f")

    schema = sql_db.schema.strip() if sql_db.schema else None

    header_lines: List[str] = [
        "-- ThothAI SQL comment synchronization script",
        f"-- Database: {sql_db.name}",
        f"-- Schema: {schema or sql_db.db_name}",
        f"-- Generated at: {generated_at.isoformat(timespec='seconds')}",
        "-- Database Type: MySQL/MariaDB",
        "",
    ]

    statements: List[str] = []

    ordered_tables = sorted(tables, key=lambda table: table.name or "")

    for table in ordered_tables:
        table_name = table.name
        description = (table.description or "").strip()
        if description:
            statements.append(
                f"ALTER TABLE {_mysql_identifier(table_name)} COMMENT = {_mysql_literal(description)};"
            )

        for column in _iter_columns(table):
            column_description = (column.column_description or "").strip()
            if not column_description:
                continue

            statements.append(
                "ALTER TABLE {table_name} MODIFY COLUMN {column_name} {column_type} COMMENT {comment};".format(
                    table_name=_mysql_identifier(table_name),
                    column_name=_mysql_identifier(column.original_column_name),
                    column_type=_mysql_column_type(column),
                    comment=_mysql_literal(column_description),
                )
            )

    if not statements:
        raise ValueError(
            "No comments found for the selected tables/columns; script would be empty."
        )

    body = "\n".join(statements) + "\n"
    content = "\n".join(header_lines) + body

    filename = _build_filename(sql_db, tables, timestamp)
    absolute_path = _write_to_data_exchange(content, filename)

    return CommentScript(content=content, filename=filename, absolute_path=absolute_path)


def _mysql_identifier(name: str) -> str:
    escaped = name.replace("`", "``")
    return f"`{escaped}`"


def _mysql_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _mysql_column_type(column: SqlColumn) -> str:
    data_format = column.data_format or ""
    if data_format:
        return data_format
    return "TEXT"


def _build_filename(
    sql_db: SqlDb,
    tables: Sequence[SqlTable],
    timestamp: str,
) -> str:
    db_slug = slugify(sql_db.name) or "database"

    if len(tables) == 1:
        table_slug = slugify(tables[0].name) or "table"
        identifier = f"{db_slug}__{table_slug}"
    else:
        identifier = f"{db_slug}__{len(tables)}_tables"

    return f"comments_{identifier}_{timestamp}.sql"


def _write_to_data_exchange(content: str, filename: str) -> Path:
    base_dir = Path(get_data_exchange_path())
    base_dir.mkdir(parents=True, exist_ok=True)

    file_path = base_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path
