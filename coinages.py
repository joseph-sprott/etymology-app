"""
"Who coined this word?" -- a lookup, never an origin.

A LEAF MODULE: imports nothing project-local, so it cannot influence a bucket
or a percentage. Same contract as `shakespeare.py`, which it sits beside.

TWO SOURCES, TWO STRENGTHS OF CLAIM, kept apart on purpose:

  `coinages.json`  -- Wiktionary's own `Category:English terms coined by X`
                      (CC BY-SA). An explicit attribution by a human editor,
                      so the wording is "coined by".
  `shakespeare.py` -- rests on the OED naming Shakespeare the earliest known
                      source for ~1,700 words. That is a claim about
                      DOCUMENTATION, not invention: Victorian OED readers
                      combed him far harder than his contemporaries. So the
                      wording there stays "popularized by".

Shakespeare appears in both. The softer wording wins for him, because the
stronger one would overstate what the evidence supports.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "coinages.json")

_WORDS: Optional[Dict[str, dict]] = None


def _load() -> Dict[str, dict]:
    """Read once. A missing file disables the feature, never breaks it."""
    global _WORDS
    if _WORDS is not None:
        return _WORDS
    try:
        with open(_PATH, encoding="utf-8") as handle:
            _WORDS = json.load(handle).get("words") or {}
    except (OSError, json.JSONDecodeError, AttributeError):
        _WORDS = {}
    return _WORDS


def coiner(word: Optional[str]) -> Optional[str]:
    """Who Wiktionary credits with coining this word, or None."""
    entry = _load().get((word or "").strip().lower())
    return entry.get("coiner") if entry else None


def count() -> int:
    return len(_load())
