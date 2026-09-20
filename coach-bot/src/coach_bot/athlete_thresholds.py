"""Parse Intervals.icu athlete profile into coaching thresholds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SportThresholds:
    ftp: int | None = None
    lthr: int | None = None
    max_hr: int | None = None
    threshold_pace_m_s: float | None = None


@dataclass
class AthleteThresholds:
    """Normalized thresholds for workout builder and coach context."""

    ride: SportThresholds = field(default_factory=SportThresholds)
    run: SportThresholds = field(default_factory=SportThresholds)
    swim: SportThresholds = field(default_factory=SportThresholds)
    raw: dict[str, Any] = field(default_factory=dict)

    def format_block(self) -> str:
        lines = ["## Intervals terskler (William)"]
        if self.ride.ftp:
            lines.append(f"- Sykkel FTP: {self.ride.ftp} W")
        if self.ride.lthr:
            lines.append(f"- Sykkel LTHR: {self.ride.lthr} bpm")
        if self.run.lthr:
            lines.append(f"- Løp LTHR: {self.run.lthr} bpm")
        if self.run.threshold_pace_m_s:
            pace_min_km = 1000.0 / (self.run.threshold_pace_m_s * 60) if self.run.threshold_pace_m_s else None
            if pace_min_km:
                lines.append(f"- Løp terskeltempo: ~{pace_min_km:.2f} min/km")
        if self.ride.max_hr or self.run.max_hr:
            mx = self.ride.max_hr or self.run.max_hr
            lines.append(f"- Max puls (profil): {mx} bpm")
        if len(lines) == 1:
            lines.append(
                "(FTP/LTHR ikke satt i Intervals – bruk % HR/RPE i planer til profil er oppdatert.)"
            )
        return "\n".join(lines)


def _int_or_none(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def _float_or_none(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_athlete_payload(data: dict[str, Any]) -> AthleteThresholds:
    """Best-effort mapping from GET /athlete/{id} JSON."""
    if not data:
        return AthleteThresholds()

    ride = SportThresholds(
        ftp=_int_or_none(
            data.get("icu_ftp")
            or data.get("ftp")
            or data.get("ride_ftp")
            or data.get("cycling_ftp")
        ),
        lthr=_int_or_none(data.get("icu_lthr") or data.get("lthr") or data.get("lthr_cycling")),
        max_hr=_int_or_none(data.get("max_heartrate") or data.get("max_hr") or data.get("icu_max_hr")),
    )
    run = SportThresholds(
        lthr=_int_or_none(data.get("lthr_running") or data.get("run_lthr")),
        max_hr=_int_or_none(data.get("max_heartrate") or data.get("max_hr")),
        threshold_pace_m_s=_float_or_none(
            data.get("threshold_pace") or data.get("icu_threshold_pace")
        ),
    )
    swim = SportThresholds(
        lthr=_int_or_none(data.get("lthr_swimming")),
    )

    # Some profiles nest sport settings
    for key in ("sportSettings", "sports", "settings"):
        nested = data.get(key)
        if not isinstance(nested, dict):
            continue
        for sport_key, cfg in nested.items():
            if not isinstance(cfg, dict):
                continue
            sk = str(sport_key).lower()
            if "ride" in sk or "bike" in sk or "cycl" in sk:
                ride.ftp = ride.ftp or _int_or_none(cfg.get("ftp") or cfg.get("icu_ftp"))
                ride.lthr = ride.lthr or _int_or_none(cfg.get("lthr") or cfg.get("lthr_cycling"))
            if "run" in sk:
                run.lthr = run.lthr or _int_or_none(cfg.get("lthr") or cfg.get("lthr_running"))
                run.threshold_pace_m_s = run.threshold_pace_m_s or _float_or_none(
                    cfg.get("threshold_pace")
                )

    return AthleteThresholds(ride=ride, run=run, swim=swim, raw=data)
