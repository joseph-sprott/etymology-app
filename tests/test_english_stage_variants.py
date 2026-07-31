"""
A dialect of an English stage is still English. A creole named after it is not.

Found by the 2026-07-30 random-word scan (issue #25): `Northern Middle
English` and `Anglian Old English` bucketed as `Other` and were not recognised
as English stages at all. They are Middle and Old English -- Germanic, and
native descent.

THE TRAP, and the reason this is not "anything ending in English":
`Chinese Pidgin English` and `Trinidadian Creole English` also end that way
and are NOT stages of English. They are contact languages, and a word BORROWED
from one is a borrowing, not native descent. Treating them as a stage would
make those loans read as inherited -- the exact "absence of evidence" family
of bug that issue #22 and the `derived`-edge work have already had to fix
twice.

`is_english_stage` gates real behaviour: whether a node counts as a donor at
all, and whether a native-core claim has evidence. Widening it carelessly is
how a borrowing gets recorded as inheritance.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import linguistics
from buckets_wikt import bucket_for_name

DIALECTS = ["Northern Middle English", "Anglian Old English",
            "Northumbrian Old English"]
CONTACT = ["Chinese Pidgin English", "Trinidadian Creole English"]


@pytest.mark.parametrize("name", DIALECTS)
def test_a_dialect_of_an_english_stage_is_germanic(name):
    assert bucket_for_name(name) == "Germanic"


@pytest.mark.parametrize("name", DIALECTS)
def test_a_dialect_of_an_english_stage_counts_as_a_stage(name):
    assert linguistics.is_english_stage(name)


@pytest.mark.parametrize("name", CONTACT)
def test_a_contact_language_is_never_an_english_stage(name):
    assert not linguistics.is_english_stage(name), (
        f"{name} is a contact language; a word borrowed from it is a "
        f"BORROWING, and calling it a stage would record it as inheritance")


def test_the_plain_stages_are_untouched():
    for name in ("English", "Middle English", "Old English"):
        assert linguistics.is_english_stage(name)
        assert bucket_for_name(name) == "Germanic"
    # Scots is a sister language, not a stage. That reading is deliberate and
    # documented; this fix must not disturb it.
    assert not linguistics.is_english_stage("Scots")


@pytest.mark.parametrize("name,bucket", [
    ("Andalusian Arabic", "Semitic"),
    ("Moroccan Arabic", "Semitic"),
    ("Renaissance Latin", "Latin"),
    ("Canadian French", "French"),
    ("Attic Greek", "Greek"),
    ("Pennsylvania German", "Germanic"),
])
def test_a_qualified_variant_falls_back_to_its_parent(name, bucket):
    # Same shape, much larger population: the map knows the parent language
    # but not the qualified variant, so it fell to `Other`.
    assert bucket_for_name(name) == bucket


def test_an_unknown_language_still_reaches_Other():
    assert bucket_for_name("Klingon") == "Other"
    assert bucket_for_name("") == "Other"
