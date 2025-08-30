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

"""
Async task functions for generating AI comments for tables.
This module provides background processing capabilities to prevent timeouts
when generating comments for large datasets.
"""

import logging
import threading
from typing import List, Dict, Any
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from thoth_core.models import Workspace, SqlTable, SqlColumn
from thoth_core.thoth_ai.thoth_workflow.create_table_comments import (
    create_table_comments_async
)
from thoth_core.thoth_ai.thoth_workflow.create_column_comments import (
    create_selected_column_comments as sync_create_column_comments,
    create_selected_column_comments_async
)
from thoth_core.thoth_ai.thoth_workflow.log_handler import (
    create_table_comment_logger,
    update_workspace_log
)
from thoth_core.utilities.task_validation import check_task_can_start

logger = logging.getLogger(__name__)


class AsyncTableCommentTask:
    """Handles async processing of table comments generation."""
    
    @staticmethod
    def process_table_comments(workspace_id: int, table_ids: List[int], user_id: int = None) -> Dict[str, Any]:
        """
        Async task to generate comments for specified tables.
        
        Args:
            workspace_id: ID of the workspace
            table_ids: List of table IDs to process
            user_id: ID of the user who initiated the task
            
        Returns:
            Dict with task results and status
        """
        workspace = None
        custom_logger = None
        memory_handler = None
        
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            workspace.table_comment_status = Workspace.PreprocessingStatus.RUNNING
            workspace.table_comment_task_id = f"table_comments_{workspace_id}_{timezone.now().timestamp()}"
            workspace.table_comment_start_time = timezone.now()
            # Clear the log field at the beginning of the process
            workspace.table_comment_log = ""
            workspace.save()
            
            # Create custom logger for this task
            custom_logger, memory_handler = create_table_comment_logger(workspace)
            
            custom_logger.info(f"Starting async table comment generation for {len(table_ids)} tables")
            logger.info(f"Starting async table comments generation for workspace {workspace_id}, processing {len(table_ids)} tables")
            
            # Process tables in chunks to prevent memory issues
            chunk_size = 10
            processed_count = 0
            failed_count = 0
            
            custom_logger.info(f"Processing {len(table_ids)} tables in chunks of {chunk_size}")
            
            for i in range(0, len(table_ids), chunk_size):
                chunk = table_ids[i:i + chunk_size]
                chunk_start = i + 1
                chunk_end = min(i + chunk_size, len(table_ids))
                
                custom_logger.info(f"Processing chunk {chunk_start}-{chunk_end} of {len(table_ids)} tables")
                
                try:
                    # Use async-compatible function with detailed logging, passing workspace_id and custom logger
                    results = create_table_comments_async(chunk, workspace_id, custom_logger)
                    processed_count += results['processed']
                    failed_count += results['failed']
                    
                    # Log individual table processing details
                    if 'details' in results:
                        for detail in results['details']:
                            if detail['status'] == 'success':
                                custom_logger.info(f"✓ Successfully processed table: {detail['table']}")
                            else:
                                custom_logger.error(f"✗ Failed to process table: {detail['table']} - {detail['message']}")
                    
                    # Log any errors
                    for error in results.get('errors', []):
                        custom_logger.error(f"Error in chunk {chunk_start}-{chunk_end}: {error}")
                    
                    # Update progress in workspace log
                    update_workspace_log(workspace, memory_handler)
                    
                    custom_logger.info(f"Chunk {chunk_start}-{chunk_end} completed: {results['processed']} processed, {results['failed']} failed")
                    
                except Exception as e:
                    custom_logger.error(f"Error processing table chunk {chunk_start}-{chunk_end}: {str(e)}")
                    failed_count += len(chunk)
                    
                    # Log failed tables
                    failed_tables = SqlTable.objects.filter(id__in=chunk)
                    for table in failed_tables:
                        custom_logger.error(f"✗ Failed to process table: {table.name}")
                    
                    # Update workspace log with current state
                    update_workspace_log(workspace, memory_handler)
            
            # Add summary to logs
            memory_handler.add_summary(processed_count, failed_count, len(table_ids))
            
            # Update final status
            workspace.table_comment_end_time = timezone.now()
            if failed_count == 0:
                workspace.table_comment_status = Workspace.PreprocessingStatus.COMPLETED
                custom_logger.info("All tables processed successfully!")
            else:
                workspace.table_comment_status = Workspace.PreprocessingStatus.FAILED
                custom_logger.error(f"Processing completed with {failed_count} failures")
            
            # Final log update
            update_workspace_log(workspace, memory_handler)
            workspace.save()
            
            logger.info(f"Table comments generation completed: {processed_count} processed, {failed_count} failed")
            
            return {
                'status': 'success',
                'processed': processed_count,
                'failed': failed_count,
                'total': len(table_ids)
            }
            
        except Exception as e:
            error_msg = f"Critical error in async table comments: {str(e)}"
            logger.error(error_msg)
            
            if custom_logger:
                custom_logger.error(error_msg)
            
            if workspace:
                workspace.table_comment_status = Workspace.PreprocessingStatus.FAILED
                workspace.table_comment_end_time = timezone.now()
                
                if memory_handler:
                    update_workspace_log(workspace, memory_handler)
                else:
                    workspace.table_comment_log = error_msg
                
                workspace.save()
            
            return {
                'status': 'error',
                'error': str(e),
                'processed': 0,
                'failed': len(table_ids) if 'table_ids' in locals() else 0
            }


class AsyncColumnCommentTask:
    """Handles async processing of column comments generation."""
    
    @staticmethod
    def process_column_comments(workspace_id: int, column_ids: List[int], user_id: int = None) -> Dict[str, Any]:
        """
        Async task to generate comments for specified columns.
        
        Args:
            workspace_id: ID of the workspace
            column_ids: List of column IDs to process
            user_id: ID of the user who initiated the task
            
        Returns:
            Dict with task results and status
        """
        workspace = None
        custom_logger = None
        memory_handler = None
        
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            workspace.column_comment_status = Workspace.PreprocessingStatus.RUNNING
            workspace.column_comment_task_id = f"column_comments_{workspace_id}_{timezone.now().timestamp()}"
            workspace.column_comment_start_time = timezone.now()
            # Clear the log field at the beginning of the process
            workspace.column_comment_log = ""
            workspace.save()
            
            # Create custom logger for this task (reuse table comment logger function)
            custom_logger, memory_handler = create_table_comment_logger(workspace, 'async_column_comments')
            
            custom_logger.info(f"Starting async column comment generation for {len(column_ids)} columns")
            logger.info(f"Starting async column comments generation for workspace {workspace_id}, processing {len(column_ids)} columns")
            
            # Use the enhanced async function with detailed logging
            try:
                results = create_selected_column_comments_async(column_ids, workspace_id, custom_logger)
                processed_count = results['processed']
                failed_count = results['failed']
                
                # Log individual column processing details
                if 'details' in results:
                    for detail in results['details']:
                        if detail['status'] == 'success':
                            custom_logger.info(f"✓ Successfully processed column: {detail['column']}")
                        else:
                            custom_logger.error(f"✗ Failed to process column: {detail['column']} - {detail['message']}")
                
                # Log any errors
                for error in results.get('errors', []):
                    custom_logger.error(f"Error during processing: {error}")
                
                # Update progress in workspace log
                update_workspace_log(workspace, memory_handler, 'column_comment_log')
                
                custom_logger.info(f"Processing completed: {processed_count} processed, {failed_count} failed")
                
            except Exception as e:
                custom_logger.error(f"Error during column comment generation: {str(e)}")
                processed_count = 0
                failed_count = len(column_ids)
                
                # Update workspace log with current state
                update_workspace_log(workspace, memory_handler, 'column_comment_log')
            
            # Add summary to logs
            memory_handler.add_summary(processed_count, failed_count, len(column_ids))
            
            # Update final status
            workspace.column_comment_end_time = timezone.now()
            if failed_count == 0:
                workspace.column_comment_status = Workspace.PreprocessingStatus.COMPLETED
                custom_logger.info("All columns processed successfully!")
            else:
                workspace.column_comment_status = Workspace.PreprocessingStatus.FAILED
                custom_logger.error(f"Processing completed with {failed_count} failures")
            
            # Final log update
            update_workspace_log(workspace, memory_handler, 'column_comment_log')
            workspace.save()
            
            logger.info(f"Column comments generation completed: {processed_count} processed, {failed_count} failed")
            
            return {
                'status': 'success',
                'processed': processed_count,
                'failed': failed_count,
                'total': len(column_ids)
            }
            
        except Exception as e:
            error_msg = f"Critical error in async column comments: {str(e)}"
            logger.error(error_msg)
            
            if custom_logger:
                custom_logger.error(error_msg)
            
            if workspace:
                workspace.column_comment_status = Workspace.PreprocessingStatus.FAILED
                workspace.column_comment_end_time = timezone.now()
                
                if memory_handler:
                    update_workspace_log(workspace, memory_handler, 'column_comment_log')
                else:
                    workspace.column_comment_log = error_msg
                
                workspace.save()
            
            return {
                'status': 'error',
                'error': str(e),
                'processed': 0,
                'failed': len(column_ids) if 'column_ids' in locals() else 0
            }


def start_async_table_comments(workspace_id: int, table_ids: List[int], user_id: int = None) -> str:
    """
    Start async table comments generation in a separate thread.
    
    Args:
        workspace_id: ID of the workspace
        table_ids: List of table IDs to process
        user_id: ID of the user who initiated the task
        
    Returns:
        Task ID for tracking
    """
    def run_task():
        AsyncTableCommentTask.process_table_comments(workspace_id, table_ids, user_id)
    
    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()
    
    return f"table_comments_{workspace_id}_{timezone.now().timestamp()}"


def start_async_column_comments(workspace_id: int, column_ids: List[int], user_id: int = None) -> str:
    """
    Start async column comments generation in a separate thread.
    
    Args:
        workspace_id: ID of the workspace
        column_ids: List of column IDs to process
        user_id: ID of the user who initiated the task
        
    Returns:
        Task ID for tracking
    """
    def run_task():
        AsyncColumnCommentTask.process_column_comments(workspace_id, column_ids, user_id)
    
    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()
    
    return f"column_comments_{workspace_id}_{timezone.now().timestamp()}"
