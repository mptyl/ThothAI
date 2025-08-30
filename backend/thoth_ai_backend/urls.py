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

from django.urls import path
from . import views
# Import the new delete views along with existing ones
from . import views # Keep this for general views access
from .views import (
    ColumnsView, EvidenceView, QuestionsView, PreprocessView, DbDocsView, ErdView, GdprReportView,
)
from . import views_progress

app_name = 'thoth_ai_backend'

urlpatterns = [
    path('evidence/', EvidenceView.as_view(), name='evidence'),
    path('evidence/create/', views.manage_evidence, name='create_evidence'), # Route create to manage_evidence
    path('evidence/update/<str:evidence_id>/', views.manage_evidence, name='update_evidence'), # Route update to manage_evidence with ID
    # Add URL pattern for the confirmation page (GET)
    path('evidence/delete/<str:evidence_id>/confirm/', views.confirm_delete_evidence, name='confirm_delete_evidence'),
    # Add URL pattern for the actual deletion action (POST)
    path('evidence/delete/<str:evidence_id>/execute/', views.delete_evidence_confirmed, name='delete_evidence_confirmed'),
    # New URL for exporting evidence
    path('evidence/export_csv/', views.export_evidence_csv, name='export_evidence_csv'),
    path('evidence/import_server_csv/', views.import_evidence_server_csv, name='import_evidence_server_csv'), # New import URL
    path('vector_store/evidence/delete_all/', views.delete_all_evidence, name='delete_all_evidence'), # New delete all evidence URL
    
    path('questions/', QuestionsView.as_view(), name='questions'),
    path('questions/export_csv/', views.export_questions_csv, name='export_questions_csv'), # New export URL
    path('questions/import_server_csv/', views.import_questions_server_csv, name='import_questions_server_csv'), # New import URL
    path('vector_store/questions/delete_all/', views.delete_all_questions, name='delete_all_questions'), # New delete all questions URL
    path('columns/', ColumnsView.as_view(), name='columns'),
    path('columns/export_csv/', views.export_columns_csv, name='export_columns_csv'), # New export URL
    path('columns/import_server_csv/', views.import_columns_server_csv, name='import_columns_server_csv'), # New import URL
    path('vector_store/columns/delete_all/', views.delete_all_columns, name='delete_all_columns'), # New delete all columns URL
    # URL for viewing a specific column document's details (using string ID)
    path('columns/view/<str:column_id>/', views.view_columns, name='view_columns'),
    # URL for handling the deletion of a column document (POST request, using string ID)

    # Question (SqlDocument) CRUD URLs
    path('questions/create/', views.manage_question, name='create_question'),
    path('questions/update/<str:question_id>/', views.manage_question, name='update_question'),
    path('questions/delete/<str:question_id>/confirm/', views.confirm_delete_question, name='confirm_delete_question'),
    path('questions/delete/<str:question_id>/execute/', views.delete_question_confirmed, name='delete_question_confirmed'),

    path('preprocess/', PreprocessView.as_view(), name='preprocess'),
    # New URL pattern for preprocessing
    path('run_preprocessing/<int:workspace_id>/', views.run_preprocessing, name='run_preprocessing'),
    path('check_preprocessing_status/<int:workspace_id>/', views.check_preprocessing_status, name='check_preprocessing_status'),
    
    # Add this new URL pattern
    path('workspace/<int:workspace_id>/upload-evidences/', views_progress.upload_evidences_async, name='upload_evidences'),
    path('workspace/<int:workspace_id>/upload-questions/', views_progress.upload_questions_async, name='upload_questions'),
    # Progress check endpoints
    path('workspace/<int:workspace_id>/upload-evidences/progress/', views_progress.check_evidence_progress, name='check_evidence_progress'),
    path('workspace/<int:workspace_id>/upload-questions/progress/', views_progress.check_questions_progress, name='check_questions_progress'),
    # Keep original sync endpoints as fallback
    path('workspace/<int:workspace_id>/upload-evidences-sync/', views.upload_evidences, name='upload_evidences_sync'),
    path('workspace/<int:workspace_id>/upload-questions-sync/', views.upload_questions, name='upload_questions_sync'),
    path('update-database-columns/<int:workspace_id>/', views.update_database_columns, name='update_database_columns'),
    
    # Database documentation
    path('db-docs/', DbDocsView.as_view(), name='db_docs'),
    path('db-docs/export-pdf/', views.export_pdf, name='export_pdf'),
    
    # ERD visualization
    path('erd/', ErdView.as_view(), name='erd'),
    path('erd/export-pdf/', views.erd_export_pdf, name='erd_export_pdf'),
    
    # GDPR compliance
    path('gdpr-report/', GdprReportView.as_view(), name='gdpr_report'),
    path('gdpr-report/export-pdf/', views.gdpr_export_pdf, name='gdpr_export_pdf'),
    path('gdpr-report/export-json/', views.gdpr_export_json, name='gdpr_export_json'),
]
