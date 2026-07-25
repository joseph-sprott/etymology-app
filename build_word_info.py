"""
Builds word_info.json: per-word definition, part of speech, cognates and
doublets -- the non-ancestry information the etymology pipeline deliberately
throws away.

WHY A SEPARATE FILE (2026-07-25): this project's ancestry pipeline filters
hard on `ANCESTRY_RELS`, and three separate modules independently discard
cognate/doublet relations as "not ancestry" (convert_wikt.py's non-ancestry
skip, build_etymology_trees.py's irrelevant-leaf return, and
convert_wiktextract.py's cog/noncog/doublet exclusion). That filtering is
CORRECT and stays: a cognate is a sibling, not an ancestor, and letting one
into a lineage chain would fabricate descent that doesn't exist. So this adds
a SIBLING index alongside the ancestry data rather than loosening that filter.

Sources, unioned for coverage (both were already on disk, unread):
  - wiktextract JSONL -- `cog`/`noncog` and `doublet` etymology templates,
    plus `pos` and `senses[].glosses` for definitions.
  - etymology.parquet -- `cognate_of` / `doublet_with` rows (34,062 and 7,451
    English rows respectively), which carry full language NAMES rather than
    codes.

SCOPE: restricted to words that appear in the etymology databases
(wikt_words.json / wiktextract_words.json). Carrying glosses for all 1.38M
English headwords would be ~165MB -- too heavy to load at startup for a
tooltip. Words outside that set have no etymology to show anyway.

Template argument shapes, confirmed against real entries (they differ, which
is easy to get wrong):
  - cog/noncog: arg "1" is the COGNATE'S language code, arg "2" is the term,
    optional "t" is a gloss.   e.g. {{cog|nl|troost|t=comfort}}
  - doublet:    arg "1" is "en" (the language), args "2","3",... are the
    doublet TERMS.             e.g. {{doublet|en|café|caffè}}

    python build_word_info.py [--limit N]
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, ".")
from wiktextract_langs import name_for_wikt_code

JSONL_PATH = r"C:\Users\Josep\Desktop\Etymology Project\wiktextract_data\kaikki.org-dictionary-English.jsonl"
PARQUET_PATH = r"C:\Users\Josep\Desktop\Etymology Project\etymology.parquet"
OUT_PATH = "word_info.json"

GLOSS_MAX = 200
COGNATE_TEMPLATES = {"cog", "ucog", "noncog"}
DOUBLET_TEMPLATES = {"doublet", "dbt"}


def load_scope():
    """Words worth carrying info for: everything in either etymology database."""
    scope = set()
    for fname in ("wikt_words.json", "wiktextract_words.json"):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        if not os.path.exists(path):
            print(f"  (skipping missing {fname})", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        scope.update(w.lower() for w in data.get("words", {}))
        print(f"  {fname}: {len(data.get('words', {})):,} words", file=sys.stderr)
    return scope


def from_wiktextract(scope, limit=None):
    info = {}
    seen_entries = 0
    # Language code -> display name, harvested from the dump's OWN data rather
    # than hand-listed (2026-07-25). Cognate templates cite a bare code
    # ({{cog|nds-de|Wulf}}), and 437 distinct codes appear that
    # wiktextract_langs.py's curated map doesn't cover -- it only needs the
    # ones that map to an origin BUCKET, which is a much smaller set on
    # purpose. Hand-adding 437 display names would rebuild exactly the
    # hand-maintained-table treadmill that today's inflection work removed.
    # Instead: every `translations` and `descendants` entry in this same file
    # already pairs a code with its full language name
    # ({"lang": "Ido", "lang_code": "io", ...}), so the mapping is harvested
    # for free during the same pass and applied at write time below.
    code_to_name = {}
    with open(JSONL_PATH, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("lang") != "English":
                continue

            # Harvest code->name pairs from EVERY entry, not just in-scope
            # ones -- the mapping is global and more entries means better
            # coverage of the long tail of cognate languages.
            for section in ("translations", "descendants"):
                for row in e.get(section) or []:
                    code = row.get("lang_code") or row.get("code")
                    name = row.get("lang")
                    if code and name and code not in code_to_name:
                        code_to_name[code] = name

            word = e.get("word", "")
            key = word.lower()
            if not key or key not in scope:
                continue
            seen_entries += 1

            rec = info.setdefault(key, {"pos": [], "gloss": None,
                                         "cognates": [], "doublets": []})

            pos = e.get("pos")
            if pos and pos not in rec["pos"]:
                rec["pos"].append(pos)

            if rec["gloss"] is None:
                for sense in e.get("senses") or []:
                    glosses = sense.get("glosses") or []
                    if glosses:
                        g = glosses[0].strip()
                        rec["gloss"] = g[:GLOSS_MAX] + "..." if len(g) > GLOSS_MAX else g
                        break

            for t in e.get("etymology_templates") or []:
                name = t.get("name")
                args = t.get("args") or {}
                if name in COGNATE_TEMPLATES:
                    code, term = args.get("1"), args.get("2")
                    if not code or not term:
                        continue
                    # A single cog template can name SEVERAL languages sharing
                    # one spelling, comma-separated in arg 1 -- e.g. wolf's
                    # {{cog|fy,gsw,nl|wolf}} (West Frisian, Swiss German and
                    # Dutch all spell it "wolf"). Caught 2026-07-25 by spot-
                    # checking the built output: treating the whole string as
                    # one code produced junk rows like "fy,gsw,nl wolf" and
                    # "stq,nds-de Wulf" rendered as if that were a language.
                    for one in (c.strip() for c in code.split(",")):
                        if not one or one == "en":
                            # A "cognate" in English is by definition a
                            # doublet (same root, SAME language); Wiktionary
                            # tags some with cog anyway. Skip rather than show
                            # a confusing "English x" row in a cross-language
                            # list.
                            continue
                        # Store the CODE here; resolved to a display name at
                        # write time, once the harvest above has seen the
                        # whole file (a code cited early may only get its name
                        # from an entry appearing much later).
                        pair = [one, term]
                        if pair not in rec["cognates"]:
                            rec["cognates"].append(pair)
                elif name in DOUBLET_TEMPLATES:
                    # arg "1" is the language ("en"); the rest are terms.
                    for k in sorted(args):
                        if k == "1" or not k.isdigit():
                            continue
                        term = args[k]
                        if term and term not in rec["doublets"] and term.lower() != key:
                            rec["doublets"].append(term)

            if limit and seen_entries >= limit:
                break
            if line_no % 1_000_000 == 0:
                print(f"  ...{line_no:,} lines, {len(info):,} words", file=sys.stderr)

    # Resolve cognate language CODES to display names now that the whole file
    # has been seen. Priority: this project's own curated map first (so a
    # cognate's language label matches the name used everywhere else in the
    # app), then the harvested map, then the bare code as a last resort.
    print(f"  harvested {len(code_to_name):,} language code->name pairs", file=sys.stderr)
    unresolved = set()
    for rec in info.values():
        resolved = []
        for code, term in rec["cognates"]:
            name = name_for_wikt_code(code) or code_to_name.get(code)
            if name is None:
                unresolved.add(code)
                name = code
            if name == "English":
                continue
            pair = [name, term]
            if pair not in resolved:
                resolved.append(pair)
        rec["cognates"] = resolved
    if unresolved:
        print(f"  {len(unresolved)} codes still unnamed (shown as-is): "
              f"{sorted(unresolved)[:10]}", file=sys.stderr)
    return info


def merge_parquet(info, scope):
    """Union in etymology-db's own cognate_of / doublet_with rows."""
    df = pd.read_parquet(PARQUET_PATH)
    eng = df[(df["lang"] == "English") & (df["reltype"].isin(["cognate_of", "doublet_with"]))]
    added_cog = added_dbl = 0
    for row in eng.itertuples():
        key = str(row.term).lower()
        if key not in scope:
            continue
        rec = info.setdefault(key, {"pos": [], "gloss": None,
                                     "cognates": [], "doublets": []})
        term = row.related_term if pd.notna(row.related_term) else None
        if not term:
            continue
        if row.reltype == "cognate_of":
            lang = row.related_lang if pd.notna(row.related_lang) else None
            if not lang or lang == "English":
                continue  # same-language "cognate" is a doublet -- see above
            pair = [lang, term]
            if pair not in rec["cognates"]:
                rec["cognates"].append(pair)
                added_cog += 1
        else:
            if term not in rec["doublets"] and term.lower() != key:
                rec["doublets"].append(term)
                added_dbl += 1
    print(f"  parquet added {added_cog:,} cognates, {added_dbl:,} doublets", file=sys.stderr)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    print("loading scope from etymology databases...", file=sys.stderr)
    scope = load_scope()
    print(f"  scope: {len(scope):,} distinct words", file=sys.stderr)

    print("scanning wiktextract...", file=sys.stderr)
    info = from_wiktextract(scope, args.limit)
    print(f"  {len(info):,} words with info", file=sys.stderr)

    print("merging etymology-db cognate/doublet rows...", file=sys.stderr)
    info = merge_parquet(info, scope)

    # Drop entries that ended up carrying nothing useful.
    info = {w: r for w, r in info.items()
            if r["gloss"] or r["pos"] or r["cognates"] or r["doublets"]}

    with_gloss = sum(1 for r in info.values() if r["gloss"])
    with_cog = sum(1 for r in info.values() if r["cognates"])
    with_dbl = sum(1 for r in info.values() if r["doublets"])

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False)

    size_mb = os.path.getsize(args.out) / (1024 * 1024)
    print(f"\nwrote {len(info):,} words to {args.out} ({size_mb:.1f} MB)", file=sys.stderr)
    print(f"  with definition: {with_gloss:,}", file=sys.stderr)
    print(f"  with cognates:   {with_cog:,}", file=sys.stderr)
    print(f"  with doublets:   {with_dbl:,}", file=sys.stderr)


if __name__ == "__main__":
    main()
