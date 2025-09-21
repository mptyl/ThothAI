# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Language normalization utilities.

Provides a resolver to convert ISO-639-1 language codes (e.g., "it", "en_US",
"pt-BR") or free-form inputs (e.g., "italian") into canonical English language
names suitable for prompts (e.g., "Italian", "English").
"""

from typing import Dict


_LANG_CODE_TO_NAME: Dict[str, str] = {
    # Western European
    "en": "English",
    "it": "Italian",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "is": "Icelandic",
    # Central/Eastern European
    "pl": "Polish",
    "cs": "Czech",
    "sk": "Slovak",
    "hu": "Hungarian",
    "ro": "Romanian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sr": "Serbian",
    "sl": "Slovenian",
    # Mediterranean/others
    "el": "Greek",
    "tr": "Turkish",
    # Cyrillic
    "ru": "Russian",
    "uk": "Ukrainian",
    "kk": "Kazakh",
    # Middle East
    "ar": "Arabic",
    "he": "Hebrew",
    "fa": "Persian",
    # South Asia / SE Asia
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "th": "Thai",
    "ms": "Malay",
    # East Asia
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}


def _is_probable_name(value: str) -> bool:
    """Heuristic: treat as a name if longer than 2 chars and alphabetic/space."""
    if not value:
        return False
    v = value.strip()
    if len(v) <= 2:
        return False
    # Allow spaces and letters only
    return all(ch.isalpha() or ch.isspace() for ch in v)


def resolve_language_name(value: str | None) -> str:
    """
    Resolve various language inputs into a canonical English name.

    Rules:
    - None/empty -> "English" (default)
    - ISO-639-1 codes (case-insensitive), optionally with region variants
      like "en_US" or "pt-BR" -> base language name ("English", "Portuguese")
    - Free-form names like "italian", "ENGLISH" -> Title Case ("Italian", "English")
    - Unknown inputs -> "English"
    """
    if not value:
        return "English"

    raw = value.strip()
    if not raw:
        return "English"

    # Normalize separators for locale variants and pick base code (e.g., en_US -> en)
    lowered = raw.replace("_", "-").lower()
    base = lowered.split("-")[0]

    # If looks like a 2-letter code, map it
    if len(base) == 2 and base.isalpha():
        name = _LANG_CODE_TO_NAME.get(base)
        if name:
            return name

    # If it looks like a full name (letters/spaces), title-case it
    if _is_probable_name(raw):
        return raw.strip().title()

    # Fallback
    return "English"


def resolve_language_code(value: str | None) -> str:
    """
    Resolve various language inputs into a canonical ISO-639-1 code.

    Rules:
    - None/empty -> "en" (default)
    - ISO-639-1 codes (case-insensitive), optionally with region variants
      like "en_US" or "pt-BR" -> base code ("en", "pt") if known
    - Free-form names like "italian", "ENGLISH" -> return corresponding code
      based on canonical English name mapping
    - Unknown inputs -> "en"
    """
    if not value:
        return "en"

    raw = value.strip()
    if not raw:
        return "en"

    lowered = raw.replace("_", "-").lower()
    base = lowered.split("-")[0]

    # Direct code
    if len(base) == 2 and base.isalpha():
        if base in _LANG_CODE_TO_NAME:
            return base
        # Unknown code -> default
        return "en"

    # Name path: map Title Case name back to code
    if _is_probable_name(raw):
        name = raw.strip().title()
        for code, cname in _LANG_CODE_TO_NAME.items():
            if cname == name:
                return code
        # Try resolving via resolve_language_name then invert
        canon = resolve_language_name(raw)
        for code, cname in _LANG_CODE_TO_NAME.items():
            if cname == canon:
                return code
    # Fallback
    return "en"
