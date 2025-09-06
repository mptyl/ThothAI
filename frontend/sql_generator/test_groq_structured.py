#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Test script to diagnose Groq structured output issues with PydanticAI.
"""

import asyncio
import json
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

# Test API key (will be replaced with environment variable in production)
GROQ_API_KEY = "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"

class SQLResult(BaseModel):
    """Simple structured output for SQL generation."""
    sql_query: str = Field(description="The generated SQL query")
    explanation: str = Field(description="Explanation of the query")
    confidence: float = Field(description="Confidence score between 0 and 1")

class SimpleOutput(BaseModel):
    """Even simpler structured output for testing."""
    answer: str = Field(description="The answer to the question")
    number: int = Field(description="A number between 1 and 10")

async def test_groq_capabilities():
    """Test various Groq capabilities with PydanticAI."""
    
    # Initialize Groq model
    model = GroqModel(
        'llama-3.3-70b-versatile',
        provider=GroqProvider(api_key=GROQ_API_KEY)
    )
    
    print("=" * 60)
    print("GROQ STRUCTURED OUTPUT TEST WITH PYDANTIC-AI")
    print("=" * 60)
    
    # Test 1: Simple text generation (should work)
    print("\n1. Testing simple text generation...")
    try:
        text_agent = Agent[str](
            model,
            system_prompt="You are a helpful assistant."
        )
        result = await text_agent.run("What is 2+2?")
        print(f"✓ Text generation works: {result.output}")
        print(f"  Response type: {type(result.output)}")
    except Exception as e:
        print(f"✗ Text generation failed: {e}")
        print(f"  Error type: {type(e).__name__}")
    
    # Test 2: Simple structured output
    print("\n2. Testing simple structured output...")
    try:
        simple_agent = Agent[SimpleOutput](
            model,
            system_prompt="You are a helpful assistant. Always provide structured responses."
        )
        result = await simple_agent.run("What is the capital of France? Pick a random number between 1 and 10.")
        print(f"✓ Simple structured output works:")
        print(f"  - Answer: {result.output.answer}")
        print(f"  - Number: {result.output.number}")
        print(f"  - Type: {type(result.output)}")
    except Exception as e:
        print(f"✗ Simple structured output failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        if hasattr(e, '__cause__'):
            print(f"  Cause: {e.__cause__}")
    
    # Test 3: SQL structured output
    print("\n3. Testing SQL structured output...")
    try:
        sql_agent = Agent[SQLResult](
            model,
            system_prompt="""You are an SQL expert. Generate SQL queries based on user questions.
            Always return a structured response with the SQL query, explanation, and confidence score."""
        )
        result = await sql_agent.run("Show me all users from the users table")
        print(f"✓ SQL structured output works:")
        print(f"  - SQL: {result.output.sql_query}")
        print(f"  - Explanation: {result.output.explanation}")
        print(f"  - Confidence: {result.output.confidence}")
    except Exception as e:
        print(f"✗ SQL structured output failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        if hasattr(e, '__cause__'):
            print(f"  Cause: {e.__cause__}")
    
    # Test 4: Try with explicit JSON instructions
    print("\n4. Testing with explicit JSON instructions...")
    try:
        json_agent = Agent[SQLResult](
            model,
            system_prompt="""You are an SQL expert. Generate SQL queries based on user questions.
            
            IMPORTANT: You MUST return your response as a valid JSON object with these exact fields:
            - sql_query: The generated SQL query
            - explanation: Explanation of the query
            - confidence: Confidence score between 0 and 1
            
            Example response format:
            {
                "sql_query": "SELECT * FROM users",
                "explanation": "This query selects all users",
                "confidence": 0.95
            }"""
        )
        result = await json_agent.run(
            "Show me all users from the users table. Return as JSON."
        )
        print(f"✓ JSON-instructed structured output works:")
        print(f"  - SQL: {result.output.sql_query}")
        print(f"  - Type: {type(result.output)}")
    except Exception as e:
        print(f"✗ JSON-instructed structured output failed: {e}")
        if hasattr(e, '__cause__'):
            print(f"  Cause: {e.__cause__}")
    
    # Test 5: Test with manual JSON parsing fallback
    print("\n5. Testing manual JSON parsing fallback...")
    try:
        manual_agent = Agent[str](
            model,
            system_prompt="""You are an SQL expert. Generate SQL queries based on user questions.
            
            You MUST return ONLY a valid JSON object (no markdown, no extra text) with these fields:
            - sql_query: The generated SQL query
            - explanation: Explanation of the query  
            - confidence: Confidence score between 0 and 1"""
        )
        result = await manual_agent.run("Show me all users from the users table")
        
        # Try to parse the text response as JSON
        if isinstance(result.output, str):
            try:
                # Clean up potential markdown formatting
                json_str = result.output
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                
                parsed = json.loads(json_str.strip())
                print(f"✓ Manual JSON parsing works:")
                print(f"  - SQL: {parsed.get('sql_query')}")
                print(f"  - Explanation: {parsed.get('explanation')}")
                print(f"  - Confidence: {parsed.get('confidence')}")
            except json.JSONDecodeError as je:
                print(f"✗ JSON parsing failed: {je}")
                print(f"  Raw response: {result.output[:200]}...")
        else:
            print(f"  Response type: {type(result.output)}")
    except Exception as e:
        print(f"✗ Manual approach failed: {e}")
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_groq_capabilities())