"""Local expert knowledge base + lightweight retrieval.

Curated, evidence-based notes on endurance training, injury, nutrition and the
Lofoten race live as markdown under ``knowledge/``. This module chunks them by
heading and does simple keyword-overlap retrieval so the coach can ground its
answers in vetted content without depending on a live web/API call.

The retrieval is intentionally dependency-free (no embeddings) so it works
offline and deterministically. It can later be upgraded to embeddings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"

# Korte norske/engelske stoppord som ikke bør telle i matching.
_STOPWORDS = {
    "og", "i", "på", "for", "å", "en", "et", "er", "som", "til", "med", "av",
    "det", "den", "de", "du", "jeg", "vi", "har", "kan", "om", "hva", "hvordan",
    "eller", "men", "så", "at", "the", "a", "of", "to", "and", "is", "in", "for",
    "meg", "deg", "min", "din", "skal", "vil", "være", "litt", "mer",
}

_WORD = re.compile(r"[a-zA-ZæøåÆØÅ0-9]+")


@dataclass
class KnowledgeChunk:
    source: str
    title: str
    text: str

    @property
    def tokens(self) -> set[str]:
        return _tokenize(f"{self.title} {self.text}")


def _tokenize(text: str) -> set[str]:
    return {
        w.lower()
        for w in _WORD.findall(text or "")
        if len(w) > 2 and w.lower() not in _STOPWORDS
    }


def _split_into_chunks(md: str, source: str) -> list[KnowledgeChunk]:
    """Split a markdown doc into chunks by level-2 (##) heading."""
    chunks: list[KnowledgeChunk] = []
    title = source
    body: list[str] = []
    for line in md.splitlines():
        if line.startswith("## "):
            if body and "".join(body).strip():
                chunks.append(KnowledgeChunk(source, title, "\n".join(body).strip()))
            title = line[3:].strip()
            body = []
        elif line.startswith("# "):
            continue
        else:
            body.append(line)
    if body and "".join(body).strip():
        chunks.append(KnowledgeChunk(source, title, "\n".join(body).strip()))
    return chunks


@lru_cache(maxsize=1)
def _load_chunks() -> tuple[KnowledgeChunk, ...]:
    chunks: list[KnowledgeChunk] = []
    if not _KNOWLEDGE_DIR.is_dir():
        return tuple()
    for path in sorted(_KNOWLEDGE_DIR.glob("*.md")):
        chunks.extend(_split_into_chunks(path.read_text(encoding="utf-8"), path.stem))
    return tuple(chunks)


def topics() -> list[str]:
    """List available knowledge sources (file stems)."""
    return sorted({c.source for c in _load_chunks()})


def search(query: str, top_k: int = 3) -> list[KnowledgeChunk]:
    """Return the most relevant knowledge chunks for a query.

    Scoring: overlap of query tokens with chunk tokens, weighted by how often
    the query token appears in the chunk text. Deterministic and offline.
    """
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    scored: list[tuple[float, KnowledgeChunk]] = []
    for chunk in _load_chunks():
        low = f"{chunk.title} {chunk.text}".lower()
        title_low = chunk.title.lower()
        c_tokens = chunk.tokens
        score = 0.0
        matched = 0
        for qt in q_tokens:
            best = _best_token_match(qt, c_tokens)
            if not best:
                continue
            matched += 1
            score += 1.0 + 0.15 * (low.count(best) - 1)
            if best in title_low:
                score += 0.5  # treff i overskrift teller mer
        if matched:
            scored.append((score, chunk))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def _best_token_match(qt: str, c_tokens: set[str]) -> str | None:
    """Match on equality or shared prefix (handles bøyninger: kne↔kneet,
    løp↔løping, økt↔økter)."""
    if qt in c_tokens:
        return qt
    for ct in c_tokens:
        short, long = (qt, ct) if len(qt) <= len(ct) else (ct, qt)
        if len(short) >= 4 and long.startswith(short):
            return ct
    return None


def search_text(query: str, top_k: int = 3) -> str:
    """Human/LLM-readable rendering of the top knowledge chunks."""
    hits = search(query, top_k=top_k)
    if not hits:
        return "(fant ingen relevant fagkunnskap i basen)"
    parts = [f"[{h.source}] {h.title}\n{h.text}" for h in hits]
    return "\n\n---\n\n".join(parts)
