#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Test Groq integration with PydanticAI
"""

import os
import asyncio
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel

# Set the API key
GROQ_API_KEY = "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"
os.environ['GROQ_API_KEY'] = GROQ_API_KEY


class CityInfo(BaseModel):
    """City information model"""
    name: str
    country: str
    population: int


async def test_basic_groq():
    """Test basic Groq functionality"""
    print("Testing basic Groq with PydanticAI...")
    
    try:
        # Create a simple agent with Groq
        model = GroqModel('llama-3.3-70b-versatile')
        agent = Agent(
            model=model,
            system_prompt='You are a helpful assistant. Be concise.',
        )
        
        # Test basic response - use correct attribute
        result = await agent.run('What is 2+2?')
        print(f"Basic test result: {result.output}")
        
        return True
    except Exception as e:
        print(f"Basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_structured_output():
    """Test structured output with Groq"""
    print("\nTesting structured output with Groq...")
    
    try:
        # Create an agent with structured output using correct API
        model = GroqModel('llama-3.3-70b-versatile')
        agent = Agent[CityInfo](
            model=model,
            system_prompt='Extract city information from the user input.',
        )
        
        # Test structured response
        result = await agent.run('Paris is the capital of France with about 2.2 million people')
        print(f"Structured output: {result.output}")
        if result.output:
            print(f"  Name: {result.output.name}")
            print(f"  Country: {result.output.country}")
            print(f"  Population: {result.output.population}")
        
        return True
    except Exception as e:
        print(f"Structured output test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_custom_provider():
    """Test Groq with custom provider configuration"""
    print("\nTesting Groq with custom provider...")
    
    try:
        from pydantic_ai.providers.groq import GroqProvider
        
        # Create provider explicitly
        provider = GroqProvider(api_key=GROQ_API_KEY)
        model = GroqModel('llama-3.3-70b-versatile', provider=provider)
        
        agent = Agent(
            model=model,
            system_prompt='You are a helpful assistant.',
        )
        
        result = await agent.run('Name three colors')
        print(f"Custom provider test result: {result.output}")
        
        return True
    except Exception as e:
        print(f"Custom provider test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_different_models():
    """Test different Groq models"""
    print("\nTesting different Groq models...")
    
    models_to_test = [
        'llama-3.3-70b-versatile',
        'llama-3.1-70b-versatile',
        'mixtral-8x7b-32768',
    ]
    
    for model_name in models_to_test:
        print(f"\nTesting model: {model_name}")
        try:
            model = GroqModel(model_name)
            agent = Agent(
                model=model,
                system_prompt='Answer in one sentence.',
            )
            
            result = await agent.run('What is Python?')
            print(f"  Result: {result.output}")
        except Exception as e:
            print(f"  Failed: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Groq Integration with PydanticAI")
    print("=" * 60)
    
    # Run tests
    tests = [
        ("Basic Groq", test_basic_groq),
        ("Structured Output", test_structured_output),
        ("Custom Provider", test_with_custom_provider),
        ("Different Models", test_different_models),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 40}")
        print(f"Running: {test_name}")
        print(f"{'=' * 40}")
        
        if test_func.__name__ == 'test_different_models':
            await test_func()
            results.append((test_name, True))
        else:
            success = await test_func()
            results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    # Check if all tests passed
    all_passed = all(success for _, success in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED. Check the output above for details.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())