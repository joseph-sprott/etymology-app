"""
One typed model for an etymology tree, replacing hand-rolled dict walking.

Every inspector of these trees had grown its own recursive closure --
`_honour_correction`, the golden-master snapshot, the correction audit, and
the tests -- each spelling `node.get("branches") or node.get("children") or []`
slightly differently. That expression is load-bearing and easy to get subtly
wrong, because the ROOT of one of these trees names its descendants
`branches` while every node below it names them `children`.

`TreeNode` owns that asymmetry in one place. The dict form stays the public
shape: it is the JSON the Jinja templates read and the `tree_json` column
stores, so `to_dict()` reproduces it exactly and nothing downstream changes.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tree_model import TreeNode

SAMPLE = {
    "lang": "English", "term": "bagpipe",
    "branches": [
        {"lang": "English", "term": "bag", "reltype": "compound_of",
         "certainty": "direct", "is_affix": False, "children": []},
        {"lang": "English", "term": "pipe", "reltype": "compound_of",
         "certainty": "direct", "is_affix": False, "children": [
             {"lang": "Latin", "term": "pipa", "reltype": "derived_from",
              "certainty": "direct", "is_affix": False, "children": []}]},
    ],
}


# The trees come from sources with DIFFERENT key sets: a database-built node
# carries `is_affix` and `certainty`, a legacy stored node often carries
# neither. A `to_dict` that emitted a canonical key set would silently change
# the JSON the Jinja templates read. Round-tripping must be exact for BOTH.
LEGACY = {
    "lang": "English", "term": "walk",
    "branches": [{"lang": "Middle English", "term": "walken",
                  "reltype": "inherited_from", "children": []}],
}


def test_round_trips_a_database_built_tree_exactly():
    assert TreeNode.from_dict(SAMPLE).to_dict() == SAMPLE


def test_round_trips_a_legacy_stored_tree_exactly():
    # No `is_affix`, no `certainty`. They must not appear on the way back.
    assert TreeNode.from_dict(LEGACY).to_dict() == LEGACY


def test_a_freshly_built_node_emits_the_canonical_shape():
    node = TreeNode(lang="Latin", term="pipa", reltype="derived_from")
    assert node.to_dict() == {"lang": "Latin", "term": "pipa",
                              "reltype": "derived_from", "children": []}


def test_walk_visits_every_node_parents_first():
    langs = [n.lang for n in TreeNode.from_dict(SAMPLE).walk()]
    assert langs == ["English", "English", "English", "Latin"]


def test_languages_collects_every_language_once():
    assert TreeNode.from_dict(SAMPLE).languages() == {"English", "Latin"}


def test_the_root_asymmetry_is_absorbed():
    # The stored ROOT names its descendants `branches` while every node below
    # names them `children`. Reading that correctly is the whole reason this
    # model exists; callers should never spell the difference themselves.
    root = TreeNode.from_dict(SAMPLE)
    assert len(root.children) == 2
    assert root.is_root and not root.children[0].is_root


def test_an_empty_or_missing_tree_is_handled():
    assert TreeNode.from_dict(None) is None
    assert TreeNode.from_dict({"lang": "English", "term": "x"}).children == []


def test_a_stub_is_a_tree_that_says_nothing():
    bare_root = {"lang": "English", "term": "movie", "branches": [
        {"lang": "English", "term": "ie", "is_affix": True, "children": []},
        {"lang": "Proto-Indo-European", "term": "*m", "reltype": "has_root",
         "children": []}]}
    assert TreeNode.from_dict(bare_root).is_stub()
    assert not TreeNode.from_dict(SAMPLE).is_stub()
