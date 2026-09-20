from datetime import date
from pathlib import Path

from coach_bot import atlas


def test_append_and_search(tmp_path: Path):
    lof = tmp_path / "LOFOTEN-2027"
    lof.mkdir()
    ok, msg = atlas.append_fact(lof, "utstyr", "Ny sykkel: Canyon Aeroad 2024")
    assert ok
    assert "Lagret" in msg
    hits = atlas.search("sykkel canyon", lof, top_k=2)
    assert hits and "Canyon" in hits[0].text


def test_dedupe(tmp_path: Path):
    lof = tmp_path / "LOFOTEN-2027"
    lof.mkdir()
    atlas.append_fact(lof, "utstyr", "Powermeter på sykkelen")
    ok, _ = atlas.append_fact(lof, "utstyr", "Powermeter på sykkelen")
    assert not ok


def test_normalize_category():
    assert atlas.normalize_category("sykkel") == "Utstyr og setup"
    assert atlas.normalize_category("notat") == "Frie notater"


def test_excerpt_includes_recent(tmp_path: Path):
    lof = tmp_path / "LOFOTEN-2027"
    lof.mkdir()
    atlas.append_fact(lof, "preferanser", "Liker korte harde intervaller", on_date=date(2026, 9, 1))
    txt = atlas.excerpt_for_context(lof, "intervaller", max_chars=2000)
    assert "intervaller" in txt.lower() or "harde" in txt.lower()
