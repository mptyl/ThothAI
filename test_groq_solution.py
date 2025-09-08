#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Soluzione per Groq con PydanticAI in Thoth
"""

import os
import asyncio
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel

# Usa l'API key dal config
GROQ_API_KEY = "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"
os.environ['GROQ_API_KEY'] = GROQ_API_KEY


async def test_groq_for_sql():
    """Test Groq per generazione SQL come in Thoth"""
    
    # Crea modello Groq
    model = GroqModel('llama-3.3-70b-versatile')
    
    # Agent per SQL generation (come in Thoth)
    agent = Agent(
        model=model,
        system_prompt="""You are a SQL expert. Generate SQL queries for a California schools database.
        Return ONLY the SQL query, no explanations."""
    )
    
    # Test
    question = "Please list the lowest three eligible free rates for students aged 5-17 in continuation schools."
    result = await agent.run(question)
    
    print("Question:", question)
    print("\nGenerated SQL:")
    print(result.output)
    
    print("\n✅ Groq funziona! Il problema era probabilmente:")
    print("1. Modelli deprecati (usa llama-3.3-70b-versatile)")
    print("2. Tentativo di usare output strutturato (non supportato)")
    print("3. Usa result.output per accedere al testo generato")


if __name__ == "__main__":
    asyncio.run(test_groq_for_sql())