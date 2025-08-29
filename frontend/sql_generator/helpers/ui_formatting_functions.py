# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

def clean_explanation_text(explanation: str) -> str:
    """
    Cleans and formats explanation text for better Markdown rendering.

    Args:
        explanation (str): Raw explanation text

    Returns:
        str: Cleaned and formatted explanation text
    """
    if not explanation:
        return "No explanation available."

    # Remove extra whitespace and normalize line breaks
    cleaned = explanation.strip()

    # Split into paragraphs and filter out empty ones
    paragraphs = [paragraph.strip() for paragraph in cleaned.split('\n') if paragraph.strip()]

    if not paragraphs:
        return "No explanation available."

    # Apply formatting rules
    formatted_paragraphs = []

    for i, paragraph in enumerate(paragraphs):
        if i == 0:
            # First paragraph: no preceding newlines
            formatted_paragraphs.append(paragraph)
        elif paragraph.startswith('**'):
            # Paragraphs starting with ** get double newline (except first)
            formatted_paragraphs.append('\n\n' + paragraph)
        elif paragraph.startswith('-'):
            # Paragraphs starting with - get single newline
            formatted_paragraphs.append('\n' + paragraph)
        else:
            # Default: double newline for regular paragraphs
            formatted_paragraphs.append('\n\n' + paragraph)

    return ''.join(formatted_paragraphs)
