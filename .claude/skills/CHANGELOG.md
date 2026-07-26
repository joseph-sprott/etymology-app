# Skills changelog

Every change to any skill in this directory, logged here as it happens --
requested by Joe 2026-07-24 ("continuously be updating each skill after you
use them ... keep a log"). Newest entries first. Each entry: date, skill,
what changed, why (what using the skill revealed, or what prompted the
change).

---

## 2026-07-26 (handoff edits, applied 2026-07-26)

Two edits queued at the end of the etymology.db rework session and blocked
only by background-session isolation. Applied from `HANDOFF.md` verbatim
except where noted.

**Updated `etymology-fix-word`** — found by running the `etymology-skill-audit`
checklist: a **composability** gap. `scripts/verify.py`'s known-word panel is
the natural home for every word-level fix, but only `etymology-regen`
referenced it, so a word fixed via this skill would never enter the panel and
the next regression would find it the hard way. New step 5 ("Lock the fix in")
documents the `PANEL` dict and its three value shapes (a donor language,
`None` for must-stay-native, `"*"` for any-foreign-donor), and states the
convention that earns the panel its keep: every entry is a bug that ACTUALLY
occurred. The old steps 5/6 renumbered to 6/7. Step 6 (the tree-entry rule)
also gained a scope caveat at the top: it now applies only to a legacy
`corrections.py` fix — a word answered from `etymology.db` reads the same rows
through `etymology_db.py` for both the analyzer and the tree, so there is
nothing to mirror.

**Updated `CLAUDE.md`** (not a skill, logged here because it was the other half
of the same handoff) — added a "READ THIS FIRST" section immediately above
"Current state", because CLAUDE.md still presented `convert_wikt.py` /
`wikt_words.json` as the live pipeline; a session following it would rebuild
files nothing reads first, the same trap already fixed in `etymology-regen`.
Inserted, not replaced — the existing history is valuable and is now marked
historical rather than deleted. The Architecture table gained the five modules
the rework added. One deviation from the handoff text: it ended with "See
known issue #18 for what changed and why", but CLAUDE.md's known issues stop
at #17 and commit `8711878` didn't touch CLAUDE.md, so #18 does not exist —
pointed the reader at that commit instead rather than leave a dangling
reference.

---

## 2026-07-26 (later)

**New `scripts/verify.py` + `scripts/build.ps1`, wired into `etymology-regen`.**
Joe called this out directly, and he was right: the build-verify-diagnose loop
ran TEN times during the rework and was hand-assembled every time, dumping
several screens of output on each pass. That is slow, expensive (every stats
block stays in context permanently), and exactly the repeating pattern I am
supposed to turn into a script without being asked.

- `verify.py` runs invariants + legacy suite + a known-word panel + the
  tree/analyzer containment check, and prints FOUR lines plus detail only for
  failures. It replaced three separate commands and roughly a screen of output
  per run with a summary. It earned its keep on first run by catching that
  `went` still resolved to the Japanese board game ç¢.
- The known-word panel is the durable part: each entry records a bug that
  actually occurred, so the panel is a list of things that have gone wrong
  rather than a list of words someone liked. Convention: add a word whenever
  a word-level bug is fixed.
- `build.ps1` encodes the traps that each cost a full ten-minute build --
  detached launch (tool calls die at the 10-minute cap), CIM process lookup
  (`Get-Process python` finds nothing), stale `.new` cleanup, and the blocked-
  swap message.

**Lesson worth keeping:** the trigger for writing a script is the SECOND time
a multi-step sequence is typed, not the tenth. I noticed the repetition each
time and kept going anyway because each individual run felt cheap.

---

## 2026-07-26

**Rewrote `etymology-regen`** — it had become actively harmful, not merely
stale. It documented `convert_wikt.py` / `build_etymology_trees.py` as THE
pipeline; after the etymology.db rework those build gap-filler files the app
consults second. A session following it would have spent ~40 minutes
rebuilding 16MB of JSON nothing reads and never touched the real database.
Rewritten around `build_etymology_db.py`, with the legacy files demoted to a
clearly-labelled gap-filler section. Encoded the operational traps that cost
real time during the rework, none of which are guessable from the code:
stop the app before building (the atomic swap cannot replace a file a process
holds open); `Get-Process python` finds nothing because the Store build
reports as `python3.13`; run the build detached because background tool calls
cap at 10 minutes and killed one at 9:50; never read `cur.lastrowid` after
`INSERT OR IGNORE` without checking `rowcount == 1`; lowercase-keyed dicts
over `word` rows silently select the proper-noun homograph.

**Updated `etymology-coverage-scan`** — two of its documented gap categories
were made obsolete by the rework and would have sent a future session hunting
for already-fixed bugs: the hand-maintained `_IRREGULAR_FORMS` table is
deleted (inflections are now 361,995 tagged forms + 1,117,563 generated ones
materialized into `surface_form`), and the wolf/wolves f/v shift it named as
an open gap is covered. Also drew the line between this skill and
`scripts/compare_db.py`: coverage-scan answers "what are we still missing",
compare_db answers "did this change make anything worse". They had been
blurring together.

**Updated `etymology-fix-word`** + **new `scripts/check_db_word.py`** — step 1
pointed at the legacy parquet. The new script prints the three views that
matter side by side (raw dump templates / stored tree / what each feature
shows), because the same ad-hoc diagnostic was hand-written three times during
one session, which is the signal to make it a script. The skill's opening now
states the pattern those investigations shared: the bug is nearly always in
the step BETWEEN the dump, the builder and the lookup, not inside any one of
them — `mile` was a builder bug, `father` a dump-reading bug, `wolves` a
lookup bug whose tree and chain were both perfectly correct.

**Discovery problem worth recording:** these skills live in
`etymology-app/.claude/skills/`, but a session whose working directory is the
parent (`Etymology Project/`) or a sibling never registers them — `Skill`
reports "Unknown skill" and they are invisible for the whole session. That is
why none fired during the rework despite several being applicable. Worth
either launching sessions from `etymology-app/` or promoting these to the user
scope.

---

## 2026-07-25

**Updated `etymology-regen`** — its "which file needs rebuilding" list didn't
mention `inflections.json` or `word_info.json`, both added today, nor
`build_inflections.py`/`build_word_info.py` as triggers. Added them with their
real runtimes and the fact that they read the wiktextract dump rather than the
parquet (a different input from every other build step, so the existing
"reads the raw parquet fresh each run" note was actively misleading for these
two). Also recorded that `convert_wikt.py` now depends on `inflections.json`
existing at build time, so the two must be regenerated in order.

**Updated `etymology-fix-word`** — added a "both tools must agree at runtime"
verification step, prompted by Joe's report that "intrude" showed Latin in the
analyzer but not in Word Search. The skill already said to edit BOTH
`corrections.py` and `tree_corrections.py`, but that's necessary-not-
sufficient: the two features read different stores, so a word can diverge
without either file being wrong (here, the tree builder had no knowledge of
the wiktextract backend added the day before — 1,736 words affected, no test
caught it). The new step gives the exact two commands to compare and, more
importantly, says that a mismatch of this shape is STRUCTURAL and must not be
papered over with a per-word `tree_corrections.py` entry, which would hide the
whole class behind one word.

**Fixed a real flaw in `etymology-skill-audit`'s own `list_skills.py`** — it
reported `scripts: (none)` for `etymology-fix-word` and
`etymology-coverage-scan`, which was wrong and actively misleading: both have
had `check_word.py`/`check_raw_data.py` since they were written, kept at the
project root because that's this project's convention for a script two or
more skills share. A future session trusting "(none)" would rebuild tooling
that already exists — precisely the duplication the composability dimension
exists to catch, produced by the audit tool itself. Now scans each SKILL.md
for referenced project-root scripts and reports them on a `shared:` line.

**Discipline note (no skill change):** the `etymology-fix-word` skill's
methodology held up again — the "dry-run before deleting" habit it encodes
caught a real error today. The plan called for deleting 6 "redundant" plural
entries from `compounds.py`; simulating the deletion first showed 4 of them
(`foothills`, `downsides`, `earlobes`, `crossroads`) would regress to Unknown,
because the resolver's retry loop calls `_try()` (backends only) and never
consults the compound table. Deleting them on the plan's say-so would have
shipped a silent regression that no existing test covered.

## 2026-07-24 (tree dedup pass)

**Updated `etymology-regen`** — found a real gap while using it for the tree
duplicate-branch fix: its "which file needs rebuilding" list named
`tree_corrections.py` and `convert_wikt.py`-imported functions as triggers
for `build_etymology_trees.py`, but never the obvious third case — a change
to `build_etymology_trees.py` ITSELF, which is exactly what that task was.
Added it, plus a new sub-point telling the agent to BACK UP the existing
16MB `etymology_trees.json` before any structure-altering rebuild: the
rebuild overwrites in place, and the before/after diff is the only thing
that can actually prove a structural change didn't silently drop or
fabricate branches (it's what verified the dedup change dropped exactly
1,487 redundant branches and zero multi-node ones). Learned by doing it —
the backup was taken by instinct on this task and turned out to be the
load-bearing piece of the verification.

## 2026-07-24 (later)

**Created `etymology-parallel-sync`** — packages the backup-then-pull-then-
diff-verify sequence used by hand earlier the same session when a parallel
agent's worktree pushed `FUTURE_FEATURES_AND_RESOURCES.md` at a path that
already existed locally, untracked. Left auto-invocable (unlike
`etymology-commit-push`) since it only touches local repo state — fetch plus
a `--ff-only` pull, never `--force`, always backs up before overwriting
anything.

Found and fixed a real bug in `sync_worktree_research.ps1` while testing it
against the live repo (not just reading it back): `$ErrorActionPreference =
"Stop"` at the top of the script combined with `git fetch`'s routine stderr
output (e.g. "From https://...", printed even on success) caused PowerShell
5.1 to promote that non-terminating stderr text into a terminating error and
kill the script on a clean run. Fixed by dropping `$ErrorActionPreference =
"Stop"` entirely and checking `$LASTEXITCODE` explicitly after each git
command instead of relying on `$?` — same underlying pitfall already
documented in this project's PowerShell environment notes, now also fixed in
a script instead of just worked around inline each time.

**Created `etymology-skill-audit`** — codifies the three-dimension checklist
(visibility / deterministic-vs-non-deterministic / composability) Joe set
verbatim earlier in the session, so it's applied consistently to every new
skill going forward instead of being re-derived from memory each time.
`scripts/list_skills.py` handles the deterministic discovery pass (enumerate
skills, parse frontmatter, flag auto-invocable skills whose description
mentions a high-risk verb without `disable-model-invocation` set); the
skill's own body carries the judgment part (deciding whether a flag is real,
applying the composability check, deciding what to extract).

## 2026-07-24

**Created `etymology-coverage-scan`** — wraps `scripts/scan_unknown_words.py`
for future broad coverage audits (as opposed to `etymology-fix-word`'s
single-reported-word scope). Points at `etymology-fix-word`'s
`check_word.py`/`check_raw_data.py` for the diagnosis phase rather than
duplicating that logic. Documents the `randomwordgenerator.com` JS-only
page / static-JSON-underneath finding so it doesn't need re-discovering
next time.

**Created `etymology-commit-push`** — packages the git add/commit/push
sequence used successfully throughout the session (message-file + `-F`,
not `-m`, after a here-string quoting failure earlier in the session).
`disable-model-invocation: true` set from the start — commit/push is
literally one of the three named high-risk-side-effect categories from the
audit (deploy, commit, send messages).

**Audited and rewrote `etymology-fix-word` and `etymology-regen`** against
three dimensions Joe specified (visibility / deterministic-vs-AI /
composability):
- `etymology-regen` gained `disable-model-invocation: true` — not a literal
  deploy/commit/send, but same real-resource-risk shape (30-70 min
  unattended, restarts a live process). `etymology-fix-word` stayed
  auto-invocable (only edits local files, no external effect, and gating it
  would undercut the "notice and fix a reported word" pattern this project
  relies on).
- Extracted three inline snippets into real scripts: `scripts/check_word.py`,
  `scripts/check_raw_data.py` (project-level, shared between both skills --
  found the two skills would otherwise reinvent slightly different versions
  of the same capability), and `etymology-regen/scripts/{stop_dev_server,
  http_smoke_test}.ps1`.
- Found and fixed a real bug in `stop_dev_server.ps1` while testing it
  against the actual running server (not just reading it back): it didn't
  filter by connection `State`, so a stale dead-PID `Listen` row and an
  unrelated `TimeWait` row reporting `OwningProcess = 0` (System Idle
  Process) both got misread as "still running." Fixed by only trusting
  `State=Listen` rows.

**Used `etymology-fix-word`'s methodology (not literally the skill trigger,
already mid-session with full context) for the issue #17 347-paragraph
coverage scan and fix.** Noted here since it's the first real stress-test of
the skill's own instructions across ~15 words and several structural code
changes, not just the two words (`tag`/`auto`) it was originally written
from. The instructions held up without needing a rewrite -- no skill change
logged for this pass, but flagging that it was exercised at real scale.

**Self-noted gap, not yet fixed:** while executing the issue #17 fix,
`check_word.py`/`check_raw_data.py` were used at the start of the
investigation but NOT consistently for later checks (`unfamiliar`, `mom`,
`package`, the `un-` bound-morpheme investigation, `taxicab` debugging) --
fresh one-off scripts got written in the job tmp folder instead of reusing
the committed ones for the same underlying task. Caught when Joe asked
directly "are you using those skills/scripts?". No skill content change
needed (the scripts are fine) -- this is a discipline note for future
sessions: reach for the existing script before writing a new one for the
same check.

---

## 2026-07-24 (earlier)

**Created `etymology-fix-word`** — packages the word-verification/correction
workflow (reproduce -> check raw parquet -> verify live Wiktionary -> decide
fix shape -> always update both `corrections.py` and `tree_corrections.py`)
first exercised on `tag`/`auto`/`generate`/`meltdown`/`seen` earlier the same
session.

**Created `etymology-regen`** — packages the database regeneration +
verification procedure (which file(s) need rebuilding, the PowerShell PATH
quirk, the port-5000 restart quirk, running the regression check before
trusting a regen).
