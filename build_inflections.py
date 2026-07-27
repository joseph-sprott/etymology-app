"""
Builds inflections.json: {inflected_form: base_word} for English, from the
wiktextract dump's per-entry `forms` field.

WHY THIS EXISTS (2026-07-25): resolver.py used to carry `_IRREGULAR_FORMS`, a
hand-typed table of 189 irregular verb/noun forms (held->hold, hid->hide,
wolves->wolf via a separate bespoke f/v rule), plus a comment openly admitting
it covered "~100 of English's ~200" irregular verbs and was "not exhaustive."
Every gap in it surfaced as a real, common word reading Unknown -- that's how
`hid`/`meant`/`got`/`snuck`/`laid` were each found, one coverage scan at a time.

The wiktextract dump adopted 2026-07-24 already carries this as real, tagged
data for the entire dictionary: `hide` lists `hid` (tags: past) and `hidden`
(tags: past, participle); `wolf` lists `wolves` (tags: plural). Measured
before committing to the swap: 663,494 distinct inflected forms across
532,599 entries, covering 26/26 of the inflection failures left over from the
347-paragraph coverage scan (photographs, memorized, ponies, raspberries,
shoes, squinted, shivered, slumped, ...). So this replaces a hand-maintained
approximation with the real thing, and lets the hand table be deleted rather
than extended for the Nth time.

SCOPE -- inflection only, deliberately:
    This covers INFLECTIONAL morphology (plural, past, participle,
    comparative, superlative). It does NOT cover DERIVATIONAL morphology
    (-ness, -ment, -tion, -able, -ly, -al, -cy), which Wiktionary does not
    record in `forms` at all. resolver.py's `_SUFFIXES`/`_stem_variants`/
    `_cy_candidates` machinery therefore STAYS -- it does a different job.
    Deleting it would regress `critical` (needs -al -> critic),
    `professional` (-al -> profession) and `consistency` (-cy -> consistent,
    a word with zero rows of its own in the raw data). See resolver.py.

    python build_inflections.py [--jsonl PATH] [--out inflections.json]
"""
import argparse
import json
import sys

from wiktextract_dump import stream_english_entries

JSONL_PATH = r"C:\Users\Josep\Desktop\Etymology Project\wiktextract_data\kaikki.org-dictionary-English.jsonl"
OUT_PATH = "inflections.json"

# Only forms whose tags name a real inflected form. Anything else in `forms`
# is either a spelling variant (`alternative`, `obsolete` -- e.g. demand's
# "demaund", hide's "hyde"), which we deliberately skip because a variant is
# not the same claim as an inflection, or conjugation-table scaffolding (see
# _SCAFFOLD below).
INFLECTION_TAGS = {"past", "participle", "plural", "comparative", "superlative"}

# wiktextract emits internal conjugation-table bookkeeping rows inside
# `forms` alongside real forms -- confirmed directly against "run", whose
# forms list includes {"form": "no-table-tags", "tags": ["table-tags"]} and
# {"form": "glossary", "tags": ["inflection-template"]}. These are not words.
_SCAFFOLD_FORMS = {"no-table-tags", "table-tags", "inflection-template", "glossary"}
_SCAFFOLD_TAGS = {"table-tags", "inflection-template"}


def extract(jsonl_path: str) -> dict:
    form_to_base = {}
    entries_with_forms = 0
    scanned = 0

    for line_no, entry, word in stream_english_entries(jsonl_path):
        scanned += 1

        used_any = False
        for fm in entry.get("forms") or []:
            surface = fm.get("form")
            tags = set(fm.get("tags") or [])
            if not surface or surface in _SCAFFOLD_FORMS or (tags & _SCAFFOLD_TAGS):
                continue
            if not (tags & INFLECTION_TAGS):
                continue
            if surface.lower() == word.lower():
                continue  # e.g. run (past participle) == run; nothing to map
            used_any = True
            # First mapping wins. File order follows Wiktionary's own page
            # order (primary/most-common sense first), the same convention
            # convert_wiktextract.py documents and relies on.
            form_to_base.setdefault(surface.lower(), word)
        if used_any:
            entries_with_forms += 1

        if line_no % 1_000_000 == 0:
            print(f"  ...{line_no:,} lines, {len(form_to_base):,} forms mapped",
                  file=sys.stderr)

    print(f"{scanned:,} English entries scanned, {entries_with_forms:,} carried usable forms",
          file=sys.stderr)
    return form_to_base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=JSONL_PATH)
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    form_to_base = extract(args.jsonl)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(form_to_base, f, ensure_ascii=False)
    print(f"wrote {len(form_to_base):,} inflected forms to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
