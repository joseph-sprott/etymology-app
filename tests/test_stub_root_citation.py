"""
A bare-root stub still has a real root, and Deepest Root must show it.

Issue #14's design is explicit: for a word whose only recorded ancestry is a
`has_root` pointer, Direct Source and Notable Influence report Unknown -- no
English word borrows straight from a proto-language -- but "Deepest Root is
deliberately untouched: the PIE citation itself is real, verified Wiktionary
data, so it still shows."

`DbResolver` never implemented that half. It treats a stub as a MISS in every
mode, and the PIE citation was arriving from the legacy file-backed backends
instead. Removing them exposed it: `narrate`, `cute` and `semi` -- `narrate`
being the very word this project uses as its bare-root-stub specimen -- lost
their Deepest Root answer entirely.

Same shape as every other finding this week: the fallback was masking a
database-layer gap rather than filling one.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from resolver import DbResolver


@pytest.fixture(scope="module")
def db():
    return DbResolver()


@pytest.mark.parametrize("word", ["narrate", "cute", "semi"])
def test_deepest_root_shows_the_stubs_real_citation(db, word):
    view = db.resolve(word).view("root")
    assert view.bucket != "Unknown", (
        f"{word} is a bare-root stub; its root citation is real data and "
        f"Deepest Root must still show it")


@pytest.mark.parametrize("word", ["narrate", "cute", "semi"])
def test_direct_source_still_refuses_to_name_a_root_as_a_donor(db, word):
    # The other half of issue #14, which must NOT regress: no English word
    # borrows straight from a proto-language, so claiming one as an immediate
    # donor is impossible in principle.
    assert db.resolve(word).view("direct").bucket == "Unknown"
    assert db.resolve(word).view("influence").bucket == "Unknown"


def test_an_ordinary_word_is_unaffected(db):
    assert db.resolve("table").view("direct").bucket == "French"
    assert db.resolve("trust").view("direct").bucket == "Germanic"
