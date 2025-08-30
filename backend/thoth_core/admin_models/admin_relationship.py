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
from django.contrib import admin
from thoth_core.models import Relationship, SqlDb, SqlTable, SqlColumn
from thoth_core.utilities.utils import export_csv, import_csv


class RelationshipAdminForm(forms.ModelForm):
    database = forms.ModelChoiceField(
        queryset=SqlDb.objects.all(),
        label="Database",
        required=True,
        widget=forms.Select(attrs={"style": "width: 300px;", "id": "id_database"}),
        help_text="Select the database first, then choose tables from that database",
    )

    # Remove explicit ModelChoiceField definitions for ForeignKey fields
    # Let Django handle them automatically
    class Meta:
        model = Relationship
        fields = [
            "database",
            "source_table",
            "target_table",
            "source_column",
            "target_column",
        ]
        widgets = {
            "source_table": forms.Select(attrs={"style": "width: 300px;"}),
            "target_table": forms.Select(attrs={"style": "width: 300px;"}),
        }

    def __init__(self, *args, **kwargs):
        # Extract the request object before calling super().__init__
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Get selected database ID (either from existing instance or from form data)
        selected_db_id = None
        if self.instance and self.instance.pk:
            # If editing an existing relationship, get the database from source table
            selected_db_id = self.instance.source_table.sql_db.id
            self.fields["database"].initial = selected_db_id

            # Django automatically handles ForeignKey field values from the instance

        elif self.data and "database" in self.data:
            selected_db_id = self.data.get("database")
        elif self.request and self.request.GET.get("database"):
            # If database is passed in URL parameters
            selected_db_id = self.request.GET.get("database")

        # Set up widget attributes for all modes
        for field_name in [
            "source_table",
            "target_table",
            "source_column",
            "target_column",
        ]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({"style": "width: 300px;"})

        # Handle querysets based on whether we're editing or creating
        if self.instance and self.instance.pk:
            # Editing existing relationship - provide full querysets so values display correctly
            # JavaScript will handle filtering, but we need the current values to be available
            if "source_table" in self.fields:
                self.fields["source_table"].queryset = SqlTable.objects.all().order_by(
                    "sql_db__name", "name"
                )
            if "target_table" in self.fields:
                self.fields["target_table"].queryset = SqlTable.objects.all().order_by(
                    "sql_db__name", "name"
                )
            if "source_column" in self.fields:
                self.fields[
                    "source_column"
                ].queryset = SqlColumn.objects.all().order_by(
                    "sql_table__sql_db__name", "sql_table__name", "original_column_name"
                )
                self.fields[
                    "source_column"
                ].label_from_instance = self.label_from_instance_column
            if "target_column" in self.fields:
                self.fields[
                    "target_column"
                ].queryset = SqlColumn.objects.all().order_by(
                    "sql_table__sql_db__name", "sql_table__name", "original_column_name"
                )
                self.fields[
                    "target_column"
                ].label_from_instance = self.label_from_instance_column
        else:
            # Creating new relationship - start with empty querysets (populated by JavaScript)
            if "source_table" in self.fields:
                self.fields["source_table"].queryset = SqlTable.objects.none()
            if "target_table" in self.fields:
                self.fields["target_table"].queryset = SqlTable.objects.none()
            if "source_column" in self.fields:
                self.fields["source_column"].queryset = SqlColumn.objects.none()
                self.fields[
                    "source_column"
                ].label_from_instance = self.label_from_instance_column
            if "target_column" in self.fields:
                self.fields["target_column"].queryset = SqlColumn.objects.none()
                self.fields[
                    "target_column"
                ].label_from_instance = self.label_from_instance_column

    def label_from_instance_column(self, obj):
        """Custom label for column dropdowns to show table.column"""
        return f"{obj.sql_table.name}.{obj.original_column_name}"

    def clean(self):
        cleaned_data = super().clean()
        database = cleaned_data.get("database")
        source_table = cleaned_data.get("source_table")
        target_table = cleaned_data.get("target_table")
        source_column = cleaned_data.get("source_column")
        target_column = cleaned_data.get("target_column")

        # Validate that source table belongs to selected database
        if source_table and database and source_table.sql_db != database:
            raise forms.ValidationError(
                "Source table must belong to the selected database."
            )

        # Validate that target table belongs to selected database
        if target_table and database and target_table.sql_db != database:
            raise forms.ValidationError(
                "Target table must belong to the selected database."
            )

        # Validate that source column belongs to source table
        if source_column and source_table and source_column.sql_table != source_table:
            raise forms.ValidationError(
                "Source column must belong to the source table."
            )

        # Validate that target column belongs to target table
        if target_column and target_table and target_column.sql_table != target_table:
            raise forms.ValidationError(
                "Target column must belong to the target table."
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # The database field is not part of the Relationship model, so don't try to save it
        # It's only used for filtering in the form
        if commit:
            instance.save()
        return instance


class SqlDbRelationshipFilter(admin.SimpleListFilter):
    title = "Database"
    parameter_name = "sql_db"

    def lookups(self, request, model_admin):
        dbs = SqlDb.objects.all().order_by("name")
        return [(db.id, db.name) for db in dbs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source_table__sql_db__id=self.value())
        return queryset


class SqlTableSourceRelationshipFilter(admin.SimpleListFilter):
    title = "Source Table"
    parameter_name = "source_table"

    def lookups(self, request, model_admin):
        db_id = request.GET.get("sql_db")
        if db_id:
            tables = SqlTable.objects.filter(sql_db__id=db_id).order_by("name")
        else:
            tables = SqlTable.objects.all().order_by("name")
        return [(table.id, table.name) for table in tables]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source_table__id=self.value())
        return queryset


class SqlTableTargetRelationshipFilter(admin.SimpleListFilter):
    title = "Target Table"
    parameter_name = "target_table"

    def lookups(self, request, model_admin):
        db_id = request.GET.get("sql_db")
        if db_id:
            tables = SqlTable.objects.filter(sql_db__id=db_id).order_by("name")
        else:
            tables = SqlTable.objects.all().order_by("name")
        return [(table.id, table.name) for table in tables]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(target_table__id=self.value())
        return queryset


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    form = RelationshipAdminForm
    change_form_template = "admin/thoth_core/relationship/change_form.html"
    list_display = (
        "source_db",
        "source_table_name",
        "source_column_name",
        "target_table_name",
        "target_column_name",
    )
    list_filter = (
        SqlDbRelationshipFilter,
        SqlTableSourceRelationshipFilter,
        SqlTableTargetRelationshipFilter,
    )
    search_fields = (
        "source_table__name",
        "target_table__name",
        "source_column__original_column_name",
        "target_column__original_column_name",
    )
    ordering = (
        "source_table__sql_db__name",
        "source_table__name",
        "target_table__name",
    )
    actions = (export_csv, import_csv, "update_pk_fk_fields")

    def get_form(self, request, obj=None, **kwargs):
        """Override get_form to pass the request to the form for filtering columns based on selected database and tables."""
        FormClass = super().get_form(request, obj, **kwargs)

        class FormWithRequest(FormClass):
            def __init__(self, *args, **kwargs):
                kwargs["request"] = request
                super().__init__(*args, **kwargs)

        return FormWithRequest

    # JavaScript completely disabled - using pure Django form
    pass

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "source_table":
            kwargs["queryset"] = SqlTable.objects.all().order_by("sql_db__name", "name")
        elif db_field.name == "target_table":
            kwargs["queryset"] = SqlTable.objects.all().order_by("sql_db__name", "name")
        elif db_field.name == "source_column":
            kwargs["queryset"] = SqlColumn.objects.all().order_by(
                "sql_table__sql_db__name", "sql_table__name", "original_column_name"
            )
        elif db_field.name == "target_column":
            kwargs["queryset"] = SqlColumn.objects.all().order_by(
                "sql_table__sql_db__name", "sql_table__name", "original_column_name"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def source_db(self, obj):
        """Display the source database name."""
        return (
            obj.source_table.sql_db.name
            if obj.source_table and obj.source_table.sql_db
            else "-"
        )

    source_db.short_description = "Database"
    source_db.admin_order_field = "source_table__sql_db__name"

    def source_table_name(self, obj):
        """Display the source table name."""
        return obj.source_table.name if obj.source_table else "-"

    source_table_name.short_description = "Source Table"
    source_table_name.admin_order_field = "source_table__name"

    def source_column_name(self, obj):
        """Display the source column name."""
        return obj.source_column.original_column_name if obj.source_column else "-"

    source_column_name.short_description = "Source Column"
    source_column_name.admin_order_field = "source_column__original_column_name"

    def target_table_name(self, obj):
        """Display the target table name."""
        return obj.target_table.name if obj.target_table else "-"

    target_table_name.short_description = "Target Table"
    target_table_name.admin_order_field = "target_table__name"

    def target_column_name(self, obj):
        """Display the target column name."""
        return obj.target_column.original_column_name if obj.target_column else "-"

    target_column_name.short_description = "Target Column"
    target_column_name.admin_order_field = "target_column__original_column_name"
