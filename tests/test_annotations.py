"""
Side notes about a word: never an origin, always an aside.

Four kinds, all from data already on disk:
  coinage    -- attributed to a named person (Shakespeare and 99 others)
  calque     -- a translated borrowing, 2,437 recorded
  formation  -- what the word was built from, 673,240 edges
  era        -- when the donor language was spoken, from curated era data

One module rather than four parallel features. A note is a note; adding a
fifth kind should be one function, not another template block, another CSS
rule and another route variable. Joe's standing rule: no spaghetti.

Nothing here may touch a bucket or a percentage. That is asserted.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import annotations


def _kinds(word):
    return {n.kind for n in annotations.for_word(word)}


def test_a_shakespeare_word_still_gets_its_coinage_note():
    notes = [n for n in annotations.for_word("assassination")
             if n.kind == "coinage"]
    assert notes and "Shakespeare" in notes[0].text


def test_another_coiner_is_credited_by_name():
    # The Shakespeare feature generalised: Wiktionary attributes coinages to
    # ~400 people, and 18 recognisable ones are loaded. A note must name WHO,
    # or "coined by someone" says nothing.
    # `frabjous`, not `chortle`: Wiktionary's Carroll category holds the
    # Jabberwocky words. `chortle` is famously his too but is categorised
    # elsewhere -- checked, rather than assumed.
    notes = [n for n in annotations.for_word("frabjous") if n.kind == "coinage"]
    assert notes, "frabjous is Lewis Carroll's"
    assert "Carroll" in notes[0].text


def test_the_coinage_claim_is_worded_per_source():
    # "coined by" for a Wiktionary attribution, which is explicit; but
    # "popularized by" for Shakespeare, whose list rests on OED FIRST
    # ATTESTATION -- a claim about documentation, not invention.
    bard = [n for n in annotations.for_word("assassination")
            if n.kind == "coinage"][0]
    assert "popularized" in bard.text


def test_a_calque_is_explained_not_just_labelled():
    # `peacemaker` is peace + maker, merely MODELLED on Koine Greek. A reader
    # who does not know the word "calque" must still understand the note.
    notes = [n for n in annotations.for_word("peacemaker") if n.kind == "calque"]
    assert notes, "peacemaker is a recorded calque"
    detail = notes[0].detail or ""
    assert "word-for-word" in detail or "literally" in detail
    assert "blueprint" in detail or "translat" in detail


def test_a_built_word_says_what_it_was_built_from():
    notes = [n for n in annotations.for_word("photograph")
             if n.kind == "formation"]
    assert notes
    assert "photo" in notes[0].text and "graph" in notes[0].text


def test_an_era_note_names_when_the_donor_was_spoken():
    notes = [n for n in annotations.for_word("table") if n.kind == "era"]
    assert notes
    assert any(ch.isdigit() for ch in notes[0].text), notes[0].text


def test_an_ordinary_word_gets_no_spurious_notes():
    assert "coinage" not in _kinds("the")
    assert "calque" not in _kinds("the")


def test_notes_never_carry_a_bucket_or_percentage():
    # The whole point: an annotation is an aside. If one ever grew a bucket
    # field it could start influencing the chart.
    for word in ("assassination", "peacemaker", "photograph", "table"):
        for note in annotations.for_word(word):
            assert not hasattr(note, "bucket")
            assert not hasattr(note, "share")


def test_a_missing_word_is_handled():
    assert annotations.for_word("") == []
    assert annotations.for_word(None) == []
