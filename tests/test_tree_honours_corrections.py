"""
The Word Search tree must not contradict a hand-verified correction.

Issue #16's standing residual: `resolve_tree` consults its stored trees BEFORE
asking the resolver, so a word fixed in `corrections.py` kept rendering the
uncorrected tree unless someone also hand-wrote a matching entry in the
parallel `tree_corrections.py`. Two tables, kept in step by hand.

Measured 2026-07-31: `tree_corrections.py` holds 15 entries and every one is
already in `corrections.py` -- it contributes no word of its own -- while SIX
corrected words still had trees disagreeing with their correction:
calypso, duppy, obeah, photograph, plow, zoo.

`photograph` is the clearest: the analyzer says Greek (verified against live
Wiktionary, photo- + -graph from Ancient Greek) and the tree said
Germanic/PIE. One word, two answers, which is the exact complaint issue #16
exists to prevent.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from buckets_wikt import bucket_for_name
from corrections import WORD_CORRECTIONS
import word_trees


def _tree_buckets(word):
    """
    Every bucket the tree reaches.

    A node's `lang` is usually a real language name, but a correction's chain
    holds BUCKET names ("Norse", "African (other)"), so both readings count --
    `bucket_for_name("Norse")` does not recognise a bucket as a language and
    would otherwise report a correct tree as contradicting itself.
    """
    from tree_model import TreeNode

    node = TreeNode.from_dict(word_trees.resolve_tree(word))
    if node is None:
        return set()
    found = set()
    for lang in node.languages():
        found.add(lang)
        found.add(bucket_for_name(lang))
    return found


@pytest.mark.parametrize("word", ["photograph", "calypso", "duppy", "plow"])
def test_the_tree_reaches_the_corrected_bucket(word):
    want = WORD_CORRECTIONS[word]["p"]
    assert want in _tree_buckets(word), (
        f"{word}: corrections.py says {want}, tree shows {_tree_buckets(word)}")


def test_no_corrected_word_has_a_contradicting_tree():
    """The whole table, so a second store cannot drift from it again."""
    bad = []
    for word, fix in WORD_CORRECTIONS.items():
        buckets = _tree_buckets(word)
        if buckets and fix["p"] not in buckets:
            bad.append((word, fix["p"], sorted(buckets)[:3]))
    assert not bad, f"{len(bad)} trees contradict their correction: {bad[:8]}"
