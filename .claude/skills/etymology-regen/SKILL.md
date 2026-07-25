---
name: etymology-regen
description: This skill should be used when code changes to convert_wikt.py, build_etymology_trees.py, resolver.py's data-consuming logic, corrections.py, compounds.py, or tree_corrections.py need to be applied to the live Etymology Analyzer data (e.g. "regenerate the database", "rebuild wikt_words.json", "run the pipeline again", "apply this fix to the data"), or after such a change when confirming nothing broke.
disable-model-invocation: true
---

<!--
disable-model-invocation is set deliberately (2026-07-24 skill audit).
This isn't a literal deploy/commit/send-message action, but it carries the
same real-resource risk: a full run is a 30-70 minute unattended operation
(two ~15-20 min full-database regenerations plus verification) that also
kills and restarts a live server process. If Claude auto-triggered this on
a request that didn't actually need it, that's a large, hard-to-notice
waste, not a quick mistake to undo. User must invoke this explicitly
(`/etymology-regen`) rather than Claude deciding on its own that a regen is
warranted.
-->

# Regenerating the Etymology Analyzer database

The pipeline (`C:\Users\Josep\Desktop\Etymology Project\etymology-app`) has
two independently-buildable data files with different rebuild triggers, plus
a fixed verify-and-restart sequence. Follow this order -- skipping the
verification step or restarting the server before regeneration finishes are
the two ways this has gone wrong before.

## PowerShell environment note

Environment variable changes (PATH) do **not** persist between separate
tool invocations in this shell -- every command that needs `git`/`gh` must
re-set PATH in the SAME command:

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

`python`/`pip` do not need this (already on the base PATH); only `git`/`gh`
do.

## 1. Decide which file(s) actually need rebuilding

- **`wikt_words.json`** (via `python convert_wikt.py`) -- needed for ANY
  change to `convert_wikt.py` itself, or to `corrections.py`/`compounds.py`
  (both are applied inside `convert_wikt.py`'s `main()` before the
  inheritance patches run, as well as at `WiktionaryResolver` load time --
  see that resolver's docstring). Takes **~15-20 minutes**.
- **`etymology_trees.json`** (via `python build_etymology_trees.py`) --
  needed if `build_etymology_trees.py` ITSELF changed, OR `tree_corrections.py`
  changed, OR a function `build_etymology_trees.py` imports from
  `convert_wikt.py` changed (check its import line: currently
  `ANCESTRY_RELS, ROOT_RELS, GROUP_MARKER_RELS, NON_DONOR_LANGS,
  PARQUET_PATH, _depth_hint`). A `corrections.py`/`compounds.py`-only change
  does NOT require this -- those aren't read by the tree builder at all.
  Also takes **~15-20 minutes**.
  - **Before rebuilding, back up the current `etymology_trees.json`** (16MB,
    a plain `Copy-Item` to a scratch path) whenever the change alters tree
    STRUCTURE rather than just adding/fixing one word. The rebuild
    overwrites in place, and having the previous file is what makes a real
    before/after diff possible -- that diff is how the 2026-07-24 dedup
    change proved it dropped only redundant branches and never lost a
    multi-node branch or fabricated one. Without the baseline you can only
    check that the new file looks reasonable, not that nothing regressed.

- **`inflections.json`** (via `python build_inflections.py`) -- needed if
  `build_inflections.py` changed or the wiktextract dump was refreshed.
  **~2-3 minutes.** Note this reads the **wiktextract JSONL dump**
  (`Etymology Project\wiktextract_data\`), NOT the parquet. **Order matters:**
  `convert_wikt.py` imports `inflection_candidates` and uses it at build time,
  so `inflections.json` must exist and be current BEFORE regenerating
  `wikt_words.json`, or the inheritance bridge (`unheard`->`hear`) silently
  degrades.
- **`word_info.json`** (via `python build_word_info.py`) -- definitions, part
  of speech, cognates, doublets. **~5-8 minutes.** Reads BOTH the wiktextract
  dump and the parquet, and scopes itself to words present in
  `wikt_words.json`/`wiktextract_words.json` -- so regenerate it AFTER either
  of those changes, or newly-added words will have no definition.

The two etymology converters read the raw parquet fresh each run (~2 seconds)
and do a full 364,161-term pass -- there is no incremental/partial regen. Run each in the
background and poll rather than blocking, and don't assume a timeout under
~15 minutes means it hung. Deciding WHICH of the two to run is a judgment
call based on what actually changed -- not scripted, since it depends on
reading the diff.

```powershell
cd "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
python convert_wikt.py 2>&1          # background, ~15-20 min
python build_etymology_trees.py 2>&1 # background, ~15-20 min, only if needed
```

## 2. Run the regression check

```powershell
python test_regression.py
```

Plain script (no pytest dependency) covering the historical verified-word
suite, known multi-sense-collision corrections, the compound-display
feature, the case-fallback guard, the bare-root-stub guard, and
tree/analyzer consistency. Prints PASS/FAIL per check and exits non-zero on
any failure -- do not proceed to restarting the server if anything fails.
Investigate failures before continuing; a regen that regresses a
previously-fixed word means something in the change was too broad (see
`CLAUDE.md`'s known issues for examples of this happening and how it was
caught, e.g. the `_is_reliable_root` safety filter).

For a quick pre-check on a single word without running the full suite,
`scripts\check_word.py` (project root, shared with the `etymology-fix-word`
skill) gives the same answer faster.

## 3. Restart the local Flask dev server

```powershell
powershell -File .claude\skills\etymology-regen\scripts\stop_dev_server.ps1
```

Deterministic -- finds whatever's genuinely `Listen`-ing on port 5000, stops
it, and confirms the port is actually free before reporting success. Filters
out two Windows table-entry artifacts confirmed while writing this script
(not just documented, actually reproduced): a stale `Listen` row can outlive
its already-dead owning process for several seconds, and an unrelated
`TimeWait` row can report `OwningProcess = 0` (the System Idle Process,
never a real server) -- neither should be treated as "still running."

Then start fresh in the background (this step stays a direct background
tool invocation, not a bundled script, so the harness can track it as a
long-running process rather than a fire-and-forget daemon):

```powershell
cd "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
python app.py   # background
```

## 4. Live end-to-end check

```powershell
powershell -File .claude\skills\etymology-regen\scripts\http_smoke_test.ps1 -Word "WORD"
```

Deterministic mechanics (POST, status check, response parsing); the one
judgment call left is WHICH word to pass -- use whatever word the change was
actually about. Don't declare the regen done on the regression script alone;
this is the real HTTP round-trip through Flask and the templates, not just
the resolver layer.

## Additional resources

- `.claude\skills\etymology-regen\scripts\stop_dev_server.ps1` -- step 3.
- `.claude\skills\etymology-regen\scripts\http_smoke_test.ps1 -Word <word>` -- step 4.
- `scripts\check_word.py` (project root -- shared with the `etymology-fix-word`
  skill, not duplicated here) -- optional fast single-word pre-check,
  referenced in step 2. All paths above are relative to the project root
  (`C:\Users\Josep\Desktop\Etymology Project\etymology-app`).
