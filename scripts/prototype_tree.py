"""
Phase-1 prototype: build the NEW connected tree for a handful of words and
print it beside what the app shows today. Writes nothing, touches no
production data -- this exists so the tree shape can be judged before any
corpus-wide rebuild.

    python scripts/prototype_tree.py                 # the standard test set
    python scripts/prototype_tree.py mile father     # specific words
"""
import sys
from collections import defaultdict
from typing import Any, Dict, List

import scriptlib

scriptlib.bootstrap()

import languages
from wiktextract_dump import stream_english_entries
from wiktextract_shapes import build_trees

# Chosen to exercise every shape and every known failure mode:
#   mile/street  -> root must land at the TAIL, after Latin
#   father/cat/free -> no donor templates at all (tree-template migration)
#   telephone/nightmare/computer -> fork, not chain
#   October/close -> two narratives concatenated; must split, not corrupt
#   sandal       -> unrelated theories must NOT be joined
#   bow/bank     -> genuinely separate numbered etymologies
#   sky/coffee/beef/government/table/checkmate -> known-good, must not regress
DEFAULT_WORDS = ["mile", "street", "father", "cat", "free", "telephone",
                 "nightmare", "computer", "October", "close", "sandal",
                 "bow", "bank", "sky", "coffee", "beef", "government",
                 "table", "checkmate", "intrude"]

REL_MARK = {"inherited": "<-", "borrowed": "<=", "derived": "<~",
            "calque": "<c", "root": "<*", "formed_from": "+", "head": ""}


def _etymology_number(entry: Dict[str, Any]) -> int:
    """An int in most entries, a STRING in some -- coerce or arithmetic blows up."""
    try:
        return int(entry.get("etymology_number") or 1)
    except (TypeError, ValueError):
        return 1


def _signature(templates: List[Dict[str, Any]]) -> tuple:
    """`bear` appears 3x with byte-identical templates, one per part of speech."""
    return tuple((t.get("name"), tuple(sorted((t.get("args") or {}).items())))
                 for t in templates)


def collect(words: List[str]) -> Dict[tuple, Any]:
    """(word, etymology_number) -> merged template list. Entries are per-POS."""
    want = {w.lower() for w in words}
    groups: Dict[tuple, Any] = defaultdict(list)
    seen: Dict[tuple, set] = defaultdict(set)
    # The shared reader, not a fourth hand-rolled copy of the same loop.
    scriptlib.require_file(scriptlib.ENGLISH_DUMP,
                           "download the kaikki English extract, or set "
                           "ETYMOLOGY_DATA_ROOT to where it lives")
    for _line_no, entry, head in stream_english_entries(scriptlib.ENGLISH_DUMP):
        if head.lower() not in want:
            continue
        key = (head, _etymology_number(entry))
        templates = entry.get("etymology_templates") or []
        sig = _signature(templates)
        if sig in seen[key]:
            continue
        seen[key].add(sig)
        groups[key].extend(templates)
        if entry.get("etymology_text", "").startswith("Etymology tree"):
            groups[("_text", head, key[1])] = entry["etymology_text"]
    return groups


def render(node, langs, depth=0, out=None):
    out = out if out is not None else []
    mark = REL_MARK.get(node.rel, node.rel)
    lang = langs.get(node.lang)
    era = f"  [{lang.era_label}]" if lang and depth else ""
    term = f" {node.term!r}" if node.term else ""
    dotted = "  (dotted)" if node.certainty == "related" else ""
    out.append("   " + "  " * depth + (f"{mark} " if depth else "") +
               node.lang + term + era + dotted)
    for c in node.children:
        render(c, langs, depth + 1, out)
    return out


def old_tree(word):
    try:
        import word_trees as app
        t = app.resolve_tree(word)
    except Exception as exc:
        return [f"   (error: {exc})"]
    if not t:
        return ["   (no recorded etymology data)"]
    lines = []

    def walk(n, d=0):
        lines.append("   " + "  " * d + ("- " if d else "") + n["lang"] +
                     (f" {n['term']!r}" if n.get("term") else ""))
        for c in n["children"]:
            walk(c, d + 1)
    for b in t["branches"]:
        walk(b)
    return lines


def main():
    words = sys.argv[1:] or DEFAULT_WORDS
    langs = languages.load()
    print(f"languages loaded: {len(langs)}", file=sys.stderr)
    print("scanning dump...", file=sys.stderr)
    groups = collect(words)

    for w in words:
        keys = sorted(k for k in groups
                      if isinstance(k, tuple) and len(k) == 2 and k[0].lower() == w.lower())
        print("\n" + "=" * 72)
        print(f"  {w.upper()}")
        print("=" * 72)

        print("\n  --- TODAY ---")
        for line in old_tree(w):
            print(line)

        print("\n  --- NEW ---")
        if not keys:
            print("   (no templates found)")
            continue
        any_tree = False
        for key in keys:
            trees = build_trees(key[0], groups[key], langs, ordinal=key[1])
            for t in trees:
                any_tree = True
                label = (f"  Etymology {t.ordinal}" if len(trees) > 1 or len(keys) > 1
                         else "")
                print(f"   [{t.shape}]{label}")
                for line in render(t.head, langs):
                    print(line)
        if not any_tree:
            has_text = ("_text", key[0], key[1]) in groups
            print("   (no donor/formation/root templates"
                  f"{' -- has rendered etymology_text, shape C not yet built' if has_text else ''})")


if __name__ == "__main__":
    main()
