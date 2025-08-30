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

import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from thoth_core.models import Workspace
from thoth_ai_backend.utils.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["GET"])
def check_preprocessing_status_with_progress(request, workspace_id):
    """
    Checks the status of the preprocessing task and returns the appropriate template with progress info.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    status = workspace.preprocessing_status
    
    # Get progress information from cache
    progress = ProgressTracker.get_progress(workspace_id, 'preprocessing')
    
    if status == Workspace.PreprocessingStatus.RUNNING:
        # Task is still running, show progress
        if progress:
            # Return progress bar template
            context = {
                'workspace': workspace,
                'container_id': 'preprocessing-container',
                'show_progress': True,
                'total_items': progress.get('total_items', 0),
                'processed_items': progress.get('processed_items', 0),
                'progress_percentage': progress.get('percentage', 0),
                'spinner_text': f"Preprocessing in progress... ({progress.get('processed_items', 0)}/{progress.get('total_items', 0)})",
            }
            return render(request, 'partials/preprocessing_progress.html', context)
        else:
            # No progress data yet, show regular polling template
            return render(request, 'partials/preprocessing_polling.html', {
                'workspace': workspace,
                'hx_indicator_id': 'spinner',
                'spinner_text': 'Preprocessing in progress...'
            })
    else:
        # Task is completed or failed, clear progress and return the final status button
        if progress:
            ProgressTracker.clear_progress(workspace_id, 'preprocessing')
        
        context = {
            'container_id': 'preprocessing-container',
            'hx_url': reverse('thoth_ai_backend:run_preprocessing', args=[workspace.id]),
            'hx_indicator_id': 'spinner',
            'button_text': 'Run Preprocessing',
            'last_run_text': 'Last run on',
            'never_run_text': 'Never run',
            'spinner_text': 'Processing in progress...',
            'icon_class': 'mdi mdi-refresh',
            'button_class': 'btn-primary',
            'workspace': workspace,
            'last_run': workspace.last_preprocess,
        }
        
        if status == Workspace.PreprocessingStatus.COMPLETED:
            context['success_message'] = 'Preprocessing completed successfully!'
            if progress:
                context['success_message'] = f"Preprocessing completed successfully! Processed {progress.get('successful_items', 0)} items."
        elif status == Workspace.PreprocessingStatus.FAILED:
            context['error_message'] = workspace.last_preprocess_log or 'Preprocessing failed'
        
        return render(request, 'partials/operation_status_button_simple.html', context)