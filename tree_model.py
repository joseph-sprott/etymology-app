"""
The etymology tree as a typed object instead of a nested dict.

A LEAF MODULE: imports nothing project-local, so anything may use it.

WHY THIS EXISTS. Every inspector of these trees had grown its own recursive
closure, each spelling the same traversal slightly differently:

    node.get("branches") or node.get("children") or []

That expression is load-bearing and easy to get subtly wrong, because the ROOT
of one of these trees calls its descendants `branches` while every node below
calls them `children`. By 2026-07-31 that walk had been hand-written in
`word_trees._honour_correction`, in the golden-master snapshot, in the
corrections audit and twice in tests -- five copies of one traversal, which is
issue #16's shape (one fact, several implementations) in miniature.

READ-ONLY, DELIBERATELY. This is a view FOR INSPECTION, not a replacement for
the stored shape. The dict remains what the Jinja templates read, what
`etymology_trees.json` stores and what the `tree_json` column caches, and the
builders still produce it.

There is no `to_dict()`, and that is a decision rather than an omission. The
trees come from several sources that carry DIFFERENT key sets -- a
database-built node has `is_affix` and `certainty`, a legacy stored node often
has neither -- so a `to_dict()` would have to track which keys were present to
avoid changing the JSON that templates and the cached `tree_json` compare
against. Rebuilding dicts is not needed to fix the duplicated traversal, and
inventing a lossy one would be a trap for whoever converts the builders later.

NOT shared with `descendants.py`. That subsystem's nodes carry `raw_term`,
`variants`, `spliced` and `match` and have no `reltype` or `certainty` -- a
genuinely different shape, and one dataclass covering both would be a union of
unrelated fields pretending to be a type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Set


# A branch that is only a root CITATION is not a lineage -- the tree-side
# equivalent of the resolver's `prox_kind == "root"` stub.
_ROOT_ONLY_RELS = frozenset({"has_root"})


@dataclass
class TreeNode:
    """One form in a word's history. `children` are its ANCESTORS."""
    lang: str
    term: Optional[str] = None
    reltype: Optional[str] = None
    certainty: Optional[str] = None
    is_affix: bool = False
    children: List["TreeNode"] = field(default_factory=list)
    #: True for the tree's ROOT, whose descendants serialize as "branches".
    is_root: bool = False
    #: Which optional keys the SOURCE dict carried, so `to_dict` can reproduce
    #: it exactly. None for a node built in code, which emits the canonical
    #: shape instead. Without this, round-tripping a legacy stored tree would
    #: add `is_affix`/`certainty` keys it never had and change the JSON the
    #: templates read.
    _source_keys: Optional[frozenset] = None

    # ------------------------------------------------------------ traversal
    def walk(self) -> Iterator["TreeNode"]:
        """Every node in this subtree, parents before children."""
        yield self
        for child in self.children:
            yield from child.walk()

    def languages(self) -> Set[str]:
        """Every language named anywhere in this subtree."""
        return {n.lang for n in self.walk() if n.lang}

    def terms(self) -> Set[str]:
        return {n.term for n in self.walk() if n.term}

    # ------------------------------------------------------- (de)serialising
    @classmethod
    def from_dict(cls, raw: Optional[dict], _root: bool = True
                  ) -> Optional["TreeNode"]:
        """Build from the stored/wire dict. None passes through as None."""
        if not raw:
            return None
        kids = raw.get("branches") if _root and "branches" in raw else raw.get("children")
        return cls(
            lang=raw.get("lang"),
            term=raw.get("term"),
            reltype=raw.get("reltype"),
            certainty=raw.get("certainty"),
            is_affix=bool(raw.get("is_affix")),
            children=[cls.from_dict(k, _root=False) for k in (kids or [])],
            is_root=_root and "branches" in raw,
            _source_keys=frozenset(raw),
        )

    def to_dict(self) -> dict:
        """
        Back to the wire shape, reproducing the source's key set exactly.

        A node read from a dict emits precisely the keys that dict had; a node
        built in code emits the canonical set. That distinction is the whole
        reason `_source_keys` exists -- these trees come from stores with
        different key sets, and quietly adding `is_affix: false` to a legacy
        stored tree would change JSON the Jinja templates and the golden master
        compare against.
        """
        out = {"lang": self.lang, "term": self.term}
        optional = (("reltype", self.reltype),
                    ("certainty", self.certainty),
                    ("is_affix", self.is_affix))
        for key, value in optional:
            if self._source_keys is not None:
                if key in self._source_keys:
                    out[key] = value
            elif value not in (None, False):
                out[key] = value
        out["branches" if self.is_root else "children"] = [
            c.to_dict() for c in self.children]
        return out

    def is_stub(self) -> bool:
        """
        Does this tree say anything, or is it a stub wearing branches?

        A childless BOUND AFFIX counts for as little as a bare root pointer:
        `-ie` is not where `movie` came from. Its entry is
        `{{suffix|en|""|ie}}` -- the base is an empty string in Wiktionary's
        own data -- so its stored tree is the ending plus a root citation and
        nothing else, and letting that outrank a hand-verified correction left
        the analyzer and the Word Search disagreeing about one word.
        """
        if not self.children:
            return True
        return all(not c.children and (c.reltype in _ROOT_ONLY_RELS or c.is_affix)
                   for c in self.children)
