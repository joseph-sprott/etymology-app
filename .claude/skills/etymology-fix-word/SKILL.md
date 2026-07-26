---
name: etymology-fix-word
description: This skill should be used when the user reports a word in the Etymology Analyzer showing a wrong, unexpected, or missing origin (e.g. "why does X show Y", "X reads Unknown but shouldn't", "fix the etymology for X"), or asks to verify/correct a specific word's etymology in this project. Not for broad database-wide coverage changes or code refactors -- those are a design decision, not a single-word verification.
---

# Fixing a single word's etymology

Verifying and correcting one word's etymology in the Etymology Analyzer
(`C:\Users\Josep\Desktop\Etymology Project\etymology-app`) always follows the
same investigative sequence. Do not skip straight to writing a correction --
this project's rule 2 (see `CLAUDE.md`) is "do not guess or assume, verify
with real resources," and every prior fix in this codebase followed exactly
this sequence.

## 1. Reproduce the current answer

Since the 2026-07-26 rework the canonical store is `etymology.db`, so start
here -- it prints, side by side, what the dump gave us, what the builder made
of it, and what each feature will show:

```
python scripts\check_db_word.py WORD
python scripts\check_db_word.py WORD --raw    # + the dump's own templates
```

Read it in that order, because **the bug is nearly always in the step BETWEEN
two of those, not inside any one of them**. Every tree bug found so far had
this shape:

- `mile` -- templates fine, tree drew Middle English -> PIE with Latin
  floating beside it (builder step).
- `father` -- templates named ONE step; the rest of the chain was only in the
  rendered text, so the tree was a 2-node stub (dump-reading step).
- `wolves` -- tree and chain both fine, but the word resolved to the surname
  `Wolf` instead of `wolf` (lookup step). **Always check the `resolved to:`
  line first** -- a wrong headword makes every other line correct-but-
  irrelevant, which is exactly why it hid for so long.

Then the legacy view, still worth running because the file backends remain as
gap-fillers and the two can disagree:

```
python scripts\check_word.py WORD
```

Prints the bucket for all three modes (direct/influence/root), or `split:
part=bucket + part=bucket` if the word already resolves via a compound
split -- if so, the fix (if any is needed) belongs in step 4's compound
branch, not `corrections.py`.

## 2. Diagnose against the raw source data

Never guess why a word is wrong -- check what Wiktionary's own data actually
says:

```
python scripts\check_raw_data.py WORD
```

Prints every raw relation row for that term (`reltype`, `related_lang`,
`related_term`, `group_tag`, `parent_tag`, `parent_position`), or says
plainly if the term has no raw entry at all.

Three shapes have accounted for every bug found in this project so far --
check which one this is before deciding a fix:

- **Multi-sense collision**: the term_id's raw rows cover an unrelated sense
  sharing the same spelling (e.g. `tag`'s common "label" sense vs. an obscure
  Aramaic "crown" sense; `die`/`bull`/`and`/`low` are the same shape). Look
  for a row set that clearly doesn't match the sense the user means.
- **Case-fallback homograph**: the word has NO lowercase entry at all
  (`check_raw_data.py` says so), and `WiktionaryResolver` silently fell back
  to an unrelated capitalized entry (e.g. `ran` -> `Ran`, a Japanese-related
  entry; historically `went` -> `Went`, a surname).
- **Hedge-only relation**: the only rows present are `etymologically_related_to`
  (or `cognate_of`/`doublet_with`) -- these are NOT real ancestry, just a
  "see also" hint (e.g. `meltdown`'s only row is `etymologically_related_to
  "melt down"`, not a real `compound_of`). A word with only these relations
  has no real chain in the data at all, regardless of how obvious the answer
  seems.

## 3. Verify against live Wiktionary

Before writing anything, fetch the live page and confirm the real etymology
directly -- do not trust the raw parquet snapshot alone (it can be stale or
incomplete), and do not trust general knowledge alone either:

```
WebFetch: https://en.wiktionary.org/wiki/WORD
Prompt: "List every distinct Etymology heading with its part of speech and
full donor-language chain, including any PIE root if mentioned."
```

If the word has multiple Etymology sections, identify which one matches the
sense actually in use, and note whether the raw data (step 2) captured that
section or a different one.

## 4. Decide the fix shape and write it

- **Wrong or missing chain for a real word** -> add an entry to
  `corrections.py`'s `WORD_CORRECTIONS` dict, matching the exact shape
  already used throughout that file:
  ```python
  "word": {"p": "Bucket", "d": "DeepestBucket", "chain": ["Bucket", "DeepestBucket"],
           "prox_kind": "inherited" | "borrowed" | "derived",
           "root_lang": "Specific Language Name", "root_term": "spelling", "root_pie": True | False},
  ```
  `chain` is deduped, ordered proximate -> deepest, foreign donors only
  (English stages are implicit). `root_pie` is only `True` if the live page
  itself states a further PIE connection -- never infer one.
- **Genuinely a two-word compound with no ancestry data of its own** -> add
  to `compounds.py`'s `COMPOUND_SPLITS` dict: `'word': ('part1', 'part2')`.
  Only do this if both parts already resolve on their own (check step 1
  against each part first).
- **A "hub" word whose own correct standalone answer is a genuinely
  different sense than what OTHER words derive from it** (rare -- see
  `logy`/`poly` in `corrections.py`'s `HUB_EXCLUSIONS` for the pattern) ->
  add the word to `HUB_EXCLUSIONS` instead of `WORD_CORRECTIONS`.

Write a comment above the new entry citing what was checked (the live page
content, the raw-data root cause) -- every existing entry in both files
follows this convention, and it's what lets a future fix understand why the
override exists instead of assuming it's stale.

## 5. Always add the matching tree entry -- never skip this

This project has an explicit, repeatedly-stated rule: every feature that
surfaces word-level data must show the same answer. A `corrections.py`-only
fix is not a complete fix -- the Etymology Tree feature reads a SEPARATE
file (`etymology_trees.json`) and will keep showing the old/wrong data until
`tree_corrections.py` also has a matching entry:

```python
"word": [
    {"lang": "Language", "term": "spelling", "reltype": "inherited_from" | "derived_from" | "borrowed_from" | "has_root",
     "children": [ ... same shape, nested for each deeper step ... ]},
],
```

This should mirror the exact chain just written into `corrections.py`,
including specific attested spellings from the live Wiktionary page (step 3),
not just bucket names.

If the word is a compound handled via `compounds.py` instead, no
`tree_corrections.py` entry is needed -- `app.py`'s `resolve_tree()` already
falls back to the resolver's compound-split data automatically for any word
without its own tree, via the `RESOLVER.resolve(word).compound_parts`
mechanism (see that function's docstring in `app.py` for the full "why").

## 6. Verify, and know what's verified vs. not yet

- `corrections.py`/`compounds.py`/`HUB_EXCLUSIONS` changes take effect
  immediately (`WiktionaryResolver` applies them at load time) -- just
  re-run `python scripts\check_word.py WORD` to confirm the analyzer now
  shows the right answer. No regeneration needed.
- `tree_corrections.py` changes do NOT take effect until
  `build_etymology_trees.py` is re-run (~15-20 minutes) -- that file bakes
  `TREE_CORRECTIONS` into `etymology_trees.json` at build time, it isn't
  read live. Don't report a tree fix as verified until that regen has
  actually run. See the `etymology-regen` skill for how to run it safely.
- **Always check BOTH tools agree at runtime, not just that both files were
  edited.** Added 2026-07-25 after Joe reported "intrude doesn't show that
  it's from Latin when using word search -- why are the two tools not
  agreeing?". Editing both files is necessary but NOT sufficient: the two
  features read different stores, and a word can diverge without either file
  being wrong. In that case `etymology_trees.json` held a bare `has_root` PIE
  pointer for "intrude" while the analyzer had a full Latin chain from a
  newer backend the tree builder knows nothing about -- 1,736 words were
  affected and no test caught it. Run:

  ```powershell
  python scripts\check_word.py WORD          # what the analyzer says
  python -c "import app, json; print(json.dumps(app.resolve_tree('WORD'), ensure_ascii=False))"
  ```

  and confirm the donor language the analyzer names actually appears in the
  tree. If it doesn't, the bug is structural (one feature can't see data the
  other can) -- fix that, don't paper over it with a per-word
  `tree_corrections.py` entry, which would hide the class behind one word.
  `test_regression.py`'s "Tree and analyzer must agree" section guards this.
- If the fix looks like it could affect more than just this one word (e.g.
  it points at a root/pattern many other words might share), that's a
  bigger design decision than this skill covers -- flag it rather than
  silently expanding scope.

## Additional resources

- `scripts/check_word.py` (project root, shared with the `etymology-regen`
  skill) -- deterministic resolver check, steps 1 and 6.
- `scripts/check_raw_data.py` (project root, shared) -- deterministic raw
  parquet row dump, step 2.
