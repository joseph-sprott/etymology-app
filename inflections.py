"""
Inflected-form -> base-word lookup, shared by the query-time resolver and the
build-time converter.

Its own module (rather than living inside resolver.py) because BOTH sides need
the exact same answer and must not drift apart:
  - `resolver.py`'s ChainResolver.resolve() uses it at query time, when a
    word's own surface form isn't in the database.
  - `convert_wikt.py`'s `_patch_root_stubs()` uses it at BUILD time, so that a
    derived word citing an inflected root (e.g. "unheard" citing "heard")
    inherits correctly while the data file is being written.
Those two used to share resolver.py's hand-maintained `_IRREGULAR_FORMS`
table for exactly this reason -- keeping one shared implementation preserves
that guarantee now that the data comes from a file. See build_inflections.py
for where the data comes from and what it deliberately does NOT cover
(derivational suffixes -- resolver.py's own stemmer still handles those).

Degrades gracefully: if inflections.json is absent, every lookup returns []
and the caller falls through to its other strategies, exactly as it would for
a word with no inflection recorded. This mirrors default_resolver()'s existing
handling of a missing wikt_words.json -- a missing optional data file should
narrow results, never crash the app.
"""
import json
import os
from typing import List, Optional

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inflections.json")

_FORMS: Optional[dict] = None


def _load() -> dict:
    global _FORMS
    if _FORMS is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _FORMS = json.load(f)
        except (OSError, ValueError):
            _FORMS = {}
    return _FORMS


def base_form(word: str) -> Optional[str]:
    """The recorded base word for an inflected form, or None."""
    return _load().get(word.lower())


def inflection_candidates(word: str) -> List[str]:
    """
    Base-form candidates to try when `word` itself has no entry.

    Returns at most one candidate (a form maps to a single recorded base), in
    a list to match the shape callers already expect from the stemming
    candidate generators they concatenate this with.
    """
    base = base_form(word)
    if not base or base.lower() == word.lower():
        return []
    return [base]


def loaded_count() -> int:
    """How many inflected forms are loaded (0 if the data file is missing)."""
    return len(_load())
