"""
Prototype tool: measure whether kaikki.org's English wiktextract JSONL extract
actually has etymology data for words the CURRENT resolver can't classify,
before committing to a full migration. See FUTURE_FEATURES_AND_RESOURCES.md /
GITHUB_RESOURCES.md for the source research; this script turns that research
into a real, checkable number against this project's own data.

    python scripts/wiktextract_coverage_check.py --jsonl PATH --words-file report.json
    python scripts/wiktextract_coverage_check.py --jsonl PATH --words word1,word2,...
    python scripts/wiktextract_coverage_check.py --jsonl PATH --full-stats

Streams the JSONL line by line (the English-only extract is ~3GB -- do not
load it fully into memory). Each line is one word-sense entry; a single
headword can have multiple lines (one per etymology_number / part of speech).
Filters to lang == "English" (the extract also carries some non-English
metadata rows). "Has etymology data" means a non-empty etymology_text or
etymology_templates on at least one sense.

With --full-stats, also scans the whole file (no early exit once targets are
found) and reports the total count of distinct English headwords with any
etymology data, for a direct comparison against wikt_words.json's current
244,094-word count.
"""
import argparse
import json
import sys

sys.path.insert(0, ".")
from resolver import default_resolver


def load_words(args):
    if args.words:
        return sorted({w.strip().lower() for w in args.words.split(",") if w.strip()})
    with open(args.words_file, encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data.keys())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--words")
    ap.add_argument("--words-file")
    ap.add_argument("--out", default="wiktextract_coverage_report.json")
    ap.add_argument("--full-stats", action="store_true")
    args = ap.parse_args()

    words = load_words(args) if (args.words or args.words_file) else []
    targets = set(words)
    found = {}
    total_english_headwords_with_etymology = set()

    with open(args.jsonl, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not args.full_stats and targets and found.keys() >= targets:
                break
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("lang") != "English":
                continue
            word = entry.get("word", "")
            if not word:
                continue
            word_lc = word.lower()
            has_text = bool(entry.get("etymology_text"))
            has_templates = bool(entry.get("etymology_templates"))
            has_ety = has_text or has_templates

            if args.full_stats and has_ety:
                total_english_headwords_with_etymology.add(word_lc)

            if word_lc in targets:
                rec = found.setdefault(word_lc, {
                    "has_etymology_text": False,
                    "has_etymology_templates": False,
                    "pos_seen": set(),
                    "etymology_number_seen": set(),
                })
                rec["has_etymology_text"] = rec["has_etymology_text"] or has_text
                rec["has_etymology_templates"] = rec["has_etymology_templates"] or has_templates
                if entry.get("pos"):
                    rec["pos_seen"].add(entry["pos"])
                if entry.get("etymology_number") is not None:
                    rec["etymology_number_seen"].add(entry["etymology_number"])

            if line_no % 1_000_000 == 0:
                print(f"  ...{line_no:,} lines scanned", file=sys.stderr)

    if args.full_stats:
        print(f"\nTotal distinct English headwords with etymology data in wiktextract: "
              f"{len(total_english_headwords_with_etymology):,}")

    if not words:
        return

    resolver = default_resolver()
    rows = []
    for w in words:
        rec = found.get(w)
        current_bucket = resolver.resolve(w).view("direct").bucket
        wikt_has_ety = bool(rec and (rec["has_etymology_text"] or rec["has_etymology_templates"]))
        rows.append({
            "word": w,
            "current_bucket": current_bucket,
            "found_in_wiktextract": rec is not None,
            "wiktextract_has_etymology": wikt_has_ety,
            "pos_seen": sorted(rec["pos_seen"]) if rec else [],
            "senses_with_own_etymology_number": len(rec["etymology_number_seen"]) if rec else 0,
        })

    would_close = [r for r in rows if r["current_bucket"] == "Unknown" and r["wiktextract_has_etymology"]]
    still_missing = [r for r in rows if r["current_bucket"] == "Unknown" and not r["wiktextract_has_etymology"]]

    print(f"\n{len(words)} target words checked.")
    print(f"  {len(would_close)} currently Unknown AND have etymology data in wiktextract -- real candidates to close")
    print(f"  {len(still_missing)} currently Unknown AND still absent/no-etymology in wiktextract -- would remain gaps even after migration")

    print("\n=== Would close (etymology data exists in wiktextract, not used today) ===")
    for r in would_close:
        print(f"  {r['word']}  (pos: {', '.join(r['pos_seen'])}, senses: {r['senses_with_own_etymology_number']})")

    print("\n=== Still missing even in wiktextract ===")
    for r in still_missing:
        print(f"  {r['word']}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"\nFull report: {args.out}")


if __name__ == "__main__":
    main()
