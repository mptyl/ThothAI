#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Test script to verify semantic alias generation with different database quoting styles."""

import sys
import os
import re

# Add frontend to path
sys.path.insert(0, '/Users/mp/ThothAI/frontend')
sys.path.insert(0, '/Users/mp/ThothAI/frontend/sql_generator')

# Now we can import the service, but we'll extract just the methods we need
# to avoid import issues with the logging modules
from typing import Dict

def test_all_quoting_styles():
    """Test alias generation with different database quoting styles."""
    service = PaginatedQueryService(None, None)
    
    test_cases = [
        # PostgreSQL/Oracle/SQLite style (double quotes)
        {
            'sql': 'SELECT "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)" FROM frpm',
            'db': 'PostgreSQL',
            'expected_alias': 'free_meal_rate'
        },
        # MySQL/MariaDB/SQLite style (backticks)
        {
            'sql': 'SELECT `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` FROM frpm',
            'db': 'MySQL/MariaDB',
            'expected_alias': 'free_meal_rate'
        },
        # SQL Server style (square brackets)
        {
            'sql': 'SELECT [Free Meal Count (Ages 5-17)] / [Enrollment (Ages 5-17)] FROM frpm',
            'db': 'SQL Server',
            'expected_alias': 'free_meal_rate'
        },
        # Mixed operators with different quoting
        {
            'sql': 'SELECT "Price" * "Quantity", `Total` + `Tax`, [Discount] - [Amount] FROM sales',
            'db': 'Mixed',
            'expected_aliases': ['total_amount', 'total_plus_tax', 'discount_minus_amount']
        },
        # Complex field names with parentheses
        {
            'sql': 'SELECT "Students (K-12)" + "Teachers (Full-Time)" FROM school_data',
            'db': 'PostgreSQL',
            'expected_alias': 'students_k_12_plus_teachers_full_time'
        },
        # Escaped quotes
        {
            'sql': 'SELECT "Field""With""Quotes" / "Normal Field" FROM data',
            'db': 'PostgreSQL (escaped)',
            'expected_alias': 'field_with_quotes_per_normal_field'
        }
    ]
    
    print("Testing semantic alias generation with different database quoting styles:\n")
    print("=" * 80)
    
    for test in test_cases:
        print(f"\nDatabase: {test['db']}")
        print(f"Original SQL: {test['sql']}")
        
        try:
            result_sql = service._add_aliases_to_calculated_fields(test['sql'])
            print(f"Modified SQL: {result_sql}")
            
            # Check if the expected alias is in the result
            if 'expected_alias' in test:
                if f"AS {test['expected_alias']}" in result_sql:
                    print(f"✓ Alias '{test['expected_alias']}' correctly generated")
                else:
                    print(f"✗ Expected alias '{test['expected_alias']}' not found in result")
            elif 'expected_aliases' in test:
                for alias in test['expected_aliases']:
                    if f"AS {alias}" in result_sql:
                        print(f"✓ Alias '{alias}' correctly generated")
                    else:
                        print(f"✗ Expected alias '{alias}' not found in result")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
        
        print("-" * 80)

if __name__ == "__main__":
    test_all_quoting_styles()