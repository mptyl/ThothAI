from __future__ import annotations

import ast
import json
from typing import Any, Dict, List, Union
from django.utils.html import escape


def parse_value(value: Any) -> Any:
    """Parse a stringified Python/JSON structure into a Python object.
    Tries JSON, then Python literal. Returns the original value if parsing fails.
    """
    if value is None:
        return None
    # If already structured, return as-is
    if isinstance(value, (list, dict, tuple, int, float, bool)):
        return value
    if isinstance(value, str):
        s = value.strip()
        # Try JSON first
        try:
            return json.loads(s)
        except Exception:
            pass
        # Try Python literal
        try:
            return ast.literal_eval(s)
        except Exception:
            return value
    return value


def _title_key(key: str) -> str:
    return key.replace("_", " ").title()


def render_raw_toggle(raw_text: str, label: str = "Show raw data") -> str:
    return (
        '<details style="margin-top: 10px;">'
        f'<summary style="cursor: pointer;">{escape(label)}</summary>'
        f'<pre class="readonly thoth-pre" style="margin-top: 5px; max-height: 300px; overflow: auto;">{escape(raw_text)}</pre>'
        "</details>"
    )


def render_collapsible(title: str, inner_html: str) -> str:
    return (
        '<details class="thoth-collapsible">'
        f'<summary>{escape(title)}</summary>'
        f'<div class="thoth-body">{inner_html}</div>'
        "</details>"
    )


def _render_text(value: str, truncate: int | None = None) -> str:
    s = value if value is not None else ""
    if truncate and len(s) > truncate:
        s = s[:truncate] + "…"
    # Pre if multiline or long
    if "\n" in s or len(s) > 200:
        return f'<pre class="readonly thoth-pre">{escape(s)}</pre>'
    return escape(s)


def render_list(items: List[Any], truncate: int | None = None) -> str:
    html: List[str] = ['<ul class="thoth-ul">']
    for it in items:
        html.append("<li>")
        html.append(render_value(it, truncate=truncate))
        html.append("</li>")
    html.append("</ul>")
    return "".join(html)


def render_dict(d: Dict[str, Any], truncate: int | None = None) -> str:
    html: List[str] = ['<dl class="thoth-dl">']
    for k, v in d.items():
        html.append(f"<dt>{escape(_title_key(str(k)))}</dt>")
        html.append("<dd>")
        html.append(render_value(v, truncate=truncate))
        html.append("</dd>")
    html.append("</dl>")
    return "".join(html)


def render_value(value: Any, truncate: int | None = None) -> str:
    # Normalize tuples
    if isinstance(value, tuple):
        value = list(value)

    if isinstance(value, list):
        return render_list(value, truncate=truncate)
    if isinstance(value, dict):
        return render_dict(value, truncate=truncate)
    if isinstance(value, (int, float, bool)):
        return escape(str(value))
    if value is None:
        return "-"
    # Fallback to string
    return _render_text(str(value), truncate=truncate)
