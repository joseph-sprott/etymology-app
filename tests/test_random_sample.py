"""
Joe asked for "a couple thousand" words, "truly random".

Random means seeded and reproducible, not arbitrary: a scan whose sample
changes every run cannot be compared to the run before it, so it can never
show whether anything improved. The pool is passed in rather than queried
here, which is what lets this be tested without a database.
"""
import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import scan_unknown_words as S


def test_sample_is_random_but_reproducible():
    pool = [f"word{i}" for i in range(1000)]

    first = S.sample_words(pool, 50, seed=1)
    again = S.sample_words(pool, 50, seed=1)
    different_seed = S.sample_words(pool, 50, seed=2)

    assert len(first) == 50
    assert first == again, "same seed must give the same sample"
    assert first != different_seed, "a different seed must give a different sample"
    assert set(first) <= set(pool)
    assert len(set(first)) == 50, "no word may appear twice"


def test_sample_smaller_than_requested_returns_everything():
    pool = ["a", "b", "c"]
    assert sorted(S.sample_words(pool, 100, seed=1)) == ["a", "b", "c"]
