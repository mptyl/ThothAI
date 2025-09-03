#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import requests
import json

# The SQL query that should return 3 results
sql_query = """SELECT "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)"
FROM frpm
WHERE "Educational Option Type" = 'Continuation School'
  AND "Free Meal Count (Ages 5-17)" IS NOT NULL
  AND "Enrollment (Ages 5-17)" IS NOT NULL
  AND "Enrollment (Ages 5-17)" != 0
ORDER BY "Free Meal Count (Ages 5-17)" / "Enrollment (Ages 5-17)" ASC
LIMIT 3"""

# Request payload
payload = {
    "workspace_id": 1,
    "sql": sql_query,
    "page": 0,
    "page_size": 10,
    "sort_model": None,
    "filter_model": None
}

# Make the request
url = "http://localhost:8020/execute-query"
headers = {"Content-Type": "application/json"}

print(f"Sending request to {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    print(f"\nResponse status: {response.status_code}")
    print(f"Total rows: {result.get('total_rows', 0)}")
    print(f"Columns: {result.get('columns', [])}")
    print(f"Data rows returned: {len(result.get('data', []))}")
    
    if result.get('data'):
        print("\nFirst few rows:")
        for i, row in enumerate(result.get('data', [])[:3]):
            print(f"Row {i}: {row}")
    else:
        print("\nNo data returned!")
        
    if result.get('error'):
        print(f"\nError: {result['error']}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
except json.JSONDecodeError as e:
    print(f"Failed to parse response: {e}")
    print(f"Response text: {response.text}")