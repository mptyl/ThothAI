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
from .views import TableColumnsDetailView, ThothLogListCreateView, ThothLogDetailView

urlpatterns = [
    path('', views.index, name='index'),
    path('api/login', views.api_login, name='api_login'),
    path('api/user', views.get_current_user, name='get_current_user'),
    path('api/test_token', views.test_token),
    path('api/test_api_key', views.test_api_key),
    path('api/workspaces', views.get_user_workspaces),
    path('api/workspaces_user_list', views.get_user_workspaces_list),
    path('api/workspace/<str:workspace_name>', views.get_workspace_by_name, name='get_workspace_by_name'),
    path('api/workspace/id/<int:workspace_id>', views.get_workspace_by_id, name='get_workspace_by_id'),
    path('api/workspace/<int:workspace_id>/agent-pools/', views.get_workspace_agent_pools, name='get_workspace_agent_pools'),
    path('api/workspace/<int:workspace_id>/check-embedding/', views.check_embedding_config, name='check-embedding-config'),
    path('api/workspace/<int:workspace_id>/test-vector-db/', views.test_vector_db_connection, name='test-vector-db-connection'),
    path('api/sqldb/<str:db_name>/tables/', views.TableListByDbNameView.as_view(), name='table-list-by-db-name'),
    path('api/sqldb/<str:db_name>/table/<str:table_name>/columns/', TableColumnsDetailView.as_view(), name='table-columns-detail'),
    # URL for setting the workspace in the session via HTMX
    path('set-workspace/', views.set_workspace_session, name='set_workspace'),
    # Admin AJAX endpoints for filtering
    path('ajax/admin/tables/', views.get_tables_by_database, name='get_tables_by_database'),
    path('ajax/admin/columns/', views.get_columns_by_table, name='get_columns_by_columns'),
    # Health check endpoints
    path('health', views.health_check, name='health_check'),
    path('api/health', views.health_check, name='api_health_check'),
    # ThothLog CRUD API endpoints
    path('api/thoth-logs/', ThothLogListCreateView.as_view(), name='thothlog-list-create'),
    path('api/thoth-logs/<int:pk>/', ThothLogDetailView.as_view(), name='thothlog-detail'),
    path('api/thoth-logs/summary/', views.get_thoth_logs_summary, name='thothlog-summary'),
    
    # Frontend authentication
    path('api/generate-frontend-token/', views.generate_frontend_token, name='generate-frontend-token'),
]
