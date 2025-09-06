#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Integration test for Groq with ThothAI SQL generation.
Tests the GroqAdapter with realistic SQL generation scenarios.
"""

import asyncio
import json
from typing import Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from agents.core.groq_adapter import (
    GroqModelWrapper, 
    GroqStructuredAdapter,
    create_groq_agent_with_fallback
)

# Test API key (will be replaced with environment variable in production)
GROQ_API_KEY = "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"

# Define the same result models used in ThothAI
class TestGeneratorResult(BaseModel):
    """Result model for SQL generation similar to ThothAI."""
    generated_sql: str = Field(description="The generated SQL query")
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    explanation: str = Field(description="Explanation of the SQL query")
    tables_used: List[str] = Field(description="List of tables referenced in the query")
    
class EvaluatorResult(BaseModel):
    """Result model for SQL evaluation."""
    is_valid: bool = Field(description="Whether the SQL is valid")
    syntax_score: float = Field(description="Syntax correctness score (0-1)")
    semantic_score: float = Field(description="Semantic correctness score (0-1)")
    improvements: List[str] = Field(description="Suggested improvements")
    final_sql: str = Field(description="The final improved SQL query")

async def test_groq_sql_generation():
    """Test Groq with SQL generation using the adapter."""
    
    print("=" * 60)
    print("GROQ SQL GENERATION TEST WITH ADAPTER")
    print("=" * 60)
    
    # Initialize Groq wrapper
    groq_wrapper = GroqModelWrapper('llama-3.3-70b-versatile', GROQ_API_KEY)
    
    # Test 1: SQL Generation with structured output
    print("\n1. Testing SQL Generation Agent...")
    try:
        # Create a text agent with JSON instructions
        sql_agent = groq_wrapper.create_agent(
            result_type=None,  # Use text mode
            system_prompt="""You are an expert SQL generator for educational databases.
            
You MUST return your response as a valid JSON object with these exact fields:
- generated_sql: The SQL query
- confidence_score: A number between 0 and 1
- explanation: Explanation of the query
- tables_used: Array of table names used

Example response:
{
    "generated_sql": "SELECT * FROM students WHERE grade > 90",
    "confidence_score": 0.95,
    "explanation": "This query selects all students with grades above 90",
    "tables_used": ["students"]
}

Return ONLY the JSON object, no markdown or extra text."""
        )
        
        # Run the agent
        result = await sql_agent.run(
            "Show me all students who are enrolled in virtual schools"
        )
        
        # Parse the response
        if hasattr(result, 'output') and isinstance(result.output, str):
            parsed_result = GroqStructuredAdapter.parse_json_response(
                result.output, 
                TestGeneratorResult
            )
            
            if parsed_result:
                print("✓ SQL Generation successful:")
                print(f"  - SQL: {parsed_result.generated_sql}")
                print(f"  - Confidence: {parsed_result.confidence_score}")
                print(f"  - Tables: {parsed_result.tables_used}")
                print(f"  - Explanation: {parsed_result.explanation[:100]}...")
            else:
                print("✗ Failed to parse structured output")
                print(f"  Raw response: {result.output[:200]}...")
        else:
            print("✗ Unexpected response format")
            
    except Exception as e:
        print(f"✗ SQL Generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: SQL Evaluation with structured output
    print("\n2. Testing SQL Evaluation Agent...")
    try:
        eval_agent = groq_wrapper.create_agent(
            result_type=None,
            system_prompt="""You are an expert SQL evaluator and optimizer.
            
Evaluate the given SQL query and return a JSON object with:
- is_valid: boolean indicating if SQL is valid
- syntax_score: number between 0 and 1 for syntax correctness
- semantic_score: number between 0 and 1 for semantic correctness
- improvements: array of suggested improvements
- final_sql: the improved SQL query

Example response:
{
    "is_valid": true,
    "syntax_score": 0.9,
    "semantic_score": 0.85,
    "improvements": ["Add index hint", "Use JOIN instead of subquery"],
    "final_sql": "SELECT * FROM students WHERE school_type = 'virtual'"
}

Return ONLY the JSON object."""
        )
        
        test_sql = "SELECT * FROM students WHERE school_type = 'virtual'"
        result = await eval_agent.run(
            f"Evaluate this SQL query: {test_sql}"
        )
        
        if hasattr(result, 'output') and isinstance(result.output, str):
            parsed_result = GroqStructuredAdapter.parse_json_response(
                result.output,
                EvaluatorResult
            )
            
            if parsed_result:
                print("✓ SQL Evaluation successful:")
                print(f"  - Valid: {parsed_result.is_valid}")
                print(f"  - Syntax Score: {parsed_result.syntax_score}")
                print(f"  - Semantic Score: {parsed_result.semantic_score}")
                print(f"  - Improvements: {parsed_result.improvements}")
            else:
                print("✗ Failed to parse evaluation result")
        else:
            print("✗ Unexpected response format")
            
    except Exception as e:
        print(f"✗ SQL Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Using the convenience function
    print("\n3. Testing convenience function...")
    try:
        # This would be the ideal way if PydanticAI supported wrapping
        # For now, we demonstrate the manual approach
        simple_agent = create_groq_agent_with_fallback(
            model_name='llama-3.3-70b-versatile',
            api_key=GROQ_API_KEY,
            result_type=None,  # Text mode for Groq
            system_prompt="You are a helpful SQL assistant. Always return valid JSON."
        )
        
        result = await simple_agent.run("Create a simple SELECT query")
        print(f"✓ Convenience function works")
        if hasattr(result, 'output'):
            print(f"  Response preview: {result.output[:100]}...")
            
    except Exception as e:
        print(f"✗ Convenience function failed: {e}")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS FOR THOTH INTEGRATION")
    print("=" * 60)
    print("""
1. GROQ LIMITATION: Groq doesn't support native structured output
   - Must use JSON string responses and parse them
   - Cannot use Agent[ResultType] directly
   
2. SOLUTION APPROACH:
   - Use Agent[str] with JSON-formatted system prompts
   - Parse responses with GroqStructuredAdapter.parse_json_response()
   - Add error handling for parsing failures
   
3. IMPLEMENTATION STEPS:
   a) Modify agents to detect Groq provider
   b) When Groq detected, use text mode with JSON prompts
   c) Parse JSON responses into Pydantic models
   d) Add fallback to other providers for critical operations
   
4. CODE PATTERN:
   ```python
   if provider == 'GROQ':
       # Use text agent with JSON instructions
       agent = Agent[str](model, system_prompt=json_prompt)
       result = await agent.run(prompt)
       parsed = GroqStructuredAdapter.parse_json_response(
           result.output, ResultModel
       )
   else:
       # Use normal structured output
       agent = Agent[ResultModel](model, system_prompt=prompt)
       result = await agent.run(prompt)
       parsed = result.output
   ```
   
5. TESTING:
   - Always test JSON parsing with various response formats
   - Add retry logic for parsing failures
   - Consider caching successful patterns
    """)

if __name__ == "__main__":
    asyncio.run(test_groq_sql_generation())