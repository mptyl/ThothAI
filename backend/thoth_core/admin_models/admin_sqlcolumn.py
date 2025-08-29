from django import forms
from django.contrib import admin, messages
from django.db import models
from thoth_core.models import SqlColumn, SqlTable, SqlDb, Workspace, ColumnDataTypes
from thoth_core.utilities.utils import export_csv, import_csv
from thoth_core.thoth_ai.thoth_workflow.create_column_comments import create_selected_column_comments
from thoth_core.thoth_ai.thoth_workflow.async_table_comments import start_async_column_comments
from thoth_core.utilities.task_validation import check_task_can_start


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
        if not column.fk_field or column.fk_field.strip() == '':
            continue
            
        # Increment the counter for columns with FK values
        total_checked += 1
        
        # Get the SQL database of the table this column belongs to
        sql_db = column.sql_table.sql_db
        
        # Parse references (either a single reference or comma-separated list)
        references = [ref.strip() for ref in column.fk_field.split(',')]
        column_has_error = False
        
        for reference in references:
            # Check format: tablename.columnname
            parts = reference.split('.')
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
            if not SqlColumn.objects.filter(sql_table=ref_table, original_column_name=column_name).exists():
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

class SqlColumnAdminForm(forms.ModelForm):
    sql_table = forms.ModelChoiceField(
        queryset=SqlTable.objects.all().order_by('sql_db__name', 'name'),
        label="SQL Table",
        widget=forms.Select(attrs={'style': 'width: 300px;'}),
    )
    class Meta:
        model = SqlColumn
        fields = ['original_column_name', 'column_name', 'data_format', 'column_description', 'generated_comment', 'value_description', 'sql_table', 'pk_field', 'fk_field']
        widgets = {
            'original_column_name': forms.TextInput(attrs={'style': 'width: 300px;'}),
            'column_name': forms.TextInput(attrs={'style': 'width: 300px;'}),
            'data_format': forms.Select(choices=ColumnDataTypes, attrs={'style': 'width: 200px;'}),
            'column_description': forms.Textarea(attrs={'rows': 3, 'cols': 40}),
            'generated_comment': forms.Textarea(attrs={'rows': 6, 'cols': 80}),
            'value_description': forms.Textarea(attrs={'rows': 6, 'cols': 80}),
            'pk_field': forms.Textarea(attrs={'rows': 3, 'cols': 40}),
            'fk_field': forms.Textarea(attrs={'rows': 3, 'cols': 40}),
         }

class SqlDbColumnFilter(admin.SimpleListFilter):
    title = 'Database'
    parameter_name = 'sql_db'
    def lookups(self, request, model_admin):
        dbs = SqlDb.objects.all().order_by('name')
        return [(db.name, db.name) for db in dbs]
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sql_table__sql_db__name=self.value())
        return queryset

class SqlTableColumnFilter(admin.SimpleListFilter):
    title = 'Table'
    parameter_name = 'sql_table'
    def lookups(self, request, model_admin):
        db_name = request.GET.get('sql_db')
        if db_name:
            tables = SqlTable.objects.filter(sql_db__name=db_name).order_by('name')
        else:
            tables = SqlTable.objects.all().order_by('name')
        return [(table.name, table.name) for table in tables]
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sql_table__name=self.value())
        return queryset

@admin.register(SqlColumn)
class SqlColumnAdmin(admin.ModelAdmin):
    form = SqlColumnAdminForm
    list_display = (
        'original_column_name', 'column_name', 'data_format', 'column_description', 'generated_comment', 'value_description', 'get_table_name', 'get_db_name', 'pk_field', 'fk_field')
    list_filter = (SqlDbColumnFilter, SqlTableColumnFilter)
    search_fields = ('original_column_name', 'column_name')
    ordering = ('sql_table__sql_db__name', 'sql_table__name', 'original_column_name')
    actions = [export_csv, import_csv, 'copy_generated_to_description', 'copy_original_name_to_name', 'copy_name_to_original_name', 'validate_fk_field_format', create_selected_column_comments,  'create_column_comments_async']
    create_selected_column_comments.short_description = 'Generate selected columns comment (AI assisted)'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sql_table":
            kwargs["queryset"] = SqlTable.objects.all().order_by('sql_db__name', 'name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_table_name(self, obj):
        """Display the table name for this column."""
        return obj.sql_table.name if obj.sql_table else "-"
    get_table_name.short_description = 'Table'
    get_table_name.admin_order_field = 'sql_table__name'
    
    def get_db_name(self, obj):
        """Display the database name for this column."""
        return obj.sql_table.sql_db.name if obj.sql_table and obj.sql_table.sql_db else "-"
    get_db_name.short_description = 'Database'
    get_db_name.admin_order_field = 'sql_table__sql_db__name'

    def copy_generated_to_description(self, request, queryset):
        """
        Copy generated_comment to column_description only if generated_comment contains text.
        """
        updated_count = 0
        total_count = queryset.count()
        
        for column in queryset:
            if column.generated_comment and column.generated_comment.strip():
                column.column_description = column.generated_comment
                column.save()
                updated_count += 1
        
        if updated_count == 0:
            self.message_user(request, f"No columns updated - none of the {total_count} selected columns had text in generated_comment field.")
        else:
            self.message_user(request, f"{updated_count} of {total_count} columns updated successfully (only columns with text in generated_comment were updated).")
    copy_generated_to_description.short_description = "Copy generated comment to column description"

    def copy_original_name_to_name(self, request, queryset):
        updated = queryset.update(column_name=models.F('original_column_name'))
        self.message_user(request, f"{updated} columns updated successfully.")
    copy_original_name_to_name.short_description = "Copy original column name to column name"

    def copy_name_to_original_name(self, request, queryset):
        updated = queryset.update(original_column_name=models.F('column_name'))
        self.message_user(request, f"{updated} columns updated successfully.")
    copy_name_to_original_name.short_description = "Copy column name to original column name"

    def validate_fk_field_format(self, request, queryset):
        """
        Validates the format of fk_field for selected columns.
        """
        error_count, success_count, error_messages, total_checked = validate_fk_fields(queryset, request)
        
        # Display error messages
        for error_msg in error_messages:
            messages.error(request, error_msg)
        
        # Display summary
        if error_count == 0:
            if total_checked > 0:
                messages.success(request, f"All {total_checked} foreign key references are valid.")
            else:
                messages.info(request, "No foreign key references found to validate.")
        else:
            messages.warning(
                request, 
                f"Validation completed with {error_count} errors and {success_count} valid references out of {total_checked} checked."
            )
    validate_fk_field_format.short_description = "Validate FK field format"

    def create_column_comments_async(self, request, queryset):
        """
        Async version of column comment generation to prevent timeouts.
        Uses background processing with status tracking.
        """
        if not queryset.exists():
            self.message_user(request, "No columns selected for comment generation.", level=messages.WARNING)
            return
            
        # Check if we have a current workspace
        if not hasattr(request, 'current_workspace') or not request.current_workspace:
            self.message_user(request, "No active workspace found. Please select a workspace.", level=messages.ERROR)
            return
            
        workspace = request.current_workspace
        
        # Verify that all selected columns belong to the workspace's database
        first_column = queryset.first()
        if first_column.sql_table.sql_db != workspace.sql_db:
            self.message_user(
                request,
                f"Selected columns do not belong to the current workspace database '{workspace.sql_db.name}'. "
                f"Please ensure you're working with columns from the correct database.",
                level=messages.ERROR
            )
            return
            
        # Check if a new task can be started (with intelligent validation)
        can_start, message = check_task_can_start(workspace, 'column_comment')
        if not can_start:
            self.message_user(
                request,
                f"Cannot start column comment generation: {message}. "
                f"Current status: {workspace.column_comment_status}",
                level=messages.WARNING
            )
            return
            
        # Get all column IDs
        column_ids = list(queryset.values_list('id', flat=True))
        
        # Start async task with workspace ID
        task_id = start_async_column_comments(workspace.id, column_ids, request.user.id)
        
        # Update workspace status
        workspace.column_comment_status = Workspace.PreprocessingStatus.RUNNING
        workspace.column_comment_task_id = task_id
        workspace.column_comment_log = f"Started processing {len(column_ids)} columns"
        workspace.save()
        
        self.message_user(
            request,
            f"Started async column comment generation for {len(column_ids)} columns. "
            f"Task ID: {task_id}. Check the workspace status for progress.",
            level=messages.SUCCESS
        )
    
    create_column_comments_async.short_description = 'Generate selected columns comment (AI assisted - async)'