"""
A hand-verified correction must win, whichever backend would otherwise answer.

`corrections.py` exists to FIX confirmed-wrong answers, and its docstring is
explicit that every remaining entry was individually verified against live
Wiktionary and that redundant ones were deleted. But the table was only ever
consulted INSIDE the two legacy file-backed backends, so a correction applied
only when one of those happened to answer.

Measured 2026-07-31: 16 of 92 corrections were not reaching the output --
including `tag`, `auto` and `package`, three of the six failures issue #18
records as "deliberate answer judgment calls". They are not judgment calls;
they are corrections that never arrive.

`as` was a fourth, fixed a commit earlier by a different route: the correction
said Germanic while the app said Latin, the exact multi-sense collision the
entry was written to prevent.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from resolver import shared_resolver
from corrections import WORD_CORRECTIONS


@pytest.mark.parametrize("word", ["tag", "auto", "package", "cheese", "wang"])
def test_a_correction_is_honoured(word):
    want = WORD_CORRECTIONS[word]["p"]
    got = shared_resolver().resolve(word).view("direct").bucket
    assert got == want, f"{word}: corrections.py says {want}, app says {got}"


def test_every_correction_is_honoured():
    """The whole table, so a future backend change cannot silently bypass it."""
    missed = []
    resolver = shared_resolver()
    for word, fix in WORD_CORRECTIONS.items():
        got = resolver.resolve(word).view("direct").bucket
        if got != fix["p"]:
            missed.append((word, fix["p"], got))
    assert not missed, f"{len(missed)} corrections not honoured: {missed[:10]}"
