"""
GOLDEN MASTER. The safety net that makes refactoring safe.

Joe, 2026-07-31: "make them work the same... I dont want to have to debug the
features again."

This does not assert that any answer is CORRECT. It asserts that answers do
not CHANGE. Every word below is pinned to whatever the app returns today,
across all three modes plus its component split. A refactor that alters any of
them has changed behaviour, whether or not the new answer is better -- and
that is exactly the signal a large refactor needs, because the dangerous
regressions are the plausible-looking ones.

The words are chosen to cover every code path through the resolver cascade,
not to be interesting:
  * database hits, native and foreign
  * every backend in the chain (db / wiktextract / wiktionary / ety)
  * inflections, derivations, compounds, affixed forms
  * the collision fixes (`ran`, `wolves`, `went`, `tag`, `auto`)
  * the deliberate Unknowns
  * words fixed THIS WEEK, which are the least settled and most at risk

Regenerate deliberately with `python tests/test_golden_master.py --update`
after a change whose behaviour shift is intended and reviewed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "golden_master.json")

WORDS = [
    # native core and inherited threads
    "the", "water", "trust", "brother", "night", "free", "back", "what",
    # foreign donors, one per major bucket
    "table", "beef", "government", "justice", "army", "skill", "sky", "egg",
    "knife", "law", "they", "them", "anger", "coffee", "sugar", "algebra",
    "zero", "tea", "muskrat", "hurricane", "reggae", "robot", "quartz",
    # depth / root behaviour
    "mile", "intrude", "father", "cover", "computer", "vitamin", "sandal",
    # inflections and derivations
    "wolves", "ran", "went", "held", "became", "washing", "canines",
    "consistency", "professional", "mindset", "hidden", "unheard",
    # compounds and splits
    "upside", "bagpipe", "craftsman", "businesswoman", "blackbird",
    "basketball", "peacemaker", "outdoorsman", "mountainside", "overactive",
    # affixes -- the issue #19 family
    "darkness", "beautiful", "government", "quickly", "happiness", "careful",
    "unhappy", "undo", "rewrite", "disagree", "preview", "geology", "biology",
    # this week's fixes, least settled
    "late", "about", "movie", "photograph", "lithology", "phonograph",
    # multi-sense collisions with hand overrides
    "die", "bull", "and", "low", "with", "tag", "auto", "generate", "said",
    "she", "look", "because", "as", "can", "could",
    # deliberate Unknowns and edge cases
    "narrate", "zoophysiologist", "physiologist", "cute", "semi", "th",
]


def _tree_shape(node):
    """Language/term/reltype skeleton of a tree, order preserved."""
    if not node:
        return None
    return {"lang": node.get("lang"), "term": node.get("term"),
            "branches": [_tree_shape(b) for b in
                         (node.get("branches") or node.get("children") or [])]}


def _snapshot():
    from resolver import shared_resolver
    import word_trees

    resolver = shared_resolver()
    out = {}
    for word in sorted(set(WORDS)):
        resolution = resolver.resolve(word)
        entry = {}
        for mode in ("direct", "influence", "root"):
            view = resolution.view(mode)
            entry[mode] = {
                "bucket": view.bucket,
                "depth_lang": view.depth_lang,
                "specific_lang": view.specific_lang,
                "resolved": bool(view.resolved),
                "parts": [[p.word, p.bucket] for p in (view.parts or [])],
            }
        # The Word Search tree too: it is a SECOND derivation of the same
        # word, and the whole point of issue #16 is that the two must not
        # drift apart. Pinning only the resolver would leave half the
        # behaviour unguarded during a refactor of `word_trees`.
        entry["tree"] = _tree_shape(word_trees.resolve_tree(word))
        out[word] = entry
    return out


def _load():
    with open(BASELINE, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.parametrize("word", sorted(set(WORDS)))
def test_answer_is_unchanged(word):
    from resolver import shared_resolver

    expected = _load()[word]
    resolution = shared_resolver().resolve(word)
    for mode in ("direct", "influence", "root"):
        view = resolution.view(mode)
        want = expected[mode]
        assert view.bucket == want["bucket"], f"{word}/{mode} bucket changed"
        assert view.depth_lang == want["depth_lang"], f"{word}/{mode} depth_lang changed"
        assert view.specific_lang == want["specific_lang"], f"{word}/{mode} donor changed"
        assert bool(view.resolved) == want["resolved"], f"{word}/{mode} resolved-flag changed"
        parts = [[p.word, p.bucket] for p in (view.parts or [])]
        assert parts == want["parts"], f"{word}/{mode} component split changed"


@pytest.mark.parametrize("word", sorted(set(WORDS)))
def test_tree_is_unchanged(word):
    import word_trees

    expected = _load()[word].get("tree")
    assert _tree_shape(word_trees.resolve_tree(word)) == expected, \
        f"{word}: the Word Search tree changed shape"


if __name__ == "__main__":
    if "--update" in sys.argv:
        with open(BASELINE, "w", encoding="utf-8") as handle:
            json.dump(_snapshot(), handle, ensure_ascii=False,
                      indent=1, sort_keys=True)
        print(f"baseline written: {BASELINE}")
    else:
        print("run with --update to regenerate the baseline")
