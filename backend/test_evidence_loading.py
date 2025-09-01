#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import os
import sys
import django
from pathlib import Path

# Set up environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings")
os.environ["DB_ROOT_PATH"] = "/Users/mp/ThothAI/backend/data"

# Setup Django
django.setup()

from thoth_core.models import Workspace, SqlDb

# Check workspace and db_mode
workspace = Workspace.objects.filter(id=1).first()
if workspace:
    print(f"Workspace found: {workspace.name}")
    if workspace.sql_db:
        print(f"  SQL DB: {workspace.sql_db.name}")
        print(f"  DB Mode: {workspace.sql_db.db_mode}")
        print(f"  DB Type: {workspace.sql_db.db_type}")
        
        # Check if the expected JSON file exists
        db_root_path = Path(os.environ["DB_ROOT_PATH"])
        db_mode = workspace.sql_db.db_mode
        json_path = db_root_path / f"{db_mode}_databases" / f"{db_mode}.json"
        
        print(f"\nExpected JSON path: {json_path}")
        if json_path.exists():
            print("✓ JSON file exists!")
            
            # Try to load evidence
            print("\nTrying to load evidence...")
            try:
                from thoth_ai_backend.preprocessing.upload_evidence import upload_evidence_to_vectordb
                successful, total = upload_evidence_to_vectordb(workspace_id=1)
                print(f"Evidence loaded: {successful}/{total} items")
            except Exception as e:
                print(f"Error loading evidence: {e}")
            
            # Try to load Gold SQL
            print("\nTrying to load Gold SQL...")
            try:
                from thoth_ai_backend.preprocessing.upload_questions import upload_questions_to_vectordb
                successful, total = upload_questions_to_vectordb(workspace_id=1)
                print(f"Gold SQL loaded: {successful}/{total} pairs")
            except Exception as e:
                print(f"Error loading Gold SQL: {e}")
        else:
            print(f"✗ JSON file not found at {json_path}")
            print(f"  Available files in {db_root_path}:")
            for item in db_root_path.iterdir():
                print(f"    - {item}")
    else:
        print("  No SQL DB configured!")
else:
    print("Workspace with ID 1 not found!")