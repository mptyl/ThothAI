"""
Minimal multilingual stopword sets and helpers.

This module provides a lightweight, dependency-free collection of stopwords
for European and Mediterranean languages used by the SQL Generator relevance
guard. The sets are intentionally minimal (articles, common prepositions and
conjunctions) to avoid over-filtering while improving BM25 quality.

APIs:
- get_stopwords_for(lang: str) -> set[str]
- union_stopwords(*langs: str) -> set[str]

The input language can be an ISO-639-1 code (e.g., "it", "en_US", "pt-BR")
or a name (e.g., "Italian"). Names are resolved via language_utils.
"""

from __future__ import annotations

from typing import Dict, Set
from helpers.language_utils import resolve_language_code


# Minimal stopword lists per language code
STOPWORDS_BY_LANG: Dict[str, Set[str]] = {
    # English
    "en": {
        "the", "and", "or", "of", "in", "to", "for", "on", "by", "with",
        "a", "an", "at", "from", "as", "is", "are", "be",
    },
    # Italian
    "it": {
        "il", "lo", "la", "i", "gli", "le", "un", "una", "uno", "di", "da",
        "per", "con", "su", "tra", "fra", "e", "o", "a", "in", "al", "del",
    },
    # Spanish
    "es": {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
        "a", "en", "y", "o", "con", "por", "para", "entre", "sobre",
    },
    # Portuguese
    "pt": {
        "o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da",
        "em", "no", "na", "e", "ou", "com", "por", "para", "entre", "sobre",
    },
    # French
    "fr": {
        "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux", "et",
        "ou", "en", "dans", "avec", "pour", "par", "sur", "entre",
    },
    # German
    "de": {
        "der", "die", "das", "ein", "eine", "einer", "eines", "und", "oder",
        "in", "im", "am", "zu", "vom", "mit", "auf", "für", "von",
    },
    # Dutch
    "nl": {
        "de", "het", "een", "en", "of", "in", "op", "met", "voor", "van", "bij",
    },
    # Swedish
    "sv": {
        "en", "ett", "och", "eller", "i", "på", "för", "med", "av", "från",
    },
    # Norwegian
    "no": {
        "en", "ei", "et", "og", "eller", "i", "på", "for", "med", "av", "fra",
    },
    # Danish
    "da": {
        "en", "et", "og", "eller", "i", "på", "for", "med", "af", "fra",
    },
    # Finnish (minimal given agglutinative nature)
    "fi": {
        "ja", "tai", "jos", "kun", "niin", "että", "se", "ne",
    },
    # Icelandic
    "is": {
        "og", "eða", "í", "á", "fyrir", "með", "frá", "af", "til",
    },
    # Polish
    "pl": {
        "i", "oraz", "lub", "w", "we", "na", "do", "z", "za", "o", "u", "od",
    },
    # Czech
    "cs": {
        "a", "nebo", "v", "ve", "na", "do", "z", "s", "se", "o", "u",
    },
    # Slovak
    "sk": {
        "a", "alebo", "v", "vo", "na", "do", "z", "so", "s", "o", "u",
    },
    # Hungarian (minimal)
    "hu": {
        "és", "vagy", "a", "az", "egy", "hogy", "mert", "ban", "ben",
    },
    # Romanian
    "ro": {
        "și", "sau", "în", "pe", "la", "cu", "din", "de", "pentru", "că",
    },
    # Bulgarian
    "bg": {
        "и", "или", "в", "на", "с", "за", "от", "по", "със",
    },
    # Croatian
    "hr": {
        "i", "ili", "u", "na", "za", "od", "do", "s", "sa",
    },
    # Serbian (Latin script)
    "sr": {
        "i", "ili", "u", "na", "za", "od", "do", "s", "sa",
    },
    # Slovenian
    "sl": {
        "in", "ali", "v", "na", "za", "od", "do", "s", "z",
    },
    # Greek (transliterated minimal conjunctions/preps; unicode included)
    "el": {
        "και", "ή", "σε", "του", "της", "των", "με", "για", "από", "στο", "στη",
    },
    # Turkish
    "tr": {
        "ve", "veya", "ile", "için", "de", "da", "ki", "bir", "şu", "bu",
    },
    # Russian
    "ru": {
        "и", "или", "в", "на", "с", "для", "из", "по", "от", "за",
    },
    # Ukrainian
    "uk": {
        "і", "або", "в", "на", "з", "для", "по", "від", "за",
    },
}


def get_stopwords_for(lang: str) -> Set[str]:
    """Return stopwords for a language code or name.

    - Accepts codes with region (e.g., "pt-BR") or names ("Italian").
    - Falls back to English if unknown.
    """
    if not lang:
        return STOPWORDS_BY_LANG.get("en", set())
    code = resolve_language_code(lang)
    return STOPWORDS_BY_LANG.get(code, STOPWORDS_BY_LANG.get("en", set()))


def union_stopwords(*langs: str) -> Set[str]:
    """Return the union of stopwords for the given languages.

    Unknown languages are ignored; if none are valid, returns English set.
    """
    result: Set[str] = set()
    any_valid = False
    for lang in langs:
        if not lang:
            continue
        code = resolve_language_code(lang)
        sw = STOPWORDS_BY_LANG.get(code)
        if sw:
            any_valid = True
            result.update(sw)
    if not any_valid:
        return STOPWORDS_BY_LANG.get("en", set()).copy()
    return result

