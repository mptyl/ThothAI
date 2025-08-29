# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Token counting utility for estimating token usage in LLM contexts.

This module provides functions to count tokens in text using a 
character-based approximation (1 token ≈ 4 characters).
"""

import logging

logger = logging.getLogger(__name__)

def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string.
    
    Uses character-based approximation (1 token ≈ 4 characters).
    This is a reasonable approximation for English text.
    
    Args:
        text: The text to count tokens for
        
    Returns:
        int: Estimated number of tokens
    """
    if not text:
        return 0
    
    # Character-based approximation
    # Rule of thumb: 1 token ≈ 4 characters (conservative estimate)
    char_count = len(text)
    estimated_tokens = max(1, char_count // 4)
    
    return estimated_tokens

def count_mschema_tokens(mschema: str) -> int:
    """
    Count tokens specifically for an mschema string representation.
    
    Args:
        mschema: The mschema string to count tokens for
        
    Returns:
        int: Estimated number of tokens in the mschema
    """
    if not mschema:
        return 0
    
    # mschema typically contains structured data with lots of punctuation
    # and keywords, which may tokenize differently than regular text
    token_count = count_tokens(mschema)
    
    # Log for debugging purposes
    logger.debug(f"mschema token count: {token_count} tokens for {len(mschema)} characters")
    
    return token_count

def estimate_context_usage(
    mschema_tokens: int,
    context_window: int,
    threshold_percentage: float = 0.5
) -> tuple[bool, float]:
    """
    Determine if schema link is needed based on context usage.
    
    Args:
        mschema_tokens: Number of tokens in the mschema
        context_window: Total context window size
        threshold_percentage: Threshold percentage (default 0.5 for 50%)
        
    Returns:
        tuple[bool, float]: (needs_schema_link, usage_percentage)
            - needs_schema_link: True if schema tokens exceed threshold
            - usage_percentage: Actual percentage of context used by schema
    """
    if context_window <= 0:
        logger.warning(f"Invalid context window size: {context_window}")
        return False, 0.0
    
    usage_percentage = mschema_tokens / context_window
    needs_schema_link = usage_percentage > threshold_percentage
    
    logger.debug(
        f"Context usage: {mschema_tokens}/{context_window} = {usage_percentage:.1%}, "
        f"threshold: {threshold_percentage:.0%}, needs_schema_link: {needs_schema_link}"
    )
    
    return needs_schema_link, usage_percentage