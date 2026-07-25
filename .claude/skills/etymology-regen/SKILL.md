---
name: etymology-regen
description: This skill should be used when code changes to convert_wikt.py, build_etymology_trees.py, resolver.py's data-consuming logic, corrections.py, compounds.py, or tree_corrections.py need to be applied to the live Etymology Analyzer data (e.g. "regenerate the database", "rebuild wikt_words.json", "run the pipeline again", "apply this fix to the data"), or after such a change when confirming nothing broke.
---

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
  needed only if `tree_corrections.py` changed, OR a function
  `build_etymology_trees.py` imports from `convert_wikt.py` changed (check
  its import line: currently `ANCESTRY_RELS, ROOT_RELS, GROUP_MARKER_RELS,
  NON_DONOR_LANGS, PARQUET_PATH, _depth_hint`). A `corrections.py`/
  `compounds.py`-only change does NOT require this -- those aren't read by
  the tree builder at all. Also takes **~15-20 minutes**.

Both scripts read the raw parquet fresh each run (~2 seconds) and do a full
364,161-term pass -- there is no incremental/partial regen. Run each in the
background and poll rather than blocking, and don't assume a timeout under
~15 minutes means it hung.

```powershell
cd "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
python convert_wikt.py 2>&1          # background, ~15-20 min
python build_etymology_trees.py 2>&1 # background, ~15-20 min, only if needed
```

## 2. Run the regression check

```powershell
python test_regression.py
```

This is a plain script (no pytest dependency) covering the historical
verified-word suite, known multi-sense-collision corrections, the
compound-display feature, the case-fallback guard, the bare-root-stub guard,
and tree/analyzer consistency. It prints PASS/FAIL per check and exits
non-zero on any failure -- do not proceed to restarting the server if
anything fails. Investigate failures before continuing; a regen that
regresses a previously-fixed word means something in the change was too
broad (see `CLAUDE.md`'s known issues for examples of this happening and
how it was caught, e.g. the `_is_reliable_root` safety filter).

## 3. Restart the local Flask dev server

Port 5000 has a documented Windows quirk: a stale socket entry can report
LISTENING for several seconds after the owning process is actually dead.
Don't loop waiting for the port to report free -- confirm the PID is dead,
then start the new process directly.

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object OwningProcess
```

Stop that PID (`Stop-Process -Id <pid> -Force`), confirm it's gone
(`Get-Process -Id <pid>` should error), then start fresh in the background:

```powershell
cd "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
python app.py   # background
```

Werkzeug's debug-mode reloader spawns a child process -- if a single
`Stop-Process` doesn't fully free the port, re-check
`Get-NetTCPConnection` for whatever PID it now reports rather than assuming
the original parent PID is the only one involved.

## 4. Live end-to-end check

Don't declare the regen done on the regression script alone -- do one real
HTTP round-trip against the word(s) the change was actually about:

```powershell
Invoke-WebRequest -Uri "http://localhost:5000/" -Method Post -Body @{form="analyze"; text="the word(s) in question"; mode="direct"; word_sort="input"} -UseBasicParsing
```

Confirm a 200 status and that the per-word output shows the expected
bucket/split before reporting the change as verified.
