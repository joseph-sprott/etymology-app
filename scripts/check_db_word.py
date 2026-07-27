"""
Everything the canonical pipeline knows about one word, in one place.

The single-word diagnostic for the etymology.db era. `check_raw_data.py`
inspects the legacy parquet, which is now only a gap-filler; when a word looks
wrong today the question is almost always one of:

    what did the DUMP give us      -> the raw etymology templates
    what did the BUILDER make      -> the stored tree, its shape and edges
    what will each FEATURE show    -> spine() for the tree, lineage() for bars

...and those three, side by side, have identified every tree bug found so far
(`mile`'s false PIE edge, `father`'s missing chain, `wolves` resolving to the
surname `Wolf`). Printing them together is the whole point: the bug is usually
visible in the STEP BETWEEN two of them, not in any one alone.

    python scripts/check_db_word.py mile
    python scripts/check_db_word.py wolves --raw     # also scan the 3.2GB dump
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wiktextract_dump import stream_english_entries

import etymology_db

JSONL = r"C:\Users\Josep\Desktop\Etymology Project\wiktextract_data\kaikki.org-dictionary-English.jsonl"


def show_tree(node, depth=0):
    dotted = "  (dotted -- not counted as descent)" if node.certainty == "related" else ""
    rel = f"  [{node.rel}]" if depth else ""
    print("    " + "  " * depth + f"{node.lang} {node.term or ''}".rstrip()
          + rel + dotted)
    for child in node.children:
        show_tree(child, depth + 1)


def raw_templates(word):
    """The word's own etymology templates, straight from the dump."""
    want = word.lower()
    # Shared reader (2026-07-27) -- this was a hand-rolled copy of the same
    # open/parse/filter-English loop three other modules had.
    return [e for _ln, e, head in stream_english_entries(JSONL)
            if head.lower() == want]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("word")
    ap.add_argument("--db", default=None)
    ap.add_argument("--raw", action="store_true",
                    help="also print the dump's raw templates (~90s scan)")
    args = ap.parse_args()

    db = etymology_db.get(args.db) if args.db else etymology_db.get()
    entry = db.entry(args.word)

    print("=" * 68)
    print(f"  {args.word}")
    print("=" * 68)

    if entry is None:
        print("\n  NOT FOUND -- no surface_form row points anywhere.")
        print("  Either the dump has no entry, or the word resolved to")
        print("  status='none' (which deliberately gets no lookup row).")
    else:
        # The headword matters: `wolves` pointing at `Wolf` rather than `wolf`
        # is a whole class of bug, and it is invisible unless printed.
        print(f"\n  resolved to : {entry.headword!r}  [{entry.status}]")
        print(f"  matched via : {entry.match_kind}"
              f"{' -- ' + entry.match_note if entry.match_note else ''}")
        print(f"  etymologies : {len(entry.etymologies)}")

        for ety in entry.etymologies:
            print(f"\n  --- slot {ety.ordinal} (Wiktionary etymology "
                  f"{ety.label}, shape={ety.shape}) ---")
            show_tree(ety.head)

        if entry.primary:
            print("\n  spine   (tree's main line, solid edges only):")
            print("    " + " -> ".join(
                f"{n.lang} {n.term or ''}".strip() for n in entry.primary.spine()))
        print("\n  lineage (what the bars count -- follows components):")
        print("    " + " -> ".join(
            f"{n.lang} {n.term or ''}".strip() for n in db.lineage(entry)))

        counts = db.relation_counts(entry.word_id)
        if counts:
            print("\n  relations   :", ", ".join(
                f"{k}={v}" for k, v in sorted(counts.items())))
        senses = db.senses(entry.word_id, limit=3)
        for s in senses:
            print(f"  sense ({s['pos']}): {s['gloss'][:90]}")

    if args.raw:
        print("\n" + "-" * 68)
        print("  RAW DUMP ENTRIES")
        print("-" * 68)
        for e in raw_templates(args.word):
            print(f"\n  word={e.get('word')!r} pos={e.get('pos')} "
                  f"ety_number={e.get('etymology_number')}")
            for t in (e.get("etymology_templates") or []):
                print(f"    {t.get('name'):12} {json.dumps(t.get('args'), ensure_ascii=False)[:160]}")
            text = (e.get("etymology_text") or "")[:400]
            if text:
                print(f"    text: {text!r}")


if __name__ == "__main__":
    main()
