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
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
import json
import ast
from thoth_core.models import ThothLog
from thoth_core.utilities.utils import export_csv
from thoth_core.admin_utils import (
    parse_value,
    render_value,
    render_collapsible,
    render_raw_toggle,
)


class ThothLogAdminForm(forms.ModelForm):
    class Meta:
        model = ThothLog
        fields = "__all__"
        widgets = {
            "question": forms.Textarea(attrs={"rows": 3, "class": "vLargeTextField"}),
            "translated_question": forms.Textarea(attrs={"rows": 3, "cols": 80, "class": "vLargeTextField"}),
            "directives": forms.Textarea(attrs={"rows": 3, "cols": 80, "class": "vLargeTextField"}),
            "keywords_list": forms.Textarea(attrs={"rows": 3, "cols": 80, "class": "vLargeTextField"}),
            "evidences": forms.Textarea(attrs={"rows": 5, "cols": 80, "class": "vLargeTextField"}),
            "similar_questions": forms.Textarea(attrs={"rows": 5, "cols": 80, "class": "vLargeTextField"}),
            "similar_columns": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
            "reduced_schema": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
            "schema_with_examples": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
            "schema_from_vector_db": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
            "used_mschema": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
            "generated_tests": forms.Textarea(attrs={"rows": 5, "cols": 80, "class": "vLargeTextField"}),
            "pool_of_generated_sql": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
            "generated_sql": forms.Textarea(attrs={"rows": 10, "cols": 80, "class": "vLargeTextField"}),
            "sql_generation_failure_message": forms.Textarea(attrs={"rows": 3, "cols": 80, "class": "vLargeTextField"}),
            "sql_explanation": forms.Textarea(attrs={"rows": 5, "cols": 80, "class": "vLargeTextField"}),
            # Nuovi campi aggiunti per la riorganizzazione
            "lsh_similar_columns": forms.Textarea(attrs={"rows": 5, "cols": 80, "class": "vLargeTextField"}),
            "gold_sql_extracted": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
            "reduced_tests": forms.Textarea(attrs={"rows": 5, "cols": 80, "class": "vLargeTextField"}),
            "flags_activated": forms.Textarea(attrs={"rows": 3, "cols": 80, "class": "vLargeTextField"}),
            "evaluation_judgments": forms.Textarea(attrs={"rows": 8, "cols": 80, "class": "vLargeTextField"}),
        }


@admin.register(ThothLog)
class ThothLogAdmin(admin.ModelAdmin):
    form = ThothLogAdminForm
    list_display = (
        "id",
        "evaluation_case_badge",
        "username",
        "workspace",
        "formatted_started_at",
        "formatted_terminated_at",
        "duration",
        "get_question_preview",
    )
    list_display_links = ("id", "username")
    search_fields = ("username", "workspace", "question", "generated_sql")
    list_filter = ("workspace", "db_language", "question_language", "started_at")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    actions = [export_csv]

    class Media:
        css = {
            "all": (
                "thoth_core/admin/thothlog.css",
            )
        }

    # All fields are read-only as requested
    readonly_fields = (
        "test_status_display",
        "username",
        "workspace",
        "formatted_started_at",
        "formatted_terminated_at",
        "duration_display",
        "timing_display",
        "user_workspace_display",
        "languages_display",
        "question",
        "selected_sql_or_error",
        "db_language",
        "question_language",
        "translated_question",
        "directives",
        "formatted_keywords_list",
        "formatted_evidences",
        "formatted_similar_questions",
        "formatted_similar_columns",
        "formatted_schema_with_examples",
        "formatted_schema_from_vector_db",
        "formatted_reduced_schema",
        "formatted_used_mschema",
        "generated_tests_display",
        "generated_tests_count",
        "evaluation_results_display",
        "sql_status_display",
        "evaluation_case_display",
        "evaluation_details_display",
        "pool_of_generated_sql_display",
        "selected_sql",
        "sql_generation_failure_message",
        "sql_explanation",
        "evidence_relevance_summary_display",
        "evidence_relevance_events_display",
        "model_retry_events_display",
        "retry_history_display",
        "formatted_available_context_tokens",
        "formatted_full_schema_tokens_count",
        "formatted_schema_link_strategy",
        "enhanced_evaluation_thinking_display",
        "enhanced_evaluation_selected_sql_display",
        "sql_generation_timing_display",
        "test_generation_timing_display",
        "evaluation_timing_display",
        "sql_selection_timing_display",
        "belt_and_suspenders_start_display",
        "belt_and_suspenders_end_display",
        "belt_and_suspenders_duration_display",
        "escalation_flags_display",
        "formatted_created_at",
        "formatted_updated_at",
        # Inline timing methods
        "validation_timing_inline",
        "keyword_generation_timing_inline",
        "context_retrieval_timing_inline",
        "sql_generation_timing_inline",
        "test_generation_timing_inline", 
        "test_reduction_timing_inline",
        "evaluation_timing_inline",
        "sql_selection_timing_inline",
        "belt_and_suspenders_timing_inline",
        # Language methods
        "question_language_display",
        "db_language_display",
    )

    fieldsets = (
        # SECTION 1: Main Information
        (
            "Main Information",
            {
                "fields": (
                    "question",
                    "generated_sql_textarea",
                    "evaluation_case_display",
                ),
                "description": "Core query and result information",
            },
        ),
        
        # SECTION 2: Time and Language
        (
            "Time and Language",
            {
                "fields": (
                    "timing_display",
                    "user_workspace_display",
                    "languages_display",
                    "directives",
                    "flags_activated_display",
                ),
                "description": "Timing, user context, and language settings",
                "classes": ("collapse",),
            },
        ),
        
        # Phase 1: Validation
        (
            "Phase 1: Question Validation",
            {
                "fields": (
                    "validation_timing_inline",
                ),
                "description": "Question validation phase timing",
                "classes": ("collapse",),
            },
        ),
        
        # Phase 2: Keywords and Schema
        (
            "Phase 2: Keywords Generation & Data Preparation",
            {
                "fields": (
                    "keyword_generation_timing_inline",
                    "formatted_keywords_list",
                    "lsh_similar_columns_display",  # LHS similar columns (collapsible)
                    "formatted_reduced_schema",  # Reduced Schema (collapsible)
                ),
                "description": "Keywords extraction and data preparation",
                "classes": ("collapse",),
            },
        ),
        
        # Phase 3: Context Retrieval
        (
            "Phase 3: Context Helpers Generation",
            {
                "fields": (
                    "context_retrieval_timing_inline",
                    "formatted_evidences",
                    "gold_sql_extracted_display",
                ),
                "description": "Evidence and gold SQL retrieval from vector database",
                "classes": ("collapse",),
            },
        ),
        
        # Phase 4: SQL Generation
        (
            "Phase 4: SQL Generation",
            {
                "fields": (
                    "sql_generation_timing_inline",
                    "pool_of_generated_sql_display",
                    "sql_generation_failure_message",
                    "escalation_flags_display",
                ),
                "description": "SQL candidates generation",
                "classes": ("collapse",),
            },
        ),
        
        # Phase 5: Test Generation
        (
            "Phase 5: Test Generation",
            {
                "fields": (
                    "test_generation_timing_inline",
                    "generated_tests_display",
                    "generated_tests_count",
                ),
                "description": "Test generation for SQL validation",
                "classes": ("collapse",),
            },
        ),

        (
            "Phase 5b: Evidence Relevance Guard",
            {
                "fields": (
                    "evidence_relevance_summary_display",
                    "evidence_relevance_events_display",
                ),
                "description": "Diagnostics from evidence-derived test relevance checks",
                "classes": ("collapse",),
            },
        ),

        (
            "Phase 5c: Model Retry Diagnostics",
            {
                "fields": (
                    "retry_history_display",
                    "model_retry_events_display",
                ),
                "description": "Structured payload returned with ModelRetry responses",
                "classes": ("collapse",),
            },
        ),

        # Phase 6: SQL Evaluation and Winner Selection (renamed from Phase 7)
        (
            "Phase 6: SQL Evaluation and Winner Selection",
            {
                "fields": (
                    ("evaluation_timing_inline",),  # Will show as "Evaluation Timing"
                    ("sql_selection_timing_inline",),  # Will show as "SQL Selection Timing"
                    ("belt_and_suspenders_timing_inline",),  # Will show as "Belt & Suspenders Timing"
                    "evaluation_details_display",
                    "sql_status_display",
                    "selected_sql",
                    "sql_explanation",
                ),
                "description": "SQL candidates evaluation and winner selection",
                "classes": ("collapse",),
            },
        ),
    )

    def pool_of_generated_sql_display(self, obj):
        """Render `pool_of_generated_sql` using shared utilities: lists as bullets; theme-safe."""
        if not obj.pool_of_generated_sql:
            return "-"

        parsed = parse_value(obj.pool_of_generated_sql)
        if isinstance(parsed, list):
            inner = '<div class="readonly" style="max-height: 450px; overflow: auto;">'
            # Truncate long SQL strings within items
            inner += render_value([s if not isinstance(s, str) else (s[:800] + "…" if len(s) > 800 else s) for s in parsed])
            inner += "</div>"
            return mark_safe(render_collapsible("Pool of Generated SQL (click to expand)", inner))

        # Fallback: raw text in collapsible
        inner = format_html(
            '<pre class="readonly thoth-pre" style="max-height: 300px; overflow: auto;">{}</pre>',
            obj.pool_of_generated_sql,
        )
        return mark_safe(render_collapsible("Pool of Generated SQL (click to expand)", inner))

    pool_of_generated_sql_display.short_description = "Pool of Generated SQL"

    def formatted_keywords_list(self, obj):
        """Display keywords_list as bullet points aligned with label"""
        if not obj.keywords_list:
            return "-"

        try:
            # Try to parse as Python list
            keywords = ast.literal_eval(obj.keywords_list)
            if isinstance(keywords, list):
                # Use Django admin styling with CSS variables for theme compatibility
                html_content = '<ul style="margin: 0; padding-left: 20px; list-style-type: disc;">'
                for keyword in keywords:
                    html_content += f'<li style="margin: 2px 0; font-size: 13px; color: var(--body-fg, #333);">{keyword}</li>'
                html_content += '</ul>'
                return mark_safe(html_content)
        except:
            pass

        # Fallback to raw display in non-collapsible container
        html_content = '<div style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 12px; margin: 5px 0; background-color: var(--darkened-bg, #f8f9fa);">'
        html_content += '<h4 style="margin-top: 0; margin-bottom: 10px;">Keywords List</h4>'
        html_content += format_html(
            '<pre class="readonly" style="padding: 8px;">{}</pre>',
            obj.keywords_list,
        )
        html_content += "</div>"
        return mark_safe(html_content)

    formatted_keywords_list.short_description = "Keywords List"

    def formatted_evidences(self, obj):
        """Display evidences as bullets using shared renderer in a collapsible block."""
        if not obj.evidences:
            return "-"

        parsed = parse_value(obj.evidences)
        if isinstance(parsed, list):
            inner = '<div class="readonly" style="max-height: 400px; overflow: auto;">'
            inner += render_value([e if not isinstance(e, str) else (e[:200] + "…" if len(e) > 200 else e) for e in parsed])
            inner += "</div>"
            return mark_safe(render_collapsible("Evidences (click to expand)", inner))

        inner = format_html(
            '<pre class="readonly thoth-pre" style="max-height: 300px; overflow: auto;">{}</pre>',
            obj.evidences,
        )
        return mark_safe(render_collapsible("Evidences (click to expand)", inner))

    formatted_evidences.short_description = "Evidences"

    def formatted_similar_questions(self, obj):
        """Display similar questions as a formatted list in an expandable container"""
        if not obj.similar_questions:
            return "-"

        try:
            # Try to parse as Python list
            questions = ast.literal_eval(obj.similar_questions)
            if isinstance(questions, list):
                html_content = '<details style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 8px; margin: 5px 0;">'
                html_content += '<summary style="cursor: pointer; font-weight: bold; padding: 5px;">Similar Questions (click to expand)</summary>'
                html_content += '<div class="readonly" style="max-height: 400px; overflow-y: auto; font-size: 0.85em; line-height: 1.2; margin-top: 10px; padding: 10px;">'
                html_content += '<ul style="margin: 6px 0 0 18px; list-style: disc;">'
                for item in questions:
                    if isinstance(item, dict):
                        # Extract question and sql from dictionary
                        question_text = item.get("question", "")
                        sql_text = item.get("sql", "")
                        description = item.get("description", "")

                        html_content += '<li style="margin-bottom: 8px;">'
                        html_content += f"<div><strong>Question:</strong> {question_text}</div>"
                        if sql_text:
                            html_content += f'<div style="margin-left: 15px;"><strong>SQL:</strong> {sql_text}</div>'
                        if description:
                            html_content += f'<div style="margin-left: 15px;"><strong>Description:</strong> {description}</div>'
                        html_content += "</li>"
                    else:
                        # Fallback for non-dict items
                        display_question = (
                            str(item)[:200] + "..."
                            if len(str(item)) > 200
                            else str(item)
                        )
                        html_content += f'<li style="margin-bottom: 5px;">{display_question}</li>'
                html_content += "</ul>"
                html_content += "</div>"
                html_content += f'<details style="margin-top: 10px;"><summary style="cursor: pointer;">Show raw data</summary><pre class="readonly" style="margin-top: 5px; max-height: 300px; overflow-y: auto;">{obj.similar_questions}</pre></details>'
                html_content += "</details>"
                return mark_safe(html_content)
        except:
            pass

        # Fallback to raw display in expandable container
        html_content = '<details style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 8px; margin: 5px 0;">'
        html_content += '<summary style="cursor: pointer; font-weight: bold; padding: 5px;">Similar Questions (click to expand)</summary>'
        html_content += format_html(
            '<pre class="readonly" style="max-height: 300px; overflow-y: auto; margin-top: 10px; padding: 10px;">{}</pre>',
            obj.similar_questions,
        )
        html_content += "</details>"
        return mark_safe(html_content)

    formatted_similar_questions.short_description = "Similar Questions"

    def formatted_similar_columns(self, obj):
        """Display similar_columns using shared renderer with bullets and theme-safe styles."""
        if not obj.similar_columns:
            return "-"
        parsed = parse_value(obj.similar_columns)
        if isinstance(parsed, (list, dict)):
            inner = '<div class="readonly" style="max-height: 400px; overflow: auto;">' + render_value(parsed) + "</div>"
            inner += render_raw_toggle(obj.similar_columns, label="Show raw JSON")
            return mark_safe(render_collapsible("Similar Columns (click to expand)", inner))

        inner = format_html(
            '<pre class="readonly thoth-pre" style="max-height: 400px; overflow: auto;">{}</pre>',
            obj.similar_columns,
        )
        return mark_safe(render_collapsible("Similar Columns (click to expand)", inner))

    formatted_similar_columns.short_description = "Similar Columns"

    def formatted_schema_with_examples(self, obj):
        """Display schema_with_examples using shared renderer (bullets/dl) with raw toggle."""
        if not obj.schema_with_examples:
            return "-"
        parsed = parse_value(obj.schema_with_examples)
        if isinstance(parsed, (list, dict)):
            inner = '<div class="readonly" style="max-height: 500px; overflow: auto;">' + render_value(parsed) + "</div>"
            inner += render_raw_toggle(obj.schema_with_examples, label="Show raw JSON")
            return mark_safe(render_collapsible("Schema with Examples (click to expand)", inner))

        inner = format_html(
            '<pre class="readonly thoth-pre" style="max-height: 400px; overflow: auto;">{}</pre>',
            obj.schema_with_examples,
        )
        return mark_safe(render_collapsible("Schema with Examples (click to expand)", inner))

    formatted_schema_with_examples.short_description = "Schema with Examples"

    def formatted_schema_from_vector_db(self, obj):
        """Display schema_from_vector_db using shared renderer with bullets/dl and raw toggle."""
        if not obj.schema_from_vector_db:
            return "-"
        parsed = parse_value(obj.schema_from_vector_db)
        if isinstance(parsed, (list, dict)):
            inner = '<div class="readonly" style="max-height: 500px; overflow: auto;">' + render_value(parsed) + "</div>"
            inner += render_raw_toggle(obj.schema_from_vector_db, label="Show raw JSON")
            return mark_safe(render_collapsible("Schema from Vector DB (click to expand)", inner))

        inner = format_html(
            '<pre class="readonly thoth-pre" style="max-height: 400px; overflow: auto;">{}</pre>',
            obj.schema_from_vector_db,
        )
        return mark_safe(render_collapsible("Schema from Vector DB (click to expand)", inner))

    formatted_schema_from_vector_db.short_description = "Schema from Vector DB"

    def formatted_reduced_schema(self, obj):
        """Display reduced_schema in a collapsible section (theme-safe)."""
        if not obj.reduced_schema:
            return "-"
        inner = format_html(
            '<pre class="readonly thoth-pre" style="max-height: 400px; overflow: auto;">{}</pre>',
            obj.reduced_schema,
        )
        return mark_safe(render_collapsible("Reduced Schema (click to expand)", inner))

    formatted_reduced_schema.short_description = "Reduced Schema"

    def evidence_relevance_summary_display(self, obj):
        summary = obj.evidence_relevance_summary or {}
        if not summary:
            return "-"

        inner = '<div class="readonly" style="max-height: 260px; overflow: auto;">'
        inner += render_value(summary)
        inner += '</div>'
        raw = render_raw_toggle(
            json.dumps(summary, ensure_ascii=False, indent=2),
            label="Show raw summary"
        )
        return mark_safe(render_collapsible("Evidence relevance summary", inner + raw))

    evidence_relevance_summary_display.short_description = "Relevance Summary"

    def evidence_relevance_events_display(self, obj):
        events = obj.evidence_relevance_events or []
        if not events:
            return "-"

        inner = '<div class="readonly" style="max-height: 360px; overflow: auto;">'
        inner += render_value(events)
        inner += '</div>'
        raw = render_raw_toggle(
            json.dumps(events, ensure_ascii=False, indent=2),
            label="Show raw events"
        )
        return mark_safe(render_collapsible("Evidence relevance events", inner + raw))

    evidence_relevance_events_display.short_description = "Relevance Events"

    def model_retry_events_display(self, obj):
        events = obj.model_retry_events or []
        if not events:
            return "-"

        inner = '<div class="readonly" style="max-height: 360px; overflow: auto;">'
        inner += render_value(events)
        inner += '</div>'
        raw = render_raw_toggle(
            json.dumps(events, ensure_ascii=False, indent=2),
            label="Show raw retries"
        )
        return mark_safe(render_collapsible("Model retry events", inner + raw))

    model_retry_events_display.short_description = "Model Retry Events"

    def retry_history_display(self, obj):
        history = obj.retry_history or []
        if not history:
            return "-"

        inner = '<div class="readonly" style="max-height: 220px; overflow: auto;">'
        inner += render_value(history)
        inner += '</div>'
        return mark_safe(render_collapsible("Retry history", inner))

    retry_history_display.short_description = "Retry History"

    def formatted_used_mschema(self, obj):
        """Display used_mschema in an expandable container (theme-safe)."""
        if not obj.used_mschema:
            return "-"
        inner = format_html(
            '<pre class="readonly thoth-pre" style="max-height: 400px; overflow: auto;">{}</pre>',
            obj.used_mschema,
        )
        return mark_safe(render_collapsible("Used Schema (click to expand)", inner))

    formatted_used_mschema.short_description = "Used Schema"

    def generated_tests_display(self, obj):
        """Render generated_tests as either a simple list of strings (new filtered format)
        or as a list of tuples (legacy format). Falls back to JSON and then raw text if needed."""
        if not obj.generated_tests:
            return "-"

        # Wrap everything in an expandable container
        html_wrapper = '<details style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 8px; margin: 5px 0;">'
        html_wrapper += '<summary style="cursor: pointer; font-weight: bold; padding: 5px;">Selected Tests (click to expand)</summary>'
        html_wrapper += '<div style="margin-top: 10px;">'

        # 1) Try Python literal - check for simple list first
        try:
            data = ast.literal_eval(obj.generated_tests)
            
            # Check if it's a simple list of strings (new filtered tests format)
            if isinstance(data, list) and data and all(isinstance(item, str) for item in data):
                # Simple list format (filtered tests)
                html_content = '<div class="readonly" style="max-height: 450px; overflow-y: auto;">'
                html_content += '<h4 style="margin: 10px 0;">Semantically Filtered Tests:</h4>'
                html_content += '<ul style="margin-left: 20px; list-style: disc;">'
                for test in data:
                    html_content += f'<li style="margin: 5px 0;">{test}</li>'
                html_content += '</ul>'
                
                # Show raw data
                html_content += f'<details style="margin-top: 10px;"><summary style="cursor: pointer;">Show raw data</summary><pre class="readonly" style="margin-top: 5px; max-height: 300px; overflow-y: auto;">{obj.generated_tests}</pre></details>'
                html_content += '</div>'
                
                # Close the wrapper
                html_wrapper += html_content
                html_wrapper += '</div>'
                html_wrapper += '</details>'
                return mark_safe(html_wrapper)
                
            # Legacy format: list of tuples (thinking, answers)
            elif isinstance(data, list):
                html_content = '<div class="readonly" style="max-height: 450px; overflow-y: auto; font-size: 0.95em;">'
                for i, item in enumerate(data, 1):
                    thinking = ""
                    answers = []

                    if isinstance(item, (tuple, list)) and len(item) >= 2:
                        thinking = item[0]
                        ans = item[1]
                        if isinstance(ans, (list, tuple)):
                            answers = list(ans)
                        else:
                            answers = [ans] if ans else []
                    else:
                        # Unexpected item shape; show as raw
                        thinking = str(item)
                        answers = []

                    thinking_text = str(thinking)
                    display_thinking = (
                        thinking_text[:800] + "..."
                        if len(thinking_text) > 800
                        else thinking_text
                    )

                    html_content += '<div class="test-item" style="margin-bottom: 14px; padding: 8px; border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 6px;">'
                    html_content += f'<div style="margin-bottom: 6px;"><strong>Test {i}:</strong></div>'

                    # Test Generator Section
                    html_content += '<div class="test-generator-section" style="margin-left: 18px; margin-bottom: 10px; padding: 8px; border-radius: 4px; border: 1px solid var(--hairline-color, #e0e0e0);">'
                    html_content += '<div style="margin-bottom: 6px;"><strong>Test Generator:</strong></div>'
                    html_content += f'<div style="margin-left: 12px; margin-bottom: 6px;"><strong>Thinking:</strong> {display_thinking}</div>'
                    html_content += '<div style="margin-left: 12px;">'
                    html_content += "<strong>Unit Tests:</strong>"
                    if answers:
                        html_content += '<ul style="margin: 6px 0 0 18px;">'
                        for j, ans in enumerate(answers, 1):
                            ans_text = str(ans)
                            display_ans = (
                                ans_text[:600] + "..."
                                if len(ans_text) > 600
                                else ans_text
                            )
                            html_content += f"<li>{display_ans}</li>"
                        html_content += "</ul>"
                    else:
                        html_content += "<div>-</div>"
                    html_content += "</div>"
                    html_content += "</div>"

                    # Per-item raw view
                    raw_item = str(item)
                    html_content += f'<details style="margin-top: 6px;"><summary style="cursor: pointer;">Show raw tuple</summary><pre class="readonly" style="margin-top: 5px; max-height: 220px; overflow-y: auto;">{raw_item}</pre></details>'
                    html_content += "</div>"

                # Full raw data
                html_content += f'<details style="margin-top: 10px;"><summary style="cursor: pointer;">Show full raw data</summary><pre class="readonly" style="margin-top: 5px; max-height: 300px; overflow-y: auto;">{obj.generated_tests}</pre></details>'
                html_content += "</div>"
                # Close the wrapper
                html_wrapper += html_content
                html_wrapper += "</div>"
                html_wrapper += "</details>"
                return mark_safe(html_wrapper)
        except Exception:
            pass

        # 2) Fallback: try JSON
        try:
            data = json.loads(obj.generated_tests)
            # If it's a list of pairs (thinking, answers)
            if isinstance(data, list):
                html_content = '<div class="readonly" style="max-height: 450px; overflow-y: auto;">'
                for i, item in enumerate(data, 1):
                    thinking = ""
                    answers = []

                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        thinking = item[0]
                        ans = item[1]
                        answers = (
                            list(ans)
                            if isinstance(ans, (list, tuple))
                            else [ans]
                            if ans
                            else []
                        )
                    else:
                        thinking = str(item)
                        answers = []

                    thinking_text = str(thinking)
                    display_thinking = (
                        thinking_text[:800] + "..."
                        if len(thinking_text) > 800
                        else thinking_text
                    )

                    html_content += '<div style="margin-bottom: 12px; padding: 8px; border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 6px;">'
                    html_content += f"<div><strong>Test {i}:</strong></div>"

                    # Test Generator Section
                    html_content += (
                        '<div style="margin-left: 18px; margin-bottom: 8px;">'
                    )
                    html_content += "<strong>Test Generator:</strong>"
                    html_content += f'<div style="margin-left: 12px;"><strong>Thinking:</strong> {display_thinking}</div>'
                    html_content += (
                        '<div style="margin-left: 12px;"><strong>Unit Tests:</strong>'
                    )
                    if answers:
                        html_content += '<ul style="margin: 6px 0 0 18px;">'
                        for ans in answers:
                            ans_text = str(ans)
                            display_ans = (
                                ans_text[:600] + "..."
                                if len(ans_text) > 600
                                else ans_text
                            )
                            html_content += f"<li>{display_ans}</li>"
                        html_content += "</ul>"
                    else:
                        html_content += "<div>-</div>"
                    html_content += "</div>"
                    html_content += "</div>"

                    html_content += "</div>"
                html_content += f'<details style="margin-top: 10px;"><summary style="cursor: pointer;">Show raw data</summary><pre class="readonly" style="margin-top: 5px; max-height: 300px; overflow-y: auto;">{json.dumps(data, indent=2, ensure_ascii=False)}</pre></details>'
                html_content += "</div>"
                # Close the wrapper
                html_wrapper += html_content
                html_wrapper += "</div>"
                html_wrapper += "</details>"
                return mark_safe(html_wrapper)
        except Exception:
            pass

        # 3) Final fallback: raw text wrapped in expandable container
        html_wrapper += format_html(
            '<pre class="readonly" style="max-height: 300px; overflow-y: auto;">{}</pre>',
            obj.generated_tests,
        )
        html_wrapper += "</div>"
        html_wrapper += "</details>"
        return mark_safe(html_wrapper)

    generated_tests_display.short_description = "Selected Tests"

    def evaluation_results_display(self, obj):
        """Render evaluation_results as either a single tuple (thinking: str, verdicts: list[str])
        or a list of tuples for backwards compatibility.
        Each verdict is either 'Passed' or 'Failed - <reason>'."""
        if not obj.evaluation_results:
            return "-"

        # Wrap everything in an expandable container
        html_wrapper = '<details style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 8px; margin: 5px 0;">'
        html_wrapper += '<summary style="cursor: pointer; font-weight: bold; padding: 5px;">Evaluation Results (click to expand)</summary>'
        html_wrapper += '<div style="margin-top: 10px;">'

        # Try to parse as JSON first
        try:
            data = json.loads(obj.evaluation_results)

            # Check if it's the enhanced evaluation format (list of dicts with evaluation_type)
            if isinstance(data, list) and len(data) > 0:
                # Check if this is the enhanced evaluation format
                has_enhanced_metadata = any(
                    isinstance(item, dict) and item.get("evaluation_type") == "enhanced"
                    for item in data
                )

                if has_enhanced_metadata:
                    # Handle enhanced evaluation results
                    return self._render_enhanced_evaluation_results(data, html_wrapper)

            # Check if it's the old single tuple format [thinking, [verdicts]] or [thinking, [verdicts], [test_units]]
            if (
                isinstance(data, list)
                and len(data) >= 2
                and isinstance(data[0], str)
                and isinstance(data[1], list)
            ):
                # New format: single tuple [thinking, [verdicts]] or [thinking, [verdicts], [test_units]]
                thinking = data[0]
                verdicts = data[1]
                test_units = (
                    data[2] if len(data) > 2 and isinstance(data[2], list) else []
                )

                html_content = '<div class="readonly" style="padding: 10px; max-height: 450px; overflow-y: auto; font-size: 0.95em;">'
                html_content += '<div style="margin-bottom: 15px; border-left: 3px solid var(--primary, #4a90e2); padding-left: 10px;">'
                html_content += '<h4 style="margin: 5px 0;">Evaluation Results (Single Evaluator)</h4>'

                # Show verdicts with color coding FIRST
                if verdicts:
                    html_content += '<p style="margin: 10px 0 5px 0;"><b>SQL Candidate Verdicts:</b></p>'
                    html_content += (
                        '<ul style="margin: 5px 0 0 20px; list-style: disc;">'
                    )
                    for j, verdict in enumerate(verdicts, 1):
                        verdict_str = str(verdict).strip()

                        # Parse the verdict string to extract individual test results
                        # Expected format: "SQL #n: OK, OK, KO - reason, OK, ..."
                        if verdict_str.startswith(f"SQL #{j}:"):
                            # Extract just the test results part
                            test_results_str = verdict_str[len(f"SQL #{j}:") :].strip()
                        else:
                            test_results_str = verdict_str

                        # Split by comma but preserve the KO reasons
                        test_results = []
                        current_result = ""
                        for part in test_results_str.split(","):
                            part = part.strip()
                            if part.startswith("OK") or (
                                current_result and not current_result.startswith("KO")
                            ):
                                if current_result:
                                    test_results.append(current_result)
                                current_result = part
                            elif part.startswith("KO"):
                                if current_result:
                                    test_results.append(current_result)
                                current_result = part
                            else:
                                # This is likely part of a KO reason
                                if current_result:
                                    current_result += ", " + part
                        if current_result:
                            test_results.append(current_result)

                        # Count failures
                        failure_count = sum(
                            1 for r in test_results if r.startswith("KO")
                        )
                        total_tests = len(test_results)
                        failure_rate = (
                            (failure_count / total_tests * 100)
                            if total_tests > 0
                            else 0
                        )

                        # Determine icon based on failure rate
                        if failure_rate > 10:
                            icon = "[FAIL]"
                        else:
                            icon = "[PASS]"

                        # Build the verdict display
                        html_content += '<li style="margin: 8px 0;">'
                        html_content += f'<span style="font-weight: normal;">SQL #{j}:</span> {icon} '

                        # Display individual test results
                        for i, result in enumerate(test_results):
                            if i > 0:
                                html_content += ", "

                            if result.startswith("OK"):
                                # OK results in normal color
                                html_content += f"<span>{result}</span>"
                            elif result.startswith("KO"):
                                # KO results in red - using Django's error color
                                html_content += f'<span style="color: var(--error-fg, #ba2121); font-weight: bold;">{result}</span>'
                            else:
                                # Unknown format, display as-is
                                html_content += f"<span>{result}</span>"

                        html_content += "</li>"
                    html_content += "</ul>"

                # Show the test units that were evaluated SECOND
                if test_units:
                    html_content += '<p style="margin: 10px 0 5px 0;"><b>Test Units Applied:</b></p>'
                    html_content += '<ul style="margin: 5px 0 15px 20px; padding: 10px; border-radius: 5px; border: 1px solid var(--hairline-color, #e0e0e0); list-style: disc;">'
                    for test in test_units:
                        html_content += (
                            f'<li style="margin: 3px 0; font-size: 0.9em;">{test}</li>'
                        )
                    html_content += "</ul>"

                # Show analysis (first 300 chars)
                if thinking:
                    preview = (
                        thinking[:300] + "..." if len(thinking) > 300 else thinking
                    )
                    html_content += f'<p style="margin: 5px 0;"><b>Evaluation Thinking:</b> <span style="font-style: italic;">{preview}</span></p>'

                html_content += "</div>"
                html_content += "</div>"
                # Close the wrapper
                html_wrapper += html_content
                html_wrapper += "</div>"
                html_wrapper += "</details>"
                return mark_safe(html_wrapper)
        except json.JSONDecodeError:
            pass

        # Try Python literal evaluation as fallback
        try:
            data = ast.literal_eval(obj.evaluation_results)

            # Check if it's a tuple or list format with [thinking, [verdicts], [test_units]]
            if (
                isinstance(data, (tuple, list))
                and len(data) >= 2
                and isinstance(data[0], str)
                and isinstance(data[1], list)
            ):
                # Current format: (thinking, [verdicts]) or (thinking, [verdicts], [test_units])
                thinking = data[0]
                verdicts = data[1]
                test_units = (
                    data[2] if len(data) > 2 and isinstance(data[2], list) else []
                )

                html_content = '<div class="readonly" style="padding: 10px; max-height: 450px; overflow-y: auto; font-size: 0.95em;">'
                html_content += '<div style="margin-bottom: 15px; border-left: 3px solid var(--primary, #4a90e2); padding-left: 10px;">'
                html_content += '<h4 style="margin: 5px 0;">Evaluation Results (Single Evaluator)</h4>'

                # Show verdicts with color coding FIRST
                if verdicts:
                    html_content += '<p style="margin: 5px 0;"><b>Verdicts:</b></p>'
                    html_content += (
                        '<ul style="margin: 5px 0 0 20px; list-style: disc;">'
                    )
                    for j, verdict in enumerate(verdicts, 1):
                        verdict_str = str(verdict).strip()

                        # Parse the verdict string to extract individual test results
                        # Expected format: "SQL #n: OK, OK, KO - reason, OK, ..."
                        if verdict_str.startswith(f"SQL #{j}:"):
                            # Extract just the test results part
                            test_results_str = verdict_str[len(f"SQL #{j}:") :].strip()
                        else:
                            test_results_str = verdict_str

                        # Split by comma but preserve the KO reasons
                        test_results = []
                        current_result = ""
                        for part in test_results_str.split(","):
                            part = part.strip()
                            if part.startswith("OK") or (
                                current_result and not current_result.startswith("KO")
                            ):
                                if current_result:
                                    test_results.append(current_result)
                                current_result = part
                            elif part.startswith("KO"):
                                if current_result:
                                    test_results.append(current_result)
                                current_result = part
                            else:
                                # This is likely part of a KO reason
                                if current_result:
                                    current_result += ", " + part
                        if current_result:
                            test_results.append(current_result)

                        # Count failures
                        failure_count = sum(
                            1 for r in test_results if r.startswith("KO")
                        )
                        total_tests = len(test_results)
                        failure_rate = (
                            (failure_count / total_tests * 100)
                            if total_tests > 0
                            else 0
                        )

                        # Determine icon based on failure rate
                        if failure_rate > 10:
                            icon = "[FAIL]"
                        else:
                            icon = "[PASS]"

                        # Build the verdict display
                        html_content += '<li style="margin: 8px 0;">'
                        html_content += f'<span style="font-weight: normal;">SQL #{j}:</span> {icon} '

                        # Display individual test results
                        for i, result in enumerate(test_results):
                            if i > 0:
                                html_content += ", "

                            if result.startswith("OK"):
                                # OK results in normal color
                                html_content += f"<span>{result}</span>"
                            elif result.startswith("KO"):
                                # KO results in red - using Django's error color
                                html_content += f'<span style="color: var(--error-fg, #ba2121); font-weight: bold;">{result}</span>'
                            else:
                                # Unknown format, display as-is
                                html_content += f"<span>{result}</span>"

                        html_content += "</li>"
                    html_content += "</ul>"

                # Show the test units that were evaluated SECOND
                if test_units:
                    html_content += '<p style="margin: 10px 0 5px 0;"><b>Test Units Applied:</b></p>'
                    html_content += '<ul style="margin: 5px 0 15px 20px; padding: 10px; border-radius: 5px; border: 1px solid var(--hairline-color, #e0e0e0); list-style: disc;">'
                    for test in test_units:
                        html_content += (
                            f'<li style="margin: 3px 0; font-size: 0.9em;">{test}</li>'
                        )
                    html_content += "</ul>"

                # Show analysis (first 300 chars)
                if thinking:
                    preview = (
                        thinking[:300] + "..." if len(thinking) > 300 else thinking
                    )
                    html_content += f'<p style="margin: 5px 0;"><b>Evaluation Thinking:</b> <span style="font-style: italic;">{preview}</span></p>'

                html_content += "</div>"
                html_content += "</div>"
                # Close the wrapper
                html_wrapper += html_content
                html_wrapper += "</div>"
                html_wrapper += "</details>"
                return mark_safe(html_wrapper)
        except (ValueError, SyntaxError):
            pass

        # Fallback to formatted display wrapped in expandable container
        html_content = '<div class="readonly" style="padding: 10px; max-height: 450px; overflow-y: auto; font-size: 0.95em;">'
        
        # Try to format as best as possible
        try:
            # If it's a string that looks like a list or dict, try to parse and format it
            raw_data = obj.evaluation_results.strip()
            if raw_data.startswith('[') or raw_data.startswith('{'):
                # Try to parse as JSON for pretty printing
                try:
                    parsed = json.loads(raw_data)
                    formatted_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                    html_content += '<div style="padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px;">'
                    html_content += '<p style="margin: 0 0 10px 0; font-weight: bold; color: var(--body-quiet-color, #666);">Raw Evaluation Data:</p>'
                    html_content += f'<pre class="readonly" style="margin: 0; padding: 10px; background: var(--darkened-bg, #f0f0f0); color: var(--body-fg, #333); border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; overflow-x: auto;">{formatted_json}</pre>'
                    html_content += '</div>'
                except:
                    # If JSON parsing fails, try Python literal eval
                    try:
                        parsed = ast.literal_eval(raw_data)
                        formatted_str = self._format_python_object(parsed)
                        html_content += '<div style="padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px;">'
                        html_content += '<p style="margin: 0 0 10px 0; font-weight: bold; color: var(--body-quiet-color, #666);">Evaluation Data:</p>'
                        html_content += f'<pre class="readonly" style="margin: 0; padding: 10px; background: var(--darkened-bg, #f0f0f0); color: var(--body-fg, #333); border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; overflow-x: auto;">{formatted_str}</pre>'
                        html_content += '</div>'
                    except:
                        # Last resort: show as is but nicely formatted
                        html_content += '<div style="padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px;">'
                        html_content += '<p style="margin: 0 0 10px 0; font-weight: bold; color: var(--body-quiet-color, #666);">Raw Evaluation Data:</p>'
                        html_content += f'<pre class="readonly" style="margin: 0; padding: 10px; background: var(--darkened-bg, #f0f0f0); color: var(--body-fg, #333); border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; overflow-x: auto;">{obj.evaluation_results}</pre>'
                        html_content += '</div>'
            else:
                # Plain text format
                html_content += '<div style="padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px;">'
                html_content += '<p style="margin: 0 0 10px 0; font-weight: bold; color: var(--body-quiet-color, #666);">Evaluation Notes:</p>'
                html_content += f'<div style="padding: 10px; background: var(--darkened-bg, #f0f0f0); color: var(--body-fg, #333); border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px;">{obj.evaluation_results}</div>'
                html_content += '</div>'
        except Exception as e:
            # Ultimate fallback
            html_content += '<div style="padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px;">'
            html_content += f'<pre class="readonly" style="margin: 0; padding: 10px; background: var(--darkened-bg, #f0f0f0); color: var(--body-fg, #333); border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px;">{obj.evaluation_results}</pre>'
            html_content += '</div>'
        
        html_content += '</div>'
        html_wrapper += html_content
        html_wrapper += "</div>"
        html_wrapper += "</details>"
        return mark_safe(html_wrapper)

    evaluation_results_display.short_description = "Evaluation Results"
    
    def _format_python_object(self, obj, indent=0):
        """Helper method to format Python objects nicely"""
        indent_str = "  " * indent
        if isinstance(obj, dict):
            if not obj:
                return "{}"
            lines = ["{"]
            for i, (key, value) in enumerate(obj.items()):
                comma = "," if i < len(obj) - 1 else ""
                if isinstance(value, (dict, list)):
                    lines.append(f'{indent_str}  "{key}": {self._format_python_object(value, indent + 1)}{comma}')
                else:
                    if isinstance(value, str):
                        lines.append(f'{indent_str}  "{key}": "{value}"{comma}')
                    else:
                        lines.append(f'{indent_str}  "{key}": {value}{comma}')
            lines.append(f"{indent_str}}}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            if not obj:
                return "[]"
            if all(isinstance(item, (str, int, float, bool, type(None))) for item in obj):
                # Simple list - format inline if short
                formatted = str(obj)
                if len(formatted) < 80:
                    return formatted
            # Complex list - format with line breaks
            lines = ["["]
            for i, item in enumerate(obj):
                comma = "," if i < len(obj) - 1 else ""
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent_str}  {self._format_python_object(item, indent + 1)}{comma}")
                else:
                    if isinstance(item, str):
                        # Truncate very long strings
                        display_item = item if len(item) <= 200 else item[:200] + "..."
                        lines.append(f'{indent_str}  "{display_item}"{comma}')
                    else:
                        lines.append(f"{indent_str}  {item}{comma}")
            lines.append(f"{indent_str}]")
            return "\n".join(lines)
        elif isinstance(obj, str):
            # Truncate very long strings
            return f'"{obj}"' if len(obj) <= 200 else f'"{obj[:200]}..."'
        else:
            return str(obj)

    def _render_enhanced_evaluation_results(self, data, html_wrapper):
        """Render enhanced evaluation results with GOLD/FAILED status and case information."""
        from django.utils.safestring import mark_safe

        # Find the metadata entry
        metadata = next(
            (
                item
                for item in data
                if isinstance(item, dict) and item.get("evaluation_type") == "enhanced"
            ),
            None,
        )

        html_content = '<div class="readonly" style="padding: 10px; max-height: 450px; overflow-y: auto; font-size: 0.95em;">'
        html_content += '<div style="margin-bottom: 15px; border-left: 3px solid var(--success, #28a745); padding-left: 10px;">'
        html_content += '<h4 style="margin: 5px 0;">Enhanced Evaluation Results</h4>'

        if metadata:
            # Show evaluation status with appropriate colors
            status = metadata.get("status", "UNKNOWN")
            case = metadata.get("case", "Unknown")

            if status == "GOLD":
                status_color = "#28a745"  # Green
                status_icon = "✅"
            elif status == "FAILED":
                status_color = "#dc3545"  # Red
                status_icon = "❌"
            else:
                status_color = "#ffc107"  # Yellow
                status_icon = "⚠️"

            html_content += f'<div style="background: {status_color}15; border: 1px solid {status_color}; border-radius: 4px; padding: 10px; margin: 10px 0;">'
            html_content += f'<p><b>{status_icon} Final Status:</b> <span style="color: {status_color}; font-weight: bold;">{status}</span></p>'
            html_content += f"<p><b>🎯 Evaluation Case:</b> {case}</p>"

            # Show processing time if available
            processing_time = metadata.get("processing_time_ms", 0)
            if processing_time:
                html_content += (
                    f"<p><b>⏱️ Processing Time:</b> {processing_time:.1f}ms</p>"
                )

            # Show escalation info if applicable
            requires_escalation = metadata.get("requires_escalation", False)
            if requires_escalation:
                html_content += "<p><b>🚨 Requires Escalation:</b> Yes</p>"

            # Show auxiliary agents used
            aux_agents = metadata.get("auxiliary_agents_used", [])
            if aux_agents:
                html_content += (
                    f"<p><b>🤖 Auxiliary Agents Used:</b> {', '.join(aux_agents)}</p>"
                )

            # Show best pass rate
            best_pass_rate = metadata.get("best_pass_rate", 0)
            if best_pass_rate > 0:
                html_content += (
                    f"<p><b>📊 Best Pass Rate:</b> {best_pass_rate:.1f}%</p>"
                )

            html_content += "</div>"

        # Show individual SQL evaluation results
        sql_results = [
            item for item in data if isinstance(item, dict) and "sql_index" in item
        ]
        if sql_results:
            html_content += (
                '<h5 style="margin: 15px 0 10px 0;">SQL Candidate Results:</h5>'
            )
            html_content += '<div style="max-height: 200px; overflow-y: auto;">'

            for sql_result in sql_results:
                sql_index = sql_result.get("sql_index", "Unknown")
                answer = sql_result.get("answer", "No answer")
                status = sql_result.get("status", "UNKNOWN")
                pass_rate = sql_result.get("pass_rate", 0)
                selected = sql_result.get("selected", False)

                border_color = "#28a745" if selected else "#e0e0e0"
                background = "#f8f9fa" if selected else "transparent"

                html_content += f'<div style="border: 1px solid {border_color}; border-radius: 4px; padding: 8px; margin: 5px 0; background: {background};">'
                html_content += f"<p><b>SQL #{sql_index + 1}</b> {'👑 (Selected)' if selected else ''}</p>"
                html_content += f"<p><b>Status:</b> {status} | <b>Pass Rate:</b> {pass_rate:.1f}%</p>"
                html_content += f"<p><b>Answer:</b> {answer[:100]}{'...' if len(answer) > 100 else ''}</p>"
                html_content += "</div>"

            html_content += "</div>"

        html_content += "</div></div>"
        html_wrapper += html_content
        html_wrapper += "</div>"
        html_wrapper += "</details>"

        return mark_safe(html_wrapper)

    def selection_metrics_display(self, obj):
        """Render selection_metrics field with detailed test results and selection reason"""
        if not obj.selection_metrics:
            return "-"

        # Wrap everything in an expandable container
        html_wrapper = '<details style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 8px; margin: 5px 0;">'
        html_wrapper += '<summary style="cursor: pointer; font-weight: bold; padding: 5px;">Selection Metrics (click to expand)</summary>'
        html_wrapper += '<div style="margin-top: 10px;">'

        try:
            # Try to parse as JSON
            data = json.loads(obj.selection_metrics)

            # Check if this is enhanced evaluation format
            if data.get("evaluation_type") == "enhanced":
                return self._render_enhanced_selection_metrics(data, html_wrapper)

            html_content = '<div class="readonly" style="padding: 10px; max-height: 600px; overflow-y: auto; font-size: 0.95em;">'
            html_content += '<div style="margin-bottom: 15px; border-left: 3px solid var(--primary, #4a90e2); padding-left: 10px;">'
            html_content += '<h4 style="margin: 5px 0;">Selection Metrics</h4>'

            # Summary Information
            html_content += '<div style="margin: 10px 0; padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px;">'
            html_content += f'<p style="margin: 5px 0;"><b>Total SQL Candidates:</b> {data.get("total_sqls", 0)}</p>'
            html_content += f'<p style="margin: 5px 0;"><b>Evaluation Threshold:</b> {data.get("evaluation_threshold", 0)}%</p>'

            # Finalists
            finalists = data.get("finalists", [])
            if finalists:
                # Handle both dict and int format for finalists
                if isinstance(finalists[0], dict):
                    sql_index = finalists[0].get("sql_index", 0)
                else:
                    sql_index = finalists[0]
                html_content += f'<p style="margin: 5px 0;"><b>Selected SQL:</b> SQL #{sql_index + 1} [SELECTED]</p>'

            # Selection Reason
            selection_reason = data.get("selection_reason", "")
            if selection_reason:
                if "No SQL met" in selection_reason:
                    html_content += f'<p style="margin: 5px 0; color: var(--error-fg, #ba2121);"><b>Selection Result:</b> {selection_reason}</p>'
                else:
                    html_content += f'<p style="margin: 5px 0; color: var(--body-success-fg, #28a745);"><b>Selection Result:</b> {selection_reason}</p>'
            html_content += "</div>"

            # SQL Scores Details
            sql_scores = data.get("sql_scores", [])
            if sql_scores:
                html_content += (
                    '<h5 style="margin: 15px 0 10px 0;">SQL Candidate Scores:</h5>'
                )

                for score in sql_scores:
                    sql_index = score.get("sql_index", 0)
                    passed_count = score.get("passed_count", 0)
                    total_tests = score.get("total_tests", 0)
                    pass_rate = score.get("pass_rate", 0)
                    pass_percentage = pass_rate * 100

                    # Determine color and icon based on pass rate vs threshold
                    threshold = data.get("evaluation_threshold", 90)
                    if pass_percentage >= threshold:
                        color = "var(--body-success-fg, #28a745)"
                        icon = "[PASS]"
                    elif pass_percentage >= 70:
                        color = "var(--body-warning-fg, #ffc107)"
                        icon = "[WARN]"
                    else:
                        color = "var(--error-fg, #ba2121)"
                        icon = "[FAIL]"

                    html_content += '<div style="margin: 10px 0; padding: 10px; border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 5px;">'
                    html_content += f'<p style="margin: 5px 0; font-weight: bold;">SQL #{sql_index + 1} {icon}</p>'
                    html_content += f'<p style="margin: 5px 0 5px 15px;">Tests Passed: <span style="color: {color}; font-weight: bold;">{passed_count}/{total_tests} ({pass_percentage:.1f}%)</span></p>'

                    # Show test details if available - only show failed tests
                    test_details = score.get("test_details", [])
                    if test_details:
                        # Filter for failed tests only
                        failed_tests = []
                        for i, detail in enumerate(test_details, 1):
                            # Handle new format: [description, result] instead of dict
                            if isinstance(detail, list) and len(detail) >= 2:
                                test_desc = detail[0]
                                result = detail[1]
                                # Check if test failed based on result
                                passed = result.strip().upper() == "OK"
                                if not passed:
                                    # Extract reason from result if available
                                    if " - " in result:
                                        _, reason = result.split(" - ", 1)
                                        failed_tests.append((i, f"FAILED - {reason}"))
                                    else:
                                        failed_tests.append((i, "FAILED - " + result))
                            elif isinstance(detail, dict):
                                # Keep backward compatibility with dict format
                                test_desc = detail.get("test_desc", f"Test {i}")
                                passed = detail.get("passed", False)
                                if not passed:
                                    failed_tests.append((i, "FAILED"))
                        
                        # Only show Test Details section if there are failed tests
                        if failed_tests:
                            html_content += '<details style="margin: 5px 0 5px 15px;">'
                            html_content += (
                                '<summary style="cursor: pointer;">Test Details</summary>'
                            )
                            html_content += (
                                '<ul style="margin: 5px 0 0 20px; font-size: 0.9em;">'
                            )
                            for test_num, failure_desc in failed_tests:
                                html_content += f'<li style="margin: 3px 0;"><span style="color: var(--error-fg, #ba2121);">✗</span> Test {test_num}: <span style="color: var(--error-fg, #ba2121);">{failure_desc}</span></li>'
                            html_content += "</ul>"
                            html_content += "</details>"

                    # Show failure reasons if any
                    failure_reasons = score.get("failure_reasons", [])
                    if failure_reasons:
                        html_content += '<p style="margin: 10px 0 5px 15px; font-weight: bold; color: var(--error-fg, #ba2121);">Failure Reasons:</p>'
                        html_content += (
                            '<ul style="margin: 5px 0 0 30px; font-size: 0.9em;">'
                        )
                        for failure in failure_reasons:
                            # Handle new format: failure reasons are now strings
                            if isinstance(failure, str):
                                html_content += '<li style="margin: 5px 0;">'
                                html_content += f'<span style="color: var(--error-fg, #ba2121);">→ {failure}</span>'
                                html_content += "</li>"
                            elif isinstance(failure, dict):
                                # Keep backward compatibility with dict format
                                test_num = failure.get("test_num", "?")
                                test_desc = failure.get("test_desc", "")
                                reason = failure.get("reason", "Unknown")
                                html_content += '<li style="margin: 5px 0;">'
                                html_content += (
                                    f"<b>Test {test_num}:</b> {test_desc}<br>"
                                )
                                html_content += f'<span style="color: var(--error-fg, #ba2121); margin-left: 10px;">→ {reason}</span>'
                                html_content += "</li>"
                        html_content += "</ul>"

                    html_content += "</div>"

            # Test Units
            test_units = data.get("test_units", [])
            if test_units:
                html_content += (
                    '<h5 style="margin: 15px 0 10px 0;">Test Units Applied:</h5>'
                )
                html_content += '<ul style="margin: 5px 0 0 20px; padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px; font-size: 0.9em; list-style: disc;">'
                for test in test_units:
                    html_content += f'<li style="margin: 3px 0;">{test}</li>'
                html_content += "</ul>"

            html_content += "</div>"

            # Raw data toggle
            html_content += '<details style="margin-top: 15px;"><summary style="cursor: pointer;">Show raw JSON</summary>'
            html_content += f'<pre class="readonly" style="margin-top: 5px; max-height: 300px; overflow-y: auto;">{json.dumps(data, indent=2, ensure_ascii=False)}</pre>'
            html_content += "</details>"

            html_content += "</div>"
            # Close the wrapper
            html_wrapper += html_content
            html_wrapper += "</div>"
            html_wrapper += "</details>"
            return mark_safe(html_wrapper)

        except json.JSONDecodeError:
            pass

        # Fallback to raw display if not valid JSON, wrapped in expandable container
        html_wrapper += format_html(
            '<pre class="readonly" style="max-height: 300px; overflow-y: auto;">{}</pre>',
            obj.selection_metrics,
        )
        html_wrapper += "</div>"
        html_wrapper += "</details>"
        return mark_safe(html_wrapper)

    selection_metrics_display.short_description = "Selection Metrics"

    def _render_enhanced_selection_metrics(self, data, html_wrapper):
        """Render enhanced selection metrics with case information and auxiliary agent details."""
        from django.utils.safestring import mark_safe

        html_content = '<div class="readonly" style="padding: 10px; max-height: 600px; overflow-y: auto; font-size: 0.95em;">'
        html_content += '<div style="margin-bottom: 15px; border-left: 3px solid var(--primary, #4a90e2); padding-left: 10px;">'
        html_content += '<h4 style="margin: 5px 0;">Enhanced Selection Metrics</h4>'

        # Overall evaluation summary
        html_content += '<div style="margin: 10px 0; padding: 10px; background: var(--body-bg, #f8f9fa); border-radius: 5px;">'

        # Case classification and final status
        case = data.get("case_classification", "Unknown")
        final_status = data.get("final_status", "Unknown")

        if final_status == "GOLD":
            status_color = "#28a745"
            status_icon = "✅"
        elif final_status == "FAILED":
            status_color = "#dc3545"
            status_icon = "❌"
        else:
            status_color = "#ffc107"
            status_icon = "⚠️"

        html_content += f'<p style="margin: 5px 0;"><b>{status_icon} Final Status:</b> <span style="color: {status_color}; font-weight: bold;">{final_status}</span></p>'
        html_content += (
            f'<p style="margin: 5px 0;"><b>🎯 Evaluation Case:</b> {case}</p>'
        )

        # Selected SQL index
        selected_index = data.get("selected_sql_index")
        if selected_index is not None:
            html_content += f'<p style="margin: 5px 0;"><b>🎉 Selected SQL:</b> SQL #{selected_index + 1}</p>'

        # Processing time
        processing_time = data.get("processing_time_ms", 0)
        if processing_time:
            html_content += f'<p style="margin: 5px 0;"><b>⏱️ Processing Time:</b> {processing_time:.1f}ms</p>'

        html_content += "</div>"

        # Pass rates section
        pass_rates = data.get("pass_rates", {})
        if pass_rates:
            html_content += '<h5 style="margin: 15px 0 10px 0;">Pass Rates by SQL:</h5>'
            html_content += '<div style="max-height: 200px; overflow-y: auto;">'

            for sql_key, rate in pass_rates.items():
                border_color = (
                    "#28a745" if rate >= 100 else "#ffc107" if rate >= 90 else "#dc3545"
                )

                html_content += f'<div style="border: 1px solid {border_color}; border-radius: 4px; padding: 5px; margin: 3px 0; display: inline-block; min-width: 100px;">'
                html_content += f'<span style="font-weight: bold;">{sql_key}:</span> <span style="color: {border_color};">{rate:.1f}%</span>'
                html_content += "</div>"

            html_content += "</div>"

        # Auxiliary agents section
        aux_agents = data.get("auxiliary_agents", {})
        if aux_agents:
            html_content += (
                '<h5 style="margin: 15px 0 10px 0;">Auxiliary Agents Used:</h5>'
            )
            html_content += '<div style="margin: 5px 0;">'

            for agent_type, used in aux_agents.items():
                icon = "✅" if used else "❌"
                color = "#28a745" if used else "#6c757d"
                html_content += f'<span style="color: {color}; margin-right: 15px;">{icon} <b>{agent_type.replace("_", " ").title()}:</b> {"Used" if used else "Not Used"}</span><br>'

            html_content += "</div>"

        # Case-specific details
        if case == "B" and "sql_selection" in data:
            sql_selection = data["sql_selection"]
            html_content += '<h5 style="margin: 15px 0 10px 0;">SQL Selection Details (Case B):</h5>'
            html_content += '<div style="background: #e7f3ff; border: 1px solid #b3d9ff; border-radius: 4px; padding: 10px; margin: 5px 0;">'
            html_content += f"<p><b>Quality Criteria Applied:</b> {sql_selection.get('quality_criteria_applied', False)}</p>"
            reasoning = sql_selection.get("reasoning", "No reasoning provided")
            html_content += f"<p><b>Selection Reasoning:</b> {reasoning[:200]}{'...' if len(reasoning) > 200 else ''}</p>"
            html_content += "</div>"

        elif case == "C" and "deep_evaluation" in data:
            deep_eval = data["deep_evaluation"]
            html_content += '<h5 style="margin: 15px 0 10px 0;">Deep Evaluation Details (Case C):</h5>'
            html_content += '<div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; margin: 5px 0;">'
            html_content += f"<p><b>Extended Thinking Used:</b> {deep_eval.get('extended_thinking_used', False)}</p>"
            html_content += f"<p><b>Temperature Lowered:</b> {deep_eval.get('temperature_lowered', False)}</p>"
            assessment = deep_eval.get(
                "supervisor_assessment", "No assessment provided"
            )
            html_content += f"<p><b>Supervisor Assessment:</b> {assessment[:200]}{'...' if len(assessment) > 200 else ''}</p>"
            html_content += "</div>"

        # Escalation information
        escalation_info = data.get("escalation_info", {})
        if escalation_info.get("requires_escalation", False):
            html_content += (
                '<h5 style="margin: 15px 0 10px 0;">Escalation Information:</h5>'
            )
            html_content += '<div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 10px; margin: 5px 0;">'
            html_content += "<p><b>🚨 Requires Escalation:</b> Yes</p>"
            context = escalation_info.get("escalation_context", "No context provided")
            html_content += f"<p><b>Context:</b> {context}</p>"
            reason = escalation_info.get("escalation_reason")
            if reason:
                html_content += f"<p><b>Reason:</b> {reason}</p>"
            html_content += "</div>"

        # Session logs summary if available
        session_logs = data.get("session_logs", {})
        if session_logs:
            html_content += '<h5 style="margin: 15px 0 10px 0;">Session Summary:</h5>'
            html_content += '<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 10px; margin: 5px 0;">'
            html_content += (
                f"<p><b>Session ID:</b> {session_logs.get('session_id', 'Unknown')}</p>"
            )
            html_content += (
                f"<p><b>Total Events:</b> {session_logs.get('total_events', 0)}</p>"
            )

            event_types = session_logs.get("event_types", {})
            if event_types:
                html_content += "<p><b>Event Types:</b></p>"
                html_content += '<ul style="margin: 5px 0 0 20px;">'
                for event_type, count in event_types.items():
                    if count > 0:
                        html_content += (
                            f"<li>{event_type.replace('_', ' ').title()}: {count}</li>"
                        )
                html_content += "</ul>"

            html_content += "</div>"

        html_content += "</div></div>"
        html_wrapper += html_content
        html_wrapper += "</div>"
        html_wrapper += "</details>"

        return mark_safe(html_wrapper)

    def get_question_preview(self, obj):
        """Return a preview of the question (first 100 characters)"""
        if obj.question:
            return (
                obj.question[:100] + "..." if len(obj.question) > 100 else obj.question
            )
        return "-"

    get_question_preview.short_description = "Question Preview"

    def has_add_permission(self, request):
        """Disable manual creation since logs should be created programmatically"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make the admin read-only"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes"""
        return request.user.is_superuser

    def formatted_started_at(self, obj):
        """Format started_at timestamp with seconds in local timezone"""
        if obj.started_at:
            # Convert to local timezone
            local_time = timezone.localtime(obj.started_at)
            return local_time.strftime("%Y-%m-%d %H:%M:%S")
        return "-"

    formatted_started_at.short_description = "Started At"

    def formatted_terminated_at(self, obj):
        """Format terminated_at timestamp with seconds in local timezone"""
        if obj.terminated_at:
            # Convert to local timezone
            local_time = timezone.localtime(obj.terminated_at)
            return local_time.strftime("%Y-%m-%d %H:%M:%S")
        return "-"

    formatted_terminated_at.short_description = "Terminated At"

    def sql_status_display(self, obj):
        """Display SQL execution status with visual badge"""
        if not obj.sql_status:
            return "-"
        
        status = obj.sql_status.lower()
        color = "#28a745" if "pass" in status else "#dc3545" if "fail" in status or "error" in status else "#ffc107"
        
        html = f'''
        <span style="
            display: inline-block;
            background-color: {color};
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        ">{obj.sql_status}</span>
        '''
        return mark_safe(html)
    
    sql_status_display.short_description = "SQL Status"

    def evaluation_case_display(self, obj):
        """Display evaluation case category"""
        if not obj.evaluation_case:
            return "-"
        return obj.evaluation_case
    
    evaluation_case_display.short_description = "Evaluation Case"

    def evaluation_details_display(self, obj):
        """Display detailed evaluation results as formatted JSON"""
        if not obj.evaluation_details:
            return "-"
        
        html = '<div style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 10px; background-color: var(--darkened-bg, #f8f9fa);">'
        html += '<h4 style="margin-top: 0;">Evaluation Details</h4>'
        
        try:
            # Get pool of generated SQL to show SQL values
            pool_of_sql = []
            if obj.pool_of_generated_sql:
                parsed_pool = parse_value(obj.pool_of_generated_sql)
                if isinstance(parsed_pool, list):
                    pool_of_sql = parsed_pool
            
            # Get selection metrics to extract pass rates
            selection_data = None
            if obj.selection_metrics:
                try:
                    selection_data = json.loads(obj.selection_metrics)
                except:
                    pass
            
            # evaluation_details is already a JSONField, so it should be a Python object
            details = obj.evaluation_details if isinstance(obj.evaluation_details, list) else json.loads(obj.evaluation_details) if isinstance(obj.evaluation_details, str) else []
            
            for i, detail in enumerate(details, 1):
                html += f'<div style="margin: 10px 0; padding: 10px; background-color: var(--body-bg, white); border-radius: 3px;">'
                
                # Get SQL value for this test number
                sql_value = ""
                if i <= len(pool_of_sql):
                    sql_value = str(pool_of_sql[i-1])
                
                # Get pass rate for this SQL
                pass_rate_str = ""
                if selection_data and 'sql_scores' in selection_data:
                    for score in selection_data['sql_scores']:
                        if score.get('sql_index') == i - 1:  # 0-indexed in data
                            pass_rate = score.get('pass_rate', 0)
                            # Convert to percentage if needed
                            if pass_rate <= 1:
                                pass_percentage = int(pass_rate * 100)
                            else:
                                pass_percentage = int(pass_rate)
                            pass_rate_str = f"{pass_percentage}%"
                            break
                
                # Display SQL # with value
                if sql_value:
                    html += f'<div style="width: 100%;"><strong>SQL #{i} - </strong>'
                    html += f'<span style="display: inline-block; max-width: calc(100% - 100px); overflow-x: auto; white-space: nowrap; vertical-align: middle;">{sql_value}</span></div>'
                    if pass_rate_str:
                        html += f'<span style="margin-left: 20px;"><strong>Pass Rate:</strong> {pass_rate_str}</span><br>'
                else:
                    html += f'<strong>Test {i}:</strong><br>'
                    if pass_rate_str:
                        html += f'<span style="margin-left: 20px;"><strong>Pass Rate:</strong> {pass_rate_str}</span><br>'
                
                if isinstance(detail, dict):
                    for key, value in detail.items():
                        # Skip pass_rate if already shown
                        if key.lower() != 'pass_rate':
                            html += f'<span style="margin-left: 20px;"><strong>{key}:</strong> {value}</span><br>'
                else:
                    html += f'<span style="margin-left: 20px;">{detail}</span><br>'
                html += '</div>'
        except Exception as e:
            html += f'<pre style="color: var(--error-fg, #dc3545);">Error parsing evaluation details: {e}</pre>'
        
        html += '</div>'
        return mark_safe(html)
    
    evaluation_details_display.short_description = "Evaluation Details"

    

    def test_generation_timing_display(self, obj):
        """Display test generation timing information"""
        html = '<div style="font-family: monospace; line-height: 1.6;">'
        
        if obj.test_generation_start:
            start = timezone.localtime(obj.test_generation_start)
            html += f'<strong>Started:</strong> {start.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.test_generation_end:
            end = timezone.localtime(obj.test_generation_end)
            html += f'<strong>Ended:</strong> {end.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.test_generation_duration_ms > 0:
            duration_sec = obj.test_generation_duration_ms / 1000
            html += f'<strong>Duration:</strong> {duration_sec:.1f}s'
        
        html += '</div>'
        return mark_safe(html) if obj.test_generation_start or obj.test_generation_duration_ms else "-"
    
    test_generation_timing_display.short_description = "Test Generation Timing"

    def evaluation_timing_display(self, obj):
        """Display evaluation timing information"""
        html = '<div style="font-family: monospace; line-height: 1.6;">'
        
        if obj.evaluation_start:
            start = timezone.localtime(obj.evaluation_start)
            html += f'<strong>Started:</strong> {start.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.evaluation_end:
            end = timezone.localtime(obj.evaluation_end)
            html += f'<strong>Ended:</strong> {end.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.evaluation_duration_ms > 0:
            duration_sec = obj.evaluation_duration_ms / 1000
            html += f'<strong>Duration:</strong> {duration_sec:.1f}s'
        
        html += '</div>'
        return mark_safe(html) if obj.evaluation_start or obj.evaluation_duration_ms else "-"
    
    evaluation_timing_display.short_description = "Evaluation Timing"

    def sql_selection_timing_display(self, obj):
        """Display SQL selection timing information"""
        html = '<div style="font-family: monospace; line-height: 1.6;">'
        
        if obj.sql_selection_start:
            start = timezone.localtime(obj.sql_selection_start)
            html += f'<strong>Started:</strong> {start.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.sql_selection_end:
            end = timezone.localtime(obj.sql_selection_end)
            html += f'<strong>Ended:</strong> {end.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.sql_selection_duration_ms > 0:
            duration_sec = obj.sql_selection_duration_ms / 1000
            html += f'<strong>Duration:</strong> {duration_sec:.1f}s'
        
        html += '</div>'
        return mark_safe(html) if obj.sql_selection_start or obj.sql_selection_duration_ms else "-"
    
    sql_selection_timing_display.short_description = "SQL Selection Timing"
    
    def sql_generation_timing_display(self, obj):
        """Display SQL generation timing information"""
        html = '<div style="font-family: monospace; line-height: 1.6;">'
        
        if obj.sql_generation_start:
            start = timezone.localtime(obj.sql_generation_start)
            html += f'<strong>Started:</strong> {start.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.sql_generation_end:
            end = timezone.localtime(obj.sql_generation_end)
            html += f'<strong>Ended:</strong> {end.strftime("%H:%M:%S.%f")[:-3]}<br>'
        
        if obj.sql_generation_duration_ms > 0:
            duration_sec = obj.sql_generation_duration_ms / 1000
            html += f'<strong>Duration:</strong> {duration_sec:.1f}s'
        
        html += '</div>'
        return mark_safe(html) if obj.sql_generation_start or obj.sql_generation_duration_ms else "-"
    
    sql_generation_timing_display.short_description = "SQL Generation Timing"

    def formatted_created_at(self, obj):
        """Format created_at timestamp with seconds in local timezone"""
        if obj.created_at:
            # Convert to local timezone
            local_time = timezone.localtime(obj.created_at)
            return local_time.strftime("%Y-%m-%d %H:%M:%S")
        return "-"

    formatted_created_at.short_description = "Created At"

    def formatted_updated_at(self, obj):
        """Format updated_at timestamp with seconds in local timezone"""
        if obj.updated_at:
            # Convert to local timezone
            local_time = timezone.localtime(obj.updated_at)
            return local_time.strftime("%Y-%m-%d %H:%M:%S")
        return "-"

    formatted_updated_at.short_description = "Updated At"

    def formatted_available_context_tokens(self, obj):
        """Format available context tokens"""
        if obj.available_context_tokens is not None:
            # Format number with thousands separator
            tokens = f"{obj.available_context_tokens:,}"

            return format_html(
                '<div style="font-family: monospace; font-size: 1.1em;">'
                "<strong>{}</strong> tokens"
                "</div>",
                tokens,
            )
        return "-"

    formatted_available_context_tokens.short_description = "Available Context Tokens"

    def formatted_full_schema_tokens_count(self, obj):
        """Format full schema tokens count with percentage of context used"""
        if obj.full_schema_tokens_count is not None:
            # Format number with thousands separator
            tokens = f"{obj.full_schema_tokens_count:,}"

            # Calculate percentage if both values are available
            if obj.available_context_tokens and obj.available_context_tokens > 0:
                percentage = (
                    obj.full_schema_tokens_count / obj.available_context_tokens
                ) * 100

                return format_html(
                    '<div style="font-family: monospace; font-size: 1.1em;">'
                    "<strong>{}</strong> tokens ({}%)"
                    "</div>",
                    tokens,
                    f"{percentage:.1f}",
                )
            else:
                # Just show the token count if no context size available
                return format_html(
                    '<div style="font-family: monospace; font-size: 1.1em;">'
                    "<strong>{}</strong> tokens"
                    "</div>",
                    tokens,
                )
        return "-"

    formatted_full_schema_tokens_count.short_description = "Full Schema Token Count"

    def formatted_schema_link_strategy(self, obj):
        """Display the schema link strategy"""
        if obj.schema_link_strategy:
            return obj.schema_link_strategy
        return "-"

    formatted_schema_link_strategy.short_description = "Schema Link Strategy"

    def selected_sql(self, obj):
        """Display the generated_sql field with the label 'Selected SQL'"""
        return obj.generated_sql or "-"

    selected_sql.short_description = "Selected SQL"

    def selected_sql_or_error(self, obj):
        """Display the selected SQL or error message if SQL generation failed"""
        if obj.generated_sql:
            # If we have a generated SQL, show it using Django admin styles
            sql_text = obj.generated_sql[:500]  # Limit to first 500 chars for basic info
            if len(obj.generated_sql) > 500:
                sql_text += "..."
            
            html = f'''
            <div class="readonly">
                <span style="color: var(--body-loud-color, #0c4b33); font-weight: bold;">✓ SQL Generated</span>
                <textarea readonly class="vLargeTextField" style="margin-top: 8px; font-family: 'Bitstream Vera Sans Mono', Monaco, 'Courier New', Courier, monospace; font-size: 12px; width: 100%; min-height: 100px;">{sql_text}</textarea>
            </div>
            '''
            return mark_safe(html)
        elif obj.sql_generation_failure_message:
            # If we have a failure message, show it using Django admin error styles
            html = f'''
            <div class="readonly">
                <span style="color: var(--error-fg, #ba2121); font-weight: bold;">✗ SQL Generation Failed</span>
                <div style="margin-top: 8px; color: var(--error-fg, #ba2121); background: var(--error-bg, #ffe6e6); padding: 10px; border-radius: 4px;">{obj.sql_generation_failure_message}</div>
            </div>
            '''
            return mark_safe(html)
        else:
            # No SQL and no error message
            return mark_safe('<div class="readonly" style="color: var(--body-quiet-color, #666); font-style: italic;">- No SQL generated -</div>')
    selected_sql_or_error.short_description = "Selected SQL / Error"

    def get_test_status(self, obj):
        """Calculate the test status based on selection_metrics and evaluation_results"""
        # Check evaluation_case FIRST for A-GOLD, B-GOLD, etc. statuses
        # This takes priority over sql_generation_failure_message
        if obj.evaluation_case:
            case = obj.evaluation_case.upper()
            if "GOLD" in case:
                return "GOLD", {"pass_rate": 100, "message": f"Test passed: {obj.evaluation_case}"}
            elif "SILVER" in case:
                # For silver cases, still show as passed (star)
                return "GOLD", {"pass_rate": 90, "message": f"Test passed: {obj.evaluation_case}"}
            elif "FAILED" in case:
                return "KO", {"pass_rate": 0, "message": f"Test failed: {obj.evaluation_case}"}
        
        # Check for SQL generation failure only if no evaluation_case
        if obj.sql_generation_failure_message:
            return "KO", {"pass_rate": 0, "message": "SQL generation failed"}
        
        if not obj.selection_metrics:
            return None, None  # status, details
        
        try:
            # Try to parse selection_metrics as JSON
            data = json.loads(obj.selection_metrics)
            
            # Check for enhanced evaluation format with GOLD status
            if data.get("evaluation_type") == "enhanced":
                final_status = data.get("final_status")
                if final_status == "GOLD":
                    return "GOLD", {"pass_rate": 100, "message": "All tests passed"}
                elif final_status == "FAILED":
                    return "KO", {"pass_rate": 0, "message": "No SQL met criteria"}
            
            # Check for finalists (selected SQL)
            finalists = data.get("finalists", [])
            if not finalists:
                # No SQL selected
                return "KO", {"pass_rate": 0, "message": "No SQL selected"}
            
            # Get the selected SQL index
            if isinstance(finalists[0], dict):
                selected_index = finalists[0].get("sql_index", 0)
            else:
                selected_index = finalists[0]
            
            # Find the score for the selected SQL
            sql_scores = data.get("sql_scores", [])
            for score in sql_scores:
                if score.get("sql_index") == selected_index:
                    pass_rate = score.get("pass_rate", 0)
                    passed_count = score.get("passed_count", 0)
                    total_tests = score.get("total_tests", 0)
                    
                    # Convert pass_rate from 0-1 to percentage if needed
                    if pass_rate <= 1:
                        pass_percentage = pass_rate * 100
                    else:
                        pass_percentage = pass_rate
                    
                    if pass_percentage == 100:
                        return "GOLD", {
                            "pass_rate": 100,
                            "passed_count": passed_count,
                            "total_tests": total_tests,
                            "message": "Perfect score!"
                        }
                    elif pass_percentage > 0:
                        return f"{pass_percentage:.0f}%", {
                            "pass_rate": pass_percentage,
                            "passed_count": passed_count,
                            "total_tests": total_tests,
                            "message": f"Passed {passed_count}/{total_tests} tests"
                        }
                    else:
                        return "KO", {
                            "pass_rate": 0,
                            "passed_count": 0,
                            "total_tests": total_tests,
                            "message": "All tests failed"
                        }
            
            # If we couldn't find the score for selected SQL
            return "OK", {"pass_rate": None, "message": "SQL selected but score unknown"}
            
        except (json.JSONDecodeError, Exception):
            # Fallback - check if SQL was generated
            if obj.generated_sql:
                return "OK", {"pass_rate": None, "message": "SQL generated"}
            return "KO", {"pass_rate": 0, "message": "No SQL generated"}
    
    def test_status_badge(self, obj):
        """Display a simple test status indicator for the list view"""
        status, details = self.get_test_status(obj)
        
        if not status:
            return "-"
        
        if status == "GOLD":
            # Just a golden star
            return format_html(
                '<span style="font-size: 16px;">⭐</span>'
            )
        elif status == "KO":
            # Just a red X
            return format_html(
                '<span style="color: #dc3545; font-size: 14px; font-weight: bold;">❌</span>'
            )
        elif "%" in status:
            # Just the percentage in green and bold
            return format_html(
                '<span style="color: #28a745; font-weight: bold; font-size: 13px;">{}</span>',
                status
            )
        
        # Default OK status - just show "OK" in gray
        return format_html(
            '<span style="color: #6c757d; font-weight: bold; font-size: 13px;">OK</span>'
        )
    
    test_status_badge.short_description = "Test Status"
    
    def test_status_display(self, obj):
        """Display simple test status for the form view"""
        status, details = self.get_test_status(obj)
        
        if not status:
            return "-"
        
        # Simple display with just the symbols and minimal text
        html_content = '<div style="margin: 10px 0; padding: 10px;">'
        
        if status == "GOLD":
            # Just a golden star with text
            html_content += (
                '<span style="font-size: 24px; margin-right: 10px;">⭐</span>'
                '<span style="font-size: 16px; font-weight: bold;">All tests passed (100%)</span>'
            )
            if details and details.get("total_tests"):
                html_content += f'<span style="margin-left: 10px; color: #666; font-size: 14px;">({details["total_tests"]} tests)</span>'
            
        elif status == "KO":
            # Just a red X with text
            html_content += (
                '<span style="color: #dc3545; font-size: 20px; font-weight: bold; margin-right: 10px;">❌</span>'
                '<span style="font-size: 16px; font-weight: bold;">Failed</span>'
            )
            if details:
                message = details.get("message", "No SQL generated or selected")
                html_content += f'<span style="margin-left: 10px; color: #666; font-size: 14px;">({message})</span>'
            
        elif "%" in status:
            # Just the percentage in green and bold with details
            html_content += (
                f'<span style="color: #28a745; font-weight: bold; font-size: 18px; margin-right: 10px;">{status}</span>'
                '<span style="font-size: 16px;">Tests passed</span>'
            )
            if details and details.get("total_tests"):
                html_content += (
                    f'<span style="margin-left: 10px; color: #666; font-size: 14px;">'
                    f'({details.get("passed_count", 0)}/{details["total_tests"]} tests)</span>'
                )
        else:
            # Default OK status - simple gray text
            html_content += (
                '<span style="color: #6c757d; font-weight: bold; font-size: 16px; margin-right: 10px;">OK</span>'
                '<span style="font-size: 14px; color: #666;">SQL generated</span>'
            )
        
        html_content += '</div>'
        return mark_safe(html_content)
    
    def enhanced_evaluation_thinking_display(self, obj):
        """Display enhanced evaluation thinking with user-friendly formatting"""
        if not obj.enhanced_evaluation_thinking:
            return "-"
        
        from django.utils.safestring import mark_safe
        
        # Create a nicely formatted display with Django admin styling
        html_content = '<div style="background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 10px 0;">'
        html_content += '<h4 style="margin-top: 0; color: #333;">Enhanced Evaluation Reasoning</h4>'
        html_content += '<pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px; color: #555; margin: 0;">'
        html_content += format_html("{}", obj.enhanced_evaluation_thinking)
        html_content += '</pre>'
        html_content += '</div>'
        
        return mark_safe(html_content)
    
    enhanced_evaluation_thinking_display.short_description = "Enhanced Evaluation Thinking"
    
    def enhanced_evaluation_answers_display(self, obj):
        """Display enhanced evaluation answers using Django admin standard styling"""
        if not obj.enhanced_evaluation_answers:
            return "-"
        
        from django.utils.safestring import mark_safe
        import json
        
        try:
            # Format the JSON data nicely
            answers = obj.enhanced_evaluation_answers
            if isinstance(answers, str):
                answers = json.loads(answers)
            
            # Use Django admin standard styling - bullet list without custom colors
            html_content = '<ul style="margin: 0; padding-left: 25px; list-style: disc;">'
            
            for answer in answers:
                html_content += f'<li style="margin: 3px 0; font-family: monospace; font-size: 13px; color: var(--body-fg, #333); line-height: 1.4;">{format_html("{}", answer)}</li>'
            
            html_content += '</ul>'
            
            return mark_safe(html_content)
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, display raw text
            return format_html('<pre style="font-family: monospace; font-size: 13px; color: var(--body-fg, #333);">{}</pre>', 
                              obj.enhanced_evaluation_answers)
    
    enhanced_evaluation_answers_display.short_description = "Evaluation Answers"
    
    def enhanced_evaluation_selected_sql_display(self, obj):
        """Display enhanced evaluation selected SQL (theme-safe)"""
        if not obj.enhanced_evaluation_selected_sql:
            return "-"
        
        inner = (
            '<div style="margin-top: 8px;">'
            '<pre class="readonly thoth-pre" style="overflow: auto; white-space: pre;">' 
            f"{format_html('{}', obj.enhanced_evaluation_selected_sql)}" 
            "</pre>"
            "</div>"
        )
        return mark_safe(render_collapsible("Enhanced Evaluation Selected SQL", inner))
    
    enhanced_evaluation_selected_sql_display.short_description = "Enhanced Selected SQL"
    
    test_status_display.short_description = "Test Execution Status"
    
    # NEW METHODS for reorganized logging
    
    def evaluation_case_badge(self, obj):
        """Simple badge for evaluation case - used in list display"""
        case = obj.evaluation_case
        
        if not case:
            return "-"
        
        color_map = {
            "A-GOLD": "#FFD700",  # Gold yellow
            "B-GOLD": "#FFD700",  # Gold yellow
            "A-SILVER": "#C0C0C0",  # Silver gray
            "B-SILVER": "#C0C0C0",  # Silver gray
            "C-FAILED": "#dc3545",  # Red (same as D-FAILED)
            "D-FAILED": "#dc3545",  # Red
        }
        color = color_map.get(case, "#6c757d")
        # Better text contrast - use black for gold/silver, white for red failed cases
        text_color = "white" if case in ["D-FAILED", "C-FAILED"] else "black"
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, text_color, case
        )
    evaluation_case_badge.short_description = "Result"
    
    def evaluation_case_display(self, obj):
        """Badge with explanation for evaluation case - used in detail form"""
        case = obj.evaluation_case
        
        if not case:
            return "-"
        
        # Case explanations (updated for new algorithm logic)
        case_explanations = {
            "A-GOLD": "Single perfect SQL (100% pass rate) - direct selection",
            "B-GOLD": "Multiple perfect SQLs (100% pass rate) - best SQL selected via agent",
            "A-SILVER": "Single SQL above threshold - direct selection", 
            "B-SILVER": "Multiple SQLs above threshold - best SQL selected via agent",
            "C-FAILED": "No SQL met the quality threshold",
            "D-FAILED": "SQL generation or evaluation failed",
        }
        
        color_map = {
            "A-GOLD": "#FFD700",  # Gold yellow
            "B-GOLD": "#FFD700",  # Gold yellow
            "A-SILVER": "#C0C0C0",  # Silver gray
            "B-SILVER": "#C0C0C0",  # Silver gray
            "C-FAILED": "#dc3545",  # Red (same as D-FAILED)
            "D-FAILED": "#dc3545",  # Red
        }
        color = color_map.get(case, "#6c757d")
        # Better text contrast - use black for gold/silver, white for red failed cases
        text_color = "white" if case in ["D-FAILED", "C-FAILED"] else "black"
        
        # Get explanation
        explanation = case_explanations.get(case, "")
        
        # Return badge followed by explanation
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 5px 10px; border-radius: 3px; font-weight: bold; margin-right: 10px;">{}</span>'
            '<span style="color: #666; font-style: italic;">{}</span>',
            color, text_color, case, explanation
        )
    evaluation_case_display.short_description = "Evaluation Result"
    
    def generated_sql_textarea(self, obj):
        """SQL with fixed width textarea"""
        if obj.generated_sql:
            return format_html(
                '<textarea readonly style="width: 600px; height: 150px; font-family: monospace;" class="vLargeTextField">{}</textarea>',
                obj.generated_sql
            )
        elif obj.sql_generation_failure_message:
            return format_html(
                '<div style="color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px;">'
                '<strong>❌ SQL Generation Failed:</strong><br>{}'
                '</div>',
                obj.sql_generation_failure_message
            )
        return "-"
    generated_sql_textarea.short_description = "SQL Generation"
    
    def duration_display(self, obj):
        """Display duration without label"""
        if obj.duration:
            return format_html('<strong>{}</strong>', obj.duration)
        return "-"
    duration_display.short_description = "Duration"
    
    def timing_display(self, obj):
        """Display Started At, Terminated At, and Duration in a horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.started_at:
            local_time = timezone.localtime(obj.started_at)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.terminated_at:
            local_time = timezone.localtime(obj.terminated_at)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.duration:
            duration = obj.duration
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    timing_display.short_description = "Timing Information"
    
    def user_workspace_display(self, obj):
        """Display Username and Workspace side by side"""
        username = obj.username if obj.username else "-"
        workspace = obj.workspace if obj.workspace else "-"
        
        html = '''
        <table style="width: 100%; table-layout: fixed; border: none;">
            <tr>
                <td style="width: 50%; padding-right: 20px; border: none;">
                    <strong>Username:</strong> {}
                </td>
                <td style="width: 50%; border: none;">
                    <strong>Workspace:</strong> {}
                </td>
            </tr>
        </table>
        '''.format(username, workspace)
        
        return format_html(html)
    user_workspace_display.short_description = "User and Workspace"
    
    def languages_display(self, obj):
        """Display Question Language and Database Language side by side"""
        question_lang = obj.question_language if obj.question_language else "-"
        db_lang = obj.db_language if obj.db_language else "-"
        
        html = '''
        <table style="width: 100%; table-layout: fixed; border: none;">
            <tr>
                <td style="width: 50%; padding-right: 20px; border: none;">
                    <strong>Question Language:</strong> {}
                </td>
                <td style="width: 50%; border: none;">
                    <strong>Database Language:</strong> {}
                </td>
            </tr>
        </table>
        '''.format(question_lang, db_lang)
        
        return format_html(html)
    languages_display.short_description = "Languages"
    
    def escalation_flags_display(self, obj):
        """Display escalation flags with visual indicators."""
        # Check if any escalation occurred
        advanced = getattr(obj, 'advanced_escalation', False)
        expert = getattr(obj, 'expert_escalation', False)
        
        if not advanced and not expert:
            return format_html(
                '<span style="color: #666; font-style: italic;">No escalation</span>'
            )
        
        flags_html = []
        if advanced:
            flags_html.append(
                '<span style="background: #ffc107; color: #000; padding: 2px 8px; border-radius: 3px; margin-right: 5px;">'
                '⬆️ ADVANCED'
                '</span>'
            )
        if expert:
            flags_html.append(
                '<span style="background: #dc3545; color: #fff; padding: 2px 8px; border-radius: 3px;">'
                '⬆️⬆️ EXPERT'
                '</span>'
            )
        
        return format_html(''.join(flags_html))
    
    escalation_flags_display.short_description = "Escalation Status"
    
    def flags_activated_display(self, obj):
        """Display frontend UI flags with their on/off status"""
        if not obj.flags_activated:
            return "-"
        
        try:
            if isinstance(obj.flags_activated, str):
                all_flags = json.loads(obj.flags_activated)
            else:
                all_flags = obj.flags_activated
            
            # Define frontend UI flags to display (hide backend technical flags)
            frontend_flags = [
                'show_sql',
                'explain_generated_query', 
                'treat_empty_result_as_error',
                'belt_and_suspenders'
            ]
            
            # Filter to show only frontend flags
            flags = {}
            for flag_name in frontend_flags:
                if flag_name in all_flags:
                    flags[flag_name] = all_flags[flag_name]
                elif flag_name == 'belt_and_suspenders':
                    # Special handling for belt_and_suspenders - check timestamps if not in flags
                    if hasattr(obj, 'belt_and_suspenders_start') and obj.belt_and_suspenders_start:
                        flags[flag_name] = True
                    else:
                        flags[flag_name] = False
                else:
                    # Default to False for missing frontend flags
                    flags[flag_name] = False
                
            html = '<div style="margin: 5px 0;">'
            for flag_name, flag_value in flags.items():
                if flag_value:
                    # Green badge for active flags
                    html += f'<span style="background: #28a745; color: white; padding: 3px 8px; margin: 2px; border-radius: 3px; font-size: 12px; display: inline-block;">{flag_name}</span> '
                else:
                    # Gray badge for inactive flags
                    html += f'<span style="background: #6c757d; color: white; padding: 3px 8px; margin: 2px; border-radius: 3px; font-size: 12px; opacity: 0.5; display: inline-block;">{flag_name}</span> '
            html += '</div>'
            return mark_safe(html)
        except Exception as e:
            return f"Error: {str(e)}"
    flags_activated_display.short_description = "Flags Attivati"
    
    # Timestamp display methods for new phases
    def validation_start_display(self, obj):
        if obj.validation_start:
            return timezone.localtime(obj.validation_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    validation_start_display.short_description = "Start"
    
    def validation_end_display(self, obj):
        if obj.validation_end:
            return timezone.localtime(obj.validation_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    validation_end_display.short_description = "End"
    
    def validation_duration_display(self, obj):
        if obj.validation_duration_ms > 0:
            return f"{obj.validation_duration_ms / 1000:.1f}s"
        return "-"
    validation_duration_display.short_description = "Validation Duration"
    
    def keyword_generation_start_display(self, obj):
        if obj.keyword_generation_start:
            return timezone.localtime(obj.keyword_generation_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    keyword_generation_start_display.short_description = "Start"
    
    def keyword_generation_end_display(self, obj):
        if obj.keyword_generation_end:
            return timezone.localtime(obj.keyword_generation_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    keyword_generation_end_display.short_description = "End"
    
    def keyword_generation_duration_display(self, obj):
        if obj.keyword_generation_duration_ms > 0:
            return f"{obj.keyword_generation_duration_ms / 1000:.1f}s"
        return "-"
    keyword_generation_duration_display.short_description = "Keywords Duration"
    
    def schema_preparation_start_display(self, obj):
        if obj.schema_preparation_start:
            return timezone.localtime(obj.schema_preparation_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    schema_preparation_start_display.short_description = "Start"
    
    def schema_preparation_end_display(self, obj):
        if obj.schema_preparation_end:
            return timezone.localtime(obj.schema_preparation_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    schema_preparation_end_display.short_description = "End"
    
    def schema_preparation_duration_display(self, obj):
        if obj.schema_preparation_duration_ms > 0:
            return f"{obj.schema_preparation_duration_ms / 1000:.1f}s"
        return "-"
    schema_preparation_duration_display.short_description = "Schema Prep Duration"
    
    def context_retrieval_start_display(self, obj):
        if obj.context_retrieval_start:
            return timezone.localtime(obj.context_retrieval_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    context_retrieval_start_display.short_description = "Start"
    
    def context_retrieval_end_display(self, obj):
        if obj.context_retrieval_end:
            return timezone.localtime(obj.context_retrieval_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    context_retrieval_end_display.short_description = "End"
    
    def context_retrieval_duration_display(self, obj):
        if obj.context_retrieval_duration_ms > 0:
            return f"{obj.context_retrieval_duration_ms / 1000:.1f}s"
        return "-"
    context_retrieval_duration_display.short_description = "Context Duration"
    
    def test_reduction_start_display(self, obj):
        if obj.test_reduction_start:
            return timezone.localtime(obj.test_reduction_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    test_reduction_start_display.short_description = "Start"
    
    def test_reduction_end_display(self, obj):
        if obj.test_reduction_end:
            return timezone.localtime(obj.test_reduction_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    test_reduction_end_display.short_description = "End"
    
    def test_reduction_duration_display(self, obj):
        if obj.test_reduction_duration_ms > 0:
            return f"{obj.test_reduction_duration_ms / 1000:.1f}s"
        return "-"
    test_reduction_duration_display.short_description = "Test Reduction Duration"
    
    def sql_generation_start_display(self, obj):
        if obj.sql_generation_start:
            return timezone.localtime(obj.sql_generation_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    sql_generation_start_display.short_description = "Start"
    
    def sql_generation_end_display(self, obj):
        if obj.sql_generation_end:
            return timezone.localtime(obj.sql_generation_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    sql_generation_end_display.short_description = "End"
    
    def sql_generation_duration_display(self, obj):
        if obj.sql_generation_duration_ms > 0:
            return f"{obj.sql_generation_duration_ms / 1000:.1f}s"
        return "-"
    sql_generation_duration_display.short_description = "SQL Gen Duration"
    
    def test_generation_start_display(self, obj):
        if obj.test_generation_start:
            return timezone.localtime(obj.test_generation_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    test_generation_start_display.short_description = "Start"
    
    def test_generation_end_display(self, obj):
        if obj.test_generation_end:
            return timezone.localtime(obj.test_generation_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"  
    test_generation_end_display.short_description = "End"
    
    def test_generation_duration_display(self, obj):
        if obj.test_generation_duration_ms > 0:
            return f"{obj.test_generation_duration_ms / 1000:.1f}s"
        return "-"
    test_generation_duration_display.short_description = "Test Gen Duration"
    
    def evaluation_start_display(self, obj):
        if obj.evaluation_start:
            return timezone.localtime(obj.evaluation_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    evaluation_start_display.short_description = "Start"
    
    def evaluation_end_display(self, obj):
        if obj.evaluation_end:
            return timezone.localtime(obj.evaluation_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    evaluation_end_display.short_description = "End"
    
    def evaluation_duration_display(self, obj):
        if obj.evaluation_duration_ms > 0:
            return f"{obj.evaluation_duration_ms / 1000:.1f}s"
        return "-"
    evaluation_duration_display.short_description = "Evaluation Duration"
    
    def belt_and_suspenders_start_display(self, obj):
        if obj.belt_and_suspenders_start:
            return timezone.localtime(obj.belt_and_suspenders_start).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    belt_and_suspenders_start_display.short_description = "B&S Start"
    
    def belt_and_suspenders_end_display(self, obj):
        if obj.belt_and_suspenders_end:
            return timezone.localtime(obj.belt_and_suspenders_end).strftime("%H:%M:%S.%f")[:-3]
        return "-"
    belt_and_suspenders_end_display.short_description = "B&S End"
    
    def belt_and_suspenders_duration_display(self, obj):
        if obj.belt_and_suspenders_duration_ms > 0:
            return f"{obj.belt_and_suspenders_duration_ms / 1000:.1f}s"
        return "-"
    belt_and_suspenders_duration_display.short_description = "B&S Duration"
    
    # Inline timestamp display methods (start, end, duration on same line)
    def validation_timing_inline(self, obj):
        """Display validation timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.validation_start:
            local_time = timezone.localtime(obj.validation_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.validation_end:
            local_time = timezone.localtime(obj.validation_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.validation_duration_ms and obj.validation_duration_ms > 0:
            duration = f"{obj.validation_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    validation_timing_inline.short_description = "Timing Information"
    
    def keyword_generation_timing_inline(self, obj):
        """Display keyword generation timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.keyword_generation_start:
            local_time = timezone.localtime(obj.keyword_generation_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.keyword_generation_end:
            local_time = timezone.localtime(obj.keyword_generation_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.keyword_generation_duration_ms and obj.keyword_generation_duration_ms > 0:
            duration = f"{obj.keyword_generation_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    keyword_generation_timing_inline.short_description = "Timing Information"
    
    def context_retrieval_timing_inline(self, obj):
        """Display context retrieval timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.context_retrieval_start:
            local_time = timezone.localtime(obj.context_retrieval_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.context_retrieval_end:
            local_time = timezone.localtime(obj.context_retrieval_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.context_retrieval_duration_ms and obj.context_retrieval_duration_ms > 0:
            duration = f"{obj.context_retrieval_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    context_retrieval_timing_inline.short_description = "Timing Information"
    
    def sql_generation_timing_inline(self, obj):
        """Display SQL generation timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.sql_generation_start:
            local_time = timezone.localtime(obj.sql_generation_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.sql_generation_end:
            local_time = timezone.localtime(obj.sql_generation_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.sql_generation_duration_ms and obj.sql_generation_duration_ms > 0:
            duration = f"{obj.sql_generation_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    sql_generation_timing_inline.short_description = "Timing Information"
    
    def test_generation_timing_inline(self, obj):
        """Display test generation timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.test_generation_start:
            local_time = timezone.localtime(obj.test_generation_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.test_generation_end:
            local_time = timezone.localtime(obj.test_generation_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.test_generation_duration_ms and obj.test_generation_duration_ms > 0:
            duration = f"{obj.test_generation_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    test_generation_timing_inline.short_description = "Timing Information"
    
    def test_reduction_timing_inline(self, obj):
        """Display test reduction timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.test_reduction_start:
            local_time = timezone.localtime(obj.test_reduction_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.test_reduction_end:
            local_time = timezone.localtime(obj.test_reduction_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.test_reduction_duration_ms and obj.test_reduction_duration_ms > 0:
            duration = f"{obj.test_reduction_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    test_reduction_timing_inline.short_description = "Timing Information"
    
    def evaluation_timing_inline(self, obj):
        """Display evaluation timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.evaluation_start:
            local_time = timezone.localtime(obj.evaluation_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.evaluation_end:
            local_time = timezone.localtime(obj.evaluation_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.evaluation_duration_ms and obj.evaluation_duration_ms > 0:
            duration = f"{obj.evaluation_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    evaluation_timing_inline.short_description = "Evaluation Timing"
    
    def sql_selection_timing_inline(self, obj):
        """Display SQL selection timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.sql_selection_start:
            local_time = timezone.localtime(obj.sql_selection_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.sql_selection_end:
            local_time = timezone.localtime(obj.sql_selection_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.sql_selection_duration_ms and obj.sql_selection_duration_ms > 0:
            duration = f"{obj.sql_selection_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    sql_selection_timing_inline.short_description = "SQL Selection Timing"
    
    def belt_and_suspenders_timing_inline(self, obj):
        """Display belt and suspenders timing with full date/time in horizontal layout"""
        started = "-"
        terminated = "-"
        duration = "-"
        
        if obj.belt_and_suspenders_start:
            local_time = timezone.localtime(obj.belt_and_suspenders_start)
            started = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.belt_and_suspenders_end:
            local_time = timezone.localtime(obj.belt_and_suspenders_end)
            terminated = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if obj.belt_and_suspenders_duration_ms and obj.belt_and_suspenders_duration_ms > 0:
            duration = f"{obj.belt_and_suspenders_duration_ms / 1000:.1f}s"
        
        html = '''
        <div style="display: flex; gap: 30px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Started At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Terminated At:</strong>
                <span>{}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <strong style="margin-bottom: 5px;">Duration:</strong>
                <span>{}</span>
            </div>
        </div>
        '''.format(started, terminated, duration)
        
        return format_html(html)
    belt_and_suspenders_timing_inline.short_description = "Belt & Suspenders Timing"
    
    # Language display methods
    def question_language_display(self, obj):
        """Display question language with proper labeling"""
        return obj.question_language or "Not detected"
    question_language_display.short_description = "Question Language"
    
    def db_language_display(self, obj):
        """Display database language with proper labeling"""  
        return obj.db_language or "Not set"
    db_language_display.short_description = "Database Language"
    
    def lsh_similar_columns_display(self, obj):
        """Display LSH similar columns in a collapsible section"""
        if not obj.lsh_similar_columns:
            return "-"
        
        try:
            if isinstance(obj.lsh_similar_columns, str):
                data = json.loads(obj.lsh_similar_columns)
            else:
                data = obj.lsh_similar_columns
            
            # Create collapsible container using Django admin styling with proper theme support
            html_content = '<details style="border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 4px; padding: 8px; margin: 5px 0; background-color: var(--darkened-bg, #f9f9f9);">'
            html_content += '<summary style="cursor: pointer; font-weight: bold; padding: 5px; color: var(--body-fg, #333);">LSH Similar Columns (click to expand)</summary>'
            html_content += '<div style="margin-top: 10px;">'
            html_content += format_html(
                '<pre class="readonly" style="font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: auto; background: var(--body-bg, #ffffff); color: var(--body-fg, #333); padding: 10px; border: 1px solid var(--hairline-color, #e0e0e0); border-radius: 3px; margin: 0;">{}</pre>',
                json.dumps(data, indent=2, ensure_ascii=False)
            )
            html_content += '</div>'
            html_content += '</details>'
            return mark_safe(html_content)
        except:
            return str(obj.lsh_similar_columns)[:200] + "..."
    lsh_similar_columns_display.short_description = "LSH Similar Columns"
    
    def gold_sql_extracted_display(self, obj):
        """Display gold SQL extracted from vector DB"""
        if not obj.gold_sql_extracted:
            return "-"
        try:
            if isinstance(obj.gold_sql_extracted, str):
                data = json.loads(obj.gold_sql_extracted)
            else:
                data = obj.gold_sql_extracted
            
            html = '<div style="max-height: 300px; overflow-y: auto;">'
            for i, item in enumerate(data[:5]):  # Show max 5 items
                html += f'<div style="margin: 10px 0; padding: 10px; border-left: 3px solid #28a745;">'
                html += f'<strong>Example {i+1}:</strong><br>'
                html += f'<em>Q:</em> {item.get("question", "N/A")}<br>'
                html += f'<code style="background: #f8f9fa; padding: 5px;">{item.get("sql", "N/A")}</code>'
                html += '</div>'
            if len(data) > 5:
                html += f'<div style="text-align: center; color: #666;">... and {len(data) - 5} more examples</div>'
            html += '</div>'
            return mark_safe(html)
        except:
            return str(obj.gold_sql_extracted)[:200] + "..."
    gold_sql_extracted_display.short_description = "Gold SQL Examples"
    
    def reduced_tests_display(self, obj):
        """Display reduced tests if available"""
        if not obj.reduced_tests:
            return "-"
        try:
            if isinstance(obj.reduced_tests, str):
                data = json.loads(obj.reduced_tests)
            else:
                data = obj.reduced_tests
            return format_html('<pre style="font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto;">{}</pre>', 
                             json.dumps(data, indent=2, ensure_ascii=False))
        except:
            return str(obj.reduced_tests)[:200] + "..."
    reduced_tests_display.short_description = "Reduced Tests"

    
    def process_end_time_display(self, obj):
        """Display process end time"""
        if obj.process_end_time:
            return timezone.localtime(obj.process_end_time).strftime("%Y-%m-%d %H:%M:%S")
        return "-"
    process_end_time_display.short_description = "Process End Time"
    
    class Media:
        css = {
            'all': ('admin/css/custom_thothlog.css',)
        }
