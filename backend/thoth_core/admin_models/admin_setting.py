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

from django.contrib import admin
from thoth_core.models import Setting
from thoth_core.utilities.utils import export_csv, import_csv


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("name", "theme", "get_language_display")
    search_fields = ("name",)
    ordering = ("name",)
    actions = (export_csv, import_csv)

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name", "theme", "language"),
                "description": "Basic settings for the workspace.",
            },
        ),
        (
            "AI Prompt Configuration",
            {
                "fields": ("system_prompt",),
                "description": "Configure global system prompt for backend tasks.",
            },
        ),
        (
            "LSH Similarity Settings",
            {
                "fields": (
                    "signature_size",
                    "n_grams",
                    "threshold",
                    "lsh_top_n",
                    "edit_distance_threshold",
                    "embedding_similarity_threshold",
                    "max_examples_per_column",
                    "verbose",
                    "use_value_description",
                ),
                "classes": ("collapse",),
                "description": "Configure LSH similarity search parameters and filtering thresholds.",
            },
        ),
        (
            "Schema Linking Settings",
            {
                "fields": (
                    "max_columns_before_schema_linking",
                    "max_context_usage_before_linking",
                ),
                "classes": ("collapse",),
                "description": "Configure schema linking behavior based on database complexity and context window usage.",
            },
        ),
    )

    # No foreign keys remaining that need special handling
