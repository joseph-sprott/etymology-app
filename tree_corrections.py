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

    # "tag": matches corrections.py's "tag" entry -- etymology-db's raw data
    # for this term_id only carried the rare Aramaic "crown" sense (a
    # separate Wiktionary Etymology section), not the common label/game
    # sense actually needed here. No further stage beyond Middle English is
    # recorded for this sense on the live page (only cognates -- Norwegian/
    # Swedish/Icelandic tagg/tág -- not ancestry), so honestly stops there
    # rather than guessing a deeper Norse/Germanic form.
    "tag": [
        {"lang": "Middle English", "term": "tagge", "reltype": "inherited_from", "children": []},
    ],

    # "auto": matches corrections.py's "auto" entry -- the raw data's real
    # derived_from Ancient Greek edge was outranked by a circular
    # clipping_of "autorickshaw" -> derived_from Hindi artifact (see
    # corrections.py for the full explanation). No further PIE connection
    # recorded for αὐτός itself in this data.
    "auto": [
        {"lang": "Ancient Greek", "term": "αὐτός", "reltype": "derived_from", "children": []},
    ],

    # "generate": matches corrections.py's "generate" entry -- raw data only
    # had a bare has_root PIE pointer plus two etymologically_related_to
    # (hedge, not ancestry) mentions of Latin generō/genus. Hand-built from
    # the live page's stated chain: generō <- genus <- PIE *ǵenh₁-.
    "generate": [
        {"lang": "Latin", "term": "generō", "reltype": "derived_from", "children": [
            {"lang": "Latin", "term": "genus", "reltype": "derived_from", "children": [
                {"lang": "Proto-Indo-European", "term": "*ǵenh₁-", "reltype": "has_root", "children": []},
            ]},
        ]},
    ],

    # The following ten all match corrections.py's 2026-07-24 entries (issue
    # #17, the 347-paragraph coverage scan) -- see that file for the full
    # per-word verification notes. Chains here mirror corrections.py's
    # root_lang/root_term exactly.

    "previous": [
        {"lang": "Latin", "term": "praevius", "reltype": "derived_from", "children": []},
    ],

    # "mom": inherits mama's own already-correct tree (same reasoning as
    # corrections.py's "mom" entry).
    "mom": [
        {"lang": "Middle English", "term": "mome", "reltype": "inherited_from", "children": [
            {"lang": "Old English", "term": "*mōme", "reltype": "inherited_from", "children": [
                {"lang": "Proto-West Germanic", "term": "*mōmā", "reltype": "derived_from", "children": [
                    {"lang": "Proto-Germanic", "term": "*mōmǭ", "reltype": "derived_from", "children": [
                        {"lang": "Proto-Indo-European", "term": "*méh₂-méh₂", "reltype": "derived_from", "children": []},
                    ]},
                ]},
            ]},
        ]},
    ],

    # "package": inherits pack's own already-correct tree.
    "package": [
        {"lang": "Middle English", "term": "pak", "reltype": "inherited_from", "children": [
            {"lang": "Old English", "term": "pæcca", "reltype": "inherited_from", "children": []},
        ]},
        {"lang": "Middle Dutch", "term": "pak", "reltype": "derived_from", "children": [
            {"lang": "Proto-Germanic", "term": "*pakkô", "reltype": "derived_from", "children": []},
        ]},
    ],

    "incident": [
        {"lang": "Middle French", "term": "incident", "reltype": "borrowed_from", "children": [
            {"lang": "Latin", "term": "incidēns", "reltype": "derived_from", "children": [
                {"lang": "Latin", "term": "incidō", "reltype": "derived_from", "children": [
                    {"lang": "Latin", "term": "cadō", "reltype": "derived_from", "children": [
                        {"lang": "Proto-Indo-European", "term": "*ḱh₂d-", "reltype": "has_root", "children": []},
                    ]},
                ]},
            ]},
        ]},
    ],

    "expert": [
        {"lang": "Old French", "term": "expert", "reltype": "borrowed_from", "children": [
            {"lang": "Latin", "term": "expertus", "reltype": "derived_from", "children": [
                {"lang": "Latin", "term": "experior", "reltype": "derived_from", "children": []},
            ]},
        ]},
    ],

    "metaphor": [
        {"lang": "Middle French", "term": "métaphore", "reltype": "borrowed_from", "children": [
            {"lang": "Latin", "term": "metaphora", "reltype": "derived_from", "children": [
                {"lang": "Ancient Greek", "term": "μεταφορά", "reltype": "derived_from", "children": [
                    {"lang": "Ancient Greek", "term": "μεταφέρω", "reltype": "derived_from", "children": []},
                ]},
            ]},
        ]},
    ],

    "adult": [
        {"lang": "French", "term": "adulte", "reltype": "borrowed_from", "children": [
            {"lang": "Latin", "term": "adultus", "reltype": "derived_from", "children": [
                {"lang": "Latin", "term": "adolescō", "reltype": "derived_from", "children": []},
            ]},
        ]},
    ],

    "puppy": [
        {"lang": "Old French", "term": "poupée", "reltype": "borrowed_from", "children": []},
    ],

    "presence": [
        {"lang": "Old French", "term": "presence", "reltype": "borrowed_from", "children": [
            {"lang": "Latin", "term": "praesentia", "reltype": "derived_from", "children": [
                {"lang": "Latin", "term": "praesentem", "reltype": "derived_from", "children": []},
            ]},
        ]},
    ],

    # "familiar": no French/Anglo-Norman intermediate stage is named on the
    # live page -- Middle English borrows directly from Latin.
    "familiar": [
        {"lang": "Middle English", "term": "familiar", "reltype": "borrowed_from", "children": [
            {"lang": "Latin", "term": "familiāris", "reltype": "derived_from", "children": []},
        ]},
    ],

    "unless": [
        {"lang": "Middle English", "term": "unlesse", "reltype": "inherited_from", "children": []},
    ],
}
