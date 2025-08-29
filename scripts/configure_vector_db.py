#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
Script to configure VectorDatabase for a workspace
"""

import os
import sys
import django
import json

# Add the backend directory to the Python path
sys.path.insert(0, '/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thoth.settings')
django.setup()

from workspaces.models import Workspace, VectorDatabase

def configure_vector_db(workspace_id=14):
    try:
        # Get the workspace
        workspace = Workspace.objects.get(id=workspace_id)
        print(f"Configuring VectorDatabase for workspace: {workspace.name} (ID: {workspace.id})")
        
        # Check if VectorDatabase already exists
        vdb = VectorDatabase.objects.filter(workspace=workspace).first()
        
        if vdb:
            print(f"VectorDatabase already exists: {vdb.name}")
            print(f"  Type: {vdb.db_type}")
            print(f"  Active: {vdb.is_active}")
            print(f"  Config: {json.dumps(vdb.configuration, indent=2)}")
            
            # Update configuration
            vdb.configuration = {
                "host": "qdrant",  # Use the Docker service name
                "port": 6333,
                "collection_name": "california_schools",
                "api_key": None,
                "https": False
            }
            vdb.is_active = True
            vdb.save()
            print("Updated VectorDatabase configuration")
        else:
            # Create new VectorDatabase
            vdb = VectorDatabase.objects.create(
                workspace=workspace,
                name=f"Qdrant for {workspace.name}",
                db_type="qdrant",
                configuration={
                    "host": "qdrant",  # Use the Docker service name
                    "port": 6333,
                    "collection_name": "california_schools",
                    "api_key": None,
                    "https": False
                },
                is_active=True
            )
            print(f"Created new VectorDatabase: {vdb.name}")
            
        print("\nVectorDatabase configuration completed successfully!")
        
        # Verify all vector databases
        all_vdbs = VectorDatabase.objects.all()
        print(f"\nAll VectorDatabases in system: {all_vdbs.count()}")
        for v in all_vdbs:
            print(f"  - {v.name} (Workspace: {v.workspace.name}): {v.db_type}, active={v.is_active}")
            
    except Workspace.DoesNotExist:
        print(f"Workspace with ID {workspace_id} not found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    workspace_id = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    configure_vector_db(workspace_id)