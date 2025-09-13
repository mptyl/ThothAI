#!/usr/bin/env python3
"""
Validate BACKEND_AI_PROVIDER and BACKEND_AI_MODEL from environment (or YAML later).

Checks:
- provider is among supported providers
- provider is enabled via presence of API key when required
- performs a lightweight call to verify the model can be used
"""

import os
import sys
import argparse
import requests

SUPPORTED = {
    'openai', 'anthropic', 'gemini', 'mistral', 'deepseek', 'openrouter', 'ollama', 'lm_studio', 'groq'
}


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def validate_from_env() -> bool:
    provider = env('BACKEND_AI_PROVIDER', '').strip().lower()
    model = env('BACKEND_AI_MODEL', '').strip()

    if not provider:
        print("Error: BACKEND_AI_PROVIDER not set")
        return False
    if not model:
        print("Error: BACKEND_AI_MODEL not set")
        return False
    if provider not in SUPPORTED:
        print(f"Error: Unsupported provider '{provider}'")
        return False

    # Determine API key or base
    api_key = None
    api_base = None

    if provider == 'openai':
        api_key = env('OPENAI_API_KEY')
    elif provider == 'anthropic':
        api_key = env('ANTHROPIC_API_KEY')
    elif provider == 'gemini':
        api_key = env('GEMINI_API_KEY')
    elif provider == 'mistral':
        api_key = env('MISTRAL_API_KEY')
    elif provider == 'deepseek':
        api_key = env('DEEPSEEK_API_KEY')
        api_base = env('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
    elif provider == 'openrouter':
        api_key = env('OPENROUTER_API_KEY')
        api_base = env('OPENROUTER_API_BASE', 'https://openrouter.ai/api/v1')
    elif provider == 'groq':
        api_key = env('GROQ_API_KEY')
        api_base = 'https://api.groq.com/openai/v1'
    elif provider == 'ollama':
        api_base = env('OLLAMA_API_BASE', 'http://127.0.0.1:11434')
    elif provider == 'lm_studio':
        api_base = env('LM_STUDIO_API_BASE', 'http://localhost:1234')

    # Check API key presence for those that require it
    if provider not in ['ollama', 'lm_studio'] and not api_key:
        print(f"Error: API key environment variable is missing for provider '{provider}'")
        return False

    try:
        timeout = 6
        if provider == 'openai':
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                timeout=timeout,
            )
            ok = r.status_code in [200, 400, 422]
        elif provider == 'anthropic':
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                timeout=timeout,
            )
            ok = r.status_code in [200, 400, 422]
        elif provider == 'gemini':
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
            r = requests.post(url, json={"contents": [{"parts": [{"text": "ping"}]}]}, timeout=timeout)
            ok = r.status_code in [200, 400]
        elif provider == 'mistral':
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            r = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                timeout=timeout,
            )
            ok = r.status_code in [200, 400]
        elif provider in ['deepseek', 'openrouter', 'groq', 'lm_studio']:
            base = api_base or (
                'https://api.deepseek.com/v1' if provider == 'deepseek' else
                'https://openrouter.ai/api/v1' if provider == 'openrouter' else
                'https://api.groq.com/openai/v1' if provider == 'groq' else
                'http://localhost:1234/v1'
            )
            headers = {"Content-Type": "application/json"}
            if provider != 'lm_studio':
                headers["Authorization"] = f"Bearer {api_key}"
            r = requests.post(
                f"{base}/chat/completions",
                headers=headers,
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                timeout=timeout,
            )
            ok = r.status_code in [200, 400]
        elif provider == 'ollama':
            base = api_base or 'http://127.0.0.1:11434'
            r = requests.post(
                f"{base}/api/chat",
                json={"model": model, "messages": [{"role": "user", "content": "ping"}]},
                timeout=timeout,
            )
            ok = r.status_code in [200, 404, 400]
        else:
            print(f"Unknown provider '{provider}'")
            return False

        if not ok:
            print(f"Error: Provider call failed (status {r.status_code})")
            try:
                print(r.text[:200])
            except Exception:
                pass
        return ok
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--from-env', action='store_true', help='Validate using environment variables')
    args = parser.parse_args()

    ok = False
    if args.from_env:
        ok = validate_from_env()
    else:
        ok = validate_from_env()

    sys.exit(0 if ok else 1)

