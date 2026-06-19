"""Shared embed-text builder.

Single source of truth for how MCC/VSIC entries are turned into the text that
gets embedded. The ``embed`` producer (Module 1) and any consumer must use these
exact formulas so the produced vectors — and therefore the cosine top-K ranking —
stay byte-for-byte identical to the original coupled pipeline (deterministic
Stage-1 guarantee).
"""

import re


def strip_html(text: str) -> str:
    """Remove HTML tags from text. Returns empty string if input is None/empty."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def build_mcc_text(mcc: dict) -> str:
    """Build the embed text for an MCC entry.

    Mirrors the original use-case logic exactly: stripped title + em-dash +
    stripped description truncated to 500 chars.
    """
    title = strip_html(mcc["title"])
    description = strip_html(mcc.get("description") or "")
    return f"{title} — {description[:500]}"


def build_vsic_text(vsic: dict) -> str:
    """Build the embed text for a VSIC entry.

    Mirrors the original behavior: the raw title, with no HTML stripping and no
    truncation.
    """
    return vsic["title"]
