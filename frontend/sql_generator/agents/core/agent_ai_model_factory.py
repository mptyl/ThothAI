# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Unless required by applicable law or agreed to in writing, software
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
AI model factory for creating PydanticAI model instances.

This module provides functions to create AI model instances based on 
agent configuration, supporting multiple providers like OpenAI, Anthropic,
Mistral, and others.
"""

import os
from typing import Dict, Any

from dotenv import load_dotenv
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.fallback import FallbackModel
from pathlib import Path

# Load environment variables from the correct .env file
is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
project_root = Path(__file__).parent.parent.parent.parent  # Navigate to thoth_ui dir

if is_docker:
    env_path = project_root / '.env.docker'
else:
    env_path = project_root / '.env.local'

if env_path.exists():
    load_dotenv(env_path)


def get_agent_llm_model(agent_config: Dict[str, Any]):
    """
    Creates a new model instance based on configuration.
    
    Args:
        agent_config: Dictionary containing agent configuration with ai_model info
        
    Returns:
        Configured PydanticAI model instance
        
    Raises:
        ValueError: If required API keys or configuration is missing
    """
def get_agent_llm_model(agent_config: dict):
    """Creates a new model instance based on configuration"""
    ai_model = agent_config['ai_model']
    provider = ai_model['basic_model']['provider']

    if provider == 'DEEPSEEK':
        # Assuming Deepseek uses OpenAI compatible API structure
        api_key = ai_model.get('api_key') or os.getenv("DEEPSEEK_API_KEY")
        base_url = ai_model.get('url') or os.getenv("DEEPSEEK_API_BASE")
        if not api_key:
            raise ValueError("Deepseek API key not found in config or environment variables.")
        return OpenAIModel(
            ai_model['specific_model'],
            provider=OpenAIProvider(api_key=api_key, base_url=base_url)
        )
    elif provider in ['MISTRAL', 'CODESTRAL']:
        api_key = ai_model.get('api_key') or os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("Mistral API key not found in config or environment variables.")
        return MistralModel(
            ai_model['specific_model'],
            provider=MistralProvider(api_key=api_key)
        )
    elif provider == 'OLLAMA':
        # Ollama typically doesn't use API keys, relies on base_url
        base_url = ai_model.get('url') or os.getenv("OLLAMA_API_BASE")
        if not base_url:
             raise ValueError("Ollama base URL not found in config or environment variables.")
        # Ensure base_url includes /v1 suffix for OpenAI-compatible endpoint
        if not base_url.endswith('/v1'):
            base_url = base_url.rstrip('/') + '/v1'
        # Assuming Ollama uses OpenAI compatible API structure but without API key
        return OpenAIModel(
            ai_model['specific_model'],
            provider=OpenAIProvider(api_key="ollama", base_url=base_url) # Use dummy api_key for OpenAIProvider
        )
    elif provider == 'OPENAI':
        api_key = ai_model.get('api_key') or os.getenv("OPENAI_API_KEY")     
        if not api_key:
            raise ValueError("OpenAI API key not found in config or environment variables.")
        return OpenAIModel(
            ai_model['specific_model'],
            provider=OpenAIProvider(api_key=api_key)
        )
    elif provider == 'OPENROUTER':
        # Assuming OpenRouter uses OpenAI compatible API structure
        api_key = ai_model.get('api_key') or os.getenv("OPENROUTER_API_KEY")
        base_url = ai_model.get('url') or os.getenv("OPENROUTER_API_BASE")
        if not api_key:
            raise ValueError("OpenRouter API key not found in config or environment variables.")
        specific_model = ai_model['specific_model']
        print(f"DEBUG: Creating OpenRouter model with specific_model='{specific_model}'", flush=True)
        return OpenAIModel(
            specific_model,
            provider=OpenAIProvider(api_key=api_key, base_url=base_url)
        )
    elif provider == 'GEMINI':
        api_key = ai_model.get('api_key') or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found in config or environment variables.")
        # GeminiModel uses 'model_name' keyword, not 'ai_model'
        return GeminiModel(
            ai_model.get('specific_model', 'gemini-2.5-flash'), # Default if not specified
            provider=GoogleGLAProvider(api_key=api_key)
        )
    elif provider == 'ANTHROPIC':
        api_key = ai_model.get('api_key') or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key not found in config or environment variables.")
        return AnthropicModel(
            ai_model['specific_model'],
            provider=AnthropicProvider(api_key=api_key)
        )
    elif provider == 'LMSTUDIO':
        # LMStudio uses OpenAI compatible API - configure exactly as in test
        base_url = ai_model.get('url') or os.getenv("LMSTUDIO_API_BASE") or "http://localhost:1234"
        if not base_url.endswith('/v1'):
            base_url = base_url.rstrip('/') + '/v1'
        return OpenAIModel(
            ai_model['specific_model'],
            provider=OpenAIProvider(api_key="lm-studio", base_url=base_url)
        )
    else:
        raise ValueError(f"Unsupported model provider: {provider}")


def create_fallback_model(agent_config: Dict[str, Any], default_model_config: Dict[str, Any]):
    """
    Create a FallbackModel with main model from agent_config and fallback from default_model.
    
    Args:
        agent_config: Configurazione agent (può essere None)
        default_model_config: Configurazione default_model dal workspace
    
    Returns:
        FallbackModel o singolo modello, o None se nessuna configurazione valida
    """
    models = []
    
    # Aggiungi modello principale se agent_config esiste
    if agent_config and 'ai_model' in agent_config:
        try:
            primary_model = get_agent_llm_model(agent_config)
            if primary_model:
                models.append(primary_model)
        except Exception:
            # Se fallisce la creazione del modello primario, continua con fallback
            pass
    
    # Aggiungi modello di fallback se default_model_config esiste
    if default_model_config:
        try:
            # Create artificial agent_config for default_model
            fallback_agent_config = {'ai_model': default_model_config}
            fallback_model = get_agent_llm_model(fallback_agent_config)
            if fallback_model:
                models.append(fallback_model)
        except Exception:
            # Se fallisce anche il fallback, continua
            pass
    
    # Filtra None e crea il risultato appropriato
    models = [model for model in models if model is not None]
    
    if len(models) == 0:
        return None
    elif len(models) == 1:
        return models[0]
    else:
        return FallbackModel(*models)