#!/usr/bin/env python3
"""
Validate BACKEND_AI_PROVIDER and BACKEND_AI_MODEL from environment or YAML config.

Checks:
- provider is among supported providers
- provider is enabled via presence of API key when required
- performs a lightweight call to verify the model can be used
"""

import os
import sys
import argparse
import requests
from typing import Any, Dict, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # Optional dependency; we also have a naive parser fallback

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


def _extract_from_yaml(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """
    From loaded YAML config, extract (provider, model, provider_cfg).
    Returns None if mandatory fields are missing.
    """
    backend = (cfg or {}).get('backend_ai_model') or {}
    providers = (cfg or {}).get('ai_providers') or {}

    ai_provider = (backend.get('ai_provider') or '').strip()
    ai_model = (backend.get('ai_model') or '').strip()
    if not ai_provider or not ai_model:
        return None
    provider_cfg = providers.get(ai_provider) or {}
    return ai_provider, ai_model, provider_cfg


def _naive_parse_yaml(path: str) -> Optional[Dict[str, Any]]:
    """
    Extremely lightweight YAML parser for just what we need if PyYAML isn't available.
    Supports the subset used in config.yml: top-level maps and nested maps by indentation.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return None

    root: Dict[str, Any] = {}
    stack = [( -1, root )]  # list of (indent, dict)

    def current_dict_for_indent(indent: int) -> Dict[str, Any]:
        # pop until parent has lower indent
        while stack and stack[-1][0] >= indent:
            stack.pop()
        return stack[-1][1] if stack else root

    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        indent = len(raw) - len(raw.lstrip(' '))
        line = raw.strip()
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        parent = current_dict_for_indent(indent)
        if val == '':
            # start of nested map
            new_map: Dict[str, Any] = {}
            parent[key] = new_map
            stack.append((indent, new_map))
        else:
            # scalar
            # coerce booleans
            if val.lower() in ('true', 'false'):
                parent[key] = (val.lower() == 'true')
            else:
                parent[key] = val
    return root


def validate_from_config(path: str) -> bool:
    """
    Validate using config.yml.local values. Extracts backend_ai_model and provider settings.
    """
    cfg: Optional[Dict[str, Any]] = None
    if yaml is not None:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)  # type: ignore
        except Exception as e:
            print(f"Error loading YAML: {e}")
            return False
    else:
        cfg = _naive_parse_yaml(path)
        if cfg is None:
            print("Error: Could not parse YAML and PyYAML is not installed")
            return False

    extracted = _extract_from_yaml(cfg)
    if not extracted:
        print("Error: backend_ai_model.ai_provider or ai_model missing in config")
        return False

    provider, model, provider_cfg = extracted
    provider = provider.lower().strip()
    if provider not in SUPPORTED:
        print(f"Error: Unsupported provider '{provider}' in config")
        return False

    # Check enabled and key requirements
    if not provider_cfg.get('enabled', False):
        print(f"Error: Provider '{provider}' is not enabled in config")
        return False

    api_key = provider_cfg.get('api_key')
    api_base = provider_cfg.get('api_base')
    if provider not in ['ollama', 'lm_studio'] and not api_key:
        print(f"Error: Provider '{provider}' requires an API key in config")
        return False

    # Perform the same live validation calls but using config values
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
    parser.add_argument('--from-config', metavar='PATH', nargs='?', const='config.yml.local', help='Validate using YAML config (default: config.yml.local)')
    args = parser.parse_args()

    ok = False
    if args.from_config is not None:
        ok = validate_from_config(args.from_config)
    elif args.from_env:
        ok = validate_from_env()
    else:
        # Default to config if present, else env
        default_cfg = 'config.yml.local'
        if os.path.exists(default_cfg):
            ok = validate_from_config(default_cfg)
        else:
            ok = validate_from_env()

    sys.exit(0 if ok else 1)
