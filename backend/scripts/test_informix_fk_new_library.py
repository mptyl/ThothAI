#!/usr/bin/env python
"""
Test script to verify that thoth-dbmanager 0.7.4 correctly detects Informix foreign keys.

This script tests the olimpix database FK detection without any patches,
using the fixed version of thoth-dbmanager.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()

from thoth_core.models import SqlDb
from thoth_core.dbmanagement import get_db_manager


def main():
    print("=" * 80)
    print("Testing Informix FK Detection with thoth-dbmanager 0.7.4")
    print("=" * 80)
    print()
    
    # Get olimpix database
    try:
        sqldb = SqlDb.objects.get(name='olimpix')
        print(f"✓ Found database: {sqldb.name}")
        print(f"  Type: {sqldb.db_type}")
        print()
    except SqlDb.DoesNotExist:
        print("✗ Database 'olimpix' not found in the system")
        print("  Available databases:")
        for db in SqlDb.objects.all():
            print(f"    - {db.name} ({db.db_type})")
        sys.exit(1)
    
    # Get database manager
    try:
        db_manager = get_db_manager(sqldb)
        adapter = db_manager.adapter
        print(f"✓ Created database manager")
        print(f"  Adapter type: {type(adapter).__name__}")
        print()
    except Exception as e:
        print(f"✗ Failed to create database manager: {e}")
        sys.exit(1)
    
    # Check if this is the patched version (should NOT have the patch marker)
    has_original = hasattr(adapter.__class__, '_original_get_foreign_keys_as_documents')
    if has_original:
        print("⚠ WARNING: Patch marker found! The monkey-patch is still active.")
        print("  This means the patch wasn't properly removed.")
        print()
    else:
        print("✓ No patch marker found - using library's native implementation")
        print()
    
    # Test FK retrieval
    print("Retrieving foreign keys...")
    print("-" * 80)
    
    try:
        fk_docs = adapter.get_foreign_keys_as_documents()
        
        print(f"\n✓✓✓ SUCCESS! Retrieved {len(fk_docs)} foreign key relationships ✓✓✓")
        print()
        
        if len(fk_docs) == 0:
            print("⚠ WARNING: No foreign keys found!")
            print("  Expected: 210 FK relationships for olimpix database")
            print("  This might indicate a problem with the library fix.")
            return False
        elif len(fk_docs) < 200:
            print(f"⚠ WARNING: Only {len(fk_docs)} foreign keys found")
            print("  Expected: ~210 FK relationships for olimpix database")
            print("  This might indicate incomplete FK detection.")
        else:
            print(f"✓ Foreign key count matches expected value (~210)")
        
        print()
        print("Sample foreign keys retrieved:")
        print("-" * 80)
        
        for i, fk in enumerate(fk_docs[:10], 1):
            print(f"{i:3d}. {fk.constraint_name:25s}: {fk.source_table_name}.{fk.source_column_name} -> {fk.target_table_name}.{fk.target_column_name}")
        
        if len(fk_docs) > 10:
            print(f"... ({len(fk_docs) - 10} more)")
        
        print()
        print("=" * 80)
        print("✓ Test completed successfully!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n✗✗✗ FAILED! Error retrieving foreign keys: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
