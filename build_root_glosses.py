"""
Build `root_glosses.json` -- what a reconstructed root MEANS.

Joe, 2026-07-26: "I want to be able to hover over a PIE root and see what that
root means, for example gidʰ- means kid/goatling/little goat."

The database stores 12,996 root nodes and not one gloss (`ety_node.gloss` is
empty for every row), so the meaning has to come from somewhere. It is already
in the dump: Wiktionary's own `inh`/`der`/`cog` templates carry the reconstructed
form's meaning as a named `t=`/`gloss=` argument or as the positional 4th
argument, e.g.

    {{inh|en|gem-pro|*frijaz|t=beloved, not in bondage}}

That is Wiktionary asserting what the form means, not this script inferring it
(project rule 2), which is why the gloss is read only from those explicit
arguments and never guessed from the descendant word's own definition.

`cog`/`noncog` templates are read too, which needs saying because this project
is otherwise strict that a cognate is NOT an ancestor: the gloss on a cognate
template describes the FORM being cited, and nothing here touches lineage -- it
is a dictionary of meanings keyed by spelling, never an edge.

One form often carries several wordings across the ~1.4M entries that cite it.
The most frequently attested wording wins, and the runners-up are kept so the
UI can show that Wiktionary's own entries word it more than one way.

    python build_root_glosses.py            # full dump, ~5-10 min
    python build_root_glosses.py --limit N  # first N lines, for a quick check
"""

import argparse
import collections
import itertools
import json
import os
import sys

JSONL = r"C:\Users\Josep\Desktop\Etymology Project\wiktextract_data\kaikki.org-dictionary-English.jsonl"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "root_glosses.json")

# Templates whose arguments name a form and may gloss it. Ancestry templates
# and cognate templates both qualify -- see the module docstring on why citing
# a cognate's gloss is not a lineage claim.
GLOSS_TEMPLATES = {
    "inh", "inh-lite", "inherited", "der", "derived", "bor", "borrowed",
    "cog", "ncog", "noncog", "m", "m+", "mention", "l", "root",
}

# Named gloss arguments, in the order Wiktionary's own templates prefer them.
# `tr=` is deliberately NOT here: it is a transliteration (how a non-Latin
# form is romanised), not a meaning, and reading it as one would caption a
# root with its own spelling rewritten.
NAMED_GLOSS = ("t", "gloss")

# Wiktextract leaves these in place of an argument that was empty in wikitext.
PLACEHOLDERS = {"", "-", "—", "?"}


def _gloss_from(args):
    """The explicitly-stated meaning in a template's arguments, or None."""
    for key in NAMED_GLOSS:
        val = (args.get(key) or "").strip()
        if val and val not in PLACEHOLDERS:
            return val
    # Positional: {{inh|en|gem-pro|*frijaz||beloved}} -- arg 4 is the display
    # override (usually empty) and arg 5 the gloss; some templates put the
    # gloss at 4 when there is no override. Accept either, but only when it
    # reads like a definition rather than another form.
    for key in ("5", "4"):
        val = (args.get(key) or "").strip()
        if val and val not in PLACEHOLDERS and not val.startswith("*"):
            return val
    return None


def _term_from(args):
    """The reconstructed form a template is talking about, or None."""
    for key in ("3", "2", "4"):
        val = (args.get(key) or "").strip()
        if val.startswith("*") and len(val) > 1:
            return val
    return None


def key_for(term):
    """
    Lookup key shared with the app: no leading asterisk, no surrounding
    whitespace. Case and the hyphens that mark a bound root are kept -- they
    are part of how the form is written, and collapsing them would merge forms
    Wiktionary keeps apart.
    """
    return term.lstrip("*").strip()


def scan(path, limit=None):
    counts = collections.defaultdict(collections.Counter)
    lines = 0
    with open(path, encoding="utf-8") as fh:
        for line in (itertools.islice(fh, limit) if limit else fh):
            lines += 1
            try:
                entry = json.loads(line)
            except Exception:
                continue
            for tpl in entry.get("etymology_templates") or []:
                if tpl.get("name") not in GLOSS_TEMPLATES:
                    continue
                args = tpl.get("args") or {}
                term = _term_from(args)
                if not term:
                    continue
                gloss = _gloss_from(args)
                if not gloss:
                    continue
                counts[key_for(term)][gloss] += 1
    return counts, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=JSONL)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    counts, lines = scan(args.jsonl, args.limit)

    out = {}
    for term, glosses in counts.items():
        ranked = glosses.most_common()
        out[term] = {
            "gloss": ranked[0][0],
            "count": ranked[0][1],
            # Alternative wordings, so the UI can show that Wiktionary itself
            # words this form's meaning more than one way rather than implying
            # a single settled definition.
            "also": [g for g, _ in ranked[1:4]],
        }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=0, sort_keys=True)

    size = os.path.getsize(args.out) / 1024.0 / 1024.0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"lines scanned : {lines:,}")
    print(f"forms glossed : {len(out):,}")
    print(f"written       : {args.out} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
