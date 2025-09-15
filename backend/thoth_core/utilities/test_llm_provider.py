# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
LLM Provider Testing Utility

This module provides functionality to test LLM provider connectivity
using the existing ThothLLMClient from litellm integration.
"""

import logging
from typing import Tuple
from thoth_core.thoth_ai.llm_client import create_llm_client, ThothLLMClient

# Import LiteLLM exceptions for better error handling
try:
    from litellm import (
        NotFoundError,
        AuthenticationError, 
        RateLimitError,
        BadRequestError,
        OpenAIError,
        ServiceUnavailableError,
        Timeout
    )
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

logger = logging.getLogger(__name__)


def test_llm_provider(ai_model) -> Tuple[bool, str]:
    """
    Test the connectivity and functionality of an LLM provider.
    
    Args:
        ai_model: AiModel instance containing provider configuration
        
    Returns:
        Tuple of (success: bool, message: str) indicating test result
    """
    try:
        # Extract provider info for logging
        provider_name = ai_model.basic_model.provider if ai_model.basic_model else "Unknown"
        model_name = ai_model.specific_model
        
        logger.info(f"Testing LLM provider: {provider_name} with model: {model_name}")
        
        # Create LLM client using existing infrastructure
        client = create_llm_client(ai_model)
        
        # Prepare test prompt
        test_prompt = (
            "This is a connectivity test. Please respond with exactly: "
            "'Connection successful' to confirm you received this message."
        )
        
        # Execute test with minimal parameters to reduce token usage
        response = client.generate(
            messages=test_prompt,
            max_tokens=50,  # Small limit for test response
            temperature=0.1,  # Low temperature for consistent response
        )
        
        # If we got any response object back, log usage if present
        if response and response.usage:
            logger.info(
                f"Test completed. Tokens used: "
                f"prompt={response.usage.get('prompt_tokens', 'N/A')}, "
                f"completion={response.usage.get('completion_tokens', 'N/A')}, "
                f"total={response.usage.get('total_tokens', 'N/A')}"
            )

        # Extract text safely
        response_text = (response.content.strip() if (response and response.content) else "")

        if response_text:
            # Check if response indicates success
            if "connection successful" in response_text.lower():
                success_msg = (
                    f"✓ Provider test successful!\n"
                    f"Provider: {provider_name}\n"
                    f"Model: {model_name}\n"
                    f"Response: {response_text[:100]}"
                )
                logger.info(success_msg)
                return True, success_msg
            else:
                # Got a response but not the expected one
                warning_msg = (
                    f"⚠ Provider responded but with unexpected message.\n"
                    f"Provider: {provider_name}\n"
                    f"Model: {model_name}\n"
                    f"Expected: 'Connection successful'\n"
                    f"Received: {response_text[:100]}"
                )
                logger.warning(warning_msg)
                return True, warning_msg  # Still consider it successful since we got a response

        # No textual content
        # Some providers (notably Gemini) may return an empty string while the call was successful.
        if str(provider_name).upper() == "GEMINI" and response is not None:
            info_msg = (
                f"✓ Provider responded (empty content treated as success).\n"
                f"Provider: {provider_name}\n"
                f"Model: {model_name}"
            )
            logger.info(info_msg)
            return True, info_msg

        # Otherwise, consider it a failure
        error_msg = (
            f"✗ No response received from provider.\n"
            f"Provider: {provider_name}\n"
            f"Model: {model_name}"
        )
        logger.error(error_msg)
        return False, error_msg
            
    except ValueError as e:
        # Configuration errors (missing API keys, etc.)
        error_msg = (
            f"✗ Configuration error for {provider_name}:\n"
            f"{str(e)}\n\n"
            f"Please check:\n"
            f"• API key is configured in environment variables\n"
            f"• Model name '{model_name}' is valid for this provider"
        )
        logger.error(f"Configuration error: {e}")
        return False, error_msg
    
    # LiteLLM specific exceptions (if available)
    except Exception as e:
        # Check for specific LiteLLM exceptions
        if LITELLM_AVAILABLE:
            error_class_name = type(e).__name__
            
            # Handle specific LiteLLM errors
            if isinstance(e, NotFoundError) or error_class_name == "NotFoundError":
                error_msg = (
                    f"✗ Model not found for {provider_name}:\n"
                    f"The model '{model_name}' does not exist or you don't have access to it.\n\n"
                    f"Please check:\n"
                    f"• Model name is spelled correctly\n"
                    f"• You have access to this model\n"
                    f"• Model is available in your region/plan"
                )
                logger.error(f"Model not found: {e}")
                return False, error_msg
                
            elif isinstance(e, AuthenticationError) or error_class_name == "AuthenticationError":
                error_msg = (
                    f"✗ Authentication failed for {provider_name}:\n"
                    f"Invalid or missing API key.\n\n"
                    f"Please check:\n"
                    f"• API key is correct\n"
                    f"• API key is properly configured in environment variables\n"
                    f"• API key has not expired"
                )
                logger.error(f"Authentication error: {e}")
                return False, error_msg
                
            elif isinstance(e, RateLimitError) or error_class_name == "RateLimitError":
                error_msg = (
                    f"✗ Rate limit exceeded for {provider_name}:\n"
                    f"Too many requests to the API.\n\n"
                    f"Please:\n"
                    f"• Wait a few moments and try again\n"
                    f"• Check your API usage limits\n"
                    f"• Consider upgrading your plan if needed"
                )
                logger.error(f"Rate limit error: {e}")
                return False, error_msg
                
            elif isinstance(e, BadRequestError) or error_class_name == "BadRequestError":
                error_msg = (
                    f"✗ Invalid request for {provider_name}:\n"
                    f"{str(e)}\n\n"
                    f"Please check:\n"
                    f"• Model configuration parameters\n"
                    f"• Model '{model_name}' supports the requested features"
                )
                logger.error(f"Bad request error: {e}")
                return False, error_msg
                
            elif isinstance(e, ServiceUnavailableError) or error_class_name == "ServiceUnavailableError":
                error_msg = (
                    f"✗ Service unavailable for {provider_name}:\n"
                    f"The API service is temporarily unavailable.\n\n"
                    f"Please:\n"
                    f"• Check the provider's status page\n"
                    f"• Try again in a few moments\n"
                    f"• Verify the API endpoint URL if custom"
                )
                logger.error(f"Service unavailable: {e}")
                return False, error_msg
                
            elif isinstance(e, Timeout) or error_class_name == "Timeout":
                error_msg = (
                    f"✗ Request timeout for {provider_name}:\n"
                    f"The provider took too long to respond.\n\n"
                    f"This could indicate:\n"
                    f"• Provider service is overloaded\n"
                    f"• Network latency issues\n"
                    f"• Model '{model_name}' is slow to initialize"
                )
                logger.error(f"Timeout error: {e}")
                return False, error_msg
            
            elif isinstance(e, ConnectionError):
                # Network/connection errors
                error_msg = (
                    f"✗ Connection failed to {provider_name}:\n"
                    f"{str(e)}\n\n"
                    f"Please check:\n"
                    f"• Network connectivity\n"
                    f"• Provider API endpoint is accessible\n"
                    f"• Custom URL (if configured) is correct"
                )
                logger.error(f"Connection error: {e}")
                return False, error_msg
        
        # Catch-all for unexpected errors
        error_type = type(e).__name__
        error_msg = (
            f"✗ Unexpected error testing {provider_name}:\n"
            f"{error_type}: {str(e)}\n\n"
            f"Model: {model_name}\n"
            f"Please check the logs for more details."
        )
        logger.exception(f"Unexpected error testing LLM provider: {e}")
        return False, error_msg


def test_multiple_providers(ai_models) -> dict:
    """
    Test multiple LLM providers and return results for each.
    
    Args:
        ai_models: List of AiModel instances to test
        
    Returns:
        Dictionary mapping model IDs to test results
    """
    results = {}
    
    for ai_model in ai_models:
        success, message = test_llm_provider(ai_model)
        results[ai_model.id] = {
            'model_name': str(ai_model),
            'success': success,
            'message': message
        }
        
    return results