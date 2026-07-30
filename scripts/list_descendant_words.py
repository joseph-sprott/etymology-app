"""
Which words actually produce a descendant tree, and from which root.

    python scripts/list_descendant_words.py                  # summary + samples
    python scripts/list_descendant_words.py --all            # every word
    python scripts/list_descendant_words.py --roots          # group by root form
    python scripts/list_descendant_words.py --out words.txt

WHY THIS EXISTS (Joe, 2026-07-27): "give me a list of all the PIE origins in
our database that outputs something on that feature." The premise needed
correcting first, and this script is the correction made checkable.

**You do not type a PIE root.** `/descendants?word=X` looks X up as an ENGLISH
word, finds the tree containing it, and climbs to the top. So `brother` works
and `*bʰréh₂tēr` returns nothing -- the opposite of the assumption. The useful
list is therefore "which English words work", which is what this prints.

Coverage is bounded by `build_descendants.py`'s SOURCES: a word only has a
tree if one of its ancestors has a Wiktionary descendants section AND that
ancestor's proto-language is one of the loaded extracts.
"""
import argparse
import collections
from typing import Any, Dict, Tuple

import scriptlib

scriptlib.bootstrap()

import descendants
import etymology_db

RootKey = Tuple[str, str]


def _climb(db, lang: str, term: str, cache: Dict[RootKey, RootKey]) -> RootKey:
    """
    The root `descendants.full_tree` would display, memoized.

    The walk itself lives in `descendants.climb_to_root` -- this only adds the
    cache, because thousands of words share a handful of chains and the raw
    walk would repeat the same queries tens of thousands of times.
    """
    key = (lang, term)
    if key not in cache:
        root = descendants.climb_to_root(db, None, lang, term)[-1]
        cache[key] = (root.lang, root.term)
    return cache[key]


def english_words(db):
    """Distinct English words -> the root the FEATURE will actually display."""
    rows = db._db.execute(
        "SELECT DISTINCT n.term, t.lang, t.term AS root_term, t.node_count"
        " FROM descendant_node n"
        " JOIN descendant_tree t ON t.tree_id = n.tree_id"
        " WHERE n.lang = 'English' AND n.term IS NOT NULL AND n.term != ''"
        " ORDER BY n.term")
    best = {}
    for r in rows:
        # A word can sit in several fragments; keep the biggest, which is the
        # one `descendants.full_tree` will climb from.
        cur = best.get(r["term"])
        if cur is None or r["node_count"] > cur["node_count"]:
            best[r["term"]] = {"lang": r["lang"], "term": r["root_term"],
                               "node_count": r["node_count"]}
    cache = {}
    for w, v in best.items():
        root_lang, root_term = _climb(db, v["lang"], v["term"], cache)
        v["root_lang"], v["root_term"] = root_lang, root_term
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="print every word")
    ap.add_argument("--roots", action="store_true", help="group by root form")
    ap.add_argument("--out", help="write the full word list to a file")
    args = ap.parse_args()

    db = etymology_db.get()
    words = english_words(db)

    by_root_lang = collections.Counter(v["root_lang"] for v in words.values())
    by_root = collections.defaultdict(list)
    for w, v in words.items():
        by_root[(v["root_lang"], v["root_term"])].append(w)

    print(f"{len(words):,} English words currently produce a descendant tree.")
    print(f"{len(by_root):,} distinct ancestral roots.\n")
    print("By root language:")
    for lang, n in by_root_lang.most_common():
        print(f"   {lang:<26} {n:>6,} words")

    if args.roots:
        print("\nLargest families (root -> the English words under it):")
        for (lang, root), ws in sorted(by_root.items(),
                                       key=lambda kv: -len(kv[1]))[:40]:
            print(f"\n  *{root}  ({lang}, {len(ws)} English words)")
            print("     " + ", ".join(sorted(ws)[:18]) +
                  (" ..." if len(ws) > 18 else ""))

    if args.all:
        print("\nEvery word:")
        for w in sorted(words):
            v = words[w]
            print(f"  {w:<28} <- {v['root_lang']} *{v['root_term']}")

    if not (args.all or args.roots):
        common = sorted(words, key=lambda w: -words[w]["node_count"])[:40]
        print("\nBiggest trees (good ones to try):")
        for w in common:
            v = words[w]
            print(f"   {w:<20} {v['node_count']:>6,} nodes   <- *{v['root_term']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for w in sorted(words):
                v = words[w]
                fh.write(f"{w}\t{v['root_lang']}\t*{v['root_term']}\n")
        print(f"\nwrote {len(words):,} words to {args.out}")


if __name__ == "__main__":
    main()
