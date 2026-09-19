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
    ANALYSIS = "analysis"
    SYNC_WEEK = "sync_week"
    CHART = "chart"


_LOG_PREFIX = re.compile(r"^\s*logg\s*[:]\s*", re.IGNORECASE)


def is_follow_up(message: str, has_history: bool) -> bool:
    if not has_history:
        return False
    from coach_bot.workout_extract import is_commit_message, wants_intervals_write

    if is_commit_message(message) or wants_intervals_write(message):
        return False
    text = (message or "").strip()
    if len(text) > 120:
        return False
    lower = text.lower()
    if any(k in lower for k in ("status", "ukestatus", "i morgen", "logg:")):
        return False
    return True


def detect_intent(message: str, has_history: bool = False) -> Intent:
    text = (message or "").strip()
    lower = text.lower()

    if is_follow_up(message, has_history):
        return Intent.GENERAL

    if _LOG_PREFIX.match(text) or lower.startswith("logg "):
        return Intent.LOG

    if lower.startswith("briefing:"):
        return Intent.GENERAL

    if lower in ("nullstill", "reset", "ny samtale"):
        return Intent.GENERAL

    if asks_for_charts(text):
        return Intent.CHART

    if any(k in lower for k in ("analyse", "advanced", "dybde", "acwr")):
        return Intent.ANALYSIS

    from coach_bot.workout_extract import asks_workout_for_calendar

    if asks_workout_for_calendar(text):
        return Intent.TOMORROW

    if asks_for_plan_sync(text) or any(
        k in lower
        for k in (
            "legg inn uke",
            "synk kalender",
            "synk uke",
            "ukeplan intervals",
            "legg uke",
        )
    ):
        return Intent.SYNC_WEEK

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


def asks_for_charts(message: str) -> bool:
    lower = (message or "").lower()
    return any(k in lower for k in ("graf", "chart", "visualiser", "figur", "plot"))


def asks_for_plan_sync(message: str) -> bool:
    lower = (message or "").lower()
    plan_words = (
        "treningsplan",
        "treingsplan",
        "ukeplan",
        "treningsplaner",
        "kalender",
        "intervals",
    )
    action_words = (
        "legg inn",
        "legge inn",
        "legg til",
        "synk",
        "synke",
        "opprett",
        "lage",
        "kan du",
        "putt",
        "importer",
    )
    return any(p in lower for p in plan_words) and any(a in lower for a in action_words)


def asks_capabilities(message: str) -> bool:
    """Natural questions like «kan du lage grafer og legge inn plan?»"""
    lower = (message or "").lower()
    if asks_for_charts(message) and asks_for_plan_sync(message):
        return True
    if "kan du" in lower and asks_for_charts(message):
        return True
    if "kan du" in lower and any(p in lower for p in ("treningsplan", "ukeplan", "kalender")):
        return True
    return False
