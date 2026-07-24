"""
Manual overrides for the Etymology Tree feature (etymology_trees.json),
parallel to corrections.py but for the raw tree module_import shape build_etymology_trees.py
produces, not the flattened bucket-chain shape corrections.py uses -- the two
files can't share entries because a tree needs real per-step attested
spellings and nesting, not just a bucket sequence.

Added 2026-07-23 after Joe caught that a word-level fix (corrections.py's
"seen" entry, for the Arabic-letter-transliteration collision) had NOT
propagated to the Etymology Tree, which reads straight from the raw parquet
via build_etymology_trees.py with no corrections layer at all -- so the tree
still showed the same bad data even after the analyzer was fixed. Going
forward: a word-level etymology fix isn't done until it's checked against
BOTH wikt_words.json/corrections.py (analyzer) AND here (tree), and any
future word-level feature besides.

Format: word -> branches list, in the exact node shape
build_etymology_trees.py produces ({"lang", "term", "reltype", "children"}),
so `main()` can substitute it in directly, replacing whatever (possibly
wrong, possibly entirely missing) branches the raw data produced.
"""

TREE_CORRECTIONS = {
    # "seen": etymology-db's raw data for this term_id has ONLY the
    # unrelated Arabic-letter-transliteration row (borrowed_from Arabic
    # سِين) -- the real English past-participle sense isn't in the source
    # data at all (a genuine scraper gap, not just a bucket-ordering issue),
    # so there's no raw structure to correct; this is hand-built from live
    # Wiktionary instead. Chain: Middle English seen <- Old English sēon <-
    # Proto-West Germanic *sehwan <- Proto-Germanic *sehwaną -- matches
    # corrections.py's "seen" entry (root_lang="Proto-Germanic",
    # root_term="*sehwaną"). No PIE step stated on the live page.
    "seen": [
        {"lang": "Middle English", "term": "seen", "reltype": "inherited_from", "children": [
            {"lang": "Old English", "term": "sēon", "reltype": "inherited_from", "children": [
                {"lang": "Proto-West Germanic", "term": "*sehwan", "reltype": "inherited_from", "children": [
                    {"lang": "Proto-Germanic", "term": "*sehwaną", "reltype": "inherited_from", "children": []},
                ]},
            ]},
        ]},
    ],
}
