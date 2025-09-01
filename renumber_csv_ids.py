#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import csv
import os
from typing import Dict, List, Any
from collections import OrderedDict

def read_csv(filepath: str) -> tuple[list[str], list[dict]]:
    """Read CSV file and return headers and data"""
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        data = list(reader)
    return headers, data

def write_csv(filepath: str, headers: list[str], data: list[dict]):
    """Write data to CSV file"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def create_id_mapping(data: list[dict], id_field: str = 'id') -> dict[str, str]:
    """Create mapping from old IDs to new sequential IDs"""
    mapping = {}
    new_id = 1
    for row in data:
        old_id = row[id_field]
        if old_id and old_id not in mapping:
            mapping[old_id] = str(new_id)
            new_id += 1
    return mapping

def update_ids_and_fks(data: list[dict], id_field: str, mapping: dict[str, str]) -> list[dict]:
    """Update IDs in data using mapping"""
    updated_data = []
    for row in data:
        new_row = row.copy()
        if id_field in new_row and new_row[id_field] in mapping:
            new_row[id_field] = mapping[new_row[id_field]]
        updated_data.append(new_row)
    return updated_data

def update_foreign_keys(data: list[dict], fk_field: str, mapping: dict[str, str]) -> list[dict]:
    """Update foreign key references using mapping"""
    updated_data = []
    for row in data:
        new_row = row.copy()
        if fk_field in new_row and new_row[fk_field] in mapping:
            new_row[fk_field] = mapping[new_row[fk_field]]
        updated_data.append(new_row)
    return updated_data

def update_many_to_many_field(data: list[dict], field_name: str, mapping: dict[str, str]) -> list[dict]:
    """Update many-to-many fields (comma-separated IDs)"""
    updated_data = []
    for row in data:
        new_row = row.copy()
        if field_name in new_row and new_row[field_name]:
            old_ids = new_row[field_name].split(',')
            new_ids = []
            for old_id in old_ids:
                old_id = old_id.strip()
                if old_id in mapping:
                    new_ids.append(mapping[old_id])
                else:
                    new_ids.append(old_id)  # Keep unchanged if not in mapping
            new_row[field_name] = ','.join(new_ids)
        updated_data.append(new_row)
    return updated_data

def main():
    data_dir = 'data_exchange'
    
    # Read all CSV files
    print("Reading CSV files...")
    files_data = {}
    
    # Read each file
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
            print(f"  - Read {filename}: {len(data)} rows")
    
    # Create ID mappings for each table
    print("\nCreating ID mappings...")
    mappings = {}
    
    # Process tables without FK dependencies first
    if 'groups.csv' in files_data:
        mappings['groups'] = create_id_mapping(files_data['groups.csv']['data'])
        print(f"  - groups: {len(mappings['groups'])} IDs mapped")
        
    if 'basicaimodel.csv' in files_data:
        mappings['basicaimodel'] = create_id_mapping(files_data['basicaimodel.csv']['data'])
        print(f"  - basicaimodel: {len(mappings['basicaimodel'])} IDs mapped")
        
    if 'vectordb.csv' in files_data:
        mappings['vectordb'] = create_id_mapping(files_data['vectordb.csv']['data'])
        print(f"  - vectordb: {len(mappings['vectordb'])} IDs mapped")
    
    # Process tables with FK dependencies
    if 'aimodel.csv' in files_data:
        mappings['aimodel'] = create_id_mapping(files_data['aimodel.csv']['data'])
        print(f"  - aimodel: {len(mappings['aimodel'])} IDs mapped")
        
    if 'selected_dbs.csv' in files_data:
        mappings['selected_dbs'] = create_id_mapping(files_data['selected_dbs.csv']['data'])
        print(f"  - selected_dbs: {len(mappings['selected_dbs'])} IDs mapped")
        
    if 'agent.csv' in files_data:
        mappings['agent'] = create_id_mapping(files_data['agent.csv']['data'])
        print(f"  - agent: {len(mappings['agent'])} IDs mapped")
        
    if 'groupprofile.csv' in files_data:
        mappings['groupprofile'] = create_id_mapping(files_data['groupprofile.csv']['data'])
        print(f"  - groupprofile: {len(mappings['groupprofile'])} IDs mapped")
        
    if 'workspace.csv' in files_data:
        mappings['workspace'] = create_id_mapping(files_data['workspace.csv']['data'])
        print(f"  - workspace: {len(mappings['workspace'])} IDs mapped")
    
    # Update IDs and foreign keys
    print("\nUpdating IDs and foreign keys...")
    
    # Update groups.csv
    if 'groups.csv' in files_data:
        files_data['groups.csv']['data'] = update_ids_and_fks(
            files_data['groups.csv']['data'], 'id', mappings['groups']
        )
        print("  - Updated groups.csv IDs")
    
    # Update basicaimodel.csv
    if 'basicaimodel.csv' in files_data:
        files_data['basicaimodel.csv']['data'] = update_ids_and_fks(
            files_data['basicaimodel.csv']['data'], 'id', mappings['basicaimodel']
        )
        print("  - Updated basicaimodel.csv IDs")
    
    # Update vectordb.csv
    if 'vectordb.csv' in files_data:
        files_data['vectordb.csv']['data'] = update_ids_and_fks(
            files_data['vectordb.csv']['data'], 'id', mappings['vectordb']
        )
        print("  - Updated vectordb.csv IDs")
    
    # Update aimodel.csv (has FK to basicaimodel)
    if 'aimodel.csv' in files_data:
        files_data['aimodel.csv']['data'] = update_ids_and_fks(
            files_data['aimodel.csv']['data'], 'id', mappings['aimodel']
        )
        files_data['aimodel.csv']['data'] = update_foreign_keys(
            files_data['aimodel.csv']['data'], 'basic_model', mappings['basicaimodel']
        )
        print("  - Updated aimodel.csv IDs and FKs")
    
    # Update selected_dbs.csv (has FK to vectordb)
    if 'selected_dbs.csv' in files_data:
        files_data['selected_dbs.csv']['data'] = update_ids_and_fks(
            files_data['selected_dbs.csv']['data'], 'id', mappings['selected_dbs']
        )
        files_data['selected_dbs.csv']['data'] = update_foreign_keys(
            files_data['selected_dbs.csv']['data'], 'vector_db', mappings['vectordb']
        )
        print("  - Updated selected_dbs.csv IDs and FKs")
    
    # Update agent.csv (has FK to aimodel)
    if 'agent.csv' in files_data:
        files_data['agent.csv']['data'] = update_ids_and_fks(
            files_data['agent.csv']['data'], 'id', mappings['agent']
        )
        files_data['agent.csv']['data'] = update_foreign_keys(
            files_data['agent.csv']['data'], 'ai_model', mappings['aimodel']
        )
        print("  - Updated agent.csv IDs and FKs")
    
    # Update groupprofile.csv (has FK to groups)
    if 'groupprofile.csv' in files_data:
        files_data['groupprofile.csv']['data'] = update_ids_and_fks(
            files_data['groupprofile.csv']['data'], 'id', mappings['groupprofile']
        )
        files_data['groupprofile.csv']['data'] = update_foreign_keys(
            files_data['groupprofile.csv']['data'], 'group', mappings['groups']
        )
        print("  - Updated groupprofile.csv IDs and FKs")
    
    # Update workspace.csv (has multiple FKs)
    if 'workspace.csv' in files_data:
        data = files_data['workspace.csv']['data']
        
        # Update workspace ID
        data = update_ids_and_fks(data, 'id', mappings['workspace'])
        
        # Update foreign keys
        data = update_foreign_keys(data, 'sql_db', mappings['selected_dbs'])
        data = update_foreign_keys(data, 'default_model', mappings['aimodel'])
        data = update_foreign_keys(data, 'question_validator', mappings['agent'])
        data = update_foreign_keys(data, 'kw_sel_agent', mappings['agent'])
        data = update_foreign_keys(data, 'sql_basic_agent', mappings['agent'])
        data = update_foreign_keys(data, 'sql_advanced_agent', mappings['agent'])
        data = update_foreign_keys(data, 'sql_expert_agent', mappings['agent'])
        data = update_foreign_keys(data, 'test_gen_agent_1', mappings['agent'])
        data = update_foreign_keys(data, 'test_gen_agent_2', mappings['agent'])
        data = update_foreign_keys(data, 'test_gen_agent_3', mappings['agent'])
        data = update_foreign_keys(data, 'test_evaluator_agent', mappings['agent'])
        data = update_foreign_keys(data, 'explain_sql_agent', mappings['agent'])
        data = update_foreign_keys(data, 'ask_human_help_agent', mappings['agent'])
        
        # Note: users and default_workspace are many-to-many fields but they reference
        # User model which is not in our CSV files, so we don't update them
        
        files_data['workspace.csv']['data'] = data
        print("  - Updated workspace.csv IDs and FKs")
    
    # Write updated CSV files
    print("\nWriting updated CSV files...")
    for filename, file_info in files_data.items():
        filepath = os.path.join(data_dir, filename)
        write_csv(filepath, file_info['headers'], file_info['data'])
        print(f"  - Wrote {filename}")
    
    # Print mapping summaries
    print("\n=== ID Mapping Summary ===")
    for table_name, mapping in mappings.items():
        print(f"\n{table_name}:")
        for old_id, new_id in sorted(mapping.items(), key=lambda x: int(x[1])):
            print(f"  {old_id} -> {new_id}")
    
    print("\n✓ Successfully renumbered all IDs and updated foreign keys!")
    print("Backup files are available in data_exchange_backup/")

if __name__ == "__main__":
    main()