"""User-facing error messages for Slack."""

from __future__ import annotations

import httpx
from openai import APIConnectionError, APITimeoutError, AuthenticationError


def friendly_coach_error(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in (401, 403):
            return (
                "Intervals avviste API-nøkkelen (401/403). "
                "Sjekk INTERVALS_ATHLETE_ID og INTERVALS_API_KEY i .env."
            )
        return f"Intervals-feil ({exc.response.status_code}). Sjekk athlete ID og API key."
    if isinstance(exc, httpx.TimeoutException):
        return "Intervals svarte ikke i tide. Prøv igjen om litt."
    if isinstance(exc, httpx.HTTPError):
        return f"Kunne ikke nå Intervals: {exc!s}"
    if isinstance(exc, AuthenticationError):
        return "OpenAI avviste API-nøkkelen. Sjekk OPENAI_API_KEY i .env."
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return "OpenAI svarte ikke i tide. Prøv igjen om litt."
    if isinstance(exc, FileNotFoundError):
        return f"Repo-fil mangler: {exc!s}. Sjekk REPO_ROOT."
    return f"Coach feilet: {exc!s}. Sjekk logger og .env."
