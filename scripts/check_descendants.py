r"""
Diagnose one word's descendant tree, deterministically.

Extracted from the etymology-descendants skill 2026-07-26: the skill spelled
out the same four-step Python snippet every time (is anything loaded / is the
word in a tree / does the splice find a parent / what does the assembled tree
look like). There is no decision point in any of it, so it belongs in a script
-- same result every run, no tokens spent retyping it.

Joins the same diagnostic family as check_word.py / check_db_word.py /
check_raw_data.py, and lives here rather than in the skill's own folder so a
word investigation (etymology-fix-word) can reach for it too.

    python scripts\check_descendants.py brother
"""

import argparse

import scriptlib

scriptlib.bootstrap()

import descendants
import etymology_db


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("word")
    ap.add_argument("--lang", default="English",
                    help="language of the word being looked up")
    args = ap.parse_args()

    db = etymology_db.get()

    # 1. Is anything loaded at all? Distinguishes "this word has no data" from
    #    "a full rebuild wiped the tables", which look identical from the UI.
    if not db._has_descendants():
        print("descendant tables ABSENT -- run: python build_descendants.py")
        return
    trees, nodes = db._db.execute(
        "SELECT (SELECT COUNT(*) FROM descendant_tree),"
        " (SELECT COUNT(*) FROM descendant_node)").fetchone()
    print(f"loaded: {trees:,} trees / {nodes:,} nodes")
    if not trees:
        print("  -> tables exist but are EMPTY; re-run build_descendants.py")
        return
    print("  sources: " + ", ".join(
        r[0] for r in db._db.execute(
            "SELECT DISTINCT source FROM descendant_tree ORDER BY 1")))

    # 2. Is the word anywhere in the forest?
    hits = db.trees_containing(args.word, args.lang)
    print(f"\ntrees containing {args.word!r} ({args.lang}): {len(hits)}")
    for row in hits:
        print(f"   {row['lang']:24} {row['raw_term']:18} {row['node_count']:6,} nodes")
    if not hits:
        print("   -> that branch is probably not downloaded. See the skill's"
              " coverage list; a Latin-derived word needs Proto-Italic.")
        return

    # 3. Does the climb find each parent? This is where a spelling mismatch
    #    between two pages silently truncates the tree. Uses the SAME walk
    #    `descendants.full_tree` uses, so what prints here is what the page did.
    print("\nclimb:")
    steps = descendants.climb_to_root(db, hits[0]["tree_id"],
                                      hits[0]["lang"], hits[0]["term"])
    for step in steps:
        arrow = "  (top)" if step is steps[-1] else ""
        print(f"   {step.lang} {step.term}{arrow}")

    # 4. The assembled result, which is what the page actually draws.
    result = descendants.full_tree(args.word, args.lang)
    if result is None:
        print("\nfull_tree returned None -- assembly failed despite a tree hit")
        return
    print(f"\nassembled: root {result['root_lang']} *{result['root_raw']}")
    print(f"   {result['total_nodes']:,} nodes"
          + (f" (showing {result['shown_nodes']:,}, budget-limited)"
             if result["truncated"] else ""))

    def walk(node, depth=0):
        if depth > 3:
            return
        mark = "  <== searched" if node.get("match") else ""
        print("   " + "  " * depth
              + f"{node.get('lang')}: {node.get('raw_term') or ''}{mark}")
        for kid in (node.get("children") or [])[:4]:
            walk(kid, depth + 1)

    print()
    walk(result["tree"])


if __name__ == "__main__":
    main()
