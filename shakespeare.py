"""
"Was this word popularized by Shakespeare?" -- an annotation, never an origin.

A LEAF module: it imports nothing project-local and knows nothing about
buckets, chains or percentages, so it structurally cannot influence an origin
answer. That is the point. Joe, 2026-07-30: "I dont want it to be in the
language bucket or whatever, just something on the side that basically says
'hey this word was popularized by shakespeare'."

The wording is "popularized by", not "invented by", and that is a deliberate
accuracy choice rather than hedging. The OED names Shakespeare as the earliest
known source for ~1,700-2,000 words, but that is a claim about DOCUMENTATION:
Victorian OED readers combed his work far more thoroughly than his
contemporaries', so he is credited with first uses that also appear elsewhere,
and much of this vocabulary was surely spoken before anyone wrote it down.

Data comes from `shakespeare_words.json` (see `build_shakespeare_words.py`).
Each entry records its own source, so the weaker half can be dropped without
rebuilding:
    wiktionary -- the word's own Wiktionary etymology attributes it to him
    curated    -- a published list, with no per-word sentence
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "shakespeare_words.json")

_WORDS: Optional[Dict[str, dict]] = None


def _load() -> Dict[str, dict]:
    """Read the data once. A missing file disables the feature, never breaks it."""
    global _WORDS
    if _WORDS is not None:
        return _WORDS
    try:
        with open(_PATH, encoding="utf-8") as handle:
            _WORDS = json.load(handle).get("words") or {}
    except (OSError, json.JSONDecodeError, AttributeError):
        # An annotation is not worth taking the app down for.
        _WORDS = {}
    return _WORDS


def _key(word: Optional[str]) -> str:
    return (word or "").strip().lower()


def is_shakespearean(word: Optional[str]) -> bool:
    """Is this word associated with Shakespeare?"""
    key = _key(word)
    return bool(key) and key in _load()


def note(word: Optional[str]) -> Optional[str]:
    """
    The sentence attributing the word to him, when one is recorded.

    None for a curated-list word: those give only the spelling, and inventing
    a sentence for them would state something no source said.
    """
    entry = _load().get(_key(word))
    return entry.get("note") if entry else None


def source(word: Optional[str]) -> Optional[str]:
    """"wiktionary" (the word's own etymology) or "curated" (a published list)."""
    entry = _load().get(_key(word))
    return entry.get("source") if entry else None


def count() -> int:
    return len(_load())
