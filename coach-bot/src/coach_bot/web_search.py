"""Optional live web search for up-to-date / unforeseen facts.

Uses Tavily (a search API built for LLMs) when ``TAVILY_API_KEY`` is set.
Degrades gracefully to a clear message when unconfigured or unreachable, so
the coach never breaks – it just falls back to the curated knowledge base.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"
_UNCONFIGURED = (
    "(web-søk er ikke konfigurert – legg til TAVILY_API_KEY for ferske fakta. "
    "Bruk fagkunnskapsbasen i mellomtiden.)"
)


def is_enabled() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY", "").strip())


def search_web(query: str, max_results: int = 5, timeout: float = 15.0) -> str:
    """Return a concise, sourced summary of top web results, or a graceful note."""
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        return _UNCONFIGURED
    q = (query or "").strip()
    if not q:
        return "(tomt søk)"
    try:
        resp = httpx.post(
            _TAVILY_URL,
            json={
                "api_key": key,
                "query": q,
                "max_results": max_results,
                "include_answer": True,
                "search_depth": "advanced",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover - network path
        logger.exception("web_search failed")
        return f"(web-søk feilet: {e}. Bruker fagkunnskap i stedet.)"

    return format_results(data)


def format_results(data: dict) -> str:
    """Render Tavily-style JSON into a compact, sourced text block."""
    parts: list[str] = []
    answer = (data.get("answer") or "").strip()
    if answer:
        parts.append(f"Oppsummering: {answer}")
    for r in (data.get("results") or [])[:5]:
        title = (r.get("title") or "").strip()
        content = (r.get("content") or "").strip()
        url = (r.get("url") or "").strip()
        if not (title or content):
            continue
        parts.append(f"- {title}: {content[:300]} ({url})")
    if not parts:
        return "(web-søk ga ingen treff)"
    return "\n".join(parts)
