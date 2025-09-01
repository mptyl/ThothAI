#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import csv
import os
from typing import Dict, List, Set

def read_csv(filepath: str) -> tuple[list[str], list[dict]]:
    """Read CSV file and return headers and data"""
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        data = list(reader)
    return headers, data

def get_all_ids(data: list[dict], id_field: str = 'id') -> set[str]:
    """Get all IDs from data"""
    return set(row[id_field] for row in data if row.get(id_field))

def check_sequential_ids(data: list[dict], table_name: str, id_field: str = 'id') -> bool:
    """Check if IDs are sequential starting from 1"""
    ids = sorted([int(row[id_field]) for row in data if row.get(id_field)])
    expected = list(range(1, len(ids) + 1))
    
    if ids == expected:
        print(f"✓ {table_name}: IDs are sequential (1-{len(ids)})")
        return True
    else:
        print(f"✗ {table_name}: IDs are NOT sequential!")
        print(f"  Found: {ids}")
        print(f"  Expected: {expected}")
        return False

def check_foreign_key(source_data: list[dict], fk_field: str, target_ids: set[str], 
                     source_table: str, target_table: str) -> bool:
    """Check if all foreign key references are valid"""
    invalid_refs = []
    for row in source_data:
        fk_value = row.get(fk_field)
        if fk_value and fk_value not in target_ids:
            invalid_refs.append(fk_value)
    
    if not invalid_refs:
        print(f"✓ {source_table}.{fk_field} → {target_table}: All FK references valid")
        return True
    else:
        print(f"✗ {source_table}.{fk_field} → {target_table}: Invalid FK references: {invalid_refs}")
        return False

def main():
    data_dir = 'data_exchange'
    print("=== Verifying CSV Data Integrity ===\n")
    
    # Read all CSV files
    files_data = {}
    csv_files = [
        'groups.csv',
        'basicaimodel.csv',
        'vectordb.csv',
        'aimodel.csv',
        'selected_dbs.csv',
        'agent.csv',
        'groupprofile.csv',
        'workspace.csv'
    ]
    
    for filename in csv_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            headers, data = read_csv(filepath)
            files_data[filename] = {'headers': headers, 'data': data}
    
    # Check sequential IDs
    print("1. Checking Sequential IDs:")
    print("-" * 40)
    all_sequential = True
    
    for filename in csv_files:
        if filename in files_data:
            table_name = filename.replace('.csv', '')
            is_sequential = check_sequential_ids(files_data[filename]['data'], table_name)
            all_sequential = all_sequential and is_sequential
    
    # Extract all IDs for FK validation
    id_sets = {}
    if 'groups.csv' in files_data:
        id_sets['groups'] = get_all_ids(files_data['groups.csv']['data'])
    if 'basicaimodel.csv' in files_data:
        id_sets['basicaimodel'] = get_all_ids(files_data['basicaimodel.csv']['data'])
    if 'vectordb.csv' in files_data:
        id_sets['vectordb'] = get_all_ids(files_data['vectordb.csv']['data'])
    if 'aimodel.csv' in files_data:
        id_sets['aimodel'] = get_all_ids(files_data['aimodel.csv']['data'])
    if 'selected_dbs.csv' in files_data:
        id_sets['selected_dbs'] = get_all_ids(files_data['selected_dbs.csv']['data'])
    if 'agent.csv' in files_data:
        id_sets['agent'] = get_all_ids(files_data['agent.csv']['data'])
    if 'workspace.csv' in files_data:
        id_sets['workspace'] = get_all_ids(files_data['workspace.csv']['data'])
    
    # Check foreign key integrity
    print("\n2. Checking Foreign Key Integrity:")
    print("-" * 40)
    all_fks_valid = True
    
    # Check aimodel → basicaimodel
    if 'aimodel.csv' in files_data and 'basicaimodel' in id_sets:
        is_valid = check_foreign_key(
            files_data['aimodel.csv']['data'], 'basic_model', 
            id_sets['basicaimodel'], 'aimodel', 'basicaimodel'
        )
        all_fks_valid = all_fks_valid and is_valid
    
    # Check selected_dbs → vectordb
    if 'selected_dbs.csv' in files_data and 'vectordb' in id_sets:
        is_valid = check_foreign_key(
            files_data['selected_dbs.csv']['data'], 'vector_db',
            id_sets['vectordb'], 'selected_dbs', 'vectordb'
        )
        all_fks_valid = all_fks_valid and is_valid
    
    # Check agent → aimodel
    if 'agent.csv' in files_data and 'aimodel' in id_sets:
        is_valid = check_foreign_key(
            files_data['agent.csv']['data'], 'ai_model',
            id_sets['aimodel'], 'agent', 'aimodel'
        )
        all_fks_valid = all_fks_valid and is_valid
    
    # Check groupprofile → groups
    if 'groupprofile.csv' in files_data and 'groups' in id_sets:
        is_valid = check_foreign_key(
            files_data['groupprofile.csv']['data'], 'group',
            id_sets['groups'], 'groupprofile', 'groups'
        )
        all_fks_valid = all_fks_valid and is_valid
    
    # Check workspace foreign keys
    if 'workspace.csv' in files_data:
        workspace_data = files_data['workspace.csv']['data']
        
        # Check workspace → selected_dbs
        if 'selected_dbs' in id_sets:
            is_valid = check_foreign_key(
                workspace_data, 'sql_db',
                id_sets['selected_dbs'], 'workspace', 'selected_dbs'
            )
            all_fks_valid = all_fks_valid and is_valid
        
        # Check workspace → aimodel
        if 'aimodel' in id_sets:
            is_valid = check_foreign_key(
                workspace_data, 'default_model',
                id_sets['aimodel'], 'workspace', 'aimodel'
            )
            all_fks_valid = all_fks_valid and is_valid
        
        # Check workspace → agent (multiple fields)
        if 'agent' in id_sets:
            agent_fk_fields = [
                'question_validator', 'kw_sel_agent', 'sql_basic_agent',
                'sql_advanced_agent', 'sql_expert_agent', 'test_gen_agent_1',
                'test_gen_agent_2', 'test_gen_agent_3', 'test_evaluator_agent',
                'explain_sql_agent', 'ask_human_help_agent'
            ]
            
            for fk_field in agent_fk_fields:
                is_valid = check_foreign_key(
                    workspace_data, fk_field,
                    id_sets['agent'], 'workspace', 'agent'
                )
                all_fks_valid = all_fks_valid and is_valid
    
    # Summary
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY:")
    print("=" * 50)
    
    if all_sequential and all_fks_valid:
        print("✅ ALL CHECKS PASSED!")
        print("   - All IDs are sequential starting from 1")
        print("   - All foreign key references are valid")
    else:
        print("❌ SOME CHECKS FAILED!")
        if not all_sequential:
            print("   - Some tables have non-sequential IDs")
        if not all_fks_valid:
            print("   - Some foreign key references are invalid")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()