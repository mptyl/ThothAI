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

from django.core.cache import cache
import json
import logging

logger = logging.getLogger(__name__)

class ProgressTracker:
    """
    A simple progress tracker using Django's cache to store progress information
    for long-running operations like evidence and question uploads.
    """
    
    @staticmethod
    def get_cache_key(workspace_id, operation_type):
        """Generate a unique cache key for the progress tracking."""
        return f"progress_{operation_type}_{workspace_id}"
    
    @staticmethod
    def init_progress(workspace_id, operation_type, total_items):
        """Initialize progress tracking for an operation."""
        cache_key = ProgressTracker.get_cache_key(workspace_id, operation_type)
        progress_data = {
            'total_items': total_items,
            'processed_items': 0,
            'successful_items': 0,
            'failed_items': 0,
            'status': 'processing',
            'percentage': 0
        }
        cache.set(cache_key, json.dumps(progress_data), timeout=3600)  # 1 hour timeout
        logger.info(f"Initialized progress tracking for {operation_type} in workspace {workspace_id}: {total_items} items")
        return progress_data
    
    @staticmethod
    def update_progress(workspace_id, operation_type, processed_items, successful_items, failed_items):
        """Update progress for an operation."""
        cache_key = ProgressTracker.get_cache_key(workspace_id, operation_type)
        progress_data = ProgressTracker.get_progress(workspace_id, operation_type)
        
        if progress_data:
            progress_data['processed_items'] = processed_items
            progress_data['successful_items'] = successful_items
            progress_data['failed_items'] = failed_items
            
            # Calculate percentage
            if progress_data['total_items'] > 0:
                progress_data['percentage'] = int((processed_items / progress_data['total_items']) * 100)
            else:
                progress_data['percentage'] = 0
            
            # Check if completed
            # Only mark as completed if we have a real total (not 0) and all items are processed
            if progress_data['total_items'] > 0 and processed_items >= progress_data['total_items']:
                progress_data['status'] = 'completed'
            
            cache.set(cache_key, json.dumps(progress_data), timeout=3600)
        
        return progress_data
    
    @staticmethod
    def get_progress(workspace_id, operation_type):
        """Get current progress for an operation."""
        cache_key = ProgressTracker.get_cache_key(workspace_id, operation_type)
        progress_json = cache.get(cache_key)
        
        if progress_json:
            return json.loads(progress_json)
        return None
    
    @staticmethod
    def clear_progress(workspace_id, operation_type):
        """Clear progress tracking for an operation."""
        cache_key = ProgressTracker.get_cache_key(workspace_id, operation_type)
        cache.delete(cache_key)
        logger.info(f"Cleared progress tracking for {operation_type} in workspace {workspace_id}")