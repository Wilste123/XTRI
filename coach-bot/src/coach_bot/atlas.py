"""William's long-term memory (11_ATLAS.md) – read, search, append."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from coach_bot import knowledge

_ATLAS_NAME = "11_ATLAS.md"

_SECTIONS = (
    "Utstyr og setup",
    "Preferanser og vaner",
    "Helse og skadehistorikk",
    "Mål og grenser (personlige)",
    "Hendelser og beslutninger",
    "Frie notater",
)

_CATEGORY_ALIASES: dict[str, str] = {
    "utstyr": "Utstyr og setup",
    "equipment": "Utstyr og setup",
    "setup": "Utstyr og setup",
    "sykkel": "Utstyr og setup",
    "preferanser": "Preferanser og vaner",
    "vaner": "Preferanser og vaner",
    "helse": "Helse og skadehistorikk",
    "skade": "Helse og skadehistorikk",
    "smerte": "Helse og skadehistorikk",
    "mål": "Mål og grenser (personlige)",
    "grenser": "Mål og grenser (personlige)",
    "hendelse": "Hendelser og beslutninger",
    "beslutning": "Hendelser og beslutninger",
    "notat": "Frie notater",
    "annet": "Frie notater",
}

_SECTION_HEADER = re.compile(r"^## (.+)$", re.MULTILINE)
_ENTRY = re.compile(r"^- (\d{4}-\d{2}-\d{2}): (.+)$", re.MULTILINE)


@dataclass
class AtlasEntry:
    section: str
    on_date: str
    text: str

    @property
    def blob(self) -> str:
        return f"{self.section} {self.on_date} {self.text}"


def normalize_category(raw: str) -> str:
    key = (raw or "").strip().lower()
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    for section in _SECTIONS:
        if key == section.lower():
            return section
    return "Frie notater"


def atlas_path(lofoten_dir: Path) -> Path:
    return lofoten_dir / _ATLAS_NAME


def ensure_atlas_file(path: Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "# Atlas – William (langsiktig hukommelse)\n\n"
    for section in _SECTIONS:
        body += f"## {section}\n\n"
    path.write_text(body, encoding="utf-8")


def parse_entries(text: str) -> list[AtlasEntry]:
    entries: list[AtlasEntry] = []
    current = _SECTIONS[0]
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            continue
        m = re.match(r"^- (\d{4}-\d{2}-\d{2}): (.+)$", line.strip())
        if m:
            entries.append(AtlasEntry(current, m.group(1), m.group(2).strip()))
    return entries


def read_atlas(lofoten_dir: Path) -> str:
    path = atlas_path(lofoten_dir)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def append_fact(
    lofoten_dir: Path,
    category: str,
    fact: str,
    on_date: date | None = None,
    *,
    dedupe: bool = True,
) -> tuple[bool, str]:
    """Append a dated bullet under a section. Returns (written, message)."""
    fact = (fact or "").strip()
    if not fact:
        return False, "Tomt faktum."
    section = normalize_category(category)
    path = atlas_path(lofoten_dir)
    ensure_atlas_file(path)
    text = path.read_text(encoding="utf-8")
    d = (on_date or date.today()).isoformat()
    line = f"- {d}: {fact}"

    if dedupe:
        low = fact.lower()
        for entry in parse_entries(text):
            if entry.text.lower() == low or low in entry.text.lower():
                return False, f"Finnes allerede ({entry.on_date}): {entry.text}"

    if section not in text:
        text = text.rstrip() + f"\n\n## {section}\n\n{line}\n"
    else:
        marker = f"## {section}"
        before, after = text.split(marker, 1)
        insert_at = after.find("\n## ")
        if insert_at == -1:
            after = after.rstrip() + f"\n{line}\n"
        else:
            head, tail = after[:insert_at], after[insert_at:]
            after = head.rstrip() + f"\n{line}\n" + tail
        text = before + marker + after

    path.write_text(text, encoding="utf-8")
    return True, f"Lagret i Atlas [{section}]: {fact}"


def persist_fact(
    lofoten_dir: Path,
    category: str,
    fact: str,
    github: Any | None = None,
    on_date: date | None = None,
) -> str:
    ok, msg = append_fact(lofoten_dir, category, fact, on_date=on_date, dedupe=True)
    if ok and github is not None and getattr(github, "enabled", False):
        github.publish_local(
            atlas_path(lofoten_dir),
            f"coach: atlas – {fact[:60]}",
        )
    return msg


def search(query: str, lofoten_dir: Path, top_k: int = 5) -> list[AtlasEntry]:
    entries = parse_entries(read_atlas(lofoten_dir))
    if not entries:
        return []
    q_tokens = knowledge._tokenize(query)  # noqa: SLF001 – shared token rules
    if not q_tokens:
        return entries[-top_k:]
    scored: list[tuple[float, AtlasEntry]] = []
    for entry in entries:
        blob = entry.blob.lower()
        c_tokens = knowledge._tokenize(entry.blob)  # noqa: SLF001
        score = 0.0
        matched = 0
        for qt in q_tokens:
            if qt in blob or qt in c_tokens:
                matched += 1
                score += 1.0 + 0.1 * blob.count(qt)
        if matched:
            scored.append((score, entry))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [e for _, e in scored[:top_k]]


def search_text(query: str, lofoten_dir: Path, top_k: int = 5) -> str:
    hits = search(query, lofoten_dir, top_k=top_k)
    if not hits:
        return "(ingen personlige fakta i Atlas ennå – bruk remember_fact når William deler noe varig)"
    parts = [f"[{h.section}] {h.on_date}: {h.text}" for h in hits]
    return "\n".join(parts)


def excerpt_for_context(lofoten_dir: Path, user_message: str, max_chars: int = 2500) -> str:
    """Relevant Atlas hits + recent entries if query is empty."""
    hits = search(user_message, lofoten_dir, top_k=6)
    if not hits:
        entries = parse_entries(read_atlas(lofoten_dir))
        hits = entries[-8:]
    if not hits:
        return "(Atlas tom – coach lærer når William deler varige fakta)"
    text = "\n".join(f"- {h.on_date} [{h.section}] {h.text}" for h in hits)
    if len(text) > max_chars:
        return text[-max_chars:]
    return text
