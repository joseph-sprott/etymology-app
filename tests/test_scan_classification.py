"""
The scan has to track TWO failure modes, not one.

Joe, 2026-07-30: "Take note of any word that reads as unknown AND OTHER."
They fail differently and need different fixes -- `Unknown` is missing data,
`Other` is a language we DID find but never mapped to a bucket (known issue
#3, `Other` bucket leakage). Counting them together would hide the second
behind the first.
"""
import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import scan_unknown_words as S


def test_classifies_the_two_failure_modes_apart():
    assert S.classify_bucket("Unknown") == "unknown"
    assert S.classify_bucket("Other") == "other"
    assert S.classify_bucket("Germanic") == "ok"
