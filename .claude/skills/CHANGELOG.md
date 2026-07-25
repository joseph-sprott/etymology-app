# Skills changelog

Every change to any skill in this directory, logged here as it happens --
requested by Joe 2026-07-24 ("continuously be updating each skill after you
use them ... keep a log"). Newest entries first. Each entry: date, skill,
what changed, why (what using the skill revealed, or what prompted the
change).

---

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
