"""Classify user DM intent for context trimming."""

from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    STATUS = "status"
    TOMORROW = "tomorrow"
    WEEK = "week"
    PAIN = "pain"
    RACE = "race"
    LOG = "log"
    GENERAL = "general"


_LOG_PREFIX = re.compile(r"^\s*logg\s*[:]\s*", re.IGNORECASE)


def detect_intent(message: str) -> Intent:
    text = (message or "").strip()
    lower = text.lower()

    if _LOG_PREFIX.match(text) or lower.startswith("logg "):
        return Intent.LOG

    if any(
        k in lower
        for k in (
            "i morgen",
            "imorgen",
            "tomorrow",
            "morgendagens",
            "plan i morgen",
            "hva skal jeg gjøre i morgen",
        )
    ):
        return Intent.TOMORROW

    if any(
        k in lower
        for k in (
            "ukestatus",
            "denne uken",
            "uke ",
            "ukentlig",
            "uken som kom",
            "siste uke",
        )
    ):
        return Intent.WEEK

    if any(k in lower for k in ("smerte", "vondt", "skade", "kne", "rygg", "sår")):
        return Intent.PAIN

    if any(
        k in lower
        for k in (
            "lofoten",
            "race",
            "cutoff",
            "fueling",
            "norseman",
            "half extreme",
            "konkurranse",
        )
    ):
        return Intent.RACE

    if any(
        k in lower
        for k in (
            "status",
            "hvordan ligger",
            "form",
            "ligger jeg an",
            "oppsummer",
        )
    ):
        return Intent.STATUS

    return Intent.GENERAL


def strip_log_prefix(message: str) -> str:
    return _LOG_PREFIX.sub("", message.strip()).strip()
