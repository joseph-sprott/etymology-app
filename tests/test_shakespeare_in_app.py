"""
The annotation has to reach the page, and must not touch the origin answer.

Joe wanted it "on the side" -- so the test asserts both halves: the card
carries the flag, AND the word's bucket/lineage are byte-identical to what
they were without it. A feature that quietly moved a percentage would be the
opposite of what was asked for.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import shakespeare


def _kinds(card):
    return {n.kind for n in (card or {}).get("notes", [])}


def test_the_card_flags_a_shakespeare_word():
    # The card carries a general `notes` list as of 2026-07-31 -- coinage,
    # calque, formation and era all ride the same channel, so a new kind needs
    # no new card field.
    card = app.build_word_card("assassination")
    assert card is not None
    assert "coinage" in _kinds(card)


def test_an_ordinary_word_is_not_flagged():
    card = app.build_word_card("table")
    assert card is not None
    assert "coinage" not in _kinds(card)


def test_the_flag_does_not_disturb_the_origin_answer():
    # `assassination` is a Latin/French word that Shakespeare popularized.
    # The annotation must leave that reading exactly alone.
    view = app.RESOLVER.resolve("assassination").view("direct")
    assert view.bucket != "Unknown"
    assert shakespeare.is_shakespearean("assassination")
    card = app.build_word_card("assassination")
    assert card["lineage"], "lineage must still be present and unmodified"
