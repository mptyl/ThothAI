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

# New plugin-based imports
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)  # Added get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)  # Added for CBV authentication
from django.contrib.auth.decorators import (
    login_required,
)  # Added for FBV authentication

# Import new vector store plugin architecture
from thoth_qdrant import SqlDocument, ColumnNameDocument, EvidenceDocument

# Import the custom decorators for Editor group permission checking
from .decorators import require_editor_group

# Import SqlDocument along with others
from .forms import EvidenceForm, SqlDocumentForm, ColumnForm  # Import the new forms

# Import Http404 for error handling if evidence not found
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.conf import settings

# Import decorators for restricting HTTP methods
from django.views.decorators.http import require_http_methods, require_POST

# Import reverse for redirecting
from django.urls import reverse

# Import messages framework (optional, for user feedback)
from django.contrib import messages

# Import vector store utility
from .backend_utils.vector_store_utils import (
    get_vector_store,
    export_evidence_to_csv_file,
    export_columns_to_csv_file,
    export_questions_to_csv_file,
    import_evidence_from_csv_file,
    import_columns_from_csv_file,
    import_questions_from_csv_file,
    delete_all_evidence_from_vector_store,
    delete_all_columns_from_vector_store,
    delete_all_questions_from_vector_store,
)
from .backend_utils.session_utils import get_current_workspace
import os
import logging
import re
import csv
from io import BytesIO
# Vector store handled by thoth-qdrant library

from thoth_core.models import Workspace
from thoth_ai_backend.preprocessing.upload_evidence import upload_evidence_to_vectordb
from thoth_ai_backend.preprocessing.upload_questions import upload_questions_to_vectordb
from .preprocessing.update_database_columns_direct import (
    update_database_columns_description,
)
from .async_tasks import run_preprocessing_task
import threading
from django.http import JsonResponse
from .mermaid_utils import get_erd_display_image, generate_erd_pdf
from thoth_core.thoth_ai.thoth_workflow.gdpr_scanner import generate_gdpr_html
from thoth_core.utils.documentation_translations import get_translations_for_language

logger = logging.getLogger(__name__)


class DbDocsView(LoginRequiredMixin, TemplateView):
    template_name = "db_docs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Get current workspace
            workspace = get_current_workspace(self.request)
            if not workspace or not workspace.sql_db:
                context["error"] = "No workspace or database selected"
                context["doc_content"] = None
                return context

            # Get database name and language
            db_name = workspace.sql_db.name
            language = workspace.sql_db.language or "en"
            context["db_name"] = db_name

            # Get translations for the database language
            translations = get_translations_for_language(language)

            # Format strings that need variable substitution
            no_documentation_message = translations.get('no_documentation_message',
                "Documentation has not been generated yet for database '{db_name}'.").format(db_name=db_name)

            # Format search results template for JavaScript
            search_results_current_template = translations.get('search_results_current', '{current} of {total}')

            # Format instructions with database name
            generate_instructions = [
                instruction.format(db_name=db_name)
                for instruction in translations.get('generate_instructions', [
                    "Go to the Django Admin panel",
                    "Navigate to SQL Databases",
                    "Select your database ({db_name})",
                    "Choose \"Generate database documentation (AI assisted)\" from the actions dropdown"
                ])
            ]

            # Add translation context to template
            context.update({
                'language': language,
                'page_title': translations.get('page_title', 'Database Documentation'),
                'sub_title': translations.get('page_subtitle', 'Documentation'),
                'search_placeholder': translations.get('search_placeholder', 'Search in documentation...'),
                'search_clear_title': translations.get('search_clear_title', 'Clear search'),
                'search_results_none': translations.get('search_results_none', 'No results'),
                'search_results_current': search_results_current_template,
                'search_help': translations.get('search_help', 'Press <kbd>Enter</kbd> for next, <kbd>Shift+Enter</kbd> for previous, <kbd>Esc</kbd> to clear'),
                'export_pdf': translations.get('export_pdf', '📄 Export PDF'),
                'no_documentation_available': translations.get('no_documentation_available', 'No Documentation Available'),
                'no_documentation_message': no_documentation_message,
                'no_database_selected': translations.get('no_database_selected', 'Please select a workspace with a database to view documentation.'),
                'generate_instructions_title': translations.get('generate_instructions_title', 'To generate documentation:'),
                'generate_instructions': generate_instructions,
                'go_to_database_admin': translations.get('go_to_database_admin', '📊 Go to Database Admin'),
                'go_to_home': translations.get('go_to_home', '📁 Go to Home'),
            })

            # Construct path to documentation HTML file
            from thoth_core.utilities.utils import get_exports_directory

            exports_dir = get_exports_directory()
            doc_path = os.path.join(
                settings.BASE_DIR, exports_dir, db_name, f"{db_name}_documentation.html"
            )

            # Check if documentation exists
            if os.path.exists(doc_path):
                try:
                    with open(doc_path, "r", encoding="utf-8") as f:
                        context["doc_content"] = f.read()
                    context["doc_exists"] = True
                except Exception as e:
                    logger.error(
                        f"Error reading documentation file: {e}", exc_info=True
                    )
                    context["error"] = f"Error reading documentation file: {str(e)}"
                    context["doc_content"] = None
                    context["doc_exists"] = False
            else:
                context["doc_exists"] = False
                context["doc_content"] = None
                context["info"] = (
                    f"Documentation has not been generated yet for database '{db_name}'."
                )

        except Exception as e:
            logger.error(f"Error in DbDocsView: {e}", exc_info=True)
            context["error"] = f"An error occurred: {str(e)}"
            context["doc_content"] = None
            context["doc_exists"] = False

        return context


class GdprReportView(LoginRequiredMixin, TemplateView):
    template_name = "gdpr_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Get current workspace
            workspace = get_current_workspace(self.request)
            if not workspace or not workspace.sql_db:
                context["error"] = "No workspace or database selected"
                context["report_content"] = None
                context["report_exists"] = False
                return context

            sql_db = workspace.sql_db
            context["db_name"] = sql_db.name

            # Check if GDPR report exists
            if sql_db.gdpr_report:
                # Generate HTML content from the report
                report_html = generate_gdpr_html(sql_db.gdpr_report)
                context["report_content"] = report_html
                context["report_exists"] = True
                context["scan_date"] = sql_db.gdpr_scan_date

                # Extract risk information for context
                risk_info = sql_db.gdpr_report.get("risk_score", {})
                context["risk_level"] = risk_info.get("level", "UNKNOWN")
                context["risk_score"] = risk_info.get("score", 0)
            else:
                context["report_content"] = None
                context["report_exists"] = False
                context["info"] = (
                    f"GDPR compliance scan has not been performed yet for database '{sql_db.name}'."
                )

        except Exception as e:
            logger.error(f"Error in GdprReportView: {e}", exc_info=True)
            context["error"] = f"An error occurred: {str(e)}"
            context["report_content"] = None
            context["report_exists"] = False

        return context


class ErdView(LoginRequiredMixin, TemplateView):
    template_name = "erd.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Get current workspace
            workspace = get_current_workspace(self.request)
            if not workspace or not workspace.sql_db:
                context["error"] = "No workspace or database selected"
                context["erd_image_path"] = None
                return context

            # Get database and ERD content
            sql_db = workspace.sql_db
            db_name = sql_db.name
            context["db_name"] = db_name

            # Check if ERD exists
            if not sql_db.erd or not sql_db.erd.strip():
                context["erd_exists"] = False
                context["erd_image_path"] = None
                context["info"] = (
                    f"ERD diagram has not been generated yet for database '{db_name}'. Please generate database documentation first."
                )
                return context

            # Generate SVG image for display using original ERD format
            success, image_path, error_msg = get_erd_display_image(sql_db.erd)

            if success and image_path:
                # Read SVG content for inline display
                try:
                    with open(image_path, "r", encoding="utf-8") as f:
                        svg_content = f.read()
                    context["erd_exists"] = True
                    context["svg_content"] = svg_content
                    context["erd_image_path"] = image_path

                    # Clean up temporary file
                    try:
                        os.unlink(image_path)
                    except Exception:
                        pass

                except Exception as e:
                    logger.error(f"Error reading ERD SVG file: {e}")
                    context["error"] = f"Error reading generated ERD image: {str(e)}"
                    context["erd_exists"] = False
                    context["erd_image_path"] = None
            else:
                context["error"] = error_msg or "Failed to generate ERD image"
                context["erd_exists"] = False
                context["erd_image_path"] = None

        except Exception as e:
            logger.error(f"Error in ErdView: {e}", exc_info=True)
            context["error"] = f"An error occurred: {str(e)}"
            context["erd_exists"] = False
            context["erd_image_path"] = None

        return context


class QuestionsView(LoginRequiredMixin, TemplateView):
    template_name = "questions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Try to get the vector store for the current workspace
            try:
                vector_store = get_vector_store(self.request)
                sql_documents = vector_store.get_all_sql_documents()

                # Transform SQL documents into a list of dictionaries for the template
                questions = []
                for doc in sql_documents:
                    if isinstance(doc, SqlDocument):
                        questions.append(
                            {
                                "id": getattr(
                                    doc, "id", None
                                ),  # Include id if available and needed
                                "question": doc.question,
                                "sql": doc.sql,
                                "evidence": doc.evidence,
                            }
                        )
                context["questions"] = questions

            except ValueError as e:
                # Log the error
                logger.error(f"Error reading Vector Store: {e}", exc_info=True)
                # Add error message to context
                context["error"] = f"Error reading Vectore Store: {e}"
                context["questions"] = []
        except Exception as e:
            # Log the error
            logger.error(f"Error fetching questions: {e}", exc_info=True)
            # Add error message to context
            context["error"] = f"Error fetching questions: {e}"
            context["questions"] = []

        return context


class ColumnsView(LoginRequiredMixin, TemplateView):
    template_name = "columns.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Try to get the vector store for the current workspace
            try:
                vector_store = get_vector_store(self.request)

                workspace = get_current_workspace(self.request)

                # Get columns from the vector store
                column_documents = vector_store.get_all_column_documents()

                # Transform documents into a list of dictionaries for the template
                columns = []
                for doc in column_documents:
                    if isinstance(doc, ColumnNameDocument):
                        # Ensure the ID attribute from the vector store document is included
                        columns.append(
                            {
                                "id": doc.id,  # Access the id attribute directly
                                "table_name": doc.table_name,
                                "original_column_name": doc.original_column_name,
                                "column_description": doc.column_description,
                                "value_description": doc.value_description,
                                # Add other fields if needed for the list template (columns.html)
                            }
                        )

                context["columns"] = columns

            except ValueError as e:
                # If no workspace found in session, provide empty columns
                logger.warning(f"No workspace found in session: {e}")
                context["columns"] = []
        except Exception as e:
            # Log the error
            logger.error(f"Error fetching columns: {e}", exc_info=True)
            # Add error message to context
            context["error"] = f"Error fetching columns: {e}"
            context["columns"] = []

        return context


class EvidenceView(LoginRequiredMixin, TemplateView):
    template_name = "evidence.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Try to get the vector store for the current workspace
            try:
                vector_store = get_vector_store(self.request)

                workspace = get_current_workspace(self.request)

                evidence_documents = vector_store.get_all_evidence_documents()

                # Transform evidence documents into a list of dictionaries for the template
                evidence_list = []
                for doc in evidence_documents:
                    if isinstance(doc, EvidenceDocument):
                        evidence_list.append(
                            {
                                "id": doc.id,  # Include id in case it's needed later
                                "evidence": doc.evidence,
                            }
                        )

                context["evidence_list"] = evidence_list

            except ValueError as e:
                # If no workspace found in session, provide empty evidence
                logger.warning(f"No workspace found in session: {e}")
                context["evidence_list"] = []
        except Exception as e:
            # Log the error
            logger.error(f"Error fetching evidence: {e}", exc_info=True)
            # Add error message to context
            context["error"] = f"Error fetching evidence: {e}"
            context["evidence_list"] = []

        return context


class PreprocessView(LoginRequiredMixin, TemplateView):
    template_name = "preprocess.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Try to get the vector store for the current workspace
            try:
                vector_store = get_vector_store(self.request)
                workspace = get_current_workspace(self.request)
                db = workspace.sql_db

                # Add data to context
                context["vector_store"] = vector_store
                context["workspace"] = workspace
                context["db"] = db

                # Add additional information that might be useful for the template
                context["db_name"] = db.db_name if db else "No database found"
                context["workspace_name"] = (
                    workspace.name if workspace else "No workspace found"
                )
                context["vector_store_type"] = (
                    type(vector_store).__name__
                    if vector_store
                    else "No vector store found"
                )
                context["last_preprocess"] = (
                    workspace.last_preprocess if workspace else None
                )
                context["last_evidence_load"] = (
                    workspace.last_evidence_load if workspace else None
                )
                context["last_sql_loaded"] = (
                    workspace.last_sql_loaded if workspace else None
                )

                # Add collection name if available
                if workspace and workspace.sql_db and workspace.sql_db.vector_db and workspace.sql_db.vector_db.name:
                    context["collection_name"] = workspace.sql_db.vector_db.name
                else:
                    context["collection_name"] = "Unknown"

            except ValueError as e:
                logger.error(f"Error fetching workspace: {e}", exc_info=True)
                # Add error message to context
                context["error"] = f"Error fetching workspace data: {e}"

        except Exception as e:
            # Log the error
            logger.error(f"Error in PreprocessView: {e}", exc_info=True)
            # Add error message to context
            context["error"] = f"Error in preprocessing view: {e}"

        return context


@login_required
def view_columns(request, column_id):
    """
    Displays the details of a specific ColumnNameDocument from the vector store.
    """
    try:
        vector_store = get_vector_store(request)
        column = vector_store.get_columns_document_by_id(column_id)

        if not column or not isinstance(column, ColumnNameDocument):
            raise Http404("Column document not found in vector store.")

        # Create a form instance with the column data (for display only)
        form = ColumnForm(
            initial={
                "table_name": column.table_name,
                "original_column_name": column.original_column_name,
                "column_name": getattr(column, "column_name", ""),
                "column_description": column.column_description,
                "value_description": column.value_description,
            }
        )

        # Make the form read-only since this is a view page
        for field in form.fields.values():
            field.widget.attrs["readonly"] = True
            field.widget.attrs["disabled"] = "disabled"

        context = {
            "column": column,
            "form": form,
        }

        return render(request, "view_columns.html", context)

    except Exception as e:
        logger.error(f"Error fetching column document {column_id}: {e}", exc_info=True)
        messages.error(
            request, f"Error accessing vector database or finding column: {e}"
        )
        # Redirect to the main columns list view on error
        return redirect("thoth_ai_backend:columns")


# CRUD Views for EvidenceDocument
@login_required
@require_editor_group
def manage_evidence(request, evidence_id=None):
    """
    View to handle creating a new evidence or updating an existing one.
    """
    try:
        # Get the vector store for the current workspace
        vector_store = get_vector_store(request)
        instance = None
        if evidence_id:
            # Update case: Try to fetch the existing evidence document directly by ID
            try:
                # Use the specific method to get the evidence document by its ID
                instance = vector_store.get_evidence_document_by_id(evidence_id)
                if not instance:
                    logger.warning(f"Evidence with ID {evidence_id} not found.")
                    raise Http404("Evidence not found")
                # Ensure the fetched document is actually a EvidenceDocument (optional, depends on method guarantees)
                if not isinstance(instance, EvidenceDocument):
                    logger.error(
                        f"Document found for ID {evidence_id} is not a EvidenceDocument."
                    )
                    raise Http404("Invalid document type found for evidence ID")
            except Http404:  # Re-raise Http404 specifically if caught below
                raise
            except Exception as e:
                # Catch other potential errors during fetch (e.g., connection issues)
                logger.error(
                    f"Error fetching evidence {evidence_id}: {e}", exc_info=True
                )
                raise Http404(
                    "Error fetching evidence"
                )  # Raise Http404 for consistency on failure
    except Exception as e:
        logger.error(f"Error getting vector store: {e}", exc_info=True)
        messages.error(request, f"Error accessing vector database: {e}")
        return redirect("thoth_ai_backend:evidence")

    if request.method == "POST":
        form = EvidenceForm(
            request.POST
        )  # Pass initial data for update if needed, but POST overrides
        if form.is_valid():
            evidence_text = form.cleaned_data["text"]
            try:
                if instance:  # Update existing evidence
                    # Update the evidence text
                    instance.evidence = evidence_text
                    # Assuming an update method exists in the vector store
                    # vector_store.update_evidence(instance)
                    # If update_evidence doesn't exist, we might need delete + add
                    # This depends heavily on the vector store implementation.
                    # Let's assume delete + add for now if update isn't directly supported
                    vector_store.delete_document(
                        instance.id
                    )  # Assuming delete_evidence exists
                    vector_store.add_evidence(
                        EvidenceDocument(id=instance.id, evidence=evidence_text)
                    )  # Re-add with same ID if possible, or let it generate new
                    logger.info(f"Evidence {instance.id} updated.")
                else:  # Create new evidence
                    new_evidence_doc = EvidenceDocument(evidence=evidence_text)
                    vector_store.add_evidence(new_evidence_doc)
                    logger.info("New evidence created.")

                return redirect("thoth_ai_backend:evidence")  # Redirect after success

            except Exception as e:
                # Log the error e
                logger.error(
                    f"Error saving evidence (ID: {evidence_id}): {e}", exc_info=True
                )
                # Add error to form or context if needed
                form.add_error(
                    None, f"An error occurred while saving the evidence. {e}"
                )  # Generic error

    else:  # GET request
        if instance:  # Populate form for update
            form = EvidenceForm(initial={"text": instance.evidence})
        else:  # Empty form for create
            form = EvidenceForm()

    # Render the template for GET or POST with errors
    # We'll rename 'add_evidence.html' to 'manage_evidence.html' later
    context = {
        "form": form,
        "evidence_id": evidence_id,  # Pass evidence_id to template to adjust UI (e.g., button text)
    }
    return render(request, "manage_evidence.html", context)  # Use a new template name


@login_required
@require_editor_group
@require_http_methods(["GET"])
def confirm_delete_evidence(request, evidence_id):
    """
    Displays a confirmation page before deleting an evidence.
    """
    try:
        # Get the vector store for the current workspace
        vector_store = get_vector_store(request)
        try:
            evidence = vector_store.get_evidence_document_by_id(evidence_id)
            if not evidence:
                raise Http404("Evidence not found")
            if not isinstance(evidence, EvidenceDocument):
                raise Http404("Invalid document type found for evidence ID")

        except Exception as e:
            logger.error(
                f"Error fetching evidence {evidence_id} for deletion confirmation: {e}",
                exc_info=True,
            )
            messages.error(request, "Error finding the evidence to delete.")
            return redirect("thoth_ai_backend:evidence")

        context = {"evidence": evidence}
        return render(request, "confirm_delete_evidence.html", context)
    except Exception as e:
        logger.error(f"Error getting vector store: {e}", exc_info=True)
        messages.error(request, f"Error accessing vector database: {e}")
        return redirect("thoth_ai_backend:evidence")


@login_required
@require_editor_group
@require_http_methods(["POST"])
def delete_evidence_confirmed(request, evidence_id):
    """
    Handles the actual deletion of an evidence after confirmation.
    """
    try:
        # Get the vector store for the current workspace
        vector_store = get_vector_store(request)
        try:
            # Optional: Verify evidence exists before attempting delete, though delete_document might handle not found gracefully
            # evidence = vector_store.get_evidence_document_by_id(evidence_id)
            # if not evidence:
            #     raise Http404("Evidence not found")

            vector_store.delete_document(evidence_id)
            messages.success(
                request, "Evidence successfully deleted."
            )  # Optional user feedback
            logger.info(f"Evidence {evidence_id} deleted successfully.")  # Logging

        except Exception as e:
            logger.error(f"Error deleting evidence {evidence_id}: {e}", exc_info=True)
            messages.error(
                request, "An error occurred while deleting the evidence."
            )  # Optional user feedback
    except Exception as e:
        logger.error(f"Error getting vector store: {e}", exc_info=True)
        messages.error(request, f"Error accessing vector database: {e}")

    # Redirect back to the evidence list regardless of success/error for simplicity here
    # In a real app, you might handle errors differently
    return HttpResponseRedirect(reverse("thoth_ai_backend:evidence"))


# CRUD Views for SqlDocument (Questions)


@login_required
@require_editor_group
def manage_question(request, question_id=None):
    """
    View to handle creating a new question or updating an existing one.
    """
    try:
        # Get the vector store for the current workspace
        vector_store = get_vector_store(request)
        instance = None
        if question_id:
            # Update case: Try to fetch the existing question document by ID
            try:
                instance = vector_store.get_sql_document_by_id(question_id)
                if not instance:
                    logger.warning(f"SqlDocument with ID {question_id} not found.")
                    raise Http404("Question not found")
                if not isinstance(instance, SqlDocument):
                    logger.error(
                        f"Document found for ID {question_id} is not a SqlDocument."
                    )
                    raise Http404("Invalid document type found for question ID")
            except Http404:
                raise
            except Exception as e:
                logger.error(
                    f"Error fetching question {question_id}: {e}", exc_info=True
                )
                raise Http404("Error fetching question")
    except Exception as e:
        logger.error(f"Error getting vector store: {e}", exc_info=True)
        messages.error(request, f"Error accessing vector database: {e}")
        return redirect("thoth_ai_backend:questions")

    if request.method == "POST":
        form = SqlDocumentForm(request.POST)
        if form.is_valid():
            question_text = form.cleaned_data["question"]
            sql_query = form.cleaned_data["sql"]
            evidence_text = form.cleaned_data["evidence"]
            try:
                if instance:  # Update existing question
                    instance.question = question_text
                    instance.sql = sql_query
                    instance.evidence = evidence_text
                    # Use explicit delete + add pattern, mirroring manage_evidence/manage_doc
                    vector_store.delete_document(instance.id)
                    vector_store.add_sql(
                        SqlDocument(
                            id=instance.id,
                            question=question_text,
                            sql=sql_query,
                            evidence=evidence_text,
                        )
                    )
                    messages.success(request, "Question updated successfully.")
                    logger.info(f"Question {instance.id} updated.")
                else:  # Create new question
                    new_question = SqlDocument(
                        question=question_text, sql=sql_query, evidence=evidence_text
                    )
                    vector_store.add_sql(new_question)
                    messages.success(request, "Question created successfully.")
                    logger.info("New question created.")

                return redirect(
                    "thoth_ai_backend:questions"
                )  # Redirect to the questions list view

            except Exception as e:
                logger.error(
                    f"Error saving question (ID: {question_id}): {e}", exc_info=True
                )
                messages.error(
                    request, f"An error occurred while saving the question: {e}"
                )
                form.add_error(
                    None, f"An error occurred while saving the question. {e}"
                )

    else:  # GET request
        if instance:  # Populate form for update
            form = SqlDocumentForm(
                initial={
                    "question": instance.question,
                    "sql": instance.sql,
                    "evidence": instance.evidence,
                }
            )
        else:  # Empty form for create
            form = SqlDocumentForm()

    context = {
        "form": form,
        "question_id": question_id,  # Pass question_id to template
    }
    # Need to create 'manage_question.html' template
    return render(request, "manage_question.html", context)


@login_required
@require_editor_group
@require_http_methods(["GET"])
def confirm_delete_question(request, question_id):
    """
    Displays a confirmation page before deleting a question.
    """
    try:
        # Get the vector store for the current workspace
        vector_store = get_vector_store(request)
        try:
            question = vector_store.get_sql_document_by_id(question_id)
            if not question:
                raise Http404("Question not found")
            if not isinstance(question, SqlDocument):
                raise Http404("Invalid document type found for question ID")

        except Exception as e:
            logger.error(
                f"Error fetching question {question_id} for deletion confirmation: {e}",
                exc_info=True,
            )
            messages.error(request, "Error finding the question to delete.")
            return redirect("thoth_ai_backend:questions")  # Redirect back if error

        context = {"question": question}
        # Need to create 'confirm_delete_question.html' template
        return render(request, "confirm_delete_question.html", context)
    except Exception as e:
        logger.error(f"Error getting vector store: {e}", exc_info=True)
        messages.error(request, f"Error accessing vector database: {e}")
        return redirect("thoth_ai_backend:questions")


@login_required
@require_editor_group
@require_http_methods(["POST"])
def delete_question_confirmed(request, question_id):
    """
    Handles the actual deletion of a question after confirmation.
    """
    try:
        # Get the vector store for the current workspace
        vector_store = get_vector_store(request)
        try:
            vector_store.delete_document(question_id)  # Assuming generic delete works
            messages.success(request, "Question successfully deleted.")
            logger.info(f"Question {question_id} deleted successfully.")  # Logging

        except Exception as e:
            logger.error(f"Error deleting question {question_id}: {e}", exc_info=True)
            messages.error(request, "An error occurred while deleting the question.")
    except Exception as e:
        logger.error(f"Error getting vector store: {e}", exc_info=True)
        messages.error(request, f"Error accessing vector database: {e}")

    return HttpResponseRedirect(
        reverse("thoth_ai_backend:questions")
    )  # Redirect to questions list


@login_required
@require_http_methods(["POST"])
def run_preprocessing(request, workspace_id):
    """
    Starts the preprocessing task in a background thread and returns a polling template.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)

    # Prevent starting a new task if one is already running
    if workspace.preprocessing_status == Workspace.PreprocessingStatus.RUNNING:
        messages.warning(
            request, "A preprocessing task is already running for this workspace."
        )
        # Return the polling template to continue monitoring the existing task
        return render(
            request,
            "partials/preprocessing_polling.html",
            {
                "workspace": workspace,
                "hx_indicator_id": "spinner",
                "spinner_text": "Preprocessing already in progress...",
            },
        )

    # Start the background task
    task = threading.Thread(target=run_preprocessing_task, args=(workspace.id,))
    task.start()

    # Update workspace status
    workspace.preprocessing_status = Workspace.PreprocessingStatus.RUNNING
    workspace.task_id = str(task.ident)  # Store thread identifier
    workspace.save()

    # Return the polling template to the user with improved UI
    return render(
        request,
        "partials/preprocessing_progress.html",
        {
            "workspace": workspace,
            "container_id": "preprocessing-container",
            "show_progress": True,
            "total_items": 0,  # Will be updated when progress starts
            "processed_items": 0,
            "progress_percentage": 0,
            "spinner_text": "Preprocessing started... Counting items to process...",
        },
    )


@login_required
@require_http_methods(["GET"])
def check_preprocessing_status(request, workspace_id):
    """
    Checks the status of the preprocessing task and returns the appropriate template.
    """
    from thoth_ai_backend.utils.progress_tracker import ProgressTracker

    workspace = get_object_or_404(Workspace, id=workspace_id)
    status = workspace.preprocessing_status

    # Get progress information from cache
    progress = ProgressTracker.get_progress(workspace_id, "preprocessing")

    if status == Workspace.PreprocessingStatus.RUNNING:
        # Task is still running, show progress if available
        if progress:
            # Return progress bar template
            context = {
                "workspace": workspace,
                "container_id": "preprocessing-container",
                "show_progress": True,
                "total_items": progress.get("total_items", 0),
                "processed_items": progress.get("processed_items", 0),
                "progress_percentage": progress.get("percentage", 0),
                "spinner_text": f"Preprocessing in progress... ({progress.get('processed_items', 0)}/{progress.get('total_items', 0)})",
            }
            return render(request, "partials/preprocessing_progress.html", context)
        else:
            # No progress data yet, show regular polling template
            return render(
                request,
                "partials/preprocessing_polling.html",
                {
                    "workspace": workspace,
                    "hx_indicator_id": "spinner",
                    "spinner_text": "Preprocessing in progress...",
                },
            )
    else:
        # Task is completed or failed, return the final status button
        context = {
            "container_id": "preprocessing-container",
            "hx_url": reverse(
                "thoth_ai_backend:run_preprocessing", args=[workspace.id]
            ),
            "hx_indicator_id": "spinner",
            "button_text": "Run Preprocessing",
            "last_run_text": "Last run on",
            "never_run_text": "Never run",
            "spinner_text": "Processing in progress...",
            "icon_class": "mdi mdi-refresh",
            "workspace": workspace,
            "last_run": workspace.last_preprocess,
        }
        if status == Workspace.PreprocessingStatus.COMPLETED:
            if progress:
                context["success_message"] = (
                    f"Preprocessing completed successfully! Processed {progress.get('successful_items', 0)} items."
                )
                # Clear progress after completion
                ProgressTracker.clear_progress(workspace_id, "preprocessing")
            else:
                context["success_message"] = workspace.last_preprocess_log
        elif status == Workspace.PreprocessingStatus.FAILED:
            context["error_message"] = workspace.last_preprocess_log
            # Clear progress on failure too
            if progress:
                ProgressTracker.clear_progress(workspace_id, "preprocessing")

        # Reset status to IDLE so it can be run again
        workspace.preprocessing_status = Workspace.PreprocessingStatus.IDLE
        workspace.save()

        return render(request, "partials/operation_status_button_simple.html", context)


@login_required
@require_POST
def upload_evidences(request, workspace_id):
    """
    View function to handle the HTMX request for uploading evidence to the vector database.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    context = {
        "container_id": "evidence-container",
        "hx_url": reverse("thoth_ai_backend:upload_evidences", args=[workspace.id]),
        "hx_indicator_id": "evidence-spinner",
        "button_text": "Load Evidence",
        "last_run_text": "Last upload on",
        "never_run_text": "Evidence not yet uploaded",
        "spinner_text": "Uploading evidence...",
        "icon_class": "mdi mdi-database-refresh",
        "workspace": workspace,
        "last_run": workspace.last_evidence_load,
    }

    try:
        successful_uploads, total_items = upload_evidence_to_vectordb(workspace_id)
        workspace.refresh_from_db()

        if successful_uploads > 0:
            context["success_message"] = (
                f"Successfully uploaded {successful_uploads} of {total_items} evidence items."
            )
            context["total_items"] = total_items
            context["successful_uploads"] = successful_uploads
        else:
            context["special_message"] = "No new evidence was found to upload."

        context["last_run"] = workspace.last_evidence_load

    except (ValueError, IOError) as e:
        logger.error(
            f"Error uploading evidence for workspace {workspace_id}: {e}", exc_info=True
        )
        context["error_message"] = str(e)
    except Exception as e:
        logger.error(
            f"Unexpected error uploading evidence for workspace {workspace_id}: {e}",
            exc_info=True,
        )
        context["error_message"] = f"An unexpected error occurred: {e}"

    return render(request, "partials/operation_status_button_simple.html", context)


@login_required
@require_POST
def upload_questions(request, workspace_id):
    """
    View function to handle the HTMX request for uploading questions to the vector database.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    context = {
        "container_id": "questions-container",
        "hx_url": reverse("thoth_ai_backend:upload_questions", args=[workspace.id]),
        "hx_indicator_id": "questions-spinner",
        "button_text": "Load Questions",
        "last_run_text": "Last upload on",
        "never_run_text": "Questions not yet uploaded",
        "spinner_text": "Uploading questions...",
        "icon_class": "mdi mdi-database-refresh",
        "workspace": workspace,
        "last_run": workspace.last_sql_loaded,
    }

    try:
        successful_uploads, total_items = upload_questions_to_vectordb(workspace_id)
        workspace.refresh_from_db()

        if successful_uploads > 0:
            context["success_message"] = (
                f"Successfully uploaded {successful_uploads} of {total_items} questions."
            )
            context["total_items"] = total_items
            context["successful_uploads"] = successful_uploads
        else:
            context["special_message"] = "No new questions were found to upload."

        context["last_run"] = workspace.last_sql_loaded

    except (ValueError, IOError) as e:
        logger.error(
            f"Error uploading questions for workspace {workspace_id}: {e}",
            exc_info=True,
        )
        context["error_message"] = str(e)
    except Exception as e:
        logger.error(
            f"Unexpected error uploading questions for workspace {workspace_id}: {e}",
            exc_info=True,
        )
        context["error_message"] = f"An unexpected error occurred: {e}"

    return render(request, "partials/operation_status_button_simple.html", context)


@login_required
@require_POST
def update_database_columns(request, workspace_id):
    """
    View to handle the HTMX request for updating database columns.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    context = {
        "container_id": "update-columns-container",
        "hx_url": reverse(
            "thoth_ai_backend:update_database_columns", args=[workspace.id]
        ),
        "hx_indicator_id": "columns-spinner",
        "button_text": "Update Columns Descriptions",
        "last_run_text": "Last update on",
        "never_run_text": "Columns not yet updated",
        "spinner_text": "Updating columns...",
        "icon_class": "mdi mdi-database-refresh",
        "workspace": workspace,
        "db": workspace.sql_db,
        "last_run": workspace.sql_db.last_columns_update if workspace.sql_db else None,
    }

    try:
        if not workspace.sql_db:
            raise ValueError(
                f"Workspace '{workspace.name}' has no SQL database configured."
            )

        update_database_columns_description(workspace_id=workspace_id)

        workspace.refresh_from_db()

        context["success_message"] = "Database columns updated successfully!"
        context["db"] = workspace.sql_db
        context["last_run"] = workspace.sql_db.last_columns_update

    except Exception as e:
        logger.error(
            f"Error updating database columns for workspace {workspace_id}: {e}",
            exc_info=True,
        )
        context["error_message"] = str(e)

    return render(request, "partials/operation_status_button.html", context)


# Initialize logger for this module if not already done globally
@login_required
def export_evidence_csv(request):
    try:
        vector_store = get_vector_store(request)

        # Call the utility function to handle file saving and get CSV content
        # Pass the request parameter for new path resolution
        saved_filepath, csv_content = export_evidence_to_csv_file(vector_store, request)

        # Prepare HTTP response for download
        response = HttpResponse(csv_content, content_type="text/csv")
        # Filename for download, no timestamp as per requirement
        response["Content-Disposition"] = 'attachment; filename="evidence_export.csv"'

        messages.success(
            request,
            f"Evidence exported successfully. Saved on server at: {saved_filepath}. Download started.",
        )
        return response

    except Exception as e:
        logger.error(f"Error in export_evidence_csv view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while exporting evidence: {e}")
        return HttpResponseRedirect(reverse("thoth_ai_backend:evidence"))


@login_required
def export_columns_csv(request):
    try:
        vector_store = get_vector_store(request)

        # Pass the request parameter for new path resolution
        saved_filepath, csv_content = export_columns_to_csv_file(vector_store, request)

        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="columns_export.csv"'

        messages.success(
            request,
            f"Columns exported successfully. Saved on server at: {saved_filepath}. Download started.",
        )
        return response

    except Exception as e:
        logger.error(f"Error in export_columns_csv view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while exporting columns: {e}")
        return HttpResponseRedirect(reverse("thoth_ai_backend:columns"))


@login_required
def export_questions_csv(request):
    try:
        vector_store = get_vector_store(request)

        # Pass the request parameter for new path resolution
        saved_filepath, csv_content = export_questions_to_csv_file(
            vector_store, request
        )

        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="questions_export.csv"'

        messages.success(
            request,
            f"Questions exported successfully. Saved on server at: {saved_filepath}. Download started.",
        )
        return response

    except Exception as e:
        logger.error(f"Error in export_questions_csv view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while exporting questions: {e}")
        return HttpResponseRedirect(reverse("thoth_ai_backend:questions"))


# --- CSV Import Views ---


@login_required
@require_editor_group
@require_POST
def import_evidence_server_csv(request):
    try:
        vector_store = get_vector_store(request)
        # Pass the request parameter for new path resolution
        result = import_evidence_from_csv_file(vector_store, request)

        for msg_type, text in [
            (
                messages.SUCCESS
                if "Successfully" in m
                else messages.ERROR
                if "Error" in m
                else messages.WARNING,
                m,
            )
            for m in result.get("messages", [])
        ]:
            messages.add_message(request, msg_type, text)

    except Exception as e:
        logger.error(f"Error in import_evidence_server_csv view: {e}", exc_info=True)
        messages.error(
            request, f"An unexpected error occurred during evidence import: {e}"
        )
    return HttpResponseRedirect(reverse("thoth_ai_backend:evidence"))


@login_required
@require_editor_group
@require_POST
def import_columns_server_csv(request):
    try:
        vector_store = get_vector_store(request)
        # Pass the request parameter for new path resolution
        result = import_columns_from_csv_file(vector_store, request)

        for msg_type, text in [
            (
                messages.SUCCESS
                if "Successfully" in m
                else messages.ERROR
                if "Error" in m
                else messages.WARNING,
                m,
            )
            for m in result.get("messages", [])
        ]:
            messages.add_message(request, msg_type, text)

    except Exception as e:
        logger.error(f"Error in import_columns_server_csv view: {e}", exc_info=True)
        messages.error(
            request, f"An unexpected error occurred during columns import: {e}"
        )
    return HttpResponseRedirect(reverse("thoth_ai_backend:columns"))


@login_required
@require_editor_group
@require_POST
def import_questions_server_csv(request):
    try:
        vector_store = get_vector_store(request)
        # Pass the request parameter for new path resolution
        result = import_questions_from_csv_file(vector_store, request)

        for msg_type, text in [
            (
                messages.SUCCESS
                if "Successfully" in m
                else messages.ERROR
                if "Error" in m
                else messages.WARNING,
                m,
            )
            for m in result.get("messages", [])
        ]:
            messages.add_message(request, msg_type, text)

    except Exception as e:
        logger.error(f"Error in import_questions_server_csv view: {e}", exc_info=True)
        messages.error(
            request, f"An unexpected error occurred during questions import: {e}"
        )
    return HttpResponseRedirect(reverse("thoth_ai_backend:questions"))


# --- DELETE ALL VIEWS ---


@login_required
@require_editor_group
@require_POST
def delete_all_evidence(request):
    """
    Deletes all evidence from the vector store for the current workspace.
    """
    try:
        vector_store = get_vector_store(request)
        delete_all_evidence_from_vector_store(vector_store)
        messages.success(request, "All evidence has been successfully deleted.")
    except NotImplementedError as e:
        logger.error(
            f"NotImplementedError in delete_all_evidence view: {e}", exc_info=True
        )
        messages.error(
            request,
            f"Could not delete evidence: The delete operation is not implemented correctly. {e}",
        )
    except Exception as e:
        logger.error(f"Error in delete_all_evidence view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while deleting all evidence: {e}")
    return HttpResponseRedirect(reverse("thoth_ai_backend:evidence"))


@login_required
@require_editor_group
@require_POST
def delete_all_columns(request):
    """
    Deletes all columns from the vector store for the current workspace.
    """
    try:
        vector_store = get_vector_store(request)
        delete_all_columns_from_vector_store(vector_store)
        messages.success(request, "All columns have been successfully deleted.")
    except NotImplementedError as e:
        logger.error(
            f"NotImplementedError in delete_all_columns view: {e}", exc_info=True
        )
        messages.error(
            request,
            f"Could not delete columns: The delete operation is not implemented correctly. {e}",
        )
    except Exception as e:
        logger.error(f"Error in delete_all_columns view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while deleting all columns: {e}")
    return HttpResponseRedirect(reverse("thoth_ai_backend:columns"))


@login_required
@require_POST
def delete_all_questions(request):
    """
    Deletes all questions from the vector store for the current workspace.
    """
    try:
        vector_store = get_vector_store(request)
        delete_all_questions_from_vector_store(vector_store)
        messages.success(request, "All questions have been successfully deleted.")
    except NotImplementedError as e:
        logger.error(
            f"NotImplementedError in delete_all_questions view: {e}", exc_info=True
        )
        messages.error(
            request,
            f"Could not delete questions: The delete operation is not implemented correctly. {e}",
        )
    except Exception as e:
        logger.error(f"Error in delete_all_questions view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while deleting all questions: {e}")
    return HttpResponseRedirect(reverse("thoth_ai_backend:questions"))


@login_required
def export_pdf(request):
    """
    Export database documentation as PDF using reportlab for better control
    """
    logger.info(f"export_pdf called with GET params: {request.GET}")
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
            PageBreak,
            Image,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from io import BytesIO
        import json

        db_name = request.GET.get("db_name", "database")
        logger.info(f"Processing PDF export for database: {db_name}")

        workspace = get_current_workspace(request)

        if not workspace or not workspace.sql_db:
            logger.error("No active workspace or database found")
            messages.error(request, "No active workspace or database found")
            return redirect("thoth_ai_backend:db_docs")

        # Get database object
        sql_db = workspace.sql_db

        # Create PDF buffer with reduced margins for more content space
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,  # Reduced from 72 to 36 (0.5 inch)
            topMargin=50,
            bottomMargin=36,
        )

        # Container for PDF elements
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        heading1_style = ParagraphStyle(
            "CustomHeading1",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=12,
            spaceBefore=12,
        )
        heading2_style = ParagraphStyle(
            "CustomHeading2",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#34495e"),
            spaceAfter=10,
            spaceBefore=10,
        )
        normal_style = styles["Normal"]
        normal_style.fontSize = 10
        normal_style.leading = 14

        # Title
        elements.append(Paragraph(f"{db_name} Database Documentation", title_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Database Scope
        elements.append(Paragraph("Database Scope", heading1_style))

        if sql_db.scope_json:
            try:
                scope_data = json.loads(sql_db.scope_json)
                for key, value in scope_data.items():
                    # Make title user-friendly
                    friendly_title = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
                    friendly_title = friendly_title.replace("_", " ").title()

                    elements.append(
                        Paragraph(f"<b>{friendly_title}</b>", heading2_style)
                    )
                    elements.append(Paragraph(value, normal_style))
                    elements.append(Spacer(1, 0.1 * inch))
            except json.JSONDecodeError:
                elements.append(Paragraph(sql_db.scope_json, normal_style))
        else:
            elements.append(
                Paragraph("No scope defined for this database.", normal_style)
            )

        elements.append(Spacer(1, 0.3 * inch))

        # Try to add Mermaid diagram if available
        from thoth_core.utilities.utils import get_exports_directory

        io_dir = get_exports_directory()
        erd_path = os.path.join(
            settings.BASE_DIR, io_dir, db_name, f"{db_name}_documentation_erd.png"
        )

        if os.path.exists(erd_path):
            elements.append(Paragraph("Entity Relationship Diagram", heading1_style))
            try:
                # Get image dimensions and scale proportionally
                from PIL import Image as PILImage

                pil_img = PILImage.open(erd_path)
                img_width, img_height = pil_img.size
                aspect_ratio = img_height / img_width

                # Set maximum width to fit page (6 inches) and calculate height
                max_width = 6 * inch
                max_height = 7 * inch  # Leave room for text

                # Calculate scaled dimensions maintaining aspect ratio
                if img_width > 0:
                    display_width = min(max_width, img_width)
                    display_height = display_width * aspect_ratio

                    # If height is too large, scale down based on height
                    if display_height > max_height:
                        display_height = max_height
                        display_width = display_height / aspect_ratio

                    img = Image(erd_path, width=display_width, height=display_height)
                    img.hAlign = "CENTER"
                    elements.append(img)
                    elements.append(Spacer(1, 0.3 * inch))
            except Exception as e:
                logger.warning(f"Could not add ERD image: {e}")

        # Tables and Columns
        elements.append(PageBreak())
        elements.append(Paragraph("Tables and Columns", heading1_style))

        from thoth_core.models import SqlTable, SqlColumn

        tables = SqlTable.objects.filter(sql_db=sql_db).order_by("name")

        for table in tables:
            # Table name
            elements.append(Paragraph(f"Table: <b>{table.name}</b>", heading2_style))

            # Table description
            if table.description or table.generated_comment:
                desc = table.description or table.generated_comment
                elements.append(Paragraph(f"<i>{desc}</i>", normal_style))
                elements.append(Spacer(1, 0.1 * inch))

            # Prepare table data
            table_data = [["Column Name", "Data Type", "Description", "FK"]]

            # Get columns and sort: PK first, then alphabetically
            columns = SqlColumn.objects.filter(sql_table=table)
            pk_columns = []
            other_columns = []

            for column in columns:
                if column.pk_field:
                    pk_columns.append(column)
                else:
                    other_columns.append(column)

            pk_columns.sort(key=lambda x: x.original_column_name)
            other_columns.sort(key=lambda x: x.original_column_name)
            sorted_columns = pk_columns + other_columns

            # Create styles for wrapping text in cells
            cell_style = ParagraphStyle(
                "CellStyle",
                parent=styles["Normal"],
                fontSize=9,
                leading=11,
                alignment=TA_LEFT,
                wordWrap="CJK",  # Better word wrapping
            )

            name_style = ParagraphStyle(
                "NameStyle",
                parent=styles["Normal"],
                fontSize=9,
                leading=11,
                alignment=TA_LEFT,
                wordWrap="CJK",
            )

            for column in sorted_columns:
                col_name = column.original_column_name
                if column.pk_field:
                    col_name = f"🔑 {col_name}"

                # Wrap column name if it's too long
                col_name_para = Paragraph(col_name, name_style)

                data_type = column.data_format or "TEXT"
                # Wrap data type if it's too long
                if len(data_type) > 15:
                    data_type = Paragraph(data_type, name_style)
                description = (
                    column.column_description or column.generated_comment or ""
                )
                fk = "🔗" if column.fk_field else ""

                # Clean up description - remove duplicate content
                if description:
                    # Remove potential duplicates (e.g., "INT 2013-14 CALPADS..." repeated)
                    words = description.split()
                    if len(words) > 3:
                        # Check if the description seems to have repeated content
                        half_len = len(words) // 2
                        first_half = " ".join(words[:half_len])
                        second_half = " ".join(words[half_len:])

                        # If the two halves are very similar, it might be duplicated
                        if first_half.strip() == second_half.strip():
                            description = first_half

                    description = Paragraph(description, cell_style)

                table_data.append([col_name_para, data_type, description, fk])

            # Create table with adjusted column widths (now we have ~7.5 inches width)
            t = Table(
                table_data, colWidths=[1.5 * inch, 0.9 * inch, 4.6 * inch, 0.5 * inch]
            )
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),  # Align text to top of cells
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f9f9f9")],
                        ),
                        ("TOPPADDING", (0, 1), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                    ]
                )
            )

            elements.append(t)
            elements.append(Spacer(1, 0.3 * inch))

        # Add Relationships section
        elements.append(PageBreak())
        elements.append(Paragraph("Database Relationships", heading1_style))
        elements.append(Paragraph("Foreign Key Relationships", heading2_style))

        # Get relationships
        from thoth_core.models import Relationship

        relationships = (
            Relationship.objects.filter(source_table__sql_db=sql_db)
            .select_related(
                "source_table", "source_column", "target_table", "target_column"
            )
            .order_by("source_table__name", "source_column__original_column_name")
        )

        if relationships.exists():
            # Prepare relationship table data
            rel_table_data = [
                ["Source Table", "Source Column", "Target Table", "Target Column"]
            ]

            for rel in relationships:
                source = f"{rel.source_table.name}"
                source_col = f"{rel.source_column.original_column_name}"
                target = f"{rel.target_table.name}"
                target_col = f"{rel.target_column.original_column_name}"

                rel_table_data.append([source, source_col, target, target_col])

            # Create relationships table
            rel_table = Table(
                rel_table_data, colWidths=[2 * inch, 2 * inch, 2 * inch, 1.5 * inch]
            )
            rel_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#ecf0f1")],
                        ),
                        ("TOPPADDING", (0, 1), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                    ]
                )
            )

            elements.append(rel_table)

            # Add a more readable format
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph("Relationship Details:", normal_style))
            elements.append(Spacer(1, 0.1 * inch))

            for rel in relationships:
                rel_text = f"<b>{rel.source_table.name}.{rel.source_column.original_column_name}</b> → <b>{rel.target_table.name}.{rel.target_column.original_column_name}</b>"
                elements.append(Paragraph(rel_text, normal_style))
                elements.append(Spacer(1, 0.05 * inch))

        else:
            elements.append(
                Paragraph(
                    "No foreign key relationships defined in this database.",
                    normal_style,
                )
            )

        # Build PDF
        doc.build(elements)

        # Prepare response
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{db_name}_documentation.pdf"'
        )

        logger.info(f"PDF generated successfully for {db_name}")
        return response

    except Exception as e:
        logger.error(f"Error generating PDF: {e}", exc_info=True)
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect("thoth_ai_backend:db_docs")


@login_required
def gdpr_export_pdf(request):
    """
    Export GDPR compliance report as PDF.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER

        # Get current workspace
        workspace = get_current_workspace(request)
        if not workspace or not workspace.sql_db:
            messages.error(request, "No workspace or database selected")
            return redirect("thoth_ai_backend:gdpr_report")

        sql_db = workspace.sql_db
        db_name = sql_db.name

        # Check if GDPR report exists
        if not sql_db.gdpr_report:
            messages.error(
                request,
                f"GDPR compliance scan has not been performed yet for database '{db_name}'.",
            )
            return redirect("thoth_ai_backend:gdpr_report")

        report = sql_db.gdpr_report

        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=50,
            bottomMargin=36,
        )

        # Setup styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#4a90a4"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=colors.HexColor("#4a90a4"),
            spaceAfter=12,
            spaceBefore=20,
        )

        normal_style = styles["Normal"]

        # Build PDF content
        elements = []

        # Title
        elements.append(Paragraph("GDPR Compliance Report", title_style))
        elements.append(Paragraph(f"Database: {db_name}", heading_style))

        if sql_db.gdpr_scan_date:
            elements.append(
                Paragraph(
                    f"Scan Date: {sql_db.gdpr_scan_date.strftime('%Y-%m-%d %H:%M:%S')}",
                    normal_style,
                )
            )

        # Risk Score
        risk_info = report.get("risk_score", {})
        risk_level = risk_info.get("level", "UNKNOWN")
        risk_score = risk_info.get("score", 0)

        risk_color = {
            "CRITICAL": colors.HexColor("#e74c3c"),
            "HIGH": colors.HexColor("#e67e22"),
            "MEDIUM": colors.HexColor("#f39c12"),
            "LOW": colors.HexColor("#17a2b8"),
        }.get(risk_level, colors.grey)
        risk_style = ParagraphStyle(
            "RiskStyle",
            parent=normal_style,
            textColor=risk_color,
            fontSize=14,
            fontName="Helvetica-Bold",
        )
        elements.append(
            Paragraph(f"Risk Level: {risk_level} ({risk_score}/100)", risk_style)
        )
        elements.append(Spacer(1, 0.3 * inch))

        # Summary
        elements.append(Paragraph("Summary", heading_style))
        summary = report["summary"]
        summary_data = [
            ["Metric", "Value"],
            ["Total Tables", str(summary["total_tables"])],
            ["Total Columns", str(summary["total_columns"])],
            ["Tables with Sensitive Data", str(summary["tables_with_sensitive_data"])],
            ["Sensitive Columns", str(summary["sensitive_columns"])],
            ["Critical Findings", str(summary["critical_findings"])],
            ["High Findings", str(summary["high_findings"])],
            ["Medium Findings", str(summary["medium_findings"])],
            ["Low Findings", str(summary["low_findings"])],
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a90a4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#ecf0f1")],
                    ),
                ]
            )
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Detailed Findings
        if summary["sensitive_columns"] > 0:
            elements.append(Paragraph("Detailed Findings", heading_style))

            findings_data = [["Table", "Column", "Category", "Sensitivity"]]
            for table in report["tables"]:
                if table["has_sensitive_data"]:
                    for column in table["sensitive_columns"]:
                        findings_data.append(
                            [
                                table["table_name"],
                                column["column_name"],
                                column["category"],
                                column["sensitivity"],
                            ]
                        )

            if len(findings_data) > 1:
                findings_table = Table(
                    findings_data, colWidths=[2 * inch, 2 * inch, 2 * inch, 1.5 * inch]
                )
                findings_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a90a4")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("FONTSIZE", (0, 1), (-1, -1), 9),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#ecf0f1")],
                            ),
                        ]
                    )
                )
                elements.append(findings_table)
                elements.append(PageBreak())

            # Recommendations
            if report.get("recommendations"):
                elements.append(Paragraph("Recommendations", heading_style))
                for rec in report["recommendations"]:
                    elements.append(
                        Paragraph(
                            f"<b>{rec['title']}</b> (Priority: {rec['priority']})",
                            normal_style,
                        )
                    )
                    elements.append(Paragraph(rec["description"], normal_style))
                    elements.append(Spacer(1, 0.2 * inch))
        else:
            elements.append(
                Paragraph("No Sensitive Personal Data Detected", heading_style)
            )
            elements.append(
                Paragraph(
                    "This database appears to contain no GDPR-sensitive personal information based on column name analysis.",
                    normal_style,
                )
            )
            elements.append(
                Paragraph(
                    "Note: This scan only analyzes column names. Manual review is still recommended to ensure compliance.",
                    normal_style,
                )
            )

        # Build PDF
        doc.build(elements)

        # Prepare response
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{db_name}_gdpr_compliance_report.pdf"'
        )

        logger.info(f"GDPR PDF generated successfully for {db_name}")
        return response

    except Exception as e:
        logger.error(f"Error generating GDPR PDF: {e}", exc_info=True)
        messages.error(request, f"Error generating GDPR PDF: {str(e)}")
        return redirect("thoth_ai_backend:gdpr_report")


@login_required
def gdpr_export_json(request):
    """
    Export GDPR compliance report as JSON.
    """
    try:
        # Get current workspace
        workspace = get_current_workspace(request)
        if not workspace or not workspace.sql_db:
            return JsonResponse(
                {"error": "No workspace or database selected"}, status=400
            )

        sql_db = workspace.sql_db

        # Check if GDPR report exists
        if not sql_db.gdpr_report:
            return JsonResponse(
                {
                    "error": f'GDPR compliance scan has not been performed yet for database "{sql_db.name}".'
                },
                status=404,
            )

        # Prepare response
        response = JsonResponse(sql_db.gdpr_report, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = (
            f'attachment; filename="{sql_db.name}_gdpr_compliance_report.json"'
        )

        return response

    except Exception as e:
        logger.error(f"Error exporting GDPR JSON: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def gdpr_export_csv(request):
    """
    Export GDPR compliance report as CSV.
    """
    try:
        workspace = get_current_workspace(request)
        if not workspace or not workspace.sql_db:
            messages.error(request, "No workspace or database selected")
            return redirect("thoth_ai_backend:gdpr_report")

        sql_db = workspace.sql_db
        db_name = sql_db.name

        if not sql_db.gdpr_report:
            messages.error(
                request,
                f"GDPR compliance scan has not been performed yet for database '{db_name}'.",
            )
            return redirect("thoth_ai_backend:gdpr_report")

        report = sql_db.gdpr_report

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{db_name}_gdpr_compliance_report.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["Database", db_name])
        if sql_db.gdpr_scan_date:
            writer.writerow(
                [
                    "Scan Date",
                    sql_db.gdpr_scan_date.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )
        risk_info = report.get("risk_score", {})
        if risk_info:
            writer.writerow(
                [
                    "Risk Level",
                    f"{risk_info.get('level', 'UNKNOWN')} ({risk_info.get('score', 0)}/100)",
                ]
            )

        writer.writerow([])
        writer.writerow(
            [
                "Table Name",
                "Column Name",
                "Data Type",
                "Sensitivity",
                "Category",
                "Pattern Type",
                "Description",
                "Has Sensitive Data",
            ]
        )

        tables = report.get("tables", [])
        if tables:
            for table_info in tables:
                table_name = table_info.get("table_name", "")
                description = table_info.get("description", "")
                sensitive_columns = table_info.get("sensitive_columns", [])

                if sensitive_columns:
                    for column in sensitive_columns:
                        writer.writerow(
                            [
                                table_name,
                                column.get("column_name", ""),
                                column.get("data_type", ""),
                                column.get("sensitivity", ""),
                                column.get("category", ""),
                                column.get("pattern_type", ""),
                                column.get("description", "") or description,
                                "Yes",
                            ]
                        )
                else:
                    writer.writerow(
                        [
                            table_name,
                            "",
                            "",
                            "NONE",
                            "",
                            "",
                            description,
                            "No",
                        ]
                    )
        else:
            writer.writerow([
                "No tables found in report",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ])

        logger.info(f"GDPR CSV generated successfully for {db_name}")
        return response

    except Exception as e:
        logger.error(f"Error generating GDPR CSV: {e}", exc_info=True)
        messages.error(request, f"Error generating GDPR CSV: {str(e)}")
        return redirect("thoth_ai_backend:gdpr_report")


@login_required
def erd_export_pdf(request):
    """
    Export ERD diagram as A4-optimized PDF.
    """
    try:
        # Get current workspace
        workspace = get_current_workspace(request)
        if not workspace or not workspace.sql_db:
            messages.error(request, "No workspace or database selected")
            return redirect("thoth_ai_backend:erd")

        sql_db = workspace.sql_db
        db_name = sql_db.name

        # Check if ERD exists
        if not sql_db.erd or not sql_db.erd.strip():
            messages.error(
                request,
                f"ERD diagram has not been generated yet for database '{db_name}'. Please generate database documentation first.",
            )
            return redirect("thoth_ai_backend:erd")

        # Generate PDF using original ERD format
        success, pdf_response, error_msg = generate_erd_pdf(sql_db.erd, db_name)

        if success and pdf_response:
            logger.info(f"ERD PDF generated successfully for {db_name}")
            return pdf_response
        else:
            messages.error(request, error_msg or "Failed to generate ERD PDF")
            return redirect("thoth_ai_backend:erd")

    except Exception as e:
        logger.error(f"Error in erd_export_pdf: {e}", exc_info=True)
        messages.error(request, f"Error generating ERD PDF: {str(e)}")
        return redirect("thoth_ai_backend:erd")
