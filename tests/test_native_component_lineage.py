"""
A component with purely NATIVE descent is still the word's answer.

`_deepest_part_line` picks whichever component travels through the most
foreign languages -- right for `bagpipe`, where `pipe` reaches Latin and `bag`
does not. But it scored a purely native component at ZERO and rejected it, so
a derived word whose base descends through the English stages lost its
evidence entirely and reported a miss:

    chuckled  -> chuckle -> chuck  (Middle English, Germanic)   -> MISS
    fondling  -> fond            (Middle English, Germanic)   -> MISS
    hikers    -> hiker -> hike     (Middle English, Germanic)   -> MISS

Each base resolves Germanic on its own in the database. Only the derived form
failed, and the legacy backends covered for it -- with WRONG answers in two
cases (`chuckled` read French, `fondling` read Latin; both are Germanic).

Found 2026-07-31 while diagnosing the last 8 words blocking the backend
collapse.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from resolver import DbResolver


@pytest.fixture(scope="module")
def db_only():
    return DbResolver()


@pytest.mark.parametrize("word", ["chuckled", "fondling", "hikers"])
def test_a_native_base_still_answers_the_derived_word(db_only, word):
    view = db_only.resolve(word).view("direct")
    assert view.bucket == "Germanic", (
        f"{word}'s base descends natively and the database knows it, "
        f"got {view.bucket}")


def test_a_foreign_component_still_wins_over_a_native_one(db_only):
    # The control. `bagpipe` is bag + pipe; `pipe` reaches Latin and must
    # still be preferred over the native `bag`, which is the whole reason
    # the "most foreign steps" rule exists.
    view = db_only.resolve("bagpipe").view("direct")
    assert view.bucket in ("French", "Latin"), view.bucket
