#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Direct test of the updated PaginatedQueryService alias generation with all quoting styles."""

import sys
import os
from unittest.mock import MagicMock

# Create mock modules for logging
mock_dual_logger = MagicMock()
mock_dual_logger.log_error = MagicMock()
mock_dual_logger.log_info = MagicMock()
mock_dual_logger.log_warning = MagicMock()
mock_dual_logger.log_debug = MagicMock()

mock_logging_config = MagicMock()
mock_logging_config.setup_logger = MagicMock(return_value=MagicMock())
mock_logging_config.get_logger = MagicMock(return_value=MagicMock())

sys.modules['helpers.dual_logger'] = mock_dual_logger
sys.modules['helpers.logging_config'] = mock_logging_config
sys.modules['helpers'] = MagicMock()

# Add frontend to path
sys.path.insert(0, '/Users/mp/ThothAI/frontend')
sys.path.insert(0, '/Users/mp/ThothAI/frontend/sql_generator')

# Now we can import the actual service
from sql_generator.services.paginated_query_service import PaginatedQueryService

def test_quoting_styles():
    """Test alias generation with all database quoting styles."""
    
    # Create a mock service instance (we only need the alias methods)
    service = PaginatedQueryService(None)
    
    test_cases = [
        {
            'name': 'PostgreSQL/SQLite (double quotes)',
            'sql': 'SELECT "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)" FROM frpm WHERE "Educational Option Type" = \'Continuation School\'',
            'expected_in_sql': 'AS free_meal_rate'
        },
        {
            'name': 'MySQL/MariaDB/SQLite (backticks)',
            'sql': 'SELECT `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` FROM frpm WHERE `Educational Option Type` = \'Continuation School\'',
            'expected_in_sql': 'AS free_meal_rate'
        },
        {
            'name': 'SQL Server (square brackets)',
            'sql': 'SELECT [Free Meal Count (Ages 5-17)] / [Enrollment (Ages 5-17)] FROM frpm WHERE [Educational Option Type] = \'Continuation School\'',
            'expected_in_sql': 'AS free_meal_rate'
        },
        {
            'name': 'Multiple calculations (PostgreSQL)',
            'sql': 'SELECT "Price" * "Quantity", "Total" + "Tax", "Discount" - "Amount" FROM sales',
            'expected_in_sql': ['AS total_amount', 'AS total_plus_tax', 'AS discount_minus_amount']
        },
        {
            'name': 'Complex field names with parentheses',
            'sql': 'SELECT "Students (K-12)" + "Teachers (Full-Time)" FROM school_data',
            'expected_in_sql': 'AS students_k_12_plus_teachers_full_time'
        },
        {
            'name': 'Existing alias should not be modified',
            'sql': 'SELECT "Field1" / "Field2" AS my_custom_alias FROM table1',
            'expected_in_sql': 'AS my_custom_alias'
        }
    ]
    
    print("Testing semantic alias generation with all database quoting styles:")
    print("=" * 80)
    
    success_count = 0
    total_count = len(test_cases)
    
    for test in test_cases:
        print(f"\n{test['name']}:")
        print(f"Original SQL: {test['sql'][:100]}...")
        
        try:
            result_sql, column_names = service._add_aliases_to_calculated_fields(test['sql'])
            print(f"Modified SQL: {result_sql[:150]}...")
            print(f"Column names: {column_names}")
            
            # Check if the expected alias(es) are in the result
            if isinstance(test['expected_in_sql'], list):
                all_found = True
                for expected in test['expected_in_sql']:
                    if expected in result_sql:
                        print(f"  ✓ Found '{expected}'")
                    else:
                        print(f"  ✗ Missing '{expected}'")
                        all_found = False
                if all_found:
                    success_count += 1
            else:
                if test['expected_in_sql'] in result_sql:
                    print(f"  ✓ Found '{test['expected_in_sql']}'")
                    success_count += 1
                else:
                    print(f"  ✗ Expected '{test['expected_in_sql']}' not found")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
        
        print("-" * 60)
    
    print(f"\n{success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("\n✓ All database quoting styles are handled correctly!")
    else:
        print(f"\n✗ {total_count - success_count} test(s) failed")

if __name__ == "__main__":
    # Mock the logger functions that might be used
    import helpers.dual_logger as logger_mock
    logger_mock.log_error = lambda *args, **kwargs: None
    logger_mock.log_info = lambda *args, **kwargs: None
    logger_mock.log_warning = lambda *args, **kwargs: None
    logger_mock.log_debug = lambda *args, **kwargs: None
    
    test_quoting_styles()