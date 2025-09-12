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

"""
Unified LLM client using LiteLLM for all language model operations.

This module provides a single interface for interacting with multiple LLM providers
including OpenAI, Anthropic, Google Gemini, Mistral, Ollama, and others.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

import litellm
from litellm import completion
from thoth_core.models import LLMChoices

# Configure logging
logger = logging.getLogger(__name__)

# Configure LiteLLM settings
litellm.drop_params = True  # Drop unsupported params instead of failing
litellm.set_verbose = False  # Set to True for debugging


@dataclass
class LLMResponse:
    """Standardized response from LLM operations."""

    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class ThothLLMClient:
    """
    Unified LLM client for Thoth using LiteLLM.

    This class provides a consistent interface for all LLM operations,
    handling provider-specific configurations and API endpoints.
    """

    # Provider to LiteLLM model prefix mapping
    PROVIDER_MAPPING = {
        LLMChoices.OPENAI: "",  # No prefix needed for OpenAI
        LLMChoices.CLAUDE: "claude/",
        LLMChoices.GEMINI: "gemini/",
        LLMChoices.MISTRAL: "mistral/",
        LLMChoices.OLLAMA: "ollama/",
        LLMChoices.OPENROUTER: "openrouter/",
        LLMChoices.GROQ: "groq/",  # GROQ provider
        # These use OpenAI-compatible endpoints
        LLMChoices.CODESTRAL: "",
        LLMChoices.DEEPSEEK: "",
        LLMChoices.LMSTUDIO: "",
        LLMChoices.LLAMA: "ollama/",  # Llama via Ollama
    }

    # Custom API endpoints for providers
    CUSTOM_ENDPOINTS = {
        LLMChoices.CODESTRAL: "https://api.codestral.com/v1",
        LLMChoices.DEEPSEEK: "https://api.deepseek.com/v1",
        LLMChoices.OPENROUTER: "https://openrouter.ai/api/v1",
        # LM Studio endpoint is configurable
    }

    def __init__(self, ai_model):
        """
        Initialize the LLM client with model configuration.

        Args:
            ai_model: Model configuration object with attributes:
                - basic_model.provider: LLMChoices enum value
                - specific_model: Model name/identifier
                - temperature: Optional temperature setting
                - url: Optional custom endpoint URL
        """
        self.ai_model = ai_model
        self.provider = ai_model.basic_model.provider
        self.model_name = self._get_model_name()
        self.api_key = self._get_api_key()
        self.temperature = float(ai_model.temperature) if ai_model.temperature else 0.7
        self.custom_endpoint = self._get_custom_endpoint()

        logger.info(
            f"Initialized LLM client for {self.provider} with model {self.model_name}"
        )

    def _get_model_name(self) -> str:
        """Map the model to LiteLLM format."""
        prefix = self.PROVIDER_MAPPING.get(self.provider, "")
        model = self.ai_model.specific_model

        # Handle special cases
        if self.provider in [
            LLMChoices.CODESTRAL,
            LLMChoices.DEEPSEEK,
            LLMChoices.LMSTUDIO,
        ]:
            # These use OpenAI-compatible format without prefix
            return model
        
        # For GROQ, handle special model names that GROQ accepts
        if self.provider == LLMChoices.GROQ:
            # GROQ accepts models with these prefixes as-is
            special_prefixes = [
                "openai/",      # e.g., openai/gpt-oss-20b
                "meta-llama/",  # e.g., meta-llama/llama-guard-4-12b
                "moonshotai/",  # e.g., moonshotai/kimi-k2-instruct
                "qwen/",        # e.g., qwen/qwen3-32b
            ]
            
            # Check if the model starts with any special prefix
            for prefix in special_prefixes:
                if model.startswith(prefix):
                    # Keep the full name as GROQ accepts it
                    return f"groq/{model}"  # e.g., groq/openai/gpt-oss-20b or groq/meta-llama/llama-guard-4-12b
            
            # For other models, remove any existing prefix and add groq/
            if "/" in model:
                model = model.split("/", 1)[1]
            return f"groq/{model}"
        
        # For OpenRouter, always use openrouter/ prefix and preserve vendor namespace
        if self.provider == LLMChoices.OPENROUTER:
            # If the model does not include a vendor namespace, try to infer one
            # Common mappings to help users who specify bare model IDs
            if "/" not in model:
                lower = model.lower()
                if lower.startswith("gemini"):
                    model = f"google/{model}"
                elif lower.startswith("claude"):
                    model = f"anthropic/{model}"
                elif lower.startswith("mistral") or lower.startswith("codestral"):
                    model = f"mistralai/{model}"
                elif lower.startswith("deepseek"):
                    model = f"deepseek/{model}"
                elif lower.startswith("gpt") or lower.startswith("o3"):
                    model = f"openai/{model}"
                # else: leave as-is; OpenRouter will validate
            # Preserve the vendor prefix for OpenRouter
            return f"openrouter/{model}"

        return f"{prefix}{model}" if prefix else model

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variables only."""
        # Environment variable mapping
        env_vars = {
            LLMChoices.OPENAI: "OPENAI_API_KEY",
            LLMChoices.CLAUDE: "ANTHROPIC_API_KEY",
            LLMChoices.GEMINI: "GEMINI_API_KEY",
            LLMChoices.MISTRAL: "MISTRAL_API_KEY",
            LLMChoices.CODESTRAL: "MISTRAL_API_KEY",  # Codestral uses Mistral key
            LLMChoices.DEEPSEEK: "DEEPSEEK_API_KEY",
            LLMChoices.OPENROUTER: "OPENROUTER_API_KEY",
            LLMChoices.GROQ: "GROQ_API_KEY",  # GROQ API key
            LLMChoices.LMSTUDIO: None,  # LM Studio doesn't need API key
            LLMChoices.OLLAMA: None,  # Ollama doesn't need API key
            LLMChoices.LLAMA: None,  # Llama via Ollama doesn't need API key
        }

        env_var = env_vars.get(self.provider)
        if env_var:
            return os.environ.get(env_var)

        # Some providers don't need API keys
        if self.provider in [LLMChoices.OLLAMA, LLMChoices.LLAMA, LLMChoices.LMSTUDIO]:
            return "dummy-key"  # LiteLLM requires some value

        return None

    def _get_custom_endpoint(self) -> Optional[str]:
        """Get custom API endpoint if needed."""
        # Check if model has custom URL
        if hasattr(self.ai_model, "url") and self.ai_model.url:
            return self.ai_model.url

        # Use default custom endpoints
        if self.provider in self.CUSTOM_ENDPOINTS:
            return self.CUSTOM_ENDPOINTS[self.provider]

        # Special handling for LM Studio
        if self.provider == LLMChoices.LMSTUDIO:
            return self.ai_model.url or "http://localhost:1234/v1"

        # Ollama endpoint
        if self.provider in [LLMChoices.OLLAMA, LLMChoices.LLAMA]:
            return "http://localhost:11434"

        return None

    def generate(
        self,
        messages: Union[List[Dict[str, str]], str],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            messages: List of message dicts or a single prompt string
            max_tokens: Maximum tokens to generate
            temperature: Override default temperature
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse object with the generated content

        Raises:
            Exception: If the LLM call fails
        """
        # Convert string prompt to message format
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        # Prepare completion arguments
        completion_args = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "stream": stream,
        }

        # Add API key if available
        if self.api_key:
            completion_args["api_key"] = self.api_key
        
        # Force custom_llm_provider for GROQ to ensure proper routing
        if self.provider == LLMChoices.GROQ:
            completion_args["custom_llm_provider"] = "groq"

        # Add custom endpoint if needed
        if self.custom_endpoint:
            completion_args["api_base"] = self.custom_endpoint

        # Add max tokens if specified
        if max_tokens:
            completion_args["max_tokens"] = max_tokens

        # Handle Ollama-specific parameters
        if self.provider in [LLMChoices.OLLAMA, LLMChoices.LLAMA]:
            completion_args["api_base"] = (
                self.custom_endpoint or "http://localhost:11434"
            )
            # Ollama uses num_predict instead of max_tokens
            if max_tokens:
                kwargs["num_predict"] = max_tokens
                completion_args.pop("max_tokens", None)

        # Merge additional kwargs
        completion_args.update(kwargs)

        try:
            response = completion(**completion_args)

            # Extract content from response
            if stream:
                # For streaming, return generator
                return response
            else:
                content = response.choices[0].message.content
                usage = response.usage.dict() if hasattr(response, "usage") else None

                return LLMResponse(
                    content=content,
                    model=response.model,
                    usage=usage,
                    raw_response=response,
                )

        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a chat completion with optional system prompt.

        Args:
            messages: List of message dictionaries
            system_prompt: Optional system message to prepend
            **kwargs: Additional parameters for generation

        Returns:
            LLMResponse object
        """
        # Prepend system message if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        return self.generate(messages, **kwargs)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            from litellm import token_counter

            return token_counter(model=self.model_name, text=text)
        except Exception as e:
            logger.warning(f"Token counting failed: {e}. Using approximate count.")
            # Fallback to approximate count (1 token ≈ 4 characters)
            return len(text) // 4


def create_llm_client(ai_model) -> ThothLLMClient:
    """
    Factory function to create an LLM client.

    Args:
        ai_model: Model configuration object

    Returns:
        Configured ThothLLMClient instance
    """
    return ThothLLMClient(ai_model)
