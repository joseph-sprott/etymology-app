# CLAUDE.md — Etymology Analyzer Project

> ### 📖 There is a second file: `HISTORY.md`. Read it before you change anything non-trivial.
>
> This file is the **working summary**. `HISTORY.md` is the **full record** —
> every known issue's complete narrative, and, more importantly, **every
> approach that was already tried and failed.** It is not loaded into your
> context automatically, so you have to open it. Joe should not have to remind
> you; that is what this box is for.
>
> **Open it when:** an issue entry below looks thin and you need the reasoning;
> you are about to "fix" something that looks obviously improvable; you are
> touching multi-sense collisions, chain ordering, tree branch merging, root
> inheritance, or the compound/affix split; or you catch yourself thinking
> *"why on earth is it done this way?"* — that question is almost always
> answered there.
>
> **Why it matters:** at least six documented dead ends live in that file
> (two multi-sense auto-split heuristics, two tree-merge attempts, chain
> segmentation on English-stage restarts, and a root-inheritance rule that
> pulled from bound morphemes). Each was tried against real data, broke real
> words, and was reverted. Re-deriving any of them costs hours and a database
> rebuild. It is cheaper to read than to rediscover.

## Where things are — read this INSTEAD of grepping

Line numbers drift; the file and function names don't. Jump straight to these
rather than opening a 1,000-line module to find out where something lives.
Added 2026-07-27 because exploration — greps, then reading whole files to
locate one function — is the single biggest avoidable token cost in a session.

| I need to… | Go to |
|---|---|
| change how a word's ORIGIN is decided | `resolver.py` → `DbResolver._resolve` (~620-823) |
| change fallbacks (inflection, stem, compound) | `resolver.py` → `ChainResolver.resolve` (~831-1039) |
| change what Direct/Influence/Root MEAN | `resolver.py` → `Resolution.view` (~150-290) |
| read the database | `etymology_db.py` → `Db` (~213-537); `_lineage` (~353-398) is the chain walk |
| change the upward TREE | `word_trees.py` → `resolve_tree` (~256-354), `_tree_from_db` (~122-202) |
| change the tree DIAGRAM layout | `word_trees.py` → `build_diagram` (~482-547) |
| change the DOWNWARD (descendants) tree | `descendants.py` → `full_tree` (~220-265) |
| change percentages / tokenizing | `analyzer.py` (211 lines, all of it) |
| change a COLOUR or bucket slug | `palette.py` — never inline in `app.py` |
| change page markup | `app.py` → `PAGE` / `DESC_PAGE` template strings |
| add a language → bucket mapping | `buckets_wikt.py` → `NAME_TO_BUCKET` |
| resolve a raw language code | `language_codes.py` |
| ask "is this an English stage / proto / affix?" | `linguistics.py` — **never write the test yourself** |
| write a new script in `scripts/` | start with `import scriptlib; scriptlib.bootstrap()` — never hand-roll `sys.path` or a data path |
| read the dump | `wiktextract_dump.py` → `stream_english_entries` |
| parse dump templates | `wiktextract_shapes.py` (four shapes, one per section) |
| know WHY something is the way it is | `HISTORY.md` |

**Before running anything expensive**: `python test_units.py` is ~1s and 339
checks. `python scripts/verify.py` is ~40s and prints five lines. Prefer the
first while iterating; run the second before you report done.

## Working rules (read first — these come from Joe and are non-negotiable)

1. **Just do it. Stop asking for approval.** Said once 2026-07-22, had to repeat it the same night — take it seriously. Make the call yourself (which approach, what to check, how to scope a fix, UI/design choices) and report what you did and why *after*, not before. Don't use a multiple-choice question tool for this — that's still an approval gate wearing a different UI.

   **Refined 2026-07-24** (violated a third time: asked via a multiple-choice question tool for the new GitHub repo's visibility/scope/name when creating it — those were steps toward something Joe had already asked for, not a real fork in the road). The core rule: **never ask Joe to approve or perform a step that's simply needed to reach a place he's already asked for or approved.** Decide the mechanical stuff yourself (repo name, which file goes where, which library, UI/visual details, how to scope a fix) and report after.

   **What DOES warrant asking him** (his own words, 2026-07-24):
   - A **specific design choice** with a real, non-obvious tradeoff — not "which name" but something shaping the product, e.g. known issue #14's still-open (a)/(b)/(c) fork (stay strict "verified fact only" vs. add a flagged lower-confidence tier vs. find another data source) — that's a philosophy change, not an implementation detail.
   - An **objective decision that isn't obvious** — a real fork where reasonable people could land differently and the "right" answer isn't derivable from what Joe's already said.
   - Anything **you're genuinely unsure about or don't have full clarity on** — don't guess past a real gap in understanding just to avoid asking (this doesn't relax rule 2 below: verifying a fact yourself always beats asking Joe to look it up, and always beats guessing).

   **What does NOT warrant asking**: routine/mechanical choices with an obvious sensible default (naming, scope-narrowing, which of several fine approaches); and — separately — needing Joe's own hands for something (e.g. `gh auth login`'s interactive browser step, something only his account/machine can do). That's not a decision to put to him as a question either: just tell him plainly, once, exactly what to run, and keep moving as soon as it's done.

   Other things worth interrupting Joe for, unchanged: (a) a genuinely destructive/irreversible action outside this project folder (deleting something elsewhere, force-pushing, sending/publishing something externally), or (b) a real blocker — you don't have and can't get the information needed to proceed at all, verification included. Everything else: decide, do it, tell him afterward.
2. **Do not guess or assume. Verify with real resources.** If you don't know a path, a fact, or an etymology, check it — don't ask Joe to look it up for you, and don't skip verification just because rule 1 says move fast. Verifying is not the same as asking permission.

   **`HISTORY.md` counts as a real resource, and it is the cheapest one.** Re-attempting an approach this project already tried and reverted is guessing with extra steps. Check there before redesigning anything.
3. **Be honest about limitations and bugs.** Don't overclaim accuracy; flag imperfect results explicitly.
4. **Write it like a senior engineer, the first time** (set 2026-07-30). Clean,
   modular, maintainable — no spaghetti. Hard guardrails, not preferences:
   **no function over 20 lines**; **explicit `typing` hints everywhere**;
   **guard clauses and early returns, never deep `if/else`**; **real
   `try/except` around every file/dump/HTTP/SQLite read**; **domain entities
   are `dataclass`es, never raw nested dicts or positional tuples** — a
   `Node`/`Entry`/`ClimbStep` read by name, not `step[2]` or `n["lang"]`
   (dicts are a wire format: convert at the JSON/d3 boundary, don't pass them
   through the logic). A message that
   names what failed, never a bare `except:` and never a silent `pass`
   (silence is exactly how issue #19 — affixes counted as component words —
   and issue #21 — a rebuild dropping the descendant tables — both hid).
   Small single-purpose functions, descriptive names, comments only where the
   logic is genuinely hard. When a function heads past 20 lines, extract a
   named helper rather than nest further. Existing violators are known and
   exempt until they have characterization tests — see issue #23 (the two
   deep build functions are untested).
5. **Test first.** Write the failing test, then the code. `python test_units.py`
   is ~1s; run it constantly. `scripts/verify.py` before reporting done.
6. **The Three M's — Make, Maintain, Modify skills and scripts** (set
   2026-07-30, Joe calls this one of the main things to be doing). Before
   writing one-off code, check whether a skill or a `scripts/` entry already
   covers it; if one nearly does, **extend that one** rather than write a
   parallel version. When a task turns out to be repeatable, leave a script
   behind, not just an answer. When a script or skill is wrong or slow, fix it
   as part of the task instead of working around it. New/changed skills go
   through the `etymology-skill-audit` skill. **Why:** scripts cut the
   exploration cost that dominates a session, the same work stops being
   rewritten, and each fix makes the artifact permanently better — quality
   compounds instead of restarting at zero. Scripts are code and are held to
   rule 4 (the clean-code guardrails).
7. **Never cite a number bare** (set 2026-07-30). Every reference to a numbered
   issue, rule or feature gets a few-word parenthetical saying what it is —
   "issue #16 (every feature must read from one shared source)", not "issue
   #16". Applies to chat, code comments, docstrings, commit messages and both
   markdown files. **Why:** Joe can't hold twenty issue numbers in his head,
   and a bare number makes him look it up or read past it. The number carries
   the precision; the gloss carries the meaning.

## Project vision

Input a paragraph (or an entire book) → output what percentage of the words come
from each origin language: French, Greek, Latin, Germanic, Norse, etc.

"Origin" is readable **three ways, via a toggle** (all three are first-class
features — expanded from two to three on 2026-07-22, see known issue #1):

- **Direct Source** — the language English took the word from directly
  (e.g. `skill` → Old Norse, `table` → Old French). Was called "proximate donor."
- **Notable Influence** — the most distinctive language the word passed
  through along the way (e.g. `coffee` → Turkic/Ottoman Turkish — the leg
  that both Direct Source [Germanic/Dutch] and Deepest Root [Semitic/Arabic]
  skip past). New level; see `resolver.py`'s `_pick_influence` for the exact
  rule and reasoning.
- **Deepest Root** — the oldest traceable ancestor, etymonline-style
  (e.g. `skill` → Proto-Indo-European). **Redesigned 2026-07-23** (see known
  issue #10, "Piece 1"): rather than only reporting the family bucket (e.g.
  "PIE" or "Germanic"), this now names the specific deepest attested-or-
  reconstructed form reached, and flags when that form itself connects
  further to PIE -- e.g. `sky` → **Proto-Germanic (from PIE)**, `justice` →
  **Latin (from PIE)** (no named proto-language step exists between Latin
  and PIE for this word, so it names Latin directly per Joe's confirmed
  rule), `cover` → **Late Latin** (no further PIE connection recorded at
  all, honestly not claimed). The bucket used for the percentage
  breakdown/chart is unchanged (still the family, e.g. "PIE"/"Germanic") --
  only the per-word label (`ResolvedView.depth_lang`) got richer, so the
  chart's category count stays stable across all three modes. Only surfaces
  proto-language names ALREADY explicitly recorded in a word's own chain --
  never inferred, per rule 2. See `convert_wikt.py`'s `root_lang`/`root_pie`
  fields and `resolver.py`'s `Resolution.view()` for the implementation.
- **Etymology tree** (added 2026-07-23, Joe: "I really like the etymology
  tree that Wiktionary provides") -- a per-word view showing every recorded
  branch, not just the one answer the bucket/percentage features need.
  `build_etymology_trees.py` walks the same raw `group_tag`/`parent_tag`/
  `parent_position` structure as `convert_wikt.py` but does NOT flatten it:
  `sandal` shows all 4 recorded branches (the main Latin/Greek chain, a
  Byzantine-Greek alternate, an Arabic/Sanskrit alternate, plus a redundant
  bare edge) instead of collapsing to one. Two things were tried and
  reverted because they produced actively WRONG trees, not just untidy ones
  -- worth knowing before touching this code: (1) treating `has_root` rows
  as normal positional links nested them as the *parent* of shallower forms
  (e.g. "PIE ← Middle English" for `and`, backwards) -- fixed the same way
  `convert_wikt.py` already does, pulling roots out and appending them at
  the true end of a branch; (2) merging top-level branches that don't
  restart from an English stage (to turn `cover`'s 3 disconnected top-level
  fragments into one clean chain) actively fabricated a false relationship
  for `sandal` (chained its unrelated Byzantine-Greek and Arabic/Sanskrit
  alternate theories directly into each other). Reverted -- no top-level
  merging at all, so `cover` shows as 3 separate one-line branches instead
  of one tidy chain. That's a known, accepted rough edge (a false merge
  would be worse); a smarter fix, if ever wanted, would need a reliable way
  to tell "same narrative, citation-variant restart" (`law`/`sky`/`cover`)
  apart from "genuinely different branch" (`sandal`/`and`) -- the same open
  problem noted in issue #6's `and` writeup, unsolved there for the same
  reason. Served from `app.py`'s single-word lookup form (separate from the
  paragraph analyzer), color-coded per node via the same bucket hues as the
  rest of the app.

End goal: **every possible English word in the database.**

## READ THIS FIRST — the data layer was replaced 2026-07-26

`etymology.db` (SQLite) is now the canonical per-word store, read through
`etymology_db.py` — **the only module that opens it**. Both the paragraph
analyzer (`resolver.DbResolver`) and the Word Search tree
(`word_trees._tree_from_db`) read it, which is what finally makes them
structurally unable to disagree.

Everything below this section that describes `convert_wikt.py` /
`wikt_words.json` / `etymology_trees.json` as **the** pipeline is now
**historical**. Those files still exist and are still consulted, but only as
lower-priority gap-fillers beneath the database. **Measured 2026-07-27**: on
the legacy stack's OWN vocabulary the database answers 97.9% alone, and the
old stack still rescues ~2% (`nepotistic`, `dependant`, `doldrums`, `doggie`)
— so they stay. (An earlier claim of "151 words per 150,000" understated it
by an order of magnitude.)

**`HISTORY.md` holds the full narrative of every known issue** — what was
tried, what failed, and why. It is deliberately NOT loaded into context. Read
it before re-attempting anything that looks obviously improvable; its main
value is the negative results.

Read `etymology_schema.sql` for the table design and the reasoning behind each
table. See known issue #18 for what changed and why, and #19 for the one real
regression it introduced (derivational suffixes counted as component words).

    python test_units.py                # fast logic checks, ~1s -- run constantly
    python scripts/verify.py            # is the database good? ~40s, 5 lines out
    powershell -File scripts/build.ps1  # rebuild + verify, ~10 min

    python -m coverage run --source=. --omit="scripts/*,build_*.py,convert_*.py,fetch_*.py,export_*.py,test_*.py" test_units.py
    python -m coverage run -a --source=. --omit="scripts/*,build_*.py,convert_*.py,fetch_*.py,export_*.py,test_*.py" test_regression.py
    python -m coverage report --sort=cover     # 85% as of 2026-07-27

`ETYMOLOGY_DB=0` disables the new layer entirely and falls back to the old
file-backed stack — use it to isolate whether a problem is in the database.

**Still true and still load-bearing**: rules 1–3 above; "cognates/doublets are
siblings, not ancestors"; corrections must propagate to every feature; verify
against real sources rather than guessing.

## Current state (working, tested)

- **Coverage on ordinary prose: ~98%** of tokens classified, across
  narrative, news, technical, literary and casual registers (measured
  2026-07-27). Dictionary-wide it is lower and the difference is real, not a
  contradiction — see known issue #4.
- **`etymology.db` is the answer to "where is this word from".** 1,380,567
  headwords, 428,722 with their own etymology. Everything else on disk is a
  gap-filler beneath it.
- Verified continuously by `scripts/verify.py`'s known-word panel:
  `skill`→Norse, `table`→French, `sky`→Norse, `egg`/`anger`/`knife`/`they`/
  `them`/`law`→Norse, `beef`/`government`/`justice`/`army`→French,
  `the`→Germanic (inherited). Each word in that panel earned its place by
  having been wrong once; the comment beside it names the bug it guards.
  (`trust` moved Norse→Germanic 2026-07-24 — a genuine scholarly correction
  in the source, not a regression.)

The gap-filler files, and what each is for:

| File | Holds | Why it still exists |
|---|---|---|
| `wikt_words.json` | 244,094 words, etymology-db-derived | Rescues ~2% of words the database lacks |
| `wiktextract_words.json` | 109,216 words with a structured chain | Same, layered above the older file |
| `etymology_trees.json` | Per-word nested trees | Word Search falls back to it |
| `inflections.json` | 663,494 inflected forms | `wolves`→`wolf`. Replaced 89 lines of hand-typed tables |
| `word_info.json` | 278,131 definitions, cognates, doublets | Hover cards. Cognates are SIBLINGS, deliberately out of lineage |
| `root_glosses.json` | 5,636 root meanings | What `*bʰréh₂tēr` MEANS, on hover |
| `languages.csv` | 111 curated languages with era data | `era_start` IS the depth ordering |

Full build notes for each — the measurements that justified them and the
scope limits that still bind — are in `HISTORY.md`'s appendix.

- `app.py`: throwaway local Flask UI (`python app.py` → localhost:5000). Not
  the planned Java/Spring backend, just a faster way to eyeball results than
  the terminal.

## Architecture (three layers, deliberately decoupled)

| File | Role |
|---|---|
| `analyzer.py` | Tokenize text → resolve each word → aggregate percentages. `analyze(text, mode=...)`, `format_report(...)` |
| `resolver.py` | **The swap point.** `ChainResolver([WiktionaryResolver, EtyResolver])` — backends implement `resolve(word) -> Resolution`; `Resolution.view(mode)` renders `"direct"`/`"influence"`/`"root"` from one pass |
| `buckets_wikt.py` | Language-name → origin bucket (Wiktionary backend) |
| `buckets.py` | ISO-code → origin bucket (legacy `ety` fallback backend) |
| `convert_wikt.py` | Rebuilds `wikt_words.json` from etymology-db's raw relation table (`etymology.parquet`). Rewritten 2026-07-23 to walk each word's real recorded graph (`group_tag`/`parent_tag`/`parent_position`) instead of a static per-language depth table — see known issues #2/#6. `resolve_term()` also emits `native_stages` (issue #13). Three post-processing passes run after the main loop — `_patch_root_stubs`, `_patch_foreign_root_stubs`, `_extract_auto_compounds` — close most of the bare-PIE-root-stub gap (issue #14) and write the top-level `auto_compounds` output key |
| `export_browser.py` | Legacy export for the Path-A demo page |
| `corrections.py` | Manual overrides for confirmed bad entries — now mostly genuine multi-sense collisions (e.g. `die`/`bull`, see known issue #6) rather than cross-language homograph collisions, which the 2026-07-23 rewrite fixed structurally — applied by `WiktionaryResolver` at load time |
| `_stem_candidates`/`_stem_variants` (in `resolver.py`) | Suffix-stripping fallback (washing→wash, canines→canine) — lives in `ChainResolver.resolve()`, tried across *every* backend when the surface form misses everywhere (not inside `WiktionaryResolver` — that was a real bug, see known issue #8) |
| `_expand_contractions` (in `analyzer.py`) | Expands contractions to real words before tokenizing (you'll→you will) so clitics don't resolve as wrong/unknown words |
| `_pick_influence` (in `resolver.py`) | Picks the "Notable Influence" (level 2) waypoint from a word's chain — see known issue #1 |
| `build_etymology_trees.py` | Builds `etymology_trees.json` — a per-word NESTED tree (every branch preserved), separate from `wikt_words.json`'s deliberately-flattened `chain`. Added 2026-07-23 for the etymology-tree UI feature |
| `compounds.py` | `COMPOUND_SPLITS` word→(part1, part2) allowlist for words that resolve to Unknown on their own but are verified two-word compounds (736 words). Consulted only as `ChainResolver.resolve()`'s last fallback — see known issue #11. `ChainResolver` also consults `wikt_words.json`'s auto-detected `auto_compounds` table alongside it (issue #14) — same fallback mechanism, but that data is machine-extracted from Wiktionary's own `compound_of`/`blend_of` tags, not individually hand-verified like these 736 |
| `app.py` | Throwaway local Flask test UI (`localhost:5000`) — not the planned backend. Now also serves a single-word etymology-tree lookup (`TREES`/`node_slug`) and renders compound-split words as linked component chips, alongside the paragraph analyzer |
| `etymology_db.py` | **The only module that opens `etymology.db`.** `entry()` = one indexed lookup, no branching. `lineage()` follows formation parts into their own words |
| `build_etymology_db.py` | Builds `etymology.db` from the wiktextract dump. Atomic: writes `.new`, checkpoints, swaps |
| `wiktextract_shapes.py` | The four parsers (donor chain, formation fork, `ety`/`etymon` DSL, root pointer) |
| `languages.py` / `languages.csv` | 111 curated languages with era data. `era_start` IS the depth ordering |
| `scripts/verify.py` | One command: invariants + legacy suite + known-word panel + tree/analyzer agreement, four lines out |
| `scripts/scriptlib.py` | **Leaf module for `scripts/`.** `bootstrap()` (sys.path + UTF-8 console), the data paths (`ENGLISH_DUMP`, `PARQUET_PATH`, derived from `DATA_ROOT`, overridable via `ETYMOLOGY_DATA_ROOT`), `require_file`, and the kaikki URL rules. Imports nothing project-local. Domain logic does NOT go here — `climb_to_root` lives in `descendants.py` |
| `build_descendants.py` | Loads Wiktionary DESCENDANTS trees (the downward view) into `etymology.db`. `SOURCES` is the coverage list. **Re-run after any full rebuild** — its tables aren't in the schema |
| `descendants.py` | Assembles one tree for display: climb to the root, splice fragments, merge spelling variants, apply the node budget |
| `static/d3.v7.min.js` | Vendored d3 — the project's only JavaScript dependency, used solely by the `/descendants` view |
| `linguistics.py` | **Leaf module, imports nothing project-local.** The one answer to "is this an English stage / a proto-language / an affix", and the depth ordering. If you are about to write `lang.startswith("Proto-")` anywhere, import it from here (issue #23) |
| `palette.py` | Bucket → colour slot, proto shades, sub-language shades, `THEME_CSS`. Values are CVD-validated — moving them is fine, changing them is not |
| `word_trees.py` | Word → renderable etymology tree: lookup, fallback, glosses, Wiktionary links, diagram layout. Six public functions; everything else private. Uses `shared_resolver()` |
| `test_units.py` | Fast logic suite (276 checks, ~1s, no database). Run after every edit — `test_regression.py` is the slow answer-correctness one |
| `wiktextract_dump.py` | `stream_english_entries(path)` — the one loop that reads the dump. Three build scripts had each hand-rolled it |
| `HISTORY.md` | Full narrative of every known issue. **Not** loaded into context; read on demand |

Adding a data source = one new class with `resolve()`, added to the list in
`default_resolver()`. Analyzer and UI never change.

## Environment facts (verified, do not re-guess)

- Windows machine, Python **3.13** (Microsoft Store install), user `Josep`
- Project lives at: `C:\Users\Josep\Desktop\Etymology Project\etymology-app`
  — flat, code directly in this folder. (The old nested duplicate
  `etymology-app\etymology-app` from unzipping was removed 2026-07-22.)
- `ety` package: **working**. Its `pkg_resources` dependency requires
  `setuptools`, but plain `pip install setuptools` grabs the latest version
  (v80+), which has **removed** `pkg_resources` entirely — that install looks
  successful but `import ety` still fails. Fix that actually works: pin an
  older version, `pip install "setuptools==70.0.0"`. Already done as of
  2026-07-22; both `WiktionaryResolver` and `EtyResolver` load cleanly via
  `default_resolver()`.
- Full-database smoke test run 2026-07-22 (all 71,630 words, both modes):
  100% of words bucketed. Proximate distribution matches the README table
  (Germanic 22.4%, French 19.3%, Latin 15.2%, ...). "Unresolved" count in a
  naive test script (~7,319) is *not* a bug — those are native English words
  correctly flagged as the Germanic approximation (`ResolvedView.resolved =
  False`), not lookup failures.
- **Raw etymology-db data acquired 2026-07-23** — Joe manually downloaded both
  formats from the upstream repo's OneDrive link to `C:\Users\Josep\Desktop\
  Etymology Project\`: `etymology.csv` (downloaded as a folder; the real file
  is nested one level down at `etymology.csv\etymology.csv`, 456 MB — a common
  artifact of how the download unpacked, not a data problem) and
  `etymology.parquet` (140 MB, same data, columnar/faster to read — this is
  the one `convert_wikt.py` actually reads). Both verified to have the
  documented schema: `term_id, lang, term, reltype, related_term_id,
  related_lang, related_term, position, group_tag, parent_tag,
  parent_position` — 4,222,599 rows total, 926,657 with `lang == "English"`,
  364,161 unique English term_ids. `pandas` and `pyarrow` installed to read it
  (`pip install pandas pyarrow`).
- `term_id` is unique per exact-case spelling for `lang == "English"`
  (confirmed: unique term_id count == unique term-string count) — i.e. `she`
  and `She` are genuinely separate entries in the source data, not a parsing
  artifact. This was the key fact that let issue #6 get a structural fix
  instead of another hand-patched word list — see known issue #6.
- **Console encoding, verified 2026-07-27**: this machine's Python stdout
  defaults to cp1252, so ANY throwaway `python -c` that prints a proto-form
  dies with `UnicodeEncodeError` (`*bʰréh₂tēr`, `*erþō`, `*kʷód` — i.e. most of
  what's worth printing here). It's a *printing* failure, not a data failure —
  the lookup above it already succeeded. Prefix with `PYTHONIOENCODING=utf-8`
  rather than debugging the query.
- **Restarting `app.py` cleanly (Windows quirk, hit twice 2026-07-24)**:
  `Get-NetTCPConnection -LocalPort 5000` / `netstat -ano` can keep reporting
  a LISTENING socket owned by a PID that's already dead (`Get-Process`/
  `tasklist` for that PID returns nothing) for several seconds after
  `Stop-Process` — a stale OS socket-table entry, not a real conflict. Don't
  loop waiting for the port to show as free; after confirming the owning PID
  is actually dead, just start `python app.py` directly — it binds fine
  despite the stale table entry. (Separately, Werkzeug's debug-mode
  reloader spawns a child process that a single `Stop-Process` on the
  parent doesn't always reach — kill whatever PID `Get-NetTCPConnection`
  actually reports, not an assumed parent PID.)
- `C:\Users\Josep\Downloads\wiktionary_codes.csv` (Joe, 2026-07-23) — Wiktionary's
  own full internal language-code registry, 8,652 rows, code→name only (not
  code→family). Not yet wired into anything; earmarked as the code→name
  lookup for issue #10's Piece 2 (Reconstruction pages use codes like
  `gem-pro`/`ine-pro`, not the full names etymology-db already gives us).

## Known issues

**The full narrative for every entry below lives in `HISTORY.md`** — including
the negative results (what was tried and failed, and why), which is the part
worth reading before you "improve" something. This list is the working summary:
what is still true, and what still needs deciding.

Numbers are permanent and never reused — code comments and commit messages
refer to them.

### Open — needs a decision from Joe

- **#14 — 1,245 words have no ancestry beyond a coincidental PIE root.**
  They honestly show Unknown for Direct Source / Notable Influence; Deepest
  Root still shows the real PIE citation. Every relation type in the source
  has been checked and exhausted for these specific words. Three ways
  forward, each a real trade-off rather than an implementation detail:
  **(a)** leave it — Unknown is honest; **(b)** add a clearly-labelled
  lower-confidence tier from `etymologically_related_to` (a philosophy change
  from "verified fact only", since Wiktionary tags that relation as a hedge);
  **(c)** another data source for the remainder. Joe chose (c) for the
  specific words issue #17's scan surfaced; **the general class is still
  open.**
- **#18 — 6 legacy-suite checks are deliberately failing**: `tag`, `auto`,
  `critical`, `package`, `free`, `muskrat`. These are answer judgment calls
  for Joe, not shape failures. Editing the expectations to match the code
  would destroy the evidence, so they stay red on purpose. (`movie` and
  `peacemaker` were in this list until #22 fixed them.)

### Open — live limitations

- **#3 — `Other` bucket leakage.** Languages missing from `NAME_TO_BUCKET`
  render as `Other`. ~50 of the highest-frequency gaps were added 2026-07-23;
  that was the top of the frequency list, not an exhaustive pass. Genuine
  isolates (Basque, Georgian, Sumerian, Hungarian, Finnish, Armenian) are
  left as `Other` deliberately rather than force-fitted.
  **Re-measured 2026-07-30, and the old example is gone**: `muskrat` now
  correctly reads Indigenous American / Algonquian (fixed by `language_codes.py`,
  commit `feb28ae`). Of 1,530 distinct languages in `ety_node`, 1,379 bucket as
  `Other` — but the SIX largest populations are all the deliberate isolates
  above (Armenian 495 nodes, Basque 381, Hungarian 312, Georgian 173,
  Finnish 150, Sumerian 64), so that number overstates the bug badly.
  **The real remaining mechanism is codes-vs-names**: `NAME_TO_BUCKET` is keyed
  on language NAMES, and the database still stores some donors as raw codes, so
  a code bypasses the map even when its own name is mapped. Verified pairs —
  `mni` → Manipuri → East Asian (357 nodes), `dz` → Dzongkha → East Asian (145),
  `hop` → Hopi → Indigenous American (112), `gsw` → Alemannic German →
  **Germanic** (98), `tpw` → Old Tupi → Indigenous American (95), `alg` →
  Algonquian (67), `iu` → Inuktitut (63). Each resolves correctly through
  `language_codes.py` and buckets correctly by name; only the raw code fails.
  The fix is to resolve the code before bucketing at every call site, not to add
  code keys to the map. One genuine name-level gap remains: `lt` → Lithuanian
  (125 nodes) — Baltic has no bucket at all.
- **#4 — coverage is not total.** ~31% of the 1.38M headwords have their own
  etymology; ~52% get an answer once inflection/stem/compound routing is
  counted; **ordinary prose runs ~98%**, because coverage is concentrated
  where usage is. The gap is the long tail (`isallobars`, `Bophuthatswanan`).
- **#6 — multi-sense collisions on one `term_id`.** Structurally fixed for
  the cross-language case in 2026-07-23 (store case-sensitively, stop merging
  at conversion time). What remains is genuine multi-sense entries — `die`,
  `bull`, `and`, `low` — handled by hand-verified `corrections.py` overrides.
  **Two auto-split heuristics were tried and both broke real single-sense
  words**; see HISTORY.md before attempting a third. The unsolved core: no
  reliable signal separates "restart = new sense" from "restart = spelling
  variant".
- **#10 — "Deepest Root" often means oldest *attested*, not oldest ancestor.**
  Both planned pieces shipped 2026-07-23, but honestly: the Reconstruction
  fetch closed only ~6.9% of the targeted proto gap (94 of 1,366). The rest
  is genuinely undocumented on Wiktionary itself, not a parsing failure.
- **#11 — compound display covers 736 hand-verified words**, the scope one
  curated external list surfaced. The database certainly holds more Unknown
  compounds it didn't include.
- **#15 — 256 hub words are excluded from root inheritance** by an automated
  signature check and were never individually verified. None were used as an
  inheritance source, so no coverage was gained *or* risked from them.
- **#16 — one database, one answer.** The coverage mechanisms (inheritance,
  stemming, compounds — ~164k words) are fully unified. Residual: an
  individual `corrections.py` collision fix still needs a hand-maintained
  `tree_corrections.py` twin, because `resolve_tree()` consults `TREES`
  before the resolver.
- **#17 — 105 words remain Unknown** on the 347-paragraph corpus after the
  2026-07-24 audit (191 → 139 unique, 156 → 105 real-gap). No strong shared
  pattern left; not chased further, per "fix the pattern, not every word".
  **The corpus itself is not on disk** — it was fetched live from
  randomwordgenerator.com's static bank.
- **#25 — random-word scan findings, AWAITING JOE'S DECISION (2026-07-30).**
  Documented deliberately rather than fixed — he asked to decide himself.
  2,000 truly random dictionary words: **70.0% resolved, 29.4% Unknown, 0.5%
  Other**. The Unknown are only two causes — 87% absent from the database
  entirely (issue #4's long tail; a looser stemmer was checked and would
  manufacture wrong answers), 13% derived from a base word that is itself
  missing. The 11 `Other` are four causes, of which the sharpest is that
  **`Northern Middle English` and `Anglian Old English` bucket as `Other`
  when they are plainly Germanic**. Also found: bare affix spellings resolve
  as unrelated foreign words (`ly`→Vietnamese, `ment`→Korean, `er`→Turkish,
  `ous`→Hawaiian) — inert today because of issue #19's `is_affix` flag, and a
  live landmine for any future code that skips that check. **Full breakdown
  with examples and the rejected fixes: `HISTORY.md` entry 25.**
- **#24 — the residual of #19 (affixes), in the templates that say nothing.**
  `{{suffix}}`/`{{prefix}}`/`{{confix}}` mark the bound morpheme by POSITION
  and are now read correctly. `af`/`affix`/`surf` (~49,000 templates) do not —
  they promise nothing positionally, so an UNHYPHENATED part of one is still
  judged by spelling alone, which is what leaves `disagree` reading French via
  a `dis-` that survives as a component. Three spelling rules have now been
  measured and rejected on this exact problem (they cost 263, 134 and 52
  hand-verified splits), so a fourth is not the answer. Separately, a compound
  part that is ITSELF derived can leak a morpheme one level down —
  `overactive` → over + act + `ive` — because the affix filter runs on the
  word's own parts, not recursively through a hand-verified split.
- **#21 — descendants: the Greek branch is missing.** Proto-Hellenic has no
  kaikki extract (404). One command adds any other branch:
  `python scripts/add_descendant_language.py "Proto-Italic"`. The
  `descendant_tree`/`descendant_node` tables are **not in
  `etymology_schema.sql`**, so a full rebuild drops them until
  `build_descendants.py` re-runs — `build.ps1` now does that automatically.
  **Root cause of why this kept coming back, found 2026-07-30**: `build.ps1`
  read `$proc.ExitCode` from a `Start-Process` handle, which can still be
  `$null` after the process exits, and `$null -ne 0` is TRUE in PowerShell —
  so every SUCCESSFUL build took the failure branch and quit before reaching
  the descendants step. It now calls `WaitForExit()` first. Never loosen
  variant merging to merge by language alone — it would reattach children to a
  spelling the source never claims.
- **#22 — `movie` is honest but still not right.** Re-confirmed 2026-07-30: it
  reads Unknown rather than French/Latin via `move`, because the builder
  recorded only the suffix `ie` and dropped the real component. Same shape as
  #19 (the affix-vs-component split reconstructed at lookup time): a
  lookup-layer defence against a build-time data loss.
  `zoo` and `physiologist` are absent from `etymology.db`'s 428,722 words — but
  that is a claim about the DATABASE, not the app: `zoo` resolves to Greek
  through the legacy gap-filler stack (it was hand-added to `corrections.py`
  during issue #11's compound work — needed as a part of `zookeeper`).
  `physiologist` really does read Unknown everywhere. A coverage gap this fix
  only made visible.
  **Why `movie` can never be fixed at build time, confirmed 2026-07-30**: its
  dump entry is `{{suffix|en|""|ie}}` — **the base word is an empty string in
  Wiktionary's own data.** `move` was never recorded, so nothing was lost by
  this project and nothing can be recovered by a better builder. Closing this
  needs a `corrections.py` entry or a different source, not a parser change.
- **#23 — the two deep build functions are untested.**
  `convert_wikt._patch_root_stubs` (142 lines, depth 6) and
  `build_word_info.from_wiktextract` (123 lines, depth 7) are the most
  complex code in the project and sit at 0% coverage, because exercising them
  needs the multi-GB dump. Refactoring them safely requires characterization
  tests first, which requires splitting their logic from their I/O.

### Closed — kept for the record

Each of these is fully written up in `HISTORY.md`. Listed so the numbering
stays legible and so nobody re-opens a solved problem.

| # | What it was | Closed |
|---|---|---|
| 1 | Pass-through donors (`coffee` → Dutch, not Turkic) | 2026-07-22 — became the "Notable Influence" third mode |
| 2 | Chain ordering was a static per-language table | 2026-07-23 — rewritten to walk each word's real recorded graph |
| 5 | Case-merge noise (`Sky` + `sky` blended) | 2026-07-23 — turned out to be the root cause of most of #6 |
| 7 | No home for Caribbean-origin words | 2026-07-22 — new bucket + 19 verified words |
| 8 | Missing inflected forms (`washing`, `held`) | 2026-07-25 — superseded by `inflections.json`, 663k forms |
| 9 | Contractions split into junk tokens (`don't` → `don`) | 2026-07-22 — expanded before tokenizing |
| 12 | Bar-graph drill-down, tree redesign, toggles, Deepest Root bugs | 2026-07-23 — one long session, all shipped |
| 13 | Native words lumped under one flat label | 2026-07-24 — real stage names (Old/Middle English) surfaced |
| 19 | Affixes counted as component words (`darkness` → dark + ness) | 2026-07-30 — builder keeps the distinction (`ety_node.is_affix`); 225,788 words stopped halving their origin. Residual split off as #24 |
| 20 | No link to sources; PIE roots had no meanings | 2026-07-26 — Wiktionary links + 5,636 root glosses |

## Data pipeline notes

- Raw relation table schema: `term_id, lang, term, reltype, related_term_id,
  related_lang, related_term, position, group_tag, parent_tag,
  parent_position` (confirmed against real data 2026-07-23 — see Environment
  facts). `term_id` is unique per exact-case spelling per language.
  `group_tag`/`parent_tag`/`parent_position` form a tree: a row can anchor a
  nested group of further rows (not just rows whose `reltype` is one of the
  three `group_*_root` marker types — a plain edge row can *also* carry a
  `group_tag` that further rows nest under, e.g. `law`'s `has_root` row);
  `parent_position` gives the real recorded order **within** one group, but
  separate top-level (ungrouped) sibling rows have no ordering signal between
  them at all (`position` is always 0 for those) — confirmed directly via
  `table`'s Latin/Old French edges, two independent rows with no structural
  order even though French must be shallower. See `convert_wikt.py` for the
  resulting algorithm and the two dead-end designs tried before it.
- Proximate selection rule: the first foreign (non-English-stage) entry in
  the resolved chain, now driven by real recorded order (see above) rather
  than the old `DEPTH_RANK` static table. History: pure edge-type priority
  was tried and failed (`robot` picked a German cognate over `borrowed_from
  Czech`); the unified shallowest rule fixed robot/sky but produced the
  pass-through issue (#1, resolved via the "Notable Influence" view).
- English-stage names (`English`, `Middle English`, `Old English`) are not
  donors; words that never leave them = native Germanic core.

## Next steps (agreed direction — proceed on these per rule 1, don't wait for a go-ahead)

1. ~~Joe tests the full database locally~~ — done 2026-07-22.
2. ~~Rule on the pass-through donor question~~ — done, "Notable Influence"
   view shipped 2026-07-22, doc drift closed 2026-07-23 (issue #1).
3. ~~Get the raw CSV/parquet and do a real fix for #2/#6 instead of hand-
   patching~~ — done 2026-07-23. Joe downloaded `etymology.csv`/
   `etymology.parquet`; `convert_wikt.py` rewritten to use real per-word graph
   structure; `wikt_words.json` fully regenerated (72,784 words); coverage on
   sample prose rose to ~98%. See issues #2/#6 for the full story.
4. Enhancement ideas surfaced while exploring the raw data's other relation
   types (`compound_of`, `has_prefix`/`has_suffix`/`has_confix`, `blend_of`,
   `clipping_of`, `back-formation_from`, `named_after`, `abbreviation_of`,
   `initialism_of`, `is_onomatopoeic`, `phono-semantic_matching_of`,
   `semantic_loan_of`, `doublet_with`) — none of these are ancestry edges, so
   they're irrelevant to the current bucket-percentage feature, but they're
   real per-word data already sitting in `etymology.parquet` that could
   support features beyond the current scope. Not built — Joe said the
   priority right now is confirming the paragraph analyzer works correctly
   across all three levels (done, see Current state) before adding anything
   new. Ideas, for whenever he wants to expand scope:
   - **Compound/affix breakdown** (`compound_of`, `has_prefix`, `has_suffix`,
     `has_confix`, `has_affix`, `has_prefix_with_root`): a per-word "how it's
     built" view — e.g. `said` → prefix-with-root `say` + suffix `-ed`. Could
     show morpheme-level origin instead of (or alongside) whole-word origin.
     **Partially built 2026-07-23, see known issue #11** — but narrower than
     this idea: only for words that resolve to Unknown on their own (never
     replaces a working whole-word answer), and only real word+word
     compounds (`compounds.py`), not root+bound-affix breakdowns like
     `said`→`say`+`-ed` above. **Extended 2026-07-24, known issue #14**:
     `has_prefix_with_root`/`has_confix`/`back-formation_from`/`clipping_of`/
     `compound_of`/`blend_of` are now used, but only as a narrow fallback for
     bare-PIE-root stub words specifically, not as a general per-word display
     feature. The full general morpheme-level view for every word (showing
     the breakdown even for words that already resolve fine on their own) is
     still open.
   - **"Did you know" trivia**: `named_after` (eponyms — words named after a
     real person/place), `blend_of` (portmanteaus), `back-formation_from`,
     `clipping_of`, `abbreviation_of`/`initialism_of`, `is_onomatopoeic` are
     all flags Wiktionary already records — could surface a one-line "fun
     fact" per word when one applies, no new data collection needed.
   - **Confidence/dispute flag**: words whose chain relies on `calque_of` or
     where competing groups exist for the same term_id (the multi-theory
     pattern seen in `sandal`) could be flagged as "disputed origin" in the
     UI rather than silently picking one theory.
   - **`doublet_with`**: word pairs that both descend from the same root via
     different paths (e.g. `zero`/`cipher`) — could power a "related word"
     feature.
   These all reuse data already sitting in `etymology.parquet`; none require
   another download.
5. Then: Java/Spring REST backend serving `wikt_words.json`
   (endpoint: text + mode in → breakdown JSON out). Joe knows Java/Spring
   (CS 314 coursework). Web UI after that.
6. **OPEN DECISION, asked 2026-07-24, not yet answered — see known issue
   #14.** 1,245 words genuinely have zero recorded ancestry data beyond a
   coincidental PIE root citation and now honestly show Unknown for Direct
   Source/Notable Influence. Every relation type in the raw parquet has
   already been checked and exhausted for these specific words — closing
   this further needs Joe to pick a direction, since each option is a real
   trade-off, not an implementation detail:
   - **(a)** Leave it — Unknown is the honest answer for these words, same
     as the general "coverage isn't total" limitation (known issue #4).
   - **(b)** Introduce a clearly-labeled lower-confidence tier using
     `etymologically_related_to` data (e.g. `vitamin` → "vital"/"amine") —
     this is a philosophy change from "verified fact only" (rule 2) to
     "verified fact, with a flagged best-guess fallback," since Wiktionary
     itself tags this relation as a hedge, not an assertion.
   - **(c)** Pursue a different/additional data source for just this
     remainder — hand-research into `corrections.py` one word at a time
     (slow, but zero risk to the "verified" standard), or revisit `etym-cli`/
     `engsource`/a live etymonline-style scrape (Joe asked about both
     earlier — see known issue #13 for why `engsource` wasn't needed for
     the *previous* gap; that reasoning doesn't automatically transfer here,
     since this gap is Wiktionary not HAVING the data at all, not this
     project failing to read data it already had).
   Proceed on whichever direction Joe picks per rule 1 once he answers —
   this is the one open item in this list waiting on him, not a case where
   more investigation would resolve it alone.
