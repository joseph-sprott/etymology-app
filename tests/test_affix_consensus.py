"""
The source marks the same morpheme inconsistently; take its majority verdict.

`active` records `ive` unmarked while `massive` records it marked and
`creative` records `-ive`. Wiktionary's `af`/`surf` templates promise nothing
positionally, so the builder cannot tell from one entry alone -- but across
the whole dump the answer is overwhelming:

    ness  7529/7533 marked   ly  10051/10067   ive  345/348   ful 1206/1214
    ship   907/1078          man   574/1072    head  99/647   ball   2/287

So a morpheme marked in the vast majority of its appearances IS an affix, and
the stragglers are the source being inconsistent rather than saying something
different.

THE THRESHOLD IS THE WHOLE DESIGN. At 95% `ive` is marked and `man` (54%) and
`ship` (84%) are not -- which is what keeps `craftsman` and `friendship`
splitting, per Joe's ruling that the hand-verified compounds win. A lower
threshold would start eating real compound parts; five earlier attempts at
this problem died exactly that way.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from build_etymology_db import is_consensus_affix


@pytest.mark.parametrize("marked,total", [
    (7529, 7533),   # ness
    (10051, 10067),  # ly
    (345, 348),     # ive
    (1206, 1214),   # ful
    (428, 429),     # esque
])
def test_an_overwhelmingly_marked_morpheme_is_an_affix(marked, total):
    assert is_consensus_affix(marked, total)


@pytest.mark.parametrize("marked,total", [
    (574, 1072),    # man  -- craftsman must keep splitting
    (907, 1078),    # ship -- friendship likewise
    (99, 647),      # head
    (60, 300),      # side
    (2, 287),       # ball -- basketball is not an affixed form
    (0, 224),       # bird
])
def test_an_ambiguous_or_word_like_part_is_left_alone(marked, total):
    assert not is_consensus_affix(marked, total)


def test_a_rare_term_is_not_judged_on_one_or_two_sightings():
    # 1/1 is 100% and means nothing. Requiring a floor stops a single
    # mis-tagged entry from reclassifying a morpheme everywhere.
    assert not is_consensus_affix(1, 1)
    assert not is_consensus_affix(3, 3)


def test_nothing_is_decided_without_evidence():
    assert not is_consensus_affix(0, 0)
