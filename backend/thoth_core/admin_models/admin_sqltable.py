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

from django import forms
from django.contrib import admin, messages
from thoth_core.models import SqlTable, SqlDb, SqlColumn
from thoth_core.utilities.utils import export_csv, import_csv
from thoth_core.dbmanagement import create_columns
from thoth_core.thoth_ai.thoth_workflow.create_table_comments import (
    create_table_comments,
)
from thoth_core.thoth_ai.thoth_workflow.async_table_comments import (
    start_async_table_comments,
)
from thoth_core.utilities.task_validation import check_sqldb_task_can_start
 


def validate_fk_fields(columns, request=None):
    """
    Validates the format of fk_field for the given columns.
    Returns a tuple of (error_count, success_count, error_messages, total_checked)
    """
    error_count = 0
    success_count = 0
    error_messages = []
    total_checked = 0

    for column in columns:
        # Skip empty fk_field values without counting them
        if not column.fk_field or column.fk_field.strip() == "":
            continue

        # Increment the counter for columns with FK values
        total_checked += 1

        # Get the SQL database of the table this column belongs to
        sql_db = column.sql_table.sql_db

        # Parse references (either a single reference or comma-separated list)
        references = [ref.strip() for ref in column.fk_field.split(",")]
        column_has_error = False

        for reference in references:
            # Check format: tablename.columnname
            parts = reference.split(".")
            if len(parts) != 2:
                error_msg = (
                    f"Invalid format in column '{column.original_column_name}' of table '{column.sql_table.name}': "
                    f"'{reference}' should be in format 'tablename.columnname'"
                )
                error_messages.append(error_msg)
                column_has_error = True
                continue

            table_name, column_name = parts

            # Check if the referenced table exists in the same database
            try:
                ref_table = SqlTable.objects.get(name=table_name, sql_db=sql_db)
            except SqlTable.DoesNotExist:
                error_msg = (
                    f"Invalid reference in column '{column.original_column_name}' of table '{column.sql_table.name}': "
                    f"Table '{table_name}' does not exist in database '{sql_db.name}'"
                )
                error_messages.append(error_msg)
                column_has_error = True
                continue

            # Check if the referenced column exists in the referenced table
            if not SqlColumn.objects.filter(
                sql_table=ref_table, original_column_name=column_name
            ).exists():
                error_msg = (
                    f"Invalid reference in column '{column.original_column_name}' of table '{column.sql_table.name}': "
                    f"Column '{column_name}' does not exist in table '{table_name}'"
                )
                error_messages.append(error_msg)
                column_has_error = True
                continue

        # Count errors per column, not per reference
        if column_has_error:
            error_count += 1
        else:
            success_count += 1

    return error_count, success_count, error_messages, total_checked


class SqlTableAdminForm(forms.ModelForm):
    sql_db = forms.ModelChoiceField(
        queryset=SqlDb.objects.all(),
        label="SQL Db",
        widget=forms.Select(attrs={"style": "width: 250px;"}),
    )

    class Meta:
        model = SqlTable
        fields = "__all__"


class SqlDbFilter(admin.SimpleListFilter):
    title = "Database"
    parameter_name = "sql_db"

    def lookups(self, request, model_admin):
        dbs = SqlDb.objects.all().order_by("name")
        return [(db.id, db.name) for db in dbs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sql_db__id=self.value())
        return queryset


@admin.register(SqlTable)
class SqlTableAdmin(admin.ModelAdmin):
    form = SqlTableAdminForm
    list_display = ("db_name", "name", "description", "generated_comment")
    search_fields = ("sql_db__name", "name", "description", "generated_comment")
    list_filter = (SqlDbFilter,)
    ordering = ("sql_db__name", "name")
    actions = (
        export_csv,
        import_csv,
        create_columns,
        "validate_table_fk_fields",
        "clean_invalid_pk_fk_fields",
        "copy_generated_to_description",
        create_table_comments,
        "create_table_comments_async",
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sql_db":
            kwargs["queryset"] = SqlDb.objects.all().order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def db_name(self, obj):
        return obj.sql_db.name

    db_name.short_description = "Database"
    create_table_comments.short_description = (
        "Generate selected tables comment (AI assisted)"
    )

    def copy_generated_to_description(self, request, queryset):
        """
        Copy generated_comment to description only if generated_comment contains text.
        """
        updated_count = 0
        total_count = queryset.count()

        for table in queryset:
            if table.generated_comment and table.generated_comment.strip():
                table.description = table.generated_comment
                table.save()
                updated_count += 1

        if updated_count == 0:
            self.message_user(
                request,
                f"No tables updated - none of the {total_count} selected tables had text in generated_comment field.",
            )
        else:
            self.message_user(
                request,
                f"{updated_count} of {total_count} tables updated successfully (only tables with text in generated_comment were updated).",
            )

    copy_generated_to_description.short_description = (
        "Copy generated comment to description"
    )

    def validate_table_fk_fields(self, request, queryset):
        """
        Validates the format of fk_field for all columns in the selected tables.
        """
        total_error_count = 0
        total_success_count = 0
        all_error_messages = []
        total_checked = 0

        for table in queryset:
            columns = SqlColumn.objects.filter(sql_table=table)
            error_count, success_count, error_messages, checked = validate_fk_fields(
                columns, request
            )

            total_error_count += error_count
            total_success_count += success_count
            all_error_messages.extend(error_messages)
            total_checked += checked

        # Display error messages
        for error_msg in all_error_messages:
            messages.error(request, error_msg)

        # Display summary
        if total_error_count == 0:
            if total_checked > 0:
                messages.success(
                    request,
                    f"All {total_checked} foreign key references across {queryset.count()} tables are valid.",
                )
            else:
                messages.info(
                    request,
                    f"No foreign key references found to validate in the {queryset.count()} selected tables.",
                )
        else:
            messages.warning(
                request,
                f"Validation completed with {total_error_count} errors and {total_success_count} valid references out of {total_checked} checked across {queryset.count()} tables.",
            )

    validate_table_fk_fields.short_description = "Validate FK fields in table columns"

    def clean_invalid_pk_fk_fields(self, request, queryset):
        """
        Clean invalid pk_field and fk_field values for all columns in the selected tables.
        Valid pk_field should contain 'PK' or be empty.
        Valid fk_field should be in the format 'table.column_name' or a list of such references.
        """
        total_tables = queryset.count()
        total_columns_updated = 0

        for table in queryset:
            columns_updated = 0
            columns = table.columns.all()

            for column in columns:
                updated = False

                # Check and clean pk_field
                if column.pk_field and "PK" not in column.pk_field:
                    column.pk_field = ""
                    updated = True

                # Check and clean fk_field
                if column.fk_field:
                    # Check if fk_field is in the format 'table.column' or a list of such references
                    valid_format = False

                    # Split by comma to handle lists of references
                    references = [ref.strip() for ref in column.fk_field.split(",")]

                    # Check each reference
                    valid_references = []
                    for ref in references:
                        # Check if reference is in format 'table.column'
                        parts = ref.split(".")
                        if len(parts) == 2:
                            valid_references.append(ref)

                    # If we have valid references, join them back together
                    if valid_references:
                        column.fk_field = ", ".join(valid_references)
                    else:
                        column.fk_field = ""
                        updated = True

                if updated:
                    column.save()
                    columns_updated += 1

            total_columns_updated += columns_updated

        self.message_user(
            request,
            f"Cleaned {total_columns_updated} columns across {total_tables} tables.",
        )

    clean_invalid_pk_fk_fields.short_description = (
        "Clean invalid PK/FK fields in table columns"
    )

    def create_table_comments_async(self, request, queryset):
        """
        Async version of table comment generation to prevent timeouts.
        Uses background processing with status tracking.
        """
        if not queryset.exists():
            self.message_user(
                request,
                "No tables selected for comment generation.",
                level=messages.WARNING,
            )
            return

        # Resolve target database from first selected table (no workspace dependency)
        first_table = queryset.first()
        sql_db = first_table.sql_db if first_table else None
        if not sql_db:
            self.message_user(
                request,
                "Cannot resolve target database for selected tables.",
                level=messages.ERROR,
            )
            return

        can_start, status_message = check_sqldb_task_can_start(
            sql_db, "table_comment"
        )
        # Refresh to reflect any potential cleanup performed by the validator
        sql_db.refresh_from_db()

        if not can_start:
            current_status = sql_db.table_comment_status or "UNKNOWN"
            self.message_user(
                request,
                (
                    f"Cannot start table comment generation for database '{sql_db.name}': "
                    f"{status_message}. Current status: {current_status}."
                ),
                level=messages.WARNING,
            )
            return

        # Get all table IDs
        table_ids = list(queryset.values_list("id", flat=True))

        # Start async task using database id (signature kept for compatibility)
        task_id = start_async_table_comments(sql_db.id, table_ids, request.user.id)

        # Update SqlDb status (reset end time at start)
        sql_db.table_comment_status = "RUNNING"
        sql_db.table_comment_task_id = task_id
        sql_db.table_comment_end_time = None
        sql_db.table_comment_log = f"Started processing {len(table_ids)} tables"
        sql_db.save(update_fields=[
            "table_comment_status",
            "table_comment_task_id",
            "table_comment_end_time",
            "table_comment_log",
        ])

        self.message_user(
            request,
            f"Started async table comment generation for {len(table_ids)} tables on database '{sql_db.name}'. "
            f"Task ID: {task_id}. Check the database status for progress.",
            level=messages.SUCCESS,
        )

    create_table_comments_async.short_description = (
        "Generate selected tables comment (AI assisted - async)"
    )
