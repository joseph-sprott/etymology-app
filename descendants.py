"""
Assemble one descendant tree for display, from the stored fragments.

Reads only through `etymology_db` -- the same handle the analyzer and the Word
Search use -- so this feature cannot end up with its own private view of a word
(the rule that came out of the 2026-07-24 "no feature has data another
doesn't" session).

Three jobs, none of which belong in the database layer:

1. **Find the way in.** A user types `brother`, not `*bʰréh₂tēr`. The English
   word is a leaf somewhere inside a tree; find it, then climb.
2. **Splice.** Wiktionary ends the PIE page's Germanic row at `*brōþēr` and
   continues on that form's own page. Joining the fragments is what produces
   the whole diagram from the root down.
3. **Budget.** `*erþō` ("earth") has 27,254 recorded descendants. No layout
   shows that at once and no browser should be asked to. Trees are cut to a
   node budget, deepest-and-last first, and the result says so out loud rather
   than silently pretending it is complete.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

import etymology_db

# Chosen against the real distribution: the median tree is small, and a budget
# here keeps `*erþō`'s 27k nodes from reaching the browser. The client collapses
# to a shallow depth anyway, so a bigger budget would buy nothing visible.
NODE_BUDGET = 3000

# How far to keep splicing. Real chains run PIE -> proto-branch -> proto-stage
# -> attested stage; a cycle in the data (a form listed as its own ancestor)
# would otherwise loop forever, and `seen` alone can't stop a long chain of
# distinct forms.
MAX_SPLICE_DEPTH = 6

TreeRow = Dict[str, Any]


@dataclass(frozen=True)
class ClimbStep:
    """
    One form on the way up to a family's root.

    A named record rather than a 3-tuple: callers were reading `step[2]` for
    the term and unpacking positionally, which is exactly the mistake that
    makes a `(lang, term)` pair silently swap.
    """
    tree_id: Optional[int]
    lang: str
    term: str


class SupportsParentLookup(Protocol):
    """The one method `climb_to_root` needs -- so a test can fake it."""

    def parent_tree_of(self, lang: str, term: str) -> Optional[TreeRow]: ...


def climb_to_root(db: SupportsParentLookup, tree_id: Optional[int], lang: str,
                  term: str, max_depth: int = MAX_SPLICE_DEPTH) -> List[ClimbStep]:
    """
    Every step from one node up to the topmost recorded ancestor, start first.

    THE TREE A WORD SITS IN IS NOT THE ROOT IT DISPLAYS. Wiktionary ends the
    PIE page's Germanic row at `*brōþēr` and continues on that form's own page,
    so `night` sits in the Proto-Germanic `*nahts` tree while this feature
    climbs on to PIE `*nókʷts`. Reporting the containing tree understates PIE
    coverage roughly sixty-fold -- a mistake made once already, by the first
    version of `scripts/list_descendant_words.py`.

    Returns the whole path, not just the top: `full_tree` takes the last step,
    `scripts/check_descendants.py` prints all of them, and one function serving
    both readings is why there is no longer a third copy to drift (issue #16 --
    every feature must read from one shared source).
    """
    steps: List[ClimbStep] = [ClimbStep(tree_id, lang, term)]
    seen = {(lang, term)}
    for _ in range(max_depth):
        parent = db.parent_tree_of(lang, term)
        if parent is None or (parent["lang"], parent["term"]) in seen:
            break
        tree_id, lang, term = parent["tree_id"], parent["lang"], parent["term"]
        steps.append(ClimbStep(tree_id, lang, term))
        seen.add((lang, term))
    return steps


def _splice(node, seen, depth=0):
    """
    Attach the continuation tree to any leaf that is itself a tree root.

    A leaf like Proto-Germanic `*brōþēr` on the PIE page is the same form as
    the root of the Proto-Germanic tree; that identity IS the join. Guarded by
    `seen` so a form already expanded higher up is never expanded again --
    without it, a form citing itself would recurse until the stack gave out.
    """
    if depth >= MAX_SPLICE_DEPTH:
        return node
    kids = node.get("children") or []
    if not kids and node.get("term") and node.get("lang"):
        key = (node["lang"], node["term"])
        if key not in seen:
            db = etymology_db.get()
            tid = db.tree_for_form(node["lang"], node["term"])
            if tid is not None:
                seen.add(key)
                sub = db.descendant_tree(tid)
                if sub:
                    node["children"] = sub.get("children") or []
                    node["spliced"] = True
                    kids = node["children"]
    for kid in kids:
        _splice(kid, seen, depth + 1)
    return node


def _signature(node):
    """Structural fingerprint of a node's subtree, ignoring its own spelling."""
    return (node.get("lang"),
            tuple(sorted((k.get("lang") or "", k.get("term") or "",
                          _signature(k)) for k in node.get("children") or ())))


def _merge_variants(node):
    """
    Collapse sibling spelling variants of the same word into one node.

    Wiktionary records Old English `brōþor`, `brōþer`, `brōþur`, `brōðer` and
    `brōður` as five sibling rows, each carrying its own identical Middle
    English -> English subtree. Drawn literally that is five near-identical
    ladders and the diagram becomes unreadable -- and it misrepresents the
    source, which prints them on ONE line: "Old English: brōþor, brōþer,
    brōþur, brōðer, brōður".

    Merged only when siblings share a language AND their subtrees are
    structurally identical, so nothing is claimed that the data doesn't say: a
    variant with descendants the others lack keeps its own node. The merged
    node lists every spelling, so no form is hidden.
    """
    kids = node.get("children") or []
    for kid in kids:
        _merge_variants(kid)
    if len(kids) > 1:
        groups = {}
        for kid in kids:
            groups.setdefault(_signature(kid), []).append(kid)
        if any(len(g) > 1 for g in groups.values()):
            merged = []
            for group in groups.values():
                head = group[0]
                if len(group) > 1:
                    terms, seen = [], set()
                    for member in group:
                        term = member.get("raw_term") or member.get("term")
                        if term and term not in seen:
                            seen.add(term)
                            terms.append(term)
                    head["raw_term"] = ", ".join(terms)
                    head["variants"] = len(terms)
                merged.append(head)
            node["children"] = merged
    return node


def _count(node):
    return 1 + sum(_count(k) for k in node.get("children") or ())


def _prune(node, budget):
    """
    Trim to a node budget, shallowest-first.

    Breadth-first so what survives is the top of the tree -- the part that
    carries the shape of the family. Cutting depth-first would keep one long
    thread and drop every sibling branch, which is the opposite of what the
    picture is for. A cut node keeps a `pruned` count so the UI can say how
    many were dropped instead of quietly losing them.
    """
    kept = 1
    level = [node]
    while level:
        nxt = []
        for parent in level:
            kids = parent.get("children") or []
            room = budget - kept
            if room <= 0:
                if kids:
                    parent["pruned"] = _count(parent) - 1
                    parent["children"] = []
                continue
            if len(kids) > room:
                parent["pruned"] = sum(_count(k) for k in kids[room:])
                kids = kids[:room]
                parent["children"] = kids
            kept += len(kids)
            nxt.extend(kids)
        level = nxt
    return node


def _mark(node, target_lang, target_term):
    """Flag the searched word wherever it appears, and every ancestor of it, so
    the view can open straight to it instead of making the user hunt."""
    hit = (node.get("lang") == target_lang and node.get("term") == target_term)
    for kid in node.get("children") or ():
        if _mark(kid, target_lang, target_term):
            hit = True
            node["on_path"] = True
    if hit:
        node.setdefault("on_path", True)
        if node.get("lang") == target_lang and node.get("term") == target_term:
            node["match"] = True
    return hit


# Every English word that appears anywhere in a stored tree. Loaded once and
# held, because the UI asks this question per WORD in a pasted paragraph and
# the answer decides whether to draw a link. `full_tree()` would splice, merge
# and prune an entire family to answer it -- thousands of times over for a
# page of prose.
#
# Small enough to keep: ~3,800 strings.
_COVERED: Optional[set] = None


def _covered() -> set:
    global _COVERED
    if _COVERED is None:
        db = etymology_db.get()
        try:
            _COVERED = {r[0] for r in db._db.execute(
                "SELECT DISTINCT term FROM descendant_node"
                " WHERE lang = 'English' AND term IS NOT NULL AND term != ''")}
        except Exception:
            # Descendant tables absent (nothing built yet) is a normal state,
            # and it should read as "no coverage", never as an error.
            _COVERED = set()
    return _COVERED


def tree_form(word: Optional[str]) -> Optional[str]:
    """
    The exact spelling that has a descendant tree, or None.

    Returns the FORM rather than a bare bool so a caller can link the spelling
    that actually resolves. A sentence-initial "Brother" should still offer
    the link, and it must point at `brother` -- the stored node -- rather than
    at a capitalisation the tree lookup would miss, which would render an
    empty page and read as a broken feature.

    Guaranteed consistent with `full_tree`: if this returns a form, that form
    produces a tree. `test_units.py` asserts exactly that, because the failure
    mode here is a link that promises something and then shows nothing.
    """
    word = (word or "").strip()
    if not word:
        return None
    covered = _covered()
    if word in covered:
        return word
    lower = word.lower()
    return lower if lower in covered else None


def has_tree(word: Optional[str]) -> bool:
    """Whether the descendants view has anything to show for this word."""
    return tree_form(word) is not None


def full_tree(word: str, lang: str = "English",
              budget: int = NODE_BUDGET) -> Optional[dict]:
    """
    The complete recorded descent for a word, from the deepest root down.

    Returns None when nothing is recorded -- which is the common case and not
    an error: only words whose ancestors have a Wiktionary descendants section
    can have one, and coverage today is two branches (see build_descendants.py).
    """
    word = (word or "").strip()
    if not word:
        return None
    db = etymology_db.get()

    hits = db.trees_containing(word, lang)
    if not hits:
        return None
    head = hits[0]

    # Climb to the topmost recorded ancestor before building anything, so the
    # picture starts where the family starts (PIE) rather than at whichever
    # fragment happened to contain the word.
    top = climb_to_root(db, head["tree_id"], head["lang"], head["term"])[-1]
    top_lang, top_term = top.lang, top.term

    tree = db.descendant_tree(top.tree_id)
    if tree is None:
        return None

    tree = _splice(tree, {(top_lang, top_term)})
    tree = _merge_variants(tree)
    total = _count(tree)
    tree = _prune(tree, budget)
    shown = _count(tree)
    _mark(tree, lang, word)

    return {"tree": tree, "root_lang": top_lang, "root_term": top_term,
            "root_raw": tree.get("raw_term") or top_term,
            "total_nodes": total, "shown_nodes": shown,
            "truncated": shown < total, "query": word}
