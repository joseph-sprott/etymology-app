"""
Descent through an English stage is native, whichever edge kind records it.

Issue #22 established that a native-core claim needs EVIDENCE, and the
evidence chosen was an `inherited` edge. That is too narrow. Wiktionary
records plenty of ordinary native descent as `derived`:

    lose  <- Middle English losen  [derived]
    start <- Middle English stert  [derived]

Both are plainly English descending from English, and both were being
reported as a MISS -- invisible only because the legacy file-backed backends
answered them instead. Found 2026-07-31 while measuring what collapsing the
backend cascade would actually cost.

The guard itself must survive: a word whose only recorded formation is a
suffix, or whose parts are absent from the database, still has no evidence of
native descent and must stay a miss. That is what stopped `movie` and
`zoophysiologist` being announced as Germanic.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from resolver import ChainResolver, DbResolver


@pytest.fixture(scope="module")
def db_only():
    """
    The database backend ALONE -- no legacy fallback to mask a gap.

    Deliberately the raw `DbResolver`, not a `ChainResolver` wrapping it:
    since 2026-07-31 the chain applies `corrections.py` as an override, which
    would answer `movie` from the hand-verified table and hide what the
    database itself does. These tests are about the database's own rule.
    """
    return DbResolver()


@pytest.mark.parametrize("word", ["lose", "lost", "start", "started"])
def test_derived_from_an_english_stage_is_native_descent(db_only, word):
    view = db_only.resolve(word).view("direct")
    assert view.bucket == "Germanic", (
        f"{word} descends from Middle English via a `derived` edge and the "
        f"database alone should say so, got {view.bucket}")


def test_a_suffix_only_formation_is_still_not_native(db_only):
    # `movie`'s entire recorded formation is the suffix `ie`; the builder lost
    # `move`. No descent evidence exists, so the database must still miss and
    # let the corrections layer answer.
    assert db_only.resolve("movie").view("direct").bucket == "Unknown"


def test_absent_parts_are_still_not_native(db_only):
    # `zoophysiologist` is Greek, but its parts are absent from the database,
    # so the walk dead-ends inside English. That must not become a Germanic
    # claim -- the exact bug issue #22 fixed.
    assert db_only.resolve("zoophysiologist").view("direct").bucket != "Germanic"
