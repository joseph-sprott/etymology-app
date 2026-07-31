"""
GOLDEN MASTER for the downward tree, before converting it to a typed model.

`descendants.py` is riskier to refactor than the upward tree for two reasons:
its functions MUTATE dicts in place rather than building fresh ones, and its
output is serialized straight to the vendored d3 client -- so a test can prove
the DATA is right but not that the picture is. That is recorded in issue #21
as the accepted cost of going client-side.

This pins the assembled output for a spread of real words: the root reached,
the node counts before and after the budget, and the full nested shape. It
asserts that the answer does not CHANGE, not that it is correct.

Regenerate deliberately with
`python tests/test_descendants_golden.py --update` when a change of behaviour
is intended and reviewed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "descendants_golden.json")

# Chosen to exercise every mechanism, not to be interesting:
#   brother/night  -- variant merging (Old English brōþor/brōþer/brōþur...)
#   earth          -- the node budget; *erþō has 27,254 raw descendants
#   water/father   -- ordinary multi-branch trees
#   mother/friend  -- splicing across fragment boundaries
WORDS = ["brother", "night", "earth", "water", "father", "mother", "friend"]


def _shape(node):
    """The nested skeleton, order preserved."""
    if node is None:
        return None
    return {"lang": node.get("lang"), "term": node.get("term"),
            "raw_term": node.get("raw_term"),
            "variants": node.get("variants"),
            "match": bool(node.get("match")),
            "children": [_shape(c) for c in (node.get("children") or [])]}


def _snapshot():
    import descendants

    out = {}
    for word in WORDS:
        result = descendants.full_tree(word)
        if result is None:
            out[word] = None
            continue
        out[word] = {
            "root_lang": result["root_lang"],
            "root_raw": result["root_raw"],
            "total_nodes": result["total_nodes"],
            "shown_nodes": result["shown_nodes"],
            "truncated": result["truncated"],
            "tree": _shape(result["tree"]),
        }
    return out


@pytest.mark.parametrize("word", WORDS)
def test_descendant_tree_is_unchanged(word):
    import descendants

    with open(BASELINE, encoding="utf-8") as handle:
        expected = json.load(handle)[word]
    result = descendants.full_tree(word)
    if expected is None:
        assert result is None
        return
    assert result is not None, f"{word}: tree disappeared"
    for key in ("root_lang", "root_raw", "total_nodes", "shown_nodes",
                "truncated"):
        assert result[key] == expected[key], f"{word}: {key} changed"
    assert _shape(result["tree"]) == expected["tree"], f"{word}: shape changed"


if __name__ == "__main__":
    if "--update" in sys.argv:
        with open(BASELINE, "w", encoding="utf-8") as handle:
            json.dump(_snapshot(), handle, ensure_ascii=False, indent=1,
                      sort_keys=True)
        print(f"baseline written: {BASELINE}")
    else:
        print("run with --update to regenerate the baseline")
