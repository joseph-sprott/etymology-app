"""
`DescendantNode` -- the downward tree's own model, separate from `TreeNode`.

The two shapes are genuinely different and the direction of `children` means
the opposite thing in each, so they are separate types on purpose.

Round-tripping must be exact in both directions: this JSON goes straight to
the vendored d3 client, and an added or dropped key changes what the browser
renders -- which no test can catch, because the picture is drawn client-side.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tree_model import DescendantNode

STORED = {
    "lang": "Proto-Germanic", "term": "brothar", "raw_term": "*brōþēr",
    "children": [
        {"lang": "Old English", "term": "brothor",
         "raw_term": "brōþor, brōþer", "variants": 2, "children": []},
        {"lang": "Old Norse", "term": "brothir", "raw_term": "bróðir",
         "spliced": True, "children": []},
    ],
}


def test_round_trips_the_stored_shape_exactly():
    assert DescendantNode.from_dict(STORED).to_dict() == STORED


def test_absent_keys_do_not_reappear():
    # The first child has no `spliced`/`match`; they must not be invented.
    out = DescendantNode.from_dict(STORED).to_dict()
    assert "spliced" not in out["children"][0]
    assert "match" not in out["children"][0]
    assert out["children"][1]["spliced"] is True


def test_walk_and_count_cover_the_whole_subtree():
    node = DescendantNode.from_dict(STORED)
    assert node.count() == 3
    assert [n.lang for n in node.walk()] == [
        "Proto-Germanic", "Old English", "Old Norse"]


def test_a_freshly_built_node_emits_only_what_it_has():
    node = DescendantNode(lang="English", raw_term="brother")
    assert node.to_dict() == {"lang": "English", "raw_term": "brother",
                              "children": []}
