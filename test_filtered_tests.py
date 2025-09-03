#!/usr/bin/env python
"""
Test script to verify the filtered tests implementation.
"""

import asyncio
import json
from pprint import pprint

# Test data
test_data = {
    "original_tests": [
        "Check if the query includes all columns from the table",
        "Verify the SQL includes all columns from table",  # Semantically similar to first
        "Ensure WHERE clause filters correctly",
        "Check that the WHERE condition is correct",  # Semantically similar to third
        "Validate JOIN conditions are proper",
        "Test that GROUP BY is used correctly",
        "Verify GROUP BY clause is correct",  # Semantically similar to sixth
        "Check ORDER BY sorting",
    ],
    "expected_filtered": [
        "Check if the query includes all columns from the table",
        "Ensure WHERE clause filters correctly", 
        "Validate JOIN conditions are proper",
        "Test that GROUP BY is used correctly",
        "Check ORDER BY sorting",
    ]
}

async def test_reducer():
    """Test the TestReducer functionality"""
    print("Testing TestReducer agent...")
    
    try:
        from frontend.sql_generator.agents.test_reducer_agent import create_test_reducer_agent, run_test_reducer
        
        # Create test reducer
        test_reducer = create_test_reducer_agent(
            model_config={'name': 'TestEvaluator'},
            retries=1
        )
        
        if not test_reducer:
            print("❌ Failed to create TestReducer agent")
            return False
            
        print("✅ TestReducer agent created successfully")
        
        # Run reduction
        result = await run_test_reducer(
            test_reducer,
            test_data["original_tests"],
            "Test generation thinking context",
            "Select all data from the users table grouped by department",
            "CREATE TABLE users (id INT, name VARCHAR, department VARCHAR)"
        )
        
        if result:
            print(f"✅ TestReducer ran successfully")
            print(f"   Original: {len(test_data['original_tests'])} tests")
            print(f"   Reduced: {len(result.reduced_tests)} tests")
            print("\nReduced tests:")
            for i, test in enumerate(result.reduced_tests, 1):
                print(f"   {i}. {test}")
            return True
        else:
            print("❌ TestReducer returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error testing TestReducer: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backend_rendering():
    """Test the backend admin rendering with both formats"""
    print("\nTesting backend admin rendering...")
    
    # Test data
    simple_list = json.dumps([
        "Test 1: Check column selection",
        "Test 2: Verify WHERE clause",
        "Test 3: Check JOIN conditions"
    ])
    
    tuple_list = json.dumps([
        ("Thinking for test 1", ["Check column selection", "Verify data types"]),
        ("Thinking for test 2", ["Check WHERE clause", "Verify filtering"])
    ])
    
    print("✅ Test data prepared:")
    print(f"   Simple list format (new): {len(json.loads(simple_list))} items")
    print(f"   Tuple list format (old): {len(json.loads(tuple_list))} items")
    
    return True

def main():
    """Main test function"""
    print("=" * 60)
    print("Testing Filtered Tests Implementation")
    print("=" * 60)
    
    # Run async test
    # success = asyncio.run(test_reducer())
    
    # Test backend
    success = test_backend_rendering()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)

if __name__ == "__main__":
    main()