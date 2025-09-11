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
from thoth_core.models import VectorDb
from thoth_core.utilities.utils import export_csv, import_csv


class VectorDbAdminForm(forms.ModelForm):
    """Custom form for VectorDb"""

    class Meta:
        model = VectorDb
        fields = "__all__"
        widgets = {
            "password": forms.PasswordInput(render_value=True),
        }


@admin.register(VectorDb)
class VectorDbAdmin(admin.ModelAdmin):
    form = VectorDbAdminForm
    list_display = (
        "name",
        "vect_type",
        "get_connection_info",
        "environment",
    )
    search_fields = ("name", "vect_type", "host", "environment")
    list_filter = ("vect_type",)
    ordering = ("name",)
    actions = (export_csv, import_csv, "duplicate_vectordb")
    fieldsets = [
        (None, {"fields": ("name", "vect_type")}),
        (
            "Connection Settings",
            {
                "fields": ("host", "port", "url", "path"),
                "description": "Connection details vary by vector database type",
            },
        ),
        (
            "Authentication",
            {
                "fields": ("username", "password", "environment"),
                "description": "Authentication credentials",
            },
        ),
        ("Advanced Settings", {"fields": ("tenant",), "classes": ("collapse",)}),
    ]

    def get_connection_info(self, obj):
        """Display connection information for the vector database."""
        if obj.host:
            return f"{obj.host}:{obj.port}" if obj.port else obj.host
        elif obj.url:
            return obj.url
        elif obj.path:
            return f"Path: {obj.path}"
        else:
            return "No connection info"

    get_connection_info.short_description = "Connection Info"

    def duplicate_vectordb(self, request, queryset):
        """
        Duplicate selected VectorDb instances with name + "_copy"
        """
        duplicated_count = 0

        for vectordb in queryset:
            try:
                # Store the original name for error messages
                original_name = vectordb.name

                # Create the duplicate
                vectordb.pk = None  # This will create a new instance when saved
                vectordb.id = None  # Ensure the ID is also reset
                vectordb.name = f"{original_name}_copy"

                vectordb.save()
                duplicated_count += 1

            except Exception as e:
                messages.error(
                    request, f"Error duplicating VectorDb '{original_name}': {str(e)}"
                )
                continue

        if duplicated_count > 0:
            messages.success(
                request, f"Successfully duplicated {duplicated_count} VectorDb(s)."
            )
        else:
            messages.warning(request, "No VectorDb instances were duplicated.")

    duplicate_vectordb.short_description = "Duplicate selected VectorDb instances"

    def get_form(self, request, obj=None, **kwargs):
        """Customize form to show relevant fields based on vector DB type."""
        form = super().get_form(request, obj, **kwargs)

        # Add help text to clarify field usage
        if "name" in form.base_fields:
            form.base_fields[
                "name"
            ].help_text = (
                "Collection name (Qdrant, ChromaDB, Milvus) or database name (PGVector)"
            )

        return form
