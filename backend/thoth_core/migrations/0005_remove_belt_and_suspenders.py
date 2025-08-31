# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("thoth_core", "0004_migrate_test_executor_to_evaluator"),
    ]

    operations = [
        migrations.RunSQL(
            # SQLite doesn't support DROP COLUMN directly, need to recreate table
            sql=[
                """
                CREATE TABLE thoth_core_groupprofile_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    show_sql BOOLEAN NOT NULL,
                    explain_generated_query BOOLEAN NOT NULL,
                    group_id INTEGER UNIQUE NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE
                );
                """,
                """
                INSERT INTO thoth_core_groupprofile_new (id, show_sql, explain_generated_query, group_id)
                SELECT id, show_sql, explain_generated_query, group_id 
                FROM thoth_core_groupprofile;
                """,
                "DROP TABLE thoth_core_groupprofile;",
                "ALTER TABLE thoth_core_groupprofile_new RENAME TO thoth_core_groupprofile;",
            ],
            reverse_sql=[
                """
                CREATE TABLE thoth_core_groupprofile_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    show_sql BOOLEAN NOT NULL,
                    explain_generated_query BOOLEAN NOT NULL,
                    group_id INTEGER UNIQUE NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
                    belt_and_suspenders BOOLEAN NOT NULL DEFAULT 0
                );
                """,
                """
                INSERT INTO thoth_core_groupprofile_new (id, show_sql, explain_generated_query, group_id, belt_and_suspenders)
                SELECT id, show_sql, explain_generated_query, group_id, 0
                FROM thoth_core_groupprofile;
                """,
                "DROP TABLE thoth_core_groupprofile;",
                "ALTER TABLE thoth_core_groupprofile_new RENAME TO thoth_core_groupprofile;",
            ],
            state_operations=[],  # Don't change the state since field doesn't exist in model
        ),
    ]