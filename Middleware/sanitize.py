"""
XSS protection — input sanitization utilities.
"""

import re
from html import escape

# Dangerous patterns: script tags, event handlers, javascript: URLs, etc.
_DANGEROUS_PATTERNS = [
    re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=\s*[\"'][^\"']*[\"']", re.IGNORECASE),  # onclick, onerror, etc.
    re.compile(r"on\w+\s*=\s*[^\s>]+", re.IGNORECASE),
    re.compile(r"<iframe[^>]*>", re.IGNORECASE),
    re.compile(r"<embed[^>]*>", re.IGNORECASE),
    re.compile(r"<object[^>]*>", re.IGNORECASE),
]


def sanitize_html(value: str) -> str:
    """מסיר HTML/Tag זדוני מערך מחרוזת. מחזיר טקסט נקי."""
    if not isinstance(value, str):
        return value

    # Step 1: Strip dangerous patterns entirely
    for pattern in _DANGEROUS_PATTERNS:
        value = pattern.sub("", value)

    # Step 2: Escape remaining HTML (defense in depth)
    value = escape(value)

    return value


def sanitize_dict(data: dict) -> dict:
    """מנקה HTML מכל ערכי המחרוזת ב-dict (recursive)."""
    if not isinstance(data, dict):
        return data

    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = sanitize_html(value)
        elif isinstance(value, dict):
            cleaned[key] = sanitize_dict(value)
        elif isinstance(value, list):
            cleaned[key] = [
                sanitize_dict(item) if isinstance(item, dict) else
                sanitize_html(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            cleaned[key] = value

    return cleaned
