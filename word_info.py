"""
Per-word definition / part-of-speech / cognate / doublet lookup.

Loaded once at module level and consulted by BOTH the paragraph analyzer's
hover cards and the Word Search page -- per this project's standing rule that
every feature must pool from the same store rather than each fetching its own
copy (see app.py's RESOLVER comment and CLAUDE.md).

Data comes from build_word_info.py; see that module for what's in it and why
it's kept separate from the ancestry pipeline (cognates and doublets are
SIBLING relations, deliberately excluded from lineage chains).

Degrades gracefully to empty if word_info.json is absent -- callers get None
and render their "no information" state, exactly as for a word genuinely not
in the data. A missing optional file should narrow what's shown, never crash
the app (same contract as inflections.py).
"""
import json
import os
from typing import List, Optional

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "word_info.json")

_INFO: Optional[dict] = None


def _load() -> dict:
    global _INFO
    if _INFO is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _INFO = json.load(f)
        except (OSError, ValueError):
            _INFO = {}
    return _INFO


def lookup(word: str) -> Optional[dict]:
    """
    {"pos": [...], "gloss": str|None, "cognates": [[lang, term], ...],
     "doublets": [term, ...]} for a word, or None if we have nothing.

    Tries the lowercase form first (analyzer tokens are already lowercased),
    then the word as typed -- the same order WiktionaryResolver uses, so a
    capitalized proper noun typed at sentence start doesn't shadow the common
    word.
    """
    info = _load()
    return info.get(word.lower()) or info.get(word)


def pos_label(word: str) -> Optional[str]:
    """Human-readable part of speech list, e.g. "noun, verb"."""
    rec = lookup(word)
    if not rec or not rec.get("pos"):
        return None
    return ", ".join(rec["pos"])


def gloss(word: str) -> Optional[str]:
    rec = lookup(word)
    return rec.get("gloss") if rec else None


def cognates(word: str) -> List[list]:
    rec = lookup(word)
    return rec.get("cognates", []) if rec else []


def doublets(word: str) -> List[str]:
    rec = lookup(word)
    return rec.get("doublets", []) if rec else []


def loaded_count() -> int:
    return len(_load())
