"""Parse plan start dates from chat (e.g. start planen 20-09)."""

from __future__ import annotations

import re
from datetime import date, timedelta


def parse_plan_start_date(message: str, as_of: date) -> date | None:
    """Return explicit start date from user text, or None to use today."""
    text = (message or "").strip()
    iso = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso:
        try:
            return date.fromisoformat(iso.group(1))
        except ValueError:
            pass
    m = re.search(r"(?:start(?:e)?\s+planen|fra|start)\s+(\d{1,2})[.\-/](\d{1,2})", text, re.I)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = as_of.year
        try:
            d = date(year, month, day)
            if d < as_of - timedelta(days=180):
                d = date(year + 1, month, day)
            return d
        except ValueError:
            pass
    m = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})\b", text)
    if m and any(k in text.lower() for k in ("start", "planen", "plan", "fra")):
        day, month = int(m.group(1)), int(m.group(2))
        try:
            d = date(as_of.year, month, day)
            if d < as_of - timedelta(days=180):
                d = date(as_of.year + 1, month, day)
            return d
        except ValueError:
            pass
    return None


def calendar_week_range(as_of: date, period: str) -> tuple[date, date]:
    """Return (monday, sunday) for this_week or next_week relative to as_of."""
    p = (period or "").lower().replace(" ", "_")
    this_mon = as_of - timedelta(days=as_of.weekday())
    if p in ("this_week", "denne_uke", "denne_uken", "this"):
        return this_mon, this_mon + timedelta(days=6)
    # next_week (default for «neste uke»)
    nxt_mon = this_mon + timedelta(days=7)
    return nxt_mon, nxt_mon + timedelta(days=6)
