"""
Load Wiktionary's DESCENDANTS trees into `etymology.db`.

Joe, 2026-07-26: "start from a PIE root ... you can effectively see all the
modern words that descended from the proto germanic word, and the path it took
to get there. That is very very cool and directly related to the visualization
I want."

Everything else in this project runs UPWARD -- a word to its ancestors. This
runs downward, and it is a genuinely different dataset, not a re-query of the
one we have. Wiktionary keeps it on the ancestor's page: the English entry for
`brother` knows nothing about Dutch `broeder`, but Proto-Germanic `*brōþēr`
lists both, nested, all the way down to the modern forms.

WHY SEPARATE EXTRACTS AND NOT THE 23GB DUMP
-------------------------------------------
The English extract this project already builds from cannot answer this at all:
its `descendants` rows are almost entirely depth 0 and point the wrong way
(`brother` -> Jamaican `bredda`), because everything ABOVE English lives on a
non-English page. Measured 2026-07-26: 4,547 English entries carry the field,
18,276 of 20,529 rows at depth 0.

The full multi-language dump is 23.1GB. It is not needed: each proto entry
carries its whole subtree nested, so two small per-language extracts
(Proto-Indo-European 12MB, Proto-Germanic 65MB) reconstruct the entire diagram
Joe drew. Proto-Germanic `*brōþēr` alone yields 125 nested nodes down to
English, Scots and Yola.

Adding a branch = adding one more extract to SOURCES. Proto-Italic and
Proto-Hellenic would light up the Romance and Greek sides the same way.

HOW THE TWO LEVELS JOIN
-----------------------
The PIE root lists its branch heads with NO nesting -- Wiktionary writes "see
there for further descendants" and continues on the branch's own page. So
`*bʰréh₂tēr`'s Proto-Germanic row is a leaf here and a 125-node tree there.
They are joined on (language, term) at QUERY time, not stored pre-spliced, so
adding an extract later enriches existing trees without a rebuild.

    python build_descendants.py            # ~1 min
    python build_descendants.py --stats    # what's loaded, no rebuild

Re-run this after any full `build_etymology_db.py` rebuild -- that script
creates the database fresh and these tables are not part of its schema.
"""

import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "etymology.db")
DATA = r"C:\Users\Josep\Desktop\Etymology Project\wiktextract_data"

# (file, label) -- add a line to widen coverage to another branch.
SOURCES = [
    ("pie.jsonl", "kaikki:Proto-Indo-European"),
    ("proto-germanic.jsonl", "kaikki:Proto-Germanic"),
    ("proto-indo-iranian.jsonl", "kaikki:Proto-Indo-Iranian"),
    ("proto-balto-slavic.jsonl", "kaikki:Proto-Balto-Slavic"),
    ("proto-celtic.jsonl", "kaikki:Proto-Celtic"),
    ("proto-italic.jsonl", "kaikki:Proto-Italic"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS descendant_tree (
  tree_id   INTEGER PRIMARY KEY,
  lang      TEXT NOT NULL,          -- language of the ROOT form
  term      TEXT NOT NULL,          -- root form, asterisk stripped
  raw_term  TEXT NOT NULL,          -- as written, e.g. '*bʰréh₂tēr'
  node_count INTEGER NOT NULL,
  source    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS desc_tree_lookup ON descendant_tree(lang, term);

CREATE TABLE IF NOT EXISTS descendant_node (
  node_id   INTEGER PRIMARY KEY,
  tree_id   INTEGER NOT NULL REFERENCES descendant_tree(tree_id),
  parent_id INTEGER REFERENCES descendant_node(node_id),
  lang      TEXT,
  lang_code TEXT,
  term      TEXT,                   -- asterisk stripped; NULL for a grouping row
  raw_term  TEXT,
  depth     INTEGER NOT NULL,
  ordinal   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS desc_node_tree ON descendant_node(tree_id);
CREATE INDEX IF NOT EXISTS desc_node_parent ON descendant_node(tree_id, parent_id);
-- The reverse lookup that makes this searchable by an ordinary English word:
-- "which tree contains `brother`, and where in it?"
CREATE INDEX IF NOT EXISTS desc_node_term ON descendant_node(term, lang);
"""


def clean(term):
    """
    Wiktionary marks a reconstruction with a leading asterisk. Store it stripped
    for joining (a form is cited both ways across pages) and keep the original
    for display, so the page can still show that a form is reconstructed.
    """
    if not term:
        return None
    return term.lstrip("*").strip() or None


def load(conn, path, label):
    """Insert every entry that has a descendants tree. Returns (trees, nodes)."""
    trees = nodes = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            desc = entry.get("descendants")
            if not desc:
                continue
            raw = entry.get("word") or ""
            term = clean(raw)
            if not term:
                continue

            cur = conn.execute(
                "INSERT INTO descendant_tree (lang, term, raw_term, node_count, source)"
                " VALUES (?,?,?,0,?)",
                (entry.get("lang") or "", term, raw, label))
            tree_id = cur.lastrowid
            trees += 1

            # Iterative walk with an explicit stack: these trees reach depth 10+
            # and recursion here would be one more thing to reason about during
            # a build that already takes a minute.
            count = 0
            stack = [(row, None, 0, i) for i, row in enumerate(desc)]
            while stack:
                row, parent_id, depth, ordinal = stack.pop()
                rterm = row.get("word")
                cur = conn.execute(
                    "INSERT INTO descendant_node"
                    " (tree_id, parent_id, lang, lang_code, term, raw_term, depth, ordinal)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (tree_id, parent_id, row.get("lang"), row.get("lang_code"),
                     clean(rterm), rterm, depth, ordinal))
                nid = cur.lastrowid
                count += 1
                kids = row.get("descendants") or []
                for i, kid in enumerate(kids):
                    stack.append((kid, nid, depth + 1, i))
            conn.execute("UPDATE descendant_tree SET node_count=? WHERE tree_id=?",
                         (count, tree_id))
            nodes += count
    return trees, nodes


def stats(conn):
    t, n = conn.execute(
        "SELECT (SELECT COUNT(*) FROM descendant_tree),"
        " (SELECT COUNT(*) FROM descendant_node)").fetchone()
    print(f"trees: {t:,}   nodes: {n:,}")
    print("\nby source:")
    for src, c, nn in conn.execute(
            "SELECT source, COUNT(*), SUM(node_count) FROM descendant_tree"
            " GROUP BY source ORDER BY 2 DESC"):
        print(f"   {src:32} {c:6,} trees  {nn or 0:8,} nodes")
    print("\nlargest trees:")
    for lang, term, c in conn.execute(
            "SELECT lang, raw_term, node_count FROM descendant_tree"
            " ORDER BY node_count DESC LIMIT 8"):
        print(f"   {lang:24} {term:20} {c:5,} nodes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--stats", action="store_true",
                    help="report what is loaded and exit")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    conn = sqlite3.connect(args.db)
    conn.executescript(SCHEMA)

    if args.stats:
        stats(conn)
        return

    # Full replace. These tables are derived wholly from the extracts, so a
    # rebuild is the honest way to pick up a corrected or widened source --
    # merging would leave orphans from a source that changed shape.
    conn.execute("DELETE FROM descendant_node")
    conn.execute("DELETE FROM descendant_tree")

    total_t = total_n = 0
    for name, label in SOURCES:
        path = os.path.join(args.data, name)
        if not os.path.exists(path):
            print(f"  SKIP {name} (not present)")
            continue
        t, n = load(conn, path, label)
        print(f"  {name:24} {t:6,} trees  {n:8,} nodes")
        total_t += t
        total_n += n
    conn.commit()
    print(f"\ntotal: {total_t:,} trees, {total_n:,} nodes")
    stats(conn)


if __name__ == "__main__":
    main()
