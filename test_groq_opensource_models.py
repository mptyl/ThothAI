#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Test modelli open source disponibili su Groq
"""

import os
import asyncio
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel

# API key dal config
GROQ_API_KEY = "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"
os.environ['GROQ_API_KEY'] = GROQ_API_KEY


async def test_model(model_name: str, test_query: str = "Generate SQL to count all schools"):
    """Test singolo modello"""
    try:
        model = GroqModel(model_name)
        agent = Agent(
            model=model,
            system_prompt='You are a SQL expert. Generate only the SQL query, no explanations.'
        )
        
        result = await agent.run(test_query)
        return True, result.output[:100] + "..." if len(result.output) > 100 else result.output
    except Exception as e:
        return False, str(e)[:100]


async def main():
    print("=" * 70)
    print("TEST MODELLI OPEN SOURCE SU GROQ")
    print("=" * 70)
    
    # Lista completa modelli Groq (aggiornata)
    models = {
        "Meta Llama 3.3": [
            "llama-3.3-70b-versatile",
            "llama-3.3-70b-specdec",
        ],
        "Meta Llama 3.2": [
            "llama-3.2-1b-preview",
            "llama-3.2-3b-preview",
            "llama-3.2-11b-text-preview",
            "llama-3.2-90b-text-preview",
            "llama-3.2-11b-vision-preview",
            "llama-3.2-90b-vision-preview",
        ],
        "Meta Llama 3.1": [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",  # Potrebbe essere deprecato
            "llama-3.1-70b-specdec",
            "llama-3.1-405b-reasoning",
        ],
        "Meta Llama 3": [
            "llama3-8b-8192",
            "llama3-70b-8192",
            "llama3-groq-8b-8192-tool-use-preview",
            "llama3-groq-70b-8192-tool-use-preview",
        ],
        "Mixtral": [
            "mixtral-8x7b-32768",  # Potrebbe essere deprecato
            "mixtral-8x22b-32768",
        ],
        "Google Gemma": [
            "gemma-7b-it",
            "gemma2-9b-it",
        ],
        "Autres": [
            "deepseek-r1-distill-llama-70b",
            "llama-guard-3-8b",
            "llava-v1.5-7b-4096-preview",
        ]
    }
    
    working_models = []
    
    for category, model_list in models.items():
        print(f"\n{category}:")
        print("-" * 40)
        
        for model_name in model_list:
            success, output = await test_model(model_name)
            
            if success:
                print(f"✅ {model_name}")
                print(f"   Output: {output}")
                working_models.append(model_name)
            else:
                if "decommissioned" in output:
                    print(f"❌ {model_name} - DEPRECATO")
                elif "not found" in output.lower():
                    print(f"❌ {model_name} - NON TROVATO")
                else:
                    print(f"❌ {model_name} - ERRORE: {output}")
    
    print("\n" + "=" * 70)
    print("MODELLI FUNZIONANTI:")
    print("=" * 70)
    
    if working_models:
        print("\nModelli open source disponibili su Groq:")
        for i, model in enumerate(working_models, 1):
            print(f"{i}. {model}")
        
        print("\n🎯 RACCOMANDAZIONI PER THOTH:")
        print("-" * 40)
        
        # Raccomandazioni basate sui modelli funzionanti
        if "llama-3.3-70b-versatile" in working_models:
            print("1. MIGLIORE: llama-3.3-70b-versatile (più recente, versatile)")
        if "llama3-70b-8192" in working_models:
            print("2. ALTERNATIVA: llama3-70b-8192 (stabile, buone prestazioni)")
        if "mixtral-8x22b-32768" in working_models:
            print("3. PER CONTESTI LUNGHI: mixtral-8x22b-32768 (32K token)")
        if "llama-3.2-3b-preview" in working_models:
            print("4. VELOCE: llama-3.2-3b-preview (modello piccolo, risposte rapide)")
        
        print("\n📝 CONFIGURAZIONE PER THOTH:")
        print("-" * 40)
        print("Nel tuo admin panel, configura l'AI model con:")
        print(f"- Provider: GROQ")
        print(f"- Specific Model: {working_models[0]}")
        print(f"- API Key: {GROQ_API_KEY}")
        
    else:
        print("⚠️ Nessun modello funzionante trovato!")
        print("Verifica la connessione o l'API key")


if __name__ == "__main__":
    asyncio.run(main())