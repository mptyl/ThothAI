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

import csv
import os
import sys
import django
import chardet
from pathlib import Path
import logging
from thoth_core.models import SqlDb, SqlTable, SqlColumn, Workspace
from django.utils import timezone

# Set up Django environment
sys.path.append(str(Path(__file__).resolve().parents[2]))  # Add the project root to the Python path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings")
django.setup()

# Now we can import Django models


def update_database_columns_description(workspace_id):
    """
    Function to update database columns directly.
    
    Args:
        workspace_id: The ID of the workspace to update columns for
    
    Returns:
        None
    """
    try:
        # Get the workspace
        workspace = Workspace.objects.get(id=workspace_id)
        
        # Load environment variables
        # data_root = os.getenv('DATA_ROOT')
        data_root = os.getenv('DB_ROOT_PATH')
        if not data_root:
            error_msg = "DB_ROOT_PATH not found in environment"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        # Check if SQL DB is configured
        if not workspace.sql_db:
            error_msg = f"Workspace {workspace_id} has no SQL database configured"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        db = workspace.sql_db
        database_name = db.db_name
        db_mode_value = db.db_mode # e.g., 'dev', 'test', 'prod'
        logging.info(f"Using database '{database_name}' (mode: {db_mode_value}) from workspace '{workspace.name}' (ID: {workspace_id})")

        # Set up the base directory
        project_root = Path(__file__).resolve().parents[2]  # Go up 2 levels to reach the project root
        
        # Construct the dynamic part of the path based on db_mode
        # data_root from .env is expected to be the top-level data directory, e.g., "data"
        dynamic_subdirectory = f"{db_mode_value}_databases" # e.g., "dev_databases"
        
        base_dir = os.path.join(project_root, data_root, dynamic_subdirectory, database_name, "database_description")

        # Ensure the directory exists
        if not os.path.exists(base_dir):
            error_msg = f"Data directory for column descriptions not found. . "
            error_msg += f"Searched {base_dir} for existing description directories under {os.path.join(project_root, data_root)}' and found: "
            
            available_dbs_dirs = []
            data_root_full_path = os.path.join(project_root, data_root)

            if os.path.exists(data_root_full_path) and os.path.isdir(data_root_full_path):
                # Iterate through items in data_root_full_path (e.g., "dev_databases", "prod_databases")
                for mode_subdir_name in os.listdir(data_root_full_path):
                    mode_subdir_path = os.path.join(data_root_full_path, mode_subdir_name)
                    if os.path.isdir(mode_subdir_path):
                        # Iterate through items in mode_subdir_path (e.g., "california_schools", "another_db")
                        for db_name_candidate in os.listdir(mode_subdir_path):
                            db_candidate_description_path = os.path.join(mode_subdir_path, db_name_candidate, "database_description")
                            if os.path.isdir(db_candidate_description_path):
                                # Store the relative path from data_root for clarity
                                available_dbs_dirs.append(os.path.join(mode_subdir_name, db_name_candidate, "database_description"))
            
            if available_dbs_dirs:
                error_msg += "\n- " + "\n- ".join(available_dbs_dirs)
            else:
                error_msg += "None found."
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)

        processing_errors = []

        # Iterate through CSV files in the directory
        for filename in os.listdir(base_dir):
            if filename.endswith('.csv'):
                table_name = filename[:-4]  # Remove '.csv' from the filename
                file_path = os.path.join(base_dir, filename)

                # Get the table object
                try:
                    table = SqlTable.objects.get(name__iexact=table_name, sql_db=db)
                except SqlTable.DoesNotExist:
                    err_msg = f"Table '{table_name}' (from CSV '{filename}') not found in database '{database_name}'."
                    logging.warning(err_msg)
                    processing_errors.append(err_msg)
                    continue

                with open(file_path, 'rb') as f:
                    result = chardet.detect(f.read())
                
                with open(file_path, 'r', encoding=result['encoding']) as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    # Reset file pointer to the beginning
                    csvfile.seek(0)
                    try:
                        next(reader)  # Skip header row
                    except StopIteration:
                        warn_msg = f"CSV file '{filename}' for table '{table_name}' is empty or has only a header."
                        logging.warning(warn_msg)
                        processing_errors.append(warn_msg)
                        continue # Skip empty or header-only file
                    
                    for row_num, row in enumerate(reader, start=2): # start=2 because header is row 1
                        original_column_name_raw = row.get('original_column_name', '')
                        original_column_name = original_column_name_raw.lower().strip() if not original_column_name_raw.__contains__(' ') else original_column_name_raw.strip()
                        
                        if not original_column_name:
                            err_msg = f"Missing 'original_column_name' in CSV '{filename}' for table '{table_name}' at row {row_num}."
                            logging.warning(err_msg)
                            processing_errors.append(err_msg)
                            continue

                        # Get the column object
                        try:
                            column = SqlColumn.objects.get(original_column_name__iexact=original_column_name, sql_table=table)
                            
                            # Update column fields
                            column.column_name = row.get('column_name', column.column_name) # Keep existing if not provided
                            column.column_description = row.get('column_description', column.column_description) # Keep existing
                            column.value_description = row.get('value_description', column.value_description) # Keep existing
                            
                            # Save the changes
                            column.save()
                            logging.info(f"Successfully updated column '{original_column_name}' in table '{table_name}'")
                        except SqlColumn.DoesNotExist:
                            err_msg = f"Column '{original_column_name}' (from CSV '{filename}', row {row_num}) not found in table '{table_name}'."
                            logging.warning(err_msg)
                            processing_errors.append(err_msg)
                        except Exception as e:
                            err_msg = f"Error updating column '{original_column_name}' (from CSV '{filename}', row {row_num}) in table '{table_name}': {str(e)}"
                            logging.error(err_msg)
                            processing_errors.append(err_msg)
        
        if processing_errors:
            raise Exception("Errors occurred during column description update:\n- " + "\n- ".join(processing_errors))

        # After successful update (and no processing_errors), update the last_columns_update timestamp
        db.last_columns_update = timezone.now()
        db.save()
        
        logging.info(f"Column update complete for database '{database_name}'")

    except Workspace.DoesNotExist:
        # This will be caught by the generic Exception handler below if not handled separately
        raise Exception(f"Workspace with ID {workspace_id} not found")
    except Exception as e:
        # Re-raise the exception to be caught by the view
        # Ensure the message is a simple string for the template
        logging.error(f"Error in update_database_columns_description: {str(e)}")
        raise Exception(str(e)) # Pass the original or a formatted error string


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update database column metadata from CSV files")
    parser.add_argument("--workspace_id", type=int, required=True, help="Workspace ID to determine the database")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    try:
        update_database_columns_description(workspace_id=args.workspace_id)
    except Exception as e:
        logging.error(f"Error in update_database_columns_direct: {str(e)}")
        sys.exit(1)
