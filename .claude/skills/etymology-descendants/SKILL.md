---
name: etymology-descendants
description: This skill should be used when working on the Etymology Analyzer's DESCENDANTS feature -- the downward tree showing everything that descended from an ancestral form (e.g. "add another language branch to the descendant tree", "why does X have no descendants", "the descendant tree looks wrong/duplicated", "widen descendant coverage beyond Germanic"). Not for the upward etymology tree or Word Search -- those answer where a word came from and are a different dataset.
---

# Working on the descendants feature

The rest of this project runs UPWARD: a word to its ancestors. This one runs
DOWNWARD, and it is a genuinely separate dataset, not a re-query of the one we
already had. Wiktionary keeps descendants on the *ancestor's* page: the English
entry for `brother` knows nothing about Dutch `broeder`, but Proto-Germanic
`*brōþēr` lists both, nested, all the way to the modern forms.

**The one fact that saves the most time:** the English wiktextract extract this
project builds from CANNOT answer descendant questions. Measured 2026-07-26 --
4,547 English entries carry a `descendants` field, 18,276 of 20,529 rows sit at
depth 0, and they point the wrong way (`brother` -> Jamaican `bredda`).
Everything ABOVE English lives on a page in another language. If a word has no
descendants, the answer is almost always "that branch isn't downloaded," not a
bug.

## The pieces

| File | Role |
|---|---|
| `build_descendants.py` | Loads per-language kaikki extracts into `descendant_tree` / `descendant_node` in `etymology.db`. `SOURCES` is the coverage list |
| `etymology_db.py` | Query side: `trees_containing`, `tree_for_form`, `parent_tree_of`, `descendant_tree`. Still the ONLY module that opens the database |
| `descendants.py` | Assembly: climb to the topmost root, splice fragments, merge spelling variants, apply the node budget, mark the searched word |
| `app.py` | `/descendants` route + the d3 view (`DESC_PAGE`); `static/d3.v7.min.js` is vendored, never a CDN |

## 1. Widening coverage to another branch

This is the most common request, and it is one command:

```
python scripts\add_descendant_language.py "Proto-Italic"
python scripts\add_descendant_language.py "Proto-Italic" --check   # probe only
python scripts\verify.py
```

It derives the kaikki URL, downloads, registers the source and rebuilds the two
tables. The URL derivation is the part worth having in code: the directory keeps
the hyphens but the filename strips them
(`/dictionary/Proto-Indo-European/kaikki.org-dictionary-ProtoIndoEuropean.jsonl`),
and getting it wrong 404s in a way that reads as "that language isn't available."

**Loaded as of 2026-07-26** (10,870 trees / 553,724 nodes): Proto-Indo-European
(12MB), Proto-Germanic (65MB), Proto-Celtic (11.7MB), Proto-Italic (5.2MB),
Proto-Indo-Iranian (3.3MB), Proto-Balto-Slavic (1.7MB).

Still missing and worth adding if the Greek side matters: **Proto-Hellenic has
no kaikki extract** -- `--check` returns 404, so Greek descendants would need
another route. Latin and Ancient Greek themselves are separate, much larger
extracts and would deepen the Romance/Greek tails further.

**No rebuild of `etymology.db` is needed and none should be attempted** --
`build_descendants.py` only touches its own two tables. Fragments are joined at
QUERY time on (language, term), so a newly added branch enriches existing trees
immediately: adding Proto-Italic makes the Romance side of every PIE root light
up without re-touching the PIE data.

Highest-value additions, in order: **Proto-Italic** (the Latin/Romance half of
English vocabulary), **Proto-Hellenic** (Greek), **Proto-Balto-Slavic**,
**Proto-Celtic**, **Proto-Indo-Iranian**.

**The trap:** a full `python build_etymology_db.py` rebuild creates the database
fresh and these two tables are NOT in `etymology_schema.sql`, so they vanish
silently -- the feature just starts answering "no descendants" for everything.
Re-run `build_descendants.py` after ANY full rebuild.

## 2. Diagnosing "this word has no descendants"

```
python scripts\check_descendants.py brother
```

Prints, in one pass: what's loaded and from which sources, which trees contain
the word, the climb from that tree up to the topmost root, and the assembled
result. Read it top to bottom -- each section rules out one cause:

- **Nothing loaded** -> the tables were wiped by a rebuild (see the trap above).
- **`trees_containing` empty** -> the word's branch isn't downloaded. Check
  which family it belongs to before assuming a bug: a Latin-derived word has no
  descendants here until Proto-Italic is added.
- **Tree found but shallow** -> the splice failed. It joins on (lang, term) with
  the asterisk stripped; a mismatch in how the two pages spell the form breaks
  it. `parent_tree_of` returning None while a matching tree visibly exists is
  the signature.

## 3. Rules this feature must keep

- **Merging is display-only and structure-gated.** `_merge_variants` collapses
  sibling nodes ONLY when they share a language AND their subtrees are
  structurally identical -- which is what Wiktionary itself prints ("Old
  English: brōþor, brōþer, brōþur, brōðer, brōður" on one line). The payoff is
  large: `night` goes from 3,402 nodes to 84, because the raw tree holds only
  97 distinct forms, repeated up to 180 times under variant ancestors. **Never
  loosen this to merge by language alone** -- a variant with descendants the
  others lack would have its children silently reattached to a different
  spelling, which is a factual claim the source does not make.
- **Colour comes from the server.** Nodes are tagged with a palette slug via
  `bucket_for_name`, the same taxonomy the bar chart and Word Search use.
  Do not compute colours in JavaScript: a second copy of the taxonomy is free
  to drift, which is exactly what the 2026-07-24 one-database rule forbids.
- **The node budget is not decoration.** `*erþō` has 27,254 raw descendants.
  `NODE_BUDGET` prunes breadth-first so the top of the tree survives, and a cut
  node keeps a `pruned` count so the UI can say how many were dropped. Removing
  the budget ships a browser hang.
- **d3 stays vendored.** `static/d3.v7.min.js` is checked in. No CDN -- the app
  must work offline, and this is the project's only JS dependency.

## 4. Verifying a change

```
python scripts/verify.py
```

`test_regression.py`'s "Descendant trees" section covers the three things that
have actually broken during development: the tree must climb to the PIE root,
the splice must reach modern English through Proto-Germanic, and the variant
merge must not regress (checked by node count AND by asserting no duplicate
siblings survive). The section SKIPS rather than fails when the tables are
absent, so a checkout without the extracts still runs clean.

For anything visual, look at it -- `/descendants?word=brother` should read left
to right as PIE -> branch -> Proto-Germanic -> Old English -> Middle English ->
English, with the searched word ringed in the accent colour. A screenshot is
worth more than a passing assertion here, because the failures that matter
(overlapping labels, a tree opening off-screen) are invisible to the tests.
