---
name: etymology-regen
description: This skill should be used when code changes need to be applied to the live Etymology Analyzer data (e.g. "regenerate the database", "rebuild etymology.db", "run the pipeline again", "apply this fix to the data"), or after such a change when confirming nothing broke. Covers the canonical build (build_etymology_db.py / wiktextract_shapes.py / languages.csv / compounds.py) and the legacy gap-filler files.
disable-model-invocation: true
---

<!--
disable-model-invocation is set deliberately (2026-07-24 skill audit).
This isn't a literal deploy/commit/send-message action, but it carries the
same real-resource risk: a full run is a ~10-minute unattended operation that
overwrites the live database and requires stopping the running server. If
Claude auto-triggered this on a request that didn't actually need it, that's
a large, hard-to-notice waste, not a quick mistake to undo. User must invoke
this explicitly (`/etymology-regen`).

REWRITTEN 2026-07-26. The old version documented convert_wikt.py /
build_etymology_trees.py as THE pipeline. Those now build gap-filler files
only -- the app reads etymology.db first (see resolver.DbResolver and
app._tree_from_db). Following the old instructions would rebuild 16MB of
JSON nothing consults and leave the actual database untouched.
-->

# Regenerating the Etymology Analyzer database

## The whole loop, in one command

```powershell
powershell -File scripts\build.ps1              # build + verify
powershell -File scripts\build.ps1 -Sample 20000
powershell -File scripts\build.ps1 -Words mile father wolves
```

It warns if `app.py` is holding the database, clears any stale scratch build,
launches detached (a tool call would be killed at the 10-minute cap), polls
until done, prints only the lines worth reading, then runs `scripts\verify.py`.

```powershell
python scripts\verify.py            # just the checks, ~40s
python scripts\verify.py --db etymology.db.new    # before swapping in
python scripts\verify.py --skip-regression        # faster
```

`verify.py` prints FOUR lines and detail only for failures:

```
  PASS  invariants             12/12 checks passed
  FAIL  regression (legacy)    86/103 checks passed
  PASS  known words            14/14 correct
  PASS  tree/analyzer agree    14/14 contained
```

`known words` is a panel where each entry guards a bug that actually happened
(`wolves` resolving to the surname `Wolf`, `went` to the Japanese board game,
`mile`'s false PIE edge). Add a word whenever you fix one -- that is how the
panel stays worth running. The legacy suite reports but does not gate, because
it still asserts pre-rework behaviour in places.

The sections below are the manual steps those two scripts automate; read them
when something goes wrong, not to run a normal build.

`etymology.db` is the canonical store: one row per word, read through
`etymology_db.py` (the ONLY module that opens it) by both the paragraph
analyzer and the Word Search. Rebuilding it is one command; the traps are all
in the environment around it, and every one below was hit for real.

## 1. Stop the app FIRST

The build ends by swapping a freshly built file into place, and Windows will
not replace a file another process holds open. `app.py` opens `etymology.db`
at import, so a running server blocks the swap.

```powershell
powershell -File .claude\skills\etymology-regen\scripts\stop_dev_server.ps1
```

**`Get-Process python` returns nothing here** -- the Store build reports as
`python3.13`. Use this instead, and check the command line before killing
anything, since the user may have their own session open:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" |
  Select-Object ProcessId, CreationDate, CommandLine
```

If the swap is blocked anyway, the build does **not** discard its work: the
finished database is left at `etymology.db.new`, and renaming it is all that
remains.

## 2. Build

```powershell
cd "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
python build_etymology_db.py            # ~10 min, full corpus
python build_etymology_db.py --sample 20000    # fast dev copy
python build_etymology_db.py --words mile father wolves   # one-off check
```

Run it detached rather than through a foreground tool call -- background tool
invocations are capped at 10 minutes and will kill it just before it finishes:

```powershell
Start-Process python -ArgumentList "build_etymology_db.py" `
  -WorkingDirectory "C:\Users\Josep\Desktop\Etymology Project\etymology-app" `
  -RedirectStandardOutput out.log -RedirectStandardError err.log -WindowStyle Hidden
```

Note `--words` still streams the whole 3.2GB dump (~90s); it filters, it does
not seek.

**The build gates itself.** Four validators run before the swap -- no floating
nodes, exactly one head per etymology, no word marked `resolved` without a
solid edge, no surface form pointing at an empty word. On failure it exits 1
and leaves the build at `etymology.db.new` rather than replacing anything.

## 3. Verify

```powershell
python test_etymology_db.py                      # live database
python test_etymology_db.py etymology.db.new     # before swapping it in
```

12 structural invariants: floating nodes, dotted edges never traversed by
chain code, `additive_only` sources kept out of ancestry, relations never
appearing as ancestry edges, `March`/`march` staying distinct, and
`lineage()` emitting no invented adjacency.

Then the old suite, which still covers the legacy layer:

```powershell
python test_regression.py
```

For one word, `python scripts\check_word.py WORD` (shared with
`etymology-fix-word`) is faster than either.

## 4. Compare against the previous behaviour

Before trusting a structural change, triage every difference:

```powershell
python scripts\compare_db.py --sample 150000 --dump diff.tsv
```

Buckets: `lost_data` (the only one that blocks), `bucket_changed` /
`root_changed` (read by hand), `gained_data` / `unfloated`, `same`.

The script forces `ETYMOLOGY_DB=0` for the "old" side and asserts the legacy
stack isn't contaminated. **That assert exists because a run without it
silently compared the new layer against itself** -- 0.04% changed, and
meaningless.

## 5. Restart and smoke-test

```powershell
cd "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
python app.py   # background
powershell -File .claude\skills\etymology-regen\scripts\http_smoke_test.ps1 -Word "WORD"
```

## Kill switch

`ETYMOLOGY_DB=0` disables the database for BOTH the resolver and the tree,
falling back to the legacy files. Use it to isolate whether a problem comes
from the new layer.

## Legacy files (gap-fillers only)

These no longer feed the app first. They supply the ~151-per-150,000 words
that exist in etymology-db or Etymological Wordnet but not in the wiktextract
dump. Rebuild only when changing them specifically:

- `wikt_words.json` -- `python convert_wikt.py`, ~15-20 min. Also the source
  of the 22,317 auto-detected compound splits the canonical build imports.
- `etymology_trees.json` -- `python build_etymology_trees.py`, ~15-20 min.
- `inflections.json` -- `python build_inflections.py`, ~2-3 min. Must be
  current BEFORE the canonical build: `materialize_surface_forms` reads it.
- `word_info.json` -- `python build_word_info.py`, ~5-8 min.

## Traps worth knowing

- **A build that cannot start clean now aborts loudly.** It used to swallow a
  failed delete and append to the previous database, dying later on a
  duplicate-etymology error that pointed at the wrong place entirely.
- **Never read `cur.lastrowid` after `INSERT OR IGNORE`** without checking
  `cur.rowcount == 1`. On an ignored insert lastrowid holds the last
  successful insert on the connection -- usually a row in another table.
  (`rowcount` is `-1` when undeterminable, and `-1` is truthy.)
- **Lowercase-keyed dicts over `word` rows silently pick the proper noun.**
  `wolf`/`Wolf` collide; that is how `wolves` came to resolve to the surname
  and lose its Proto-Germanic ancestry. Prefer `headword == key_lower`.
- **PATH does not persist between tool calls** -- `git`/`gh` need it re-set in
  the same command. `python` does not.

## Additional resources

- `.claude\skills\etymology-regen\scripts\stop_dev_server.ps1` -- step 1.
- `.claude\skills\etymology-regen\scripts\http_smoke_test.ps1 -Word <word>` -- step 5.
- `scripts\check_word.py`, `scripts\compare_db.py` (project root).
- `etymology_schema.sql` -- the DDL, with the reasoning for each table.
