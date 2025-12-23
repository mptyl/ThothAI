# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
API views for data exchange operations.
Provides endpoints for listing, uploading, downloading, and deleting files
in the data_exchange directory.
"""

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import os
import json
from pathlib import Path
from ..utilities.shared_paths import get_data_exchange_path


@require_http_methods(["GET"])
@login_required
def list_files(request):
    """List all files in data_exchange directory"""
    data_exchange_path = Path(get_data_exchange_path())

    if not data_exchange_path.exists():
        data_exchange_path.mkdir(parents=True, exist_ok=True)

    files = []
    for item in data_exchange_path.iterdir():
        if item.is_file():
            files.append({
                'name': item.name,
                'size': item.stat().st_size,
                'modified': item.stat().st_mtime
            })

    return JsonResponse({'files': files})


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def upload_file(request):
    """Upload a file to data_exchange directory"""
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    uploaded_file = request.FILES['file']
    data_exchange_path = Path(get_data_exchange_path())
    data_exchange_path.mkdir(parents=True, exist_ok=True)

    file_path = data_exchange_path / uploaded_file.name

    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return JsonResponse({
        'success': True,
        'filename': uploaded_file.name,
        'path': str(file_path)
    })


@require_http_methods(["GET"])
@login_required
def download_file(request, filename):
    """Download a file from data_exchange directory"""
    data_exchange_path = Path(get_data_exchange_path())
    file_path = data_exchange_path / filename

    if not file_path.exists():
        return JsonResponse({'error': 'File not found'}, status=404)

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


@require_http_methods(["DELETE"])
@login_required
def delete_file(request, filename):
    """Delete a file from data_exchange directory"""
    data_exchange_path = Path(get_data_exchange_path())
    file_path = data_exchange_path / filename

    if not file_path.exists():
        return JsonResponse({'error': 'File not found'}, status=404)

    file_path.unlink()

    return JsonResponse({'success': True, 'filename': filename})
