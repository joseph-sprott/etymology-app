"""
Builds etymology_trees.json: a per-word NESTED tree (unlike wikt_words.json's
flattened `chain`), for the etymology-tree UI feature Joe asked for 2026-07-23
("I really like the etymology tree that Wiktionary provides").

Why a separate file instead of extending wikt_words.json: the bucket/chain
pipeline in convert_wikt.py deliberately FLATTENS a term's graph into one
linear sequence (see that module's docstring) because the percentage-
breakdown feature needs one answer per word. A real tree needs the opposite --
every branch preserved, not collapsed. Reusing wikt_words.json's flattening
logic here would just rebuild the same lossy structure; this walks the raw
group_tag/parent_tag/parent_position structure directly and keeps it intact.

Tree shape per word:
  {"lang": "English", "term": "sandal", "branches": [ <node>, <node>, ... ]}
  node: {"lang": ..., "term": ..., "reltype": ..., "children": [<node>, ...]}

`branches` is a list because a term_id can carry multiple independent
top-level threads -- distinct senses (`and`'s conjunction vs. its two
obsolete Norse-derived senses) AND alternate documented theories for the
SAME sense (`sandal`'s Byzantine-Greek and Arabic/Sanskrit alternates
alongside its main Latin/Greek chain) are both real, and this deliberately
does NOT try to pick a "primary" one or tell the two apart -- see
convert_wikt.py's docstring for why that's not reliably automatable from
this data. For a word like `and`, that means the tree can look busier than
Wiktionary's own curated diagram (which merges citation-variant fragments a
human editor judged as "the same sense"); this instead shows the raw
recorded structure honestly rather than guessing which fragments to merge.

WITHIN one branch, `parent_position` gives the real recorded order (see
convert_wikt.py known issue #2 notes) -- each successive position becomes
the previous node's child, so a branch reads top-to-bottom as donor->deeper
donor, exactly like Wiktionary's own tree diagram. A nested sub-group at a
given position (e.g. sandal's Byzantine-Greek aside) splices in as a
continuation at that exact point, not a new top-level branch.

Only true ancestry relations are included (same ANCESTRY_RELS filter as
convert_wikt.py) -- cognates and "etymologically related" mentions are
excluded, consistent with the rest of this project's philosophy of only
showing real donor relationships.
"""
import json
import sys

import pandas as pd

sys.path.insert(0, ".")
from convert_wikt import (
    ANCESTRY_RELS, ROOT_RELS, GROUP_MARKER_RELS, NON_DONOR_LANGS, PARQUET_PATH,
    _depth_hint,
)
from tree_corrections import TREE_CORRECTIONS

OUT_PATH = "etymology_trees.json"


def _pos_key(row):
    return row.parent_position if pd.notna(row.parent_position) else 0


def _deepest_leaf(node):
    n = node
    while n["children"]:
        n = n["children"][-1]
    return n


def _collect(row, children_by_group, seen_groups=frozenset()):
    """
    Mirrors convert_wikt.py's `_expand()`: recursively collects `row`'s own
    ancestry content plus its group's children into two FLAT lists --
    `nodes` (normal positional links) and `roots` (has_root entries, kept
    separate). has_root's recorded position does NOT reflect real depth --
    same bug/fix as convert_wikt.py's flat pipeline (see its docstring) --
    e.g. `and`'s has_root row sits at parent_position 0, ahead of the Middle
    English form it's supposedly the root OF, which would nest PIE as
    Middle English's *parent* if not pulled out and placed at the true end.
    Returns (nodes, roots), both lists of not-yet-nested tree-node dicts.

    `seen_groups` guards against a cyclic group_tag/parent_tag chain (a
    group whose own descendants loop back to it) turning into infinite
    recursion -- convert_wikt.py's flat `_expand()` has the same theoretical
    exposure but was never observed to hit it in the flat pipeline; adding
    the guard here defensively rather than assuming the raw data is cycle-free.
    """
    reltype = row.reltype
    own_nodes, own_roots = [], []
    if reltype in ANCESTRY_RELS and pd.notna(row.related_lang) and row.related_lang not in NON_DONOR_LANGS:
        term = row.related_term if pd.notna(row.related_term) else None
        node = {"lang": row.related_lang, "term": term, "reltype": reltype, "children": []}
        if reltype in ROOT_RELS:
            own_roots = [node]
        else:
            own_nodes = [node]
    elif reltype not in GROUP_MARKER_RELS:
        return [], []  # irrelevant leaf (cognate_of, etymologically_related_to, has_affix, ...)

    child_nodes, child_roots = [], []
    if pd.notna(row.group_tag) and row.group_tag not in seen_groups:
        next_seen = seen_groups | {row.group_tag}
        for cr in sorted(children_by_group.get(row.group_tag, []), key=_pos_key):
            n, r = _collect(cr, children_by_group, next_seen)
            child_nodes.extend(n)
            child_roots.extend(r)
    return own_nodes + child_nodes, own_roots + child_roots


def _nest(nodes):
    """Chain a flat, depth-ordered list of tree-node dicts into one linear
    parent->child thread (each node becomes the previous node's only child)."""
    for i in range(len(nodes) - 1):
        _deepest_leaf(nodes[i])["children"].append(nodes[i + 1])
    return nodes[0] if nodes else None


def _thread_from_row(row, children_by_group):
    """
    Build one linear thread starting at `row` (a group-marker row OR a bare
    ancestry edge), continuing through its own group's children if it has
    any, with any has_root entries pulled to the true end. Returns the HEAD
    node of the thread, or None if `row` carries no real ancestry content.
    """
    nodes, roots = _collect(row, children_by_group)
    return _nest(nodes + roots)


def _branch_size(node):
    """Total node count in a branch (1 for a bare, childless head node)."""
    return 1 + sum(_branch_size(c) for c in node["children"])


def _collect_pairs(node, out):
    """Add every (lang, term) pair appearing anywhere in `node`'s subtree."""
    out.add((node["lang"], node["term"]))
    for c in node["children"]:
        _collect_pairs(c, out)


def dedupe_branches(branches):
    """
    Drop a top-level branch ONLY when it is a single, childless node whose
    exact (lang, term) pair is ALREADY shown elsewhere in the same tree --
    either inside a real multi-node branch, or in an earlier-kept orphan.

    Added 2026-07-24 (Joe: "sometimes there's a random PIE path that doesn't
    link to the main link to the modern word... just feels incomplete").
    Diagnosed against the live etymology_trees.json rather than guessed:
    `sky`'s real chain (Old Norse ský -> Proto-Germanic *skiwją -> PIE
    *(s)kewH-) is complete and correct, but the SAME PIE term *(s)kewH-
    also surfaces TWICE MORE as free-floating single-node branches, because
    etymology-db's raw data records those as extra parentless rows (one
    `has_root`, one redundant `derived_from`) that build_tree() -- correctly,
    per its own docstring -- turns into their own top-level branches.
    `sandal`'s already-documented "redundant bare edge" and `fruit`'s third
    branch are the same shape.

    This is deliberately NOT the branch-merging heuristic that was tried and
    reverted twice before (see build_tree's docstring: backwards PIE nesting
    for `and`, falsely fused alternate theories for `sandal`). It never
    merges, re-nests, reorders, or alters ANY branch, and never touches a
    multi-node branch at all -- those may be genuine alternate theories
    (`sandal`) or a real independent second derivation (`fruit`'s Old
    French -> Latin fructus). It only removes a bare restatement of a fact
    the tree already displays, so it cannot fabricate a relationship or lose
    real information.

    Genuinely-new-but-structurally-stranded citations are explicitly
    PRESERVED, since they are not duplicates: `religion`'s orphan PIE root
    *h₂leg- is deeper than anything its main Latin chain reaches, and
    `coffee`'s orphan Arabic ق ه ي is a different (triliteral root) term
    from the قَهْوَة already in its chain. Both survive this pass untouched.
    """
    substantive_pairs = set()
    for b in branches:
        if _branch_size(b) > 1:
            _collect_pairs(b, substantive_pairs)

    kept = []
    seen_orphan_pairs = set()
    for b in branches:
        if _branch_size(b) == 1:
            pair = (b["lang"], b["term"])
            if pair in substantive_pairs or pair in seen_orphan_pairs:
                continue  # exact restatement of something already shown
            seen_orphan_pairs.add(pair)
        kept.append(b)
    return kept


def build_tree(term, rows):
    """
    Builds the branch list for one term_id.

    Tried merging top-level items that don't restart from an English stage
    into the previous branch (the same signal convert_wikt.py's flat
    pipeline considered and rejected -- see that module's docstring), to
    turn `cover`'s 3 disconnected top-level fragments (Middle English
    coveren / Old French covrir / Late Latin coperire->Latin cooperio, each
    its own bare row with no group tying them together) into the one
    continuous chain a reader expects. It backfired: for `sandal`, it wrongly
    chained the Byzantine-Greek alternate theory directly into the unrelated
    Arabic/Sanskrit alternate theory (neither restarts from an English
    stage), fabricating a connection between two independent theories that
    isn't in the data. A false merge is worse than a fragmented-but-honest
    tree, so this does NOT merge top-level items at all -- every top-level
    row becomes its own branch. `cover` shows as 3 separate one-line
    branches instead of one clean chain; that's a real, known rough edge
    (worth a UI treatment later, e.g. visually grouping same-family
    single-node branches), but it never invents a relationship the data
    doesn't support.
    """
    children_by_group = {}
    top_level = []
    for row in rows:
        if pd.notna(row.parent_tag):
            children_by_group.setdefault(row.parent_tag, []).append(row)
        elif pd.notna(row.group_tag) or row.reltype in ANCESTRY_RELS:
            top_level.append(row)

    branches = []
    for row in top_level:
        thread = _thread_from_row(row, children_by_group)
        if thread is not None:
            branches.append(thread)
    if not branches:
        return None
    # Drop bare restatements of something the tree already shows (see
    # dedupe_branches). Runs BEFORE the sort below purely for tidiness --
    # dedupe preserves relative order and the sort is stable, so the two are
    # independent either way.
    branches = dedupe_branches(branches)
    # Order branches shallowest-first by their own head node's language --
    # added 2026-07-23 (Joe: a shallower stage like Middle English should
    # never render after a deeper one like Old English). This ONLY reorders
    # the top-level list, same as convert_wikt.py's flat pipeline does for
    # its own top-level items -- it never merges or nests branches together
    # (that was tried and reverted, see this function's docstring), so it
    # can't fabricate a relationship the data doesn't support. Stable sort:
    # branches already at the same depth tier keep their original relative
    # (recorded) order.
    branches.sort(key=lambda t: _depth_hint(t["lang"]))
    return {"lang": "English", "term": term, "branches": branches}


def main():
    print("reading parquet...", file=sys.stderr)
    df = pd.read_parquet(PARQUET_PATH)
    eng = df[df["lang"] == "English"]
    total = eng["term_id"].nunique()
    print(f"  {total} unique terms to process", file=sys.stderr)

    trees = {}
    n = 0
    for term_id, group in eng.groupby("term_id", sort=False):
        n += 1
        term = group["term"].iloc[0]
        tree = build_tree(term, list(group.itertuples()))
        if tree is not None:
            trees[term] = tree
        if n % 20000 == 0:
            print(f"  ...{n}/{total} processed, {len(trees)} trees so far", file=sys.stderr)

    # Apply hand-verified overrides (tree_corrections.py) -- see that file's
    # docstring: a word-level fix isn't done until it's checked against both
    # wikt_words.json/corrections.py (the analyzer) AND here. Applied last so
    # an override always wins over whatever (possibly wrong, possibly
    # entirely missing) raw data produced.
    # Deduped the same way as raw-data trees (see dedupe_branches) purely as
    # a consistency safety net -- hand-verified corrections shouldn't contain
    # a bare restatement of their own content, so this is expected to be a
    # no-op on every current entry, but it costs nothing and means no tree in
    # the output file can ever carry a duplicate orphan regardless of source.
    for term, branches in TREE_CORRECTIONS.items():
        trees[term] = {"lang": "English", "term": term,
                       "branches": dedupe_branches(branches)}

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(trees, f, ensure_ascii=False)
    print(f"wrote {len(trees)} trees to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
