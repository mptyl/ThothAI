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
from thoth_core.models import Workspace, Agent, AiModel, SqlDb, Setting
from thoth_core.utilities.utils import export_csv, import_csv


class WorkspaceAdminForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = "__all__"
        labels = {
            "question_validator": "Question Validator and Translator",
            "kw_sel_agent": "Keyword Extractor Agent",
            "sql_basic_agent": "Basic SQL Generator Agent",
            "sql_advanced_agent": "Advanced SQL Generator Agent",
            "sql_expert_agent": "Expert SQL Generator Agent",
            "test_gen_agent_1": "Basic Test Generator Agent",
            "test_gen_agent_2": "Advanced Test Generator Agent",
            "test_gen_agent_3": "Expert Test Generator Agent",
            "test_evaluator_agent": "Test Evaluator Agent",
        }
        help_texts = {
            "name": "Unique name for this workspace (REQUIRED)",
            "level": "Access level for this workspace",
            "description": "Description of the workspace purpose and content",
            "sql_db": "Primary SQL database for this workspace",
            "vector_db": "Vector database for semantic operations",
            "setting": "AI and system settings configuration",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "cols": 80}),
            "table_comment_log": forms.Textarea(attrs={"rows": 10, "cols": 160}),
            "column_comment_log": forms.Textarea(attrs={"rows": 10, "cols": 160}),
            "last_preprocess_log": forms.Textarea(attrs={"rows": 10, "cols": 160}),
        }


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    form = WorkspaceAdminForm
    list_display = (
        "name",
        "level",
        "description",
        "id",
        "get_table_comment_status",
        "get_column_comment_status",
        "get_preprocessing_status",
    )
    list_display_links = ("name",)
    search_fields = ("name", "description")
    list_filter = (
        "level",
        "table_comment_status",
        "column_comment_status",
        "preprocessing_status",
    )
    filter_horizontal = ("users", "default_workspace")
    actions = (
        export_csv,
        import_csv,
        "duplicate_workspace",
        "reset_comment_and_preprocessing_fields",
    )
    readonly_fields = (
        "table_comment_status",
        "table_comment_task_id",
        "table_comment_log",
        "table_comment_start_time",
        "table_comment_end_time",
        "column_comment_status",
        "column_comment_task_id",
        "column_comment_log",
        "column_comment_start_time",
        "column_comment_end_time",
        "preprocessing_status",
        "task_id",
        "last_preprocess_log",
        "preprocessing_start_time",
        "preprocessing_end_time",
        "last_preprocess",
        "last_evidence_load",
        "last_sql_loaded",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "level",
                    "description",
                    "users",
                    "default_workspace",
                ),
                "description": "All fields in this section are required except description.",
            },
        ),
        (
            "Database Configuration",
            {
                "fields": ("sql_db", "setting"),
                "description": "Configure the databases and AI settings for this workspace.",
            },
        ),
        (
            "Fallback Model",
            {
                "fields": ("default_model",),
                "classes": ("collapse",),
                "description": "Configure fallback AI model for this workspace.",
            },
        ),
        (
            "Validator, Translator and Keyword Selection Agents",
            {
                "fields": ("question_validator", "kw_sel_agent"),
                "classes": ("collapse",),
                "description": "Configure agents for validation, translation and keyword selection.",
            },
        ),
        (
            "SQL Generation Agents",
            {
                "fields": (
                    "sql_basic_agent",
                    "sql_advanced_agent",
                    "sql_expert_agent",
                    "number_of_sql_to_generate",
                ),
                "classes": ("collapse",),
                "description": "Configure agents for SQL generation at different complexity levels.",
            },
        ),
        (
            "Test Generation & Evaluation Agents",
            {
                "fields": (
                    "test_gen_agent_1",
                    "test_gen_agent_2",
                    "test_gen_agent_3",
                    "test_evaluator_agent",
                    "number_of_tests_to_generate",
                    "evaluation_threshold",
                ),
                "classes": ("collapse",),
                "description": "Configure agents for test generation and SQL evaluation.",
            },
        ),
        (
            "Explanation and Ask For Human Agents",
            {
                "fields": ("explain_sql_agent", "ask_human_help_agent"),
                "classes": ("collapse",),
                "description": "Configure agents for SQL explanation and  Asking Human Help.",
            },
        ),
        (
            "Table Comments Status",
            {
                "fields": (
                    "table_comment_status",
                    "table_comment_task_id",
                    "table_comment_log",
                    "table_comment_start_time",
                    "table_comment_end_time",
                ),
                "classes": ("collapse",),
                "description": "Status and logs for table comment generation tasks.",
            },
        ),
        (
            "Column Comments Status",
            {
                "fields": (
                    "column_comment_status",
                    "column_comment_task_id",
                    "column_comment_log",
                    "column_comment_start_time",
                    "column_comment_end_time",
                ),
                "classes": ("collapse",),
                "description": "Status and logs for column comment generation tasks.",
            },
        ),
        (
            "Preprocessing Status",
            {
                "fields": (
                    "preprocessing_status",
                    "task_id",
                    "last_preprocess_log",
                    "preprocessing_start_time",
                    "preprocessing_end_time",
                    "last_preprocess",
                    "last_evidence_load",
                    "last_sql_loaded",
                ),
                "classes": ("collapse",),
                "description": "Status and logs for preprocessing and data loading tasks.",
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
                "description": "Record creation and modification timestamps.",
            },
        ),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sql_db":
            kwargs["queryset"] = SqlDb.objects.all().order_by("name")
        elif db_field.name == "setting":
            kwargs["queryset"] = Setting.objects.all().order_by("name")
        elif db_field.name == "default_model":
            kwargs["queryset"] = AiModel.objects.all().order_by("name")
        elif db_field.name in [
            "question_validator",
            "kw_sel_agent",
            "sql_basic_agent",
            "sql_advanced_agent",
            "sql_expert_agent",
            "test_gen_agent_1",
            "test_gen_agent_2",
            "test_gen_agent_3",
            "explain_sql_agent",
            "ask_human_help_agent",
        ]:
            kwargs["queryset"] = Agent.objects.all().order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_table_comment_status(self, obj):
        """Display the table comment generation status."""
        return obj.table_comment_status if obj.table_comment_status else "IDLE"

    get_table_comment_status.short_description = "Table Comments"
    get_table_comment_status.admin_order_field = "table_comment_status"

    def get_column_comment_status(self, obj):
        """Display the column comment generation status."""
        return obj.column_comment_status if obj.column_comment_status else "IDLE"

    get_column_comment_status.short_description = "Column Comments"
    get_column_comment_status.admin_order_field = "column_comment_status"

    def get_preprocessing_status(self, obj):
        """Display the preprocessing status."""
        return obj.preprocessing_status if obj.preprocessing_status else "IDLE"

    get_preprocessing_status.short_description = "Preprocessing"
    get_preprocessing_status.admin_order_field = "preprocessing_status"

    def duplicate_workspace(self, request, queryset):
        """
        Duplicate selected Workspace instances with name + " copy"
        """
        duplicated_count = 0

        for workspace in queryset:
            try:
                # Store the original name for error messages
                original_name = workspace.name

                # Create the duplicate workspace
                workspace.pk = None  # This will create a new instance when saved
                workspace.id = None  # Ensure the ID is also reset
                workspace.name = f"{original_name} copy"

                # Reset status fields to default values for the copy
                workspace.table_comment_status = Workspace.PreprocessingStatus.IDLE
                workspace.table_comment_task_id = None
                workspace.table_comment_log = None
                workspace.table_comment_start_time = None
                workspace.table_comment_end_time = None
                workspace.column_comment_status = Workspace.PreprocessingStatus.IDLE
                workspace.column_comment_task_id = None
                workspace.column_comment_log = None
                workspace.column_comment_start_time = None
                workspace.column_comment_end_time = None
                workspace.preprocessing_status = Workspace.PreprocessingStatus.IDLE
                workspace.task_id = None
                workspace.last_preprocess_log = None
                workspace.preprocessing_start_time = None
                workspace.preprocessing_end_time = None
                workspace.last_preprocess = None
                workspace.last_evidence_load = None
                workspace.last_sql_loaded = None

                workspace.save()

                # Copy many-to-many relationships
                # Note: users and default_workspace need to be copied after save
                original_workspace = Workspace.objects.get(name=original_name)
                workspace.users.set(original_workspace.users.all())
                workspace.default_workspace.set(
                    original_workspace.default_workspace.all()
                )

                duplicated_count += 1

            except Exception as e:
                messages.error(
                    request, f"Error duplicating workspace '{original_name}': {str(e)}"
                )
                continue

        if duplicated_count > 0:
            messages.success(
                request, f"Successfully duplicated {duplicated_count} workspace(s)."
            )
        else:
            messages.warning(request, "No workspaces were duplicated.")

    duplicate_workspace.short_description = "Duplicate selected workspaces"

    def reset_comment_and_preprocessing_fields(self, request, queryset):
        """
        Reset comment generation and preprocessing status fields for selected workspaces.
        """
        reset_count = 0

        for workspace in queryset:
            try:
                # Reset table comment fields
                workspace.table_comment_status = Workspace.PreprocessingStatus.IDLE
                workspace.table_comment_task_id = None
                workspace.table_comment_log = None
                workspace.table_comment_start_time = None
                workspace.table_comment_end_time = None

                # Reset column comment fields
                workspace.column_comment_status = Workspace.PreprocessingStatus.IDLE
                workspace.column_comment_task_id = None
                workspace.column_comment_log = None
                workspace.column_comment_start_time = None
                workspace.column_comment_end_time = None

                # Reset preprocessing fields
                workspace.preprocessing_status = Workspace.PreprocessingStatus.IDLE
                workspace.task_id = None
                workspace.last_preprocess_log = None
                workspace.preprocessing_start_time = None
                workspace.preprocessing_end_time = None
                workspace.last_preprocess = None
                workspace.last_evidence_load = None
                workspace.last_sql_loaded = None

                workspace.save()
                reset_count += 1

            except Exception as e:
                messages.error(
                    request, f"Error resetting workspace '{workspace.name}': {str(e)}"
                )
                continue

        if reset_count > 0:
            messages.success(request, f"Successfully reset {reset_count} workspace(s).")
        else:
            messages.warning(request, "No workspaces were reset.")

    reset_comment_and_preprocessing_fields.short_description = (
        "Reset comment and preprocessing fields"
    )
