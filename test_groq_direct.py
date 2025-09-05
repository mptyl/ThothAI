#!/usr/bin/env python3
"""
Test script for direct Groq API calls
"""

import os
import json
from groq import Groq

# Get API key from environment
api_key = os.getenv('GROQ_API_KEY', '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')

# Initialize Groq client
client = Groq(api_key=api_key)

# First, list available models
print("Available Groq models:")
print("-" * 50)
try:
    models = client.models.list()
    for model in models.data:
        print(f"- {model.id}")
except Exception as e:
    print(f"Error listing models: {e}")

print("\n" + "=" * 50 + "\n")

# Test with different model names
test_models = [
    "openai/gpt-oss-20b",     # What's configured
    "openai/gpt-oss-120b",    # What's configured  
    "moonshotai/kimi-k2-instruct",  # What's configured
    "llama3-70b-8192",        # Known Groq model
    "mixtral-8x7b-32768",     # Known Groq model
    "llama-3.2-90b-text-preview",  # Newer Groq model
]

# Simple SQL generation prompt
system_prompt = """You are an expert SQL assistant. Generate SQL queries based on user questions."""

user_prompt = """Given the following database schema:
Tables:
- schools (CDSCode, SchoolName, DistrictName, County, SchoolType)

Question: How many schools are exclusively virtual?

Please generate a SQL query to answer this question."""

for model_name in test_models:
    print(f"Testing model: {model_name}")
    print("-" * 30)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=1280,
            top_p=0.95
        )
        
        print(f"✓ Success with {model_name}")
        print(f"Response: {response.choices[0].message.content[:200]}...")
        
    except Exception as e:
        print(f"✗ Failed with {model_name}")
        print(f"  Error: {str(e)[:200]}")
    
    print()