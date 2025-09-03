#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import requests
import json

# Test cases con diverse query
test_cases = [
    {
        "name": "Division ratio (original query)",
        "sql": """SELECT "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)"
FROM frpm
WHERE "Educational Option Type" = 'Continuation School'
  AND "Free Meal Count (Ages 5-17)" IS NOT NULL
  AND "Enrollment (Ages 5-17)" IS NOT NULL
  AND "Enrollment (Ages 5-17)" != 0
ORDER BY "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)" ASC
LIMIT 3""",
        "expected_column": "free_meal_rate"  # or similar semantic name
    },
    {
        "name": "Multiple calculations",
        "sql": """SELECT 
    "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)",
    "Free Meal Count (Ages 5-17)" + "FRPM Count (Ages 5-17)"
FROM frpm
LIMIT 2""",
        "expected_columns": ["free_meal_rate", "total_meal_count"]  # or similar
    },
    {
        "name": "Query with existing alias",
        "sql": """SELECT 
    "School Name",
    "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)" AS meal_ratio
FROM frpm
LIMIT 2""",
        "expected_columns": ["School Name", "meal_ratio"]
    }
]

def test_query(test_case):
    """Test a single query case"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_case['name']}")
    print(f"{'='*60}")
    
    # Request payload
    payload = {
        "workspace_id": 1,
        "sql": test_case["sql"],
        "page": 0,
        "page_size": 10,
        "sort_model": None,
        "filter_model": None
    }
    
    # Make the request
    url = "http://localhost:8020/execute-query"
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending request...")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Response status: {response.status_code}")
        print(f"✓ Total rows: {result.get('total_rows', 0)}")
        print(f"✓ Columns: {result.get('columns', [])}")
        print(f"✓ Data rows returned: {len(result.get('data', []))}")
        
        # Check column names
        columns = result.get('columns', [])
        if 'expected_column' in test_case:
            print(f"\nExpected column pattern: {test_case['expected_column']}")
            print(f"Actual columns: {columns}")
        elif 'expected_columns' in test_case:
            print(f"\nExpected columns: {test_case['expected_columns']}")
            print(f"Actual columns: {columns}")
        
        # Show sample data
        if result.get('data'):
            print("\nFirst row data:")
            first_row = result.get('data')[0]
            for key, value in first_row.items():
                print(f"  {key}: {value}")
            
            # Verify column names match data keys
            data_keys = list(first_row.keys())
            if set(columns) == set(data_keys):
                print("\n✓ SUCCESS: Column names match data keys!")
            else:
                print(f"\n✗ WARNING: Column mismatch!")
                print(f"  Columns array: {columns}")
                print(f"  Data keys: {data_keys}")
        else:
            print("\n✗ No data returned!")
            
        if result.get('error'):
            print(f"\n✗ Error: {result['error']}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse response: {e}")
        print(f"Response text: {response.text}")

# Run all test cases
print("Testing Semantic Alias Generation")
print("="*60)

for test_case in test_cases:
    test_query(test_case)

print("\n" + "="*60)
print("All tests completed!")