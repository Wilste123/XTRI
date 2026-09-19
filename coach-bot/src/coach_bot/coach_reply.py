"""Structured Slack coach response."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CoachReply:
    text: str
    blocks: list[dict[str, Any]] | None = None
    image_paths: list[Path] = field(default_factory=list)
