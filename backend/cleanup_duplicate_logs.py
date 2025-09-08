#!/usr/bin/env python

# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License, Version 2.0.
# See the LICENSE file in the project root for full license information.

"""
Script to clean up duplicate ThothLog entries in the database.
Duplicate logs are identified as those with the same username, workspace, and question
that were created within 5 seconds of each other.
"""

import os
import sys
import django
from datetime import timedelta

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from thoth_core.models import ThothLog
from django.db.models import Count, Min
import json

def find_duplicates():
    """Find duplicate ThothLog entries."""
    # Find groups of logs that might be duplicates
    # Group by username, workspace, and question (first 100 chars)
    from django.db.models import F, Window
    from django.db.models.functions import Substr, Lag
    
    duplicates = []
    
    # Get all logs ordered by username, workspace, question, and started_at
    all_logs = ThothLog.objects.all().order_by('username', 'workspace', 'question', 'started_at')
    
    prev_log = None
    for log in all_logs:
        if prev_log and (
            prev_log.username == log.username and
            prev_log.workspace == log.workspace and
            prev_log.question == log.question and
            log.started_at - prev_log.started_at < timedelta(seconds=5)
        ):
            # This is a potential duplicate
            duplicates.append({
                'original': prev_log,
                'duplicate': log,
                'time_diff': (log.started_at - prev_log.started_at).total_seconds()
            })
        prev_log = log
    
    return duplicates

def analyze_duplicates(duplicates):
    """Analyze duplicate patterns."""
    print(f"\nFound {len(duplicates)} potential duplicate pairs")
    
    if not duplicates:
        return
    
    print("\nDuplicate Analysis:")
    print("-" * 80)
    
    for i, dup_pair in enumerate(duplicates[:10], 1):  # Show first 10
        original = dup_pair['original']
        duplicate = dup_pair['duplicate']
        
        print(f"\n{i}. Duplicate Pair:")
        print(f"   Original ID: {original.id}, Started: {original.started_at}")
        print(f"   Duplicate ID: {duplicate.id}, Started: {duplicate.started_at}")
        print(f"   Time difference: {dup_pair['time_diff']:.2f} seconds")
        print(f"   Question: {original.question[:100]}...")
        print(f"   Workspace: {original.workspace}")
        
        # Check if the duplicate has different data (indicating it's an update)
        has_different_data = False
        
        # Check key fields for differences
        if original.generated_sql != duplicate.generated_sql:
            print(f"   ⚠️  Different SQL generated!")
            has_different_data = True
            
        # Parse selection_metrics to check test status
        try:
            orig_metrics = json.loads(original.selection_metrics) if original.selection_metrics else {}
            dup_metrics = json.loads(duplicate.selection_metrics) if duplicate.selection_metrics else {}
            
            orig_status = orig_metrics.get('final_status', '')
            dup_status = dup_metrics.get('final_status', '')
            
            if orig_status != dup_status:
                print(f"   ⚠️  Different status: {orig_status} -> {dup_status}")
                has_different_data = True
        except:
            pass
            
        if not has_different_data:
            print(f"   ✓ True duplicate - can be safely removed")

def remove_duplicates(duplicates, dry_run=True):
    """Remove duplicate logs, keeping the most complete one."""
    if dry_run:
        print("\n[DRY RUN] Would remove the following duplicates:")
    else:
        print("\nRemoving duplicates...")
    
    removed_count = 0
    
    for dup_pair in duplicates:
        original = dup_pair['original']
        duplicate = dup_pair['duplicate']
        
        # Determine which one to keep (keep the one with more data)
        # Check which has more complete data
        orig_score = 0
        dup_score = 0
        
        # Score based on presence of key fields
        if original.generated_sql:
            orig_score += 1
        if duplicate.generated_sql:
            dup_score += 1
            
        if original.selection_metrics:
            orig_score += 1
        if duplicate.selection_metrics:
            dup_score += 1
            
        if original.enhanced_evaluation_selected_sql:
            orig_score += 1
        if duplicate.enhanced_evaluation_selected_sql:
            dup_score += 1
            
        # Keep the one with higher score, or the newer one if scores are equal
        if orig_score > dup_score:
            to_remove = duplicate
            to_keep = original
        elif dup_score > orig_score:
            to_remove = original
            to_keep = original  
        else:
            # Same score, keep the newer one (likely has more complete data)
            to_remove = original
            to_keep = duplicate
        
        if dry_run:
            print(f"  Would remove ID {to_remove.id}, keep ID {to_keep.id}")
        else:
            to_remove.delete()
            print(f"  Removed ID {to_remove.id}, kept ID {to_keep.id}")
        
        removed_count += 1
    
    print(f"\n{'Would remove' if dry_run else 'Removed'} {removed_count} duplicate logs")

def main():
    """Main function."""
    print("ThothLog Duplicate Cleanup Script")
    print("=" * 80)
    
    # Find duplicates
    duplicates = find_duplicates()
    
    if not duplicates:
        print("\n✓ No duplicate logs found!")
        return
    
    # Analyze duplicates
    analyze_duplicates(duplicates)
    
    # Ask user if they want to proceed with cleanup
    print("\n" + "=" * 80)
    response = input("\nDo you want to remove these duplicates? (y/N): ").strip().lower()
    
    if response == 'y':
        remove_duplicates(duplicates, dry_run=False)
        print("\n✓ Cleanup completed!")
    else:
        print("\nCleanup cancelled.")
        print("\nTo see what would be removed without actually deleting:")
        print("  Run with dry_run=True in remove_duplicates()")

if __name__ == "__main__":
    main()