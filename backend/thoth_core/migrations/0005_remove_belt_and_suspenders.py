# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("thoth_core", "0004_migrate_test_executor_to_evaluator"),
    ]

    def database_forwards(apps, schema_editor):
        if schema_editor.connection.vendor == "sqlite":
            # SQLite doesn't support DROP COLUMN directly, need to recreate table
            schema_editor.execute("CREATE TABLE thoth_core_groupprofile_new (id INTEGER PRIMARY KEY AUTOINCREMENT, show_sql BOOLEAN NOT NULL, explain_generated_query BOOLEAN NOT NULL, group_id INTEGER UNIQUE NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE)")
            schema_editor.execute("INSERT INTO thoth_core_groupprofile_new (id, show_sql, explain_generated_query, group_id) SELECT id, show_sql, explain_generated_query, group_id FROM thoth_core_groupprofile")
            schema_editor.execute("DROP TABLE thoth_core_groupprofile")
            schema_editor.execute("ALTER TABLE thoth_core_groupprofile_new RENAME TO thoth_core_groupprofile")
        else:
            # PostgreSQL and others support DROP COLUMN
            # Check if column exists first to be safe, though this is a fresh migration run
            schema_editor.execute("ALTER TABLE thoth_core_groupprofile DROP COLUMN IF EXISTS belt_and_suspenders")

    def database_backwards(apps, schema_editor):
        if schema_editor.connection.vendor == "sqlite":
            schema_editor.execute("CREATE TABLE thoth_core_groupprofile_new (id INTEGER PRIMARY KEY AUTOINCREMENT, show_sql BOOLEAN NOT NULL, explain_generated_query BOOLEAN NOT NULL, group_id INTEGER UNIQUE NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE, belt_and_suspenders BOOLEAN NOT NULL DEFAULT 0)")
            schema_editor.execute("INSERT INTO thoth_core_groupprofile_new (id, show_sql, explain_generated_query, group_id, belt_and_suspenders) SELECT id, show_sql, explain_generated_query, group_id, 0 FROM thoth_core_groupprofile")
            schema_editor.execute("DROP TABLE thoth_core_groupprofile")
            schema_editor.execute("ALTER TABLE thoth_core_groupprofile_new RENAME TO thoth_core_groupprofile")
        else:
            schema_editor.execute("ALTER TABLE thoth_core_groupprofile ADD COLUMN belt_and_suspenders BOOLEAN NOT NULL DEFAULT FALSE")

    operations = [
        migrations.RunPython(database_forwards, database_backwards),
    ]