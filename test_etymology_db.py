"""
Invariants for the new data layer. These are the switch-over gates.

Run:  python test_etymology_db.py

Each check states a property that must hold no matter what the dump contains,
so a future source or parser change that violates one fails here rather than
quietly shipping a wrong etymology. They are deliberately structural: the
point of the rework was to make bad shapes impossible, not to police them.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import etymology_db

FAILURES = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if not ok:
        FAILURES.append(f"{name}: {detail}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  -- ' + detail) if detail and not ok else ''}")


def main():
    # Optional path argument so a freshly built database can be checked
    # BEFORE it is swapped into place -- which is the only order that makes
    # sense when the running app holds the live file open.
    path = sys.argv[1] if len(sys.argv) > 1 else etymology_db.DB_PATH
    if not os.path.exists(path):
        print(f"{path} not built; run build_etymology_db.py first")
        return 0
    db = etymology_db.get(path)
    raw = db._db

    print("\n=== structure: no floating nodes, ever ===")
    floating = raw.execute("""
        SELECT COUNT(*) FROM ety_node n
        WHERE n.is_head = 0
          AND NOT EXISTS (SELECT 1 FROM ety_edge e
                          WHERE e.ety_id = n.ety_id AND e.parent_id = n.node_id)
    """).fetchone()[0]
    check("every non-head node has a parent edge", floating == 0,
          f"{floating} floating nodes")

    heads = raw.execute("""
        SELECT COUNT(*) FROM (SELECT ety_id, SUM(is_head) h FROM ety_node
                              GROUP BY ety_id HAVING h != 1)
    """).fetchone()[0]
    check("exactly one head per etymology", heads == 0, f"{heads} bad")

    print("\n=== the dotted edge is display-only ===")
    # Load-bearing: if chain code could walk a 'related' edge, the percentage
    # bars would count a link the tree itself marks as unproven.
    bad = 0
    for word in ("father", "mile", "beef", "computer", "telephone"):
        e = db.entry(word)
        if e is None or not e.primary:
            continue
        spine = e.primary.spine()
        if any(n.certainty != "direct" for n in spine[1:]):
            bad += 1
    check("spine() never traverses a 'related' edge", bad == 0,
          f"{bad} words walked a dotted edge")

    resolved_dotted = raw.execute("""
        SELECT COUNT(*) FROM word w WHERE w.status = 'resolved'
          AND NOT EXISTS (SELECT 1 FROM etymology e JOIN ety_edge g
                          ON g.ety_id = e.ety_id
                          WHERE e.word_id = w.word_id AND g.certainty = 'direct')
    """).fetchone()[0]
    check("'resolved' implies at least one solid edge", resolved_dotted == 0,
          f"{resolved_dotted} words resolved on dotted edges alone")

    print("\n=== provenance: restricted sources stay out of ancestry ===")
    additive = raw.execute("""
        SELECT COUNT(*) FROM ety_node n JOIN source s ON s.source_id = n.source_id
        WHERE s.additive_only = 1
    """).fetchone()[0]
    check("no additive_only source supplies an ety_node", additive == 0,
          f"{additive} nodes")
    additive_e = raw.execute("""
        SELECT COUNT(*) FROM ety_edge e JOIN source s ON s.source_id = e.source_id
        WHERE s.additive_only = 1
    """).fetchone()[0]
    check("no additive_only source supplies an ety_edge", additive_e == 0,
          f"{additive_e} edges")

    print("\n=== ancestry and relations stay separate ===")
    # A cognate is a sibling. If a relation kind ever leaked into the tree
    # tables it would fabricate descent, which is the failure that got branch
    # merging reverted twice.
    leaked = raw.execute("""
        SELECT COUNT(*) FROM ety_edge WHERE rel IN
          ('cognate','doublet','synonym','antonym','derived_term','descendant')
    """).fetchone()[0]
    check("no relation kind appears as an ety_edge rel", leaked == 0,
          f"{leaked} edges")

    print("\n=== lookup: one query, no case policy at read time ===")
    for typed, expect_kind in (("march", "exact"), ("March", "verbatim")):
        e = db.entry(typed)
        check(f"{typed!r} resolves via {expect_kind}",
              e is not None and e.match_kind == expect_kind,
              f"got {e.match_kind if e else None}")
    check("'March' and 'march' are different words",
          (db.entry("March") or 0) and (db.entry("march") or 0)
          and db.entry("March").word_id != db.entry("march").word_id)

    print("\n=== lineage: every emitted pair is a stated edge ===")
    # The bug this catches: concatenating a word's dead-end English tail onto
    # a DIFFERENT component's ancestry ("Aberdeen -> Middle English schire").
    # A cross-word hop legitimately yields a node from ANOTHER word's tree, so
    # object comparison can't see the edge -- it must be checked against the
    # data. Every adjacent pair is valid if either the child sits directly
    # under the parent in one tree, or the parent's own entry records the
    # child as a component it was formed from.
    bad_pairs = []
    for word in ("Aberdeenshire", "professional", "multiculturalism",
                 "smartphone", "nationalize", "bagpipe", "father", "mile"):
        e = db.entry(word)
        if e is None:
            continue
        line = db.lineage(e)
        for parent, child in zip(line, line[1:]):
            if any(c.term == child.term and c.lang == child.lang
                   for c in parent.children):
                continue                       # same tree, stated edge
            owner = db.entry(parent.term) if parent.term else None
            if owner and owner.primary and any(
                    c.rel == "formed_from" and c.term == child.term
                    for c in owner.primary.head.children):
                continue                       # cross-word: a stated component
            bad_pairs.append(f"{word}: {parent.lang} {parent.term}"
                             f" -> {child.lang} {child.term}")
    check("lineage emits no invented adjacency", not bad_pairs,
          "; ".join(bad_pairs[:3]))

    print("\n=== the two features read the same object ===")
    same = True
    for word in ("mile", "beef", "father", "October"):
        e = db.entry(word)
        if e is None or not e.primary:
            continue
        # Tree render and chain walk must come from one Etymology instance.
        if e.primary.spine()[0] is not e.primary.head:
            same = False
    check("spine() and the rendered tree share a head node", same)

    print("\n" + "=" * 60)
    print(f"  {CHECKS[0] - len(FAILURES)}/{CHECKS[0]} checks passed")
    for f in FAILURES:
        print("   FAIL " + f)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
