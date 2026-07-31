"""
The lookup a display layer uses: "is this word associated with Shakespeare?"

Deliberately a LEAF module with no knowledge of buckets, chains or
percentages. Joe: "I dont want it to be in the language bucket or whatever,
just something on the side." Keeping it uncoupled is what makes that true --
nothing here can influence an origin answer.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shakespeare


def test_a_listed_word_is_flagged():
    assert shakespeare.is_shakespearean("assassination")


def test_lookup_ignores_case_and_surrounding_space():
    assert shakespeare.is_shakespearean("Assassination")
    assert shakespeare.is_shakespearean("  gloomy  ")


def test_an_ordinary_word_is_not_flagged():
    assert not shakespeare.is_shakespearean("table")
    assert not shakespeare.is_shakespearean("")
    assert not shakespeare.is_shakespearean(None)


def test_a_flagged_word_can_explain_itself():
    note = shakespeare.note("all the world's a stage")
    assert note and "Shakespeare" in note


def test_a_curated_word_has_no_note_but_is_still_flagged():
    # The curated lists give no sentence, only the word. The UI must cope
    # with that rather than assume every entry can explain itself.
    assert shakespeare.is_shakespearean("zany")
    assert shakespeare.note("zany") is None
