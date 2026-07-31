"""
A component argument can carry its own language code, and a sense anchor.

Wiktionary writes `{{af|en|la:obvius|-ous}}` -- the part is LATIN `obvius`,
not an English word spelled `la:obvius`. The builder stored the whole string
as the term, so the component could never resolve and `obvious` fell through
to the legacy backends. 2,217 nodes carry a prefix like this.

Separately, 471 carry a sense anchor (`-al#Etymology_1`) which is a link
target, not part of the spelling.

Found 2026-07-31 while measuring what collapsing the backend cascade costs.
Deliberately NOT touched, because they are not reliably malformed: terms
containing spaces (4,206 -- many are real phrases, `"What's up, dog?"`) and
parentheses (991 -- `(Digitalis) lanata` is a real taxonomic name).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wiktextract_shapes import split_language_prefix, clean_term


KNOWN = {"la", "ang", "grc", "grc-koi", "enm"}.__contains__


def test_a_language_prefix_is_split_off():
    assert split_language_prefix("la:obvius", KNOWN) == ("la", "obvius")
    assert split_language_prefix("ang:middes", KNOWN) == ("ang", "middes")
    assert split_language_prefix("grc-koi:x", KNOWN) == ("grc-koi", "x")


def test_an_ordinary_term_is_untouched():
    assert split_language_prefix("obvius", KNOWN) == (None, "obvius")
    assert split_language_prefix("-ous", KNOWN) == (None, "-ous")
    assert split_language_prefix("", KNOWN) == (None, "")
    assert split_language_prefix(None, KNOWN) == (None, None)


def test_a_colon_that_is_not_a_known_language_is_left_alone():
    # Shape alone cannot tell `re:invent` from `la:obvius`. Only a code the
    # language index actually knows is treated as a prefix; guessing would
    # mangle every term containing a colon.
    assert split_language_prefix("re:invent", KNOWN) == (None, "re:invent")
    assert split_language_prefix("http://x", KNOWN) == (None, "http://x")


def test_without_a_validator_nothing_is_split():
    assert split_language_prefix("la:obvius") == (None, "la:obvius")


def test_a_sense_anchor_is_stripped():
    assert clean_term("-al#Etymology_1")[0] == "-al"
    assert clean_term("-and#Etymology 2")[0] == "-and"
    assert clean_term("dose#noun")[0] == "dose"


def test_a_plain_term_survives_clean_term_unchanged():
    assert clean_term("beauty")[0] == "beauty"
    assert clean_term("-ful")[0] == "-ful"
