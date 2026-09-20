"""Generate PNG charts for Slack (CTL/ATL, discipline volume)."""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from coach_bot.aggregates import classify_sport, activity_duration_seconds, _parse_date


def _wellness_series(rows: list[dict[str, Any]], limit: int = 28) -> tuple[list[str], list[float], list[float]]:
    recent = rows[-limit:]
    labels: list[str] = []
    ctl: list[float] = []
    atl: list[float] = []
    for row in recent:
        d = str(row.get("id") or row.get("date") or "")[:10]
        labels.append(d[-5:] if d else "?")
        c = row.get("ctl") or row.get("fitness")
        a = row.get("atl") or row.get("fatigue")
        if c is not None and a is not None:
            ctl.append(float(c))
            atl.append(float(a))
    return labels, ctl, atl


def chart_theme_from_message(message: str) -> dict[str, str]:
    lower = (message or "").lower()
    if "rosa" in lower or "pink" in lower:
        return {"ctl": "#db2777", "atl": "#f472b6"}
    return {}


def render_ctl_atl_chart(
    rows: list[dict[str, Any]],
    title: str = "Belastning (CTL / ATL)",
    *,
    ctl_color: str = "#2563eb",
    atl_color: str = "#dc2626",
) -> Path | None:
    labels, ctl, atl = _wellness_series(rows)
    if len(ctl) < 2:
        return None
    fig, ax = plt.subplots(figsize=(7, 3.2), dpi=120)
    x = range(len(ctl))
    ax.plot(x, ctl, label="CTL", color=ctl_color, linewidth=2)
    ax.plot(x, atl, label="ATL", color=atl_color, linewidth=2, alpha=0.85)
    ax.set_xticks(list(x)[:: max(1, len(x) // 6)])
    ax.set_xticklabels([labels[i] for i in ax.get_xticks().astype(int) if i < len(labels)], fontsize=8)
    ax.set_title(title, fontsize=11)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out = Path(tempfile.mkstemp(suffix="-ctl-atl.png")[1])
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def render_discipline_week_chart(
    activities: list[dict[str, Any]],
    end: date,
    days: int = 7,
    title: str = "Volum siste 7 dager (t)",
) -> Path | None:
    start = end - timedelta(days=days - 1)
    by_disc: dict[str, float] = {}
    for act in activities:
        d = _parse_date(act.get("start_date_local") or act.get("start_date"))
        if d is None or d < start or d > end:
            continue
        sec = activity_duration_seconds(act)
        if sec <= 0:
            continue
        disc = classify_sport(act)
        by_disc[disc] = by_disc.get(disc, 0.0) + sec / 3600.0
    if not by_disc:
        return None
    order = ["swim", "bike", "run", "strength", "other"]
    labels = [k for k in order if k in by_disc]
    values = [by_disc[k] for k in labels]
    colors = {"swim": "#0ea5e9", "bike": "#22c55e", "run": "#f97316", "strength": "#a855f7", "other": "#94a3b8"}
    fig, ax = plt.subplots(figsize=(5, 3.2), dpi=120)
    ax.bar(labels, values, color=[colors.get(l, "#64748b") for l in labels])
    ax.set_title(title, fontsize=11)
    ax.set_ylabel("timer")
    fig.tight_layout()
    out = Path(tempfile.mkstemp(suffix="-discipline.png")[1])
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out
