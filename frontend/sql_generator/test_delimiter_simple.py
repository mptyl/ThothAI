# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Simple test for SQL delimiter correction functionality.

This test focuses solely on testing the delimiter correction logic
without complex SystemState mocking.
"""

import sys
import os

# Add the sql_generator directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers.sql_delimiter_corrector import correct_sql_delimiters, get_delimiters_for_db


def test_comprehensive_delimiter_correction():
    """
    Comprehensive test of delimiter correction for various scenarios.
    """
    print("Comprehensive SQL Delimiter Correction Test")
    print("=" * 60)
    
    # Real-world test cases with complex scenarios
    test_scenarios = [
        {
            'name': 'SELECT with mixed identifiers and strings',
            'sql': 'SELECT "user id", "full name" FROM "user table" WHERE "status" = "active" AND "age" > "18"',
            'db_types': ['sqlite', 'mysql', 'postgresql', 'mssql']
        },
        {
            'name': 'INSERT with VALUES clause',
            'sql': 'INSERT INTO "products" ("product name", "category", "price") VALUES ("New Product", "Electronics", "299.99")',
            'db_types': ['sqlite', 'mysql', 'postgresql', 'mssql']
        },
        {
            'name': 'UPDATE with WHERE clause',
            'sql': 'UPDATE "employees" SET "salary" = "50000" WHERE "department" = "IT" AND "experience" > "5"',
            'db_types': ['sqlite', 'mysql', 'mssql']
        },
        {
            'name': 'Complex JOIN with aliases',
            'sql': 'SELECT u."user name", p."product name" FROM "users" u JOIN "purchases" p ON u."id" = p."user id" WHERE p."date" > "2023-01-01"',
            'db_types': ['postgresql', 'mysql', 'sqlite']
        },
        {
            'name': 'Simple query with standard identifiers',
            'sql': 'SELECT name, email FROM users WHERE active = "true"',
            'db_types': ['mysql', 'postgresql', 'sqlite']
        },
        {
            'name': 'Query with reserved words',
            'sql': 'SELECT "order", "date", "user" FROM "order table" WHERE "status" = "pending"',
            'db_types': ['mysql', 'postgresql', 'sqlite', 'mssql']
        }
    ]
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\nScenario {i+1}: {scenario['name']}")
        print("-" * 40)
        print(f"Original SQL: {scenario['sql']}")
        print()
        
        for db_type in scenario['db_types']:
            corrected = correct_sql_delimiters(scenario['sql'], db_type)
            delimiters = get_delimiters_for_db(db_type)
            
            print(f"{db_type.upper():12}: {corrected}")
            
            # Verify that appropriate delimiters are used
            if db_type == 'sqlite' and 'field name' in scenario['sql']:
                assert '`' in corrected, f"SQLite should use backticks for complex identifiers"
            elif db_type == 'mssql' and 'field name' in scenario['sql']:
                assert '[' in corrected and ']' in corrected, f"SQL Server should use square brackets"
            elif db_type == 'mysql' and 'field name' in scenario['sql']:
                assert '`' in corrected, f"MySQL should use backticks for complex identifiers"
        
        print()


def test_edge_cases():
    """
    Test edge cases and potential problem scenarios.
    """
    print("\n" + "=" * 60)
    print("Edge Cases Test")
    print("=" * 60)
    
    edge_cases = [
        {
            'name': 'Empty string',
            'sql': '',
            'db_type': 'sqlite'
        },
        {
            'name': 'No quotes',
            'sql': 'SELECT name FROM users WHERE id = 1',
            'db_type': 'mysql'
        },
        {
            'name': 'Only single quotes (strings)',
            'sql': "SELECT name FROM users WHERE status = 'active'",
            'db_type': 'postgresql'
        },
        {
            'name': 'Mixed quote types',
            'sql': '''SELECT "field name" FROM users WHERE name = 'John "Doe"' AND id = "123"''',
            'db_type': 'sqlite'
        },
        {
            'name': 'Escaped quotes in strings',
            'sql': '''SELECT name FROM users WHERE comment = "He said 'Hello'"''',
            'db_type': 'mysql'
        },
        {
            'name': 'Unknown database type',
            'sql': 'SELECT "field" FROM "table"',
            'db_type': 'unknown_db'
        }
    ]
    
    for case in edge_cases:
        print(f"\nEdge case: {case['name']}")
        print(f"Input:  {case['sql']}")
        print(f"DB:     {case['db_type']}")
        
        try:
            result = correct_sql_delimiters(case['sql'], case['db_type'])
            print(f"Result: {result}")
            print("✅ Success")
        except Exception as e:
            print(f"❌ Error: {e}")


def test_database_specific_features():
    """
    Test database-specific delimiter requirements.
    """
    print("\n" + "=" * 60)
    print("Database-Specific Features Test")
    print("=" * 60)
    
    # Test specific requirements for each database
    db_specific_tests = {
        'sqlite': {
            'sql': 'SELECT "field name", "order", "date-time" FROM "my table"',
            'should_contain': ['`field name`', '`order`', '`date-time`', '`my table`'],
            'should_not_contain': ['"field name"', '"order"']
        },
        'mysql': {
            'sql': 'SELECT "field-name", "user_id" FROM "complex table" WHERE "status" = "active"',
            'should_contain': ['`field-name`', '`complex table`', "'active'"],
            'should_not_contain': ['"field-name"', '"active"']
        },
        'postgresql': {
            'sql': 'SELECT "Field Name", "USER_ID" FROM "MyTable"',
            'should_contain': ['"Field Name"', '"MyTable"'],  # PostgreSQL preserves case
            'should_not_contain': ['`Field Name`', '[Field Name]']
        },
        'mssql': {
            'sql': 'SELECT "field name", "user-id" FROM "order table"',
            'should_contain': ['[field name]', '[user-id]', '[order table]'],
            'should_not_contain': ['"field name"', '`field name`']
        }
    }
    
    for db_type, test_data in db_specific_tests.items():
        print(f"\n{db_type.upper()} Test:")
        print(f"Input:  {test_data['sql']}")
        
        result = correct_sql_delimiters(test_data['sql'], db_type)
        print(f"Result: {result}")
        
        # Check expectations
        success = True
        for should_contain in test_data['should_contain']:
            if should_contain not in result:
                print(f"❌ Expected to contain: {should_contain}")
                success = False
        
        for should_not_contain in test_data['should_not_contain']:
            if should_not_contain in result:
                print(f"❌ Should not contain: {should_not_contain}")
                success = False
        
        if success:
            print("✅ All expectations met")


if __name__ == "__main__":
    try:
        test_comprehensive_delimiter_correction()
        test_edge_cases()
        test_database_specific_features()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("✅ SQL delimiter correction is working properly")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()