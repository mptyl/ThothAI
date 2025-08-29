# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import threading
import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.urls import reverse
from thoth_core.models import Workspace
from thoth_ai_backend.preprocessing.upload_evidence import upload_evidence_to_vectordb
from thoth_ai_backend.preprocessing.upload_questions import upload_questions_to_vectordb
from thoth_ai_backend.utils.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

def run_upload_in_background(func, workspace_id, operation_type):
    """
    Run upload function in a background thread.
    """
    def wrapper():
        try:
            func(workspace_id)
        except Exception as e:
            logger.error(f"Error in background upload for {operation_type}: {e}")
            # Mark as failed in progress tracker
            progress = ProgressTracker.get_progress(workspace_id, operation_type)
            if progress:
                progress['status'] = 'failed'
                progress['error'] = str(e)
                ProgressTracker.update_progress(workspace_id, operation_type, 
                                               progress.get('processed_items', 0),
                                               progress.get('successful_items', 0),
                                               progress.get('failed_items', 0))
    
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    return thread

@login_required
@require_POST
def upload_evidences_async(request, workspace_id):
    """
    Start evidence upload in background and return progress bar.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    
    # Initialize progress BEFORE starting the background thread
    # This ensures the progress data exists when the first poll happens
    ProgressTracker.init_progress(workspace_id, 'evidence', 0)  # Start with 0, will be updated
    
    # Start upload in background
    run_upload_in_background(upload_evidence_to_vectordb, workspace_id, 'evidence')
    
    # Return immediately with progress bar
    context = {
        'container_id': 'evidence-container',
        'progress_url': reverse('thoth_ai_backend:check_evidence_progress', args=[workspace.id]),
        'button_text': 'Load Evidence',
        'show_progress': True,
        'total_items': 0,  # Will be updated by progress polling
        'processed_items': 0,
        'progress_percentage': 0,
        'workspace': workspace,
    }
    
    return render(request, 'partials/operation_status_button_with_progress.html', context)

@login_required
@require_POST
def upload_questions_async(request, workspace_id):
    """
    Start questions upload in background and return progress bar.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    
    # Initialize progress BEFORE starting the background thread
    # This ensures the progress data exists when the first poll happens
    ProgressTracker.init_progress(workspace_id, 'questions', 0)  # Start with 0, will be updated
    
    # Start upload in background
    run_upload_in_background(upload_questions_to_vectordb, workspace_id, 'questions')
    
    # Return immediately with progress bar
    context = {
        'container_id': 'questions-container',
        'progress_url': reverse('thoth_ai_backend:check_questions_progress', args=[workspace.id]),
        'button_text': 'Load Questions',
        'show_progress': True,
        'total_items': 0,  # Will be updated by progress polling
        'processed_items': 0,
        'progress_percentage': 0,
        'workspace': workspace,
    }
    
    return render(request, 'partials/operation_status_button_with_progress.html', context)

@login_required
@require_http_methods(["GET"])
def check_evidence_progress(request, workspace_id):
    """
    Check progress of evidence upload and return updated progress bar or completion message.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    progress = ProgressTracker.get_progress(workspace_id, 'evidence')
    
    if not progress:
        # No progress data, show button
        context = {
            'container_id': 'evidence-container',
            'hx_url': reverse('thoth_ai_backend:upload_evidences', args=[workspace.id]),
            'button_text': 'Load Evidence',
            'last_run_text': 'Last upload on',
            'never_run_text': 'Evidence not yet uploaded',
            'icon_class': 'mdi mdi-lightbulb-on-outline',
            'workspace': workspace,
            'last_run': workspace.last_evidence_load,
            'show_progress': False,
        }
    elif progress.get('status') == 'completed' and progress.get('total_items', 0) > 0:
        # Upload completed
        workspace.refresh_from_db()
        context = {
            'container_id': 'evidence-container',
            'hx_url': reverse('thoth_ai_backend:upload_evidences', args=[workspace.id]),
            'button_text': 'Load Evidence',
            'last_run_text': 'Last upload on',
            'never_run_text': 'Evidence not yet uploaded',
            'icon_class': 'mdi mdi-lightbulb-on-outline',
            'workspace': workspace,
            'last_run': workspace.last_evidence_load,
            'show_progress': False,
            'success_message': f"Successfully uploaded {progress['successful_items']} of {progress['total_items']} evidence items.",
        }
        # Clear progress after showing completion
        ProgressTracker.clear_progress(workspace_id, 'evidence')
    elif progress.get('status') == 'failed':
        # Upload failed
        context = {
            'container_id': 'evidence-container',
            'hx_url': reverse('thoth_ai_backend:upload_evidences', args=[workspace.id]),
            'button_text': 'Load Evidence',
            'last_run_text': 'Last upload on',
            'never_run_text': 'Evidence not yet uploaded',
            'icon_class': 'mdi mdi-lightbulb-on-outline',
            'workspace': workspace,
            'last_run': workspace.last_evidence_load,
            'show_progress': False,
            'error_message': f"Upload failed: {progress.get('error', 'Unknown error')}",
        }
        # Clear progress after showing error
        ProgressTracker.clear_progress(workspace_id, 'evidence')
    else:
        # Still processing - show progress bar even if total_items is 0 (still counting)
        total = progress.get('total_items', 0)
        processed = progress.get('processed_items', 0)
        percentage = progress.get('percentage', 0)
        
        # If total is 0, show an indeterminate progress bar
        if total == 0:
            display_text = "Counting items..."
            display_percentage = 0
        else:
            display_text = None
            display_percentage = percentage
            
        context = {
            'container_id': 'evidence-container',
            'progress_url': reverse('thoth_ai_backend:check_evidence_progress', args=[workspace.id]),
            'button_text': 'Load Evidence',
            'show_progress': True,
            'total_items': total,
            'processed_items': processed,
            'progress_percentage': display_percentage,
            'progress_text': display_text,  # Add custom text for display
            'workspace': workspace,
        }
    
    return render(request, 'partials/operation_status_button_with_progress.html', context)

@login_required
@require_http_methods(["GET"])
def check_questions_progress(request, workspace_id):
    """
    Check progress of questions upload and return updated progress bar or completion message.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    progress = ProgressTracker.get_progress(workspace_id, 'questions')
    
    if not progress:
        # No progress data, show button
        context = {
            'container_id': 'questions-container',
            'hx_url': reverse('thoth_ai_backend:upload_questions', args=[workspace.id]),
            'button_text': 'Load Questions',
            'last_run_text': 'Last upload on',
            'never_run_text': 'Questions not yet uploaded',
            'icon_class': 'mdi mdi-database-search',
            'workspace': workspace,
            'last_run': workspace.last_sql_loaded,
            'show_progress': False,
        }
    elif progress.get('status') == 'completed' and progress.get('total_items', 0) > 0:
        # Upload completed
        workspace.refresh_from_db()
        context = {
            'container_id': 'questions-container',
            'hx_url': reverse('thoth_ai_backend:upload_questions', args=[workspace.id]),
            'button_text': 'Load Questions',
            'last_run_text': 'Last upload on',
            'never_run_text': 'Questions not yet uploaded',
            'icon_class': 'mdi mdi-database-search',
            'workspace': workspace,
            'last_run': workspace.last_sql_loaded,
            'show_progress': False,
            'success_message': f"Successfully uploaded {progress['successful_items']} of {progress['total_items']} questions.",
        }
        # Clear progress after showing completion
        ProgressTracker.clear_progress(workspace_id, 'questions')
    elif progress.get('status') == 'failed':
        # Upload failed
        context = {
            'container_id': 'questions-container',
            'hx_url': reverse('thoth_ai_backend:upload_questions', args=[workspace.id]),
            'button_text': 'Load Questions',
            'last_run_text': 'Last upload on',
            'never_run_text': 'Questions not yet uploaded',
            'icon_class': 'mdi mdi-database-search',
            'workspace': workspace,
            'last_run': workspace.last_sql_loaded,
            'show_progress': False,
            'error_message': f"Upload failed: {progress.get('error', 'Unknown error')}",
        }
        # Clear progress after showing error
        ProgressTracker.clear_progress(workspace_id, 'questions')
    else:
        # Still processing - show progress bar even if total_items is 0 (still counting)
        total = progress.get('total_items', 0)
        processed = progress.get('processed_items', 0)
        percentage = progress.get('percentage', 0)
        
        # If total is 0, show an indeterminate progress bar
        if total == 0:
            display_text = "Counting items..."
            display_percentage = 0
        else:
            display_text = None
            display_percentage = percentage
            
        context = {
            'container_id': 'questions-container',
            'progress_url': reverse('thoth_ai_backend:check_questions_progress', args=[workspace.id]),
            'button_text': 'Load Questions',
            'show_progress': True,
            'total_items': total,
            'processed_items': processed,
            'progress_percentage': display_percentage,
            'progress_text': display_text,  # Add custom text for display
            'workspace': workspace,
        }
    
    return render(request, 'partials/operation_status_button_with_progress.html', context)