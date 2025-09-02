#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
Simple test script for error injection system.
Tests TEST01 pattern to verify error formatting.
"""

import asyncio
import aiohttp
import json


async def test_error_injection():
    """Test the error injection with TEST01 pattern."""
    
    # API configuration
    base_url = "http://localhost:8180"  # Local development port
    endpoint = "/generate-sql"
    
    # Test request with TEST01 pattern
    test_request = {
        "question": "TEST01 - Testing validation error message",
        "workspace_id": 1,
        "functionality_level": "BASIC",
        "flags": {
            "use_schema": True,
            "use_examples": False,
            "use_lsh": False,
            "use_vector": False
        }
    }
    
    print("=" * 60)
    print("TESTING ERROR INJECTION SYSTEM")
    print("=" * 60)
    print(f"\nSending request with question: {test_request['question']}")
    print(f"Expected: Validation failed error in CRITICAL_ERROR format")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}{endpoint}",
                json=test_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"\nResponse Status: {response.status}")
                print(f"Content Type: {response.headers.get('Content-Type', 'Not specified')}")
                print("\n" + "-" * 60)
                print("Response Body:")
                print("-" * 60)
                
                # Read streaming response
                full_response = ""
                async for chunk in response.content:
                    decoded = chunk.decode('utf-8')
                    full_response += decoded
                    print(decoded, end='')
                
                print("\n" + "-" * 60)
                
                # Verify the response format
                print("\nVERIFICATION:")
                if "CRITICAL_ERROR:" in full_response:
                    print("✓ CRITICAL_ERROR prefix found")
                    
                    # Extract and parse JSON part
                    try:
                        json_start = full_response.index("CRITICAL_ERROR:") + len("CRITICAL_ERROR:")
                        json_end = full_response.index("\n", json_start)
                        json_str = full_response[json_start:json_end]
                        error_data = json.loads(json_str)
                        
                        print("✓ JSON parsing successful")
                        print(f"  - Type: {error_data.get('type')}")
                        print(f"  - Component: {error_data.get('component')}")
                        print(f"  - Message: {error_data.get('message')}")
                        
                        if "TEST01" in error_data.get('message', ''):
                            print("✓ TEST01 marker found in message")
                        else:
                            print("✗ TEST01 marker NOT found in message")
                            
                    except (ValueError, json.JSONDecodeError) as e:
                        print(f"✗ JSON parsing failed: {e}")
                else:
                    print("✗ CRITICAL_ERROR prefix NOT found")
                
                if "ERROR:" in full_response or "validation failed" in full_response.lower():
                    print("✓ Error message format verified")
                else:
                    print("✗ Expected error message not found")
                    
                print("\n" + "=" * 60)
                print("TEST COMPLETED")
                print("=" * 60)
                
    except aiohttp.ClientError as e:
        print(f"\n✗ Connection error: {e}")
        print("Make sure the SQL Generator service is running on port 8180")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(test_error_injection())