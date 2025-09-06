#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Simple test to understand PydanticAI Agent result structure
"""

import os
import asyncio
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel

# Set the API key
GROQ_API_KEY = "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"
os.environ['GROQ_API_KEY'] = GROQ_API_KEY


async def main():
    """Test basic Groq functionality and understand result structure"""
    print("Testing Groq with PydanticAI - Understanding Result Structure")
    print("=" * 60)
    
    try:
        # Create a simple agent with Groq
        model = GroqModel('llama-3.3-70b-versatile')
        agent = Agent(
            model=model,
            system_prompt='You are a helpful assistant. Answer in one sentence.',
        )
        
        # Test basic response
        print("\n1. Running simple query...")
        result = await agent.run('What is 2+2?')
        
        # Explore result attributes
        print("\n2. Result type:", type(result))
        print("\n3. Result attributes:", [attr for attr in dir(result) if not attr.startswith('_')])
        
        # Try to access the content
        print("\n4. Trying different ways to access result:")
        
        # Check if it's directly accessible
        try:
            print(f"   Direct access: {result}")
        except Exception as e:
            print(f"   Direct access failed: {e}")
        
        # Check for common attributes
        for attr in ['data', 'text', 'content', 'output', 'result', 'value', 'message', 'response']:
            if hasattr(result, attr):
                print(f"   Found attribute '{attr}': {getattr(result, attr)}")
        
        # Check if it's callable or has a method
        for method in ['get', 'as_text', 'to_string', 'value']:
            if hasattr(result, method) and callable(getattr(result, method)):
                try:
                    value = getattr(result, method)()
                    print(f"   Method '{method}()': {value}")
                except:
                    pass
        
        print("\n5. Full result object inspection:")
        print(result)
        
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    print("\n" + "=" * 60)
    print("Test", "PASSED" if success else "FAILED")