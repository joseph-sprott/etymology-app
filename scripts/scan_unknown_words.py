"""
Scan a text corpus for words the resolver can't classify (Direct Source
bucket == "Unknown"), aggregating findings across many paragraphs.

    python scripts/scan_unknown_words.py --corpus PATH [--json-field FIELD] [--out report.json]

Corpus formats supported:
  - .json: expects {"data": [{"<field>": "text..."}, ...]} -- the shape
    randomwordgenerator.com's own json/paragraphs.json uses, field defaults
    to "paragraph". Pass --json-field to match a different JSON shape.
  - anything else: read as plain text, split into paragraphs on blank lines.

Uses analyzer.tokenize() (the exact tokenization the real app uses --
contractions expanded, punctuation stripped, lowercased) so results match
what a user pasting this same text into the app would actually see.

Deliberately does NOT auto-filter proper nouns/pronouns -- that judgment
belongs to whoever reviews the report, not this script (per CLAUDE.md rule
2, don't guess). Instead it computes a heuristic HINT per word: whether it
ever appears capitalized in the source text at a position that ISN'T the
start of a sentence (a real proper-noun signal, e.g. "Paris"), separately
from simply being capitalized because it started a sentence (meaningless).

Output: a frequency-sorted table on stdout, and a full JSON report (word ->
{count, capitalized_mid_sentence, example}) at --out for programmatic reuse
by the diagnosis step (see the etymology-fix-word skill's check_word.py /
check_raw_data.py for investigating individual words from that report).
"""
import argparse
import json
import re
import sys
from typing import Dict, List

import scriptlib

scriptlib.bootstrap()

from analyzer import tokenize
from resolver import default_resolver


def _capitalization_hints(paragraph: str) -> Dict[str, bool]:
    """
    word (lowercased) -> True if it EVER appears capitalized somewhere that
    isn't the first word of a sentence in this paragraph (a real proper-noun
    signal), across this one paragraph.
    """
    hints = {}
    sentence_start = True
    prev_end = 0
    for m in re.finditer(r"[A-Za-z]+|[.!?]", paragraph):
        tok = m.group(0)
        if tok in ".!?":
            sentence_start = True
            continue
        is_mid_sentence_capital = tok[0].isupper() and not sentence_start
        key = tok.lower()
        if is_mid_sentence_capital:
            hints[key] = True
        else:
            hints.setdefault(key, False)
        sentence_start = False
    return hints


def load_paragraphs(path: str, json_field: str) -> List[str]:
    """Paragraphs from a JSON corpus or a plain-text file, blank-line split."""
    scriptlib.require_file(path, "pass --corpus with a real path")
    try:
        with open(path, encoding="utf-8") as handle:
            if not path.endswith(".json"):
                text = handle.read()
                return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
            data = json.load(handle)
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"could not read {path}: {exc}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}")
    try:
        return [row[json_field] for row in data["data"]]
    except (KeyError, TypeError):
        raise SystemExit(
            f'{path} is not the expected shape. Wanted '
            f'{{"data": [{{"{json_field}": "..."}}]}}; pass --json-field to match yours.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--json-field", default="paragraph")
    ap.add_argument("--out", default="unknown_words_report.json")
    args = ap.parse_args()

    paragraphs = load_paragraphs(args.corpus, args.json_field)
    print(f"Loaded {len(paragraphs)} paragraphs from {args.corpus}", file=sys.stderr)

    resolver = default_resolver()
    findings = {}  # word -> {"count": int, "capitalized_mid_sentence": bool, "example": str}

    for i, para in enumerate(paragraphs):
        hints = _capitalization_hints(para)
        tokens = tokenize(para)
        for word in tokens:
            view = resolver.resolve(word).view("direct")
            if view.bucket != "Unknown":
                continue
            entry = findings.setdefault(word, {
                "count": 0,
                "capitalized_mid_sentence": False,
                "example": para[:200],
            })
            entry["count"] += 1
            if hints.get(word):
                entry["capitalized_mid_sentence"] = True
        if (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{len(paragraphs)} paragraphs processed", file=sys.stderr)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=2)

    ranked = sorted(findings.items(), key=lambda kv: -kv[1]["count"])
    likely_proper = [w for w, d in ranked if d["capitalized_mid_sentence"]]
    real_gaps = [w for w, d in ranked if not d["capitalized_mid_sentence"]]

    print(f"\n{len(findings)} unique Unknown words across {len(paragraphs)} paragraphs.")
    print(f"  {len(likely_proper)} flagged as likely proper nouns (capitalized mid-sentence at least once)")
    print(f"  {len(real_gaps)} with no such signal -- these are the ones worth investigating\n")

    print("=== Likely real gaps (not capitalized mid-sentence), by frequency ===")
    for w in real_gaps:
        print(f"  {findings[w]['count']:3d}x  {w}")

    print("\n=== Likely proper nouns (capitalized mid-sentence at least once) ===")
    for w in likely_proper:
        print(f"  {findings[w]['count']:3d}x  {w}")

    print(f"\nFull report written to {args.out}")


if __name__ == "__main__":
    main()
