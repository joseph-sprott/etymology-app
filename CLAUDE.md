# CLAUDE.md — Etymology Analyzer Project

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
3. **Be honest about limitations and bugs.** Don't overclaim accuracy; flag imperfect results explicitly.

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

## Current state (working, tested)

- Python pipeline is complete and functional. Coverage on sample prose:
  **~98%** of tokens classified (up from ~81% before the 2026-07-23 pipeline
  rewrite, up from ~44% with the original data source).
- Database: `wikt_words.json` — **244,094 English words** as of 2026-07-24
  (was 72,732 before issue #15's "no entry at all" widening; further widened
  by issue #17's `has_affix` + irregular/stem-bridge fixes) (plus a separate
  **~22,300-entry `auto_compounds` table**, see known issues #14/#15/#17)
  with resolved proximate bucket, deepest bucket, and donor chain.
  Rebuilt 2026-07-23 by
  `convert_wikt.py` directly from etymology-db's raw relation table (now
  present on this machine as `etymology.parquet` / `etymology.csv`, see
  Environment facts) — using the real per-word graph structure instead of a
  static depth table. See known issues #2 and #6 for what changed and why.
  Regenerated several more times since (native-stage granularity, known
  issue #13; bare-PIE-root stub fix, known issue #14) — always via
  `python convert_wikt.py`, ~15-20 min, run in the background and verified
  against the full regression suite + a live HTTP POST check before trusting
  it, every time.
- Verified correct on key test words: `skill`→Norse, `table`→French,
  `sky`→Norse, `egg`/`anger`/`knife`/`they`/`them`/`law`→Norse,
  `beef`/`government`/`justice`/`army`→French, `the`→Germanic (inherited).
  (`trust` moved from Norse to Germanic 2026-07-24 -- see the wiktextract
  entry below, a genuine scholarly correction, not a regression.)
- **`wiktextract_words.json` — 109,216 English words with a genuine
  structured donor/root chain**, added 2026-07-24 as a NEW top-priority
  resolver (`WiktextractResolver`, layered ahead of `WiktionaryResolver` via
  `ChainResolver`, never replacing it) parsed from kaikki.org's English
  wiktextract JSONL extract (`convert_wiktextract.py`). Prototyped first
  (per Joe's explicit decision) by measuring real impact against the same
  347-paragraph corpus from issue #17: 105 -> 67 real-gap Unknown words on
  that corpus (36% reduction), zero regressions, full 82-check regression
  suite passing. Deliberately conservative in this first pass -- only counts
  a word as having a real chain when it has an actual `inh`/`der`/`bor`
  donor-template edge or root pointer of its own (excludes formation-only
  templates like `suffix`/`affix`/`compound` and hedge-only ones like
  `cog`/`doublet`, same "hedge relations aren't ancestry" principle as known
  issue #14), which is why this number is smaller than the ~470k headwords
  that have SOME etymology text -- most of the gap is words whose only
  evidence is a word-formation template citing an English base word (e.g.
  "teenager" citing "teenage"), left as documented future work since the
  EXISTING resolver-layer stemmer already recovers many of these for free.
  See `etymology_chain.py` (chain-assembly logic shared with
  `convert_wikt.py`, extracted so both pipelines use one already-debugged
  implementation) and `wiktextract_langs.py` (wiktextract's own language-
  code system, empirically mapped from real frequency data, feeding into
  the existing `buckets_wikt.py` taxonomy rather than a new one). Full
  writeup of everything found and fixed during this build: see the commit
  that introduced it.
- A standalone demo page exists (`provenance-wiktionary.html`, 245-word
  embedded subset) — Joe has tested and likes it. Note: as of 2026-07-22 this
  file could not be located anywhere on disk (not in the project, Desktop, or
  Downloads) — it may only have existed as a Claude.ai artifact. Worth
  confirming with Joe if it's needed again.
- `app.py` (new 2026-07-22): a throwaway local Flask UI for testing —
  `python app.py`, open `http://localhost:5000`, paste text, toggle mode. Not
  the planned Java/Spring backend, just a faster way to eyeball results than
  the terminal.
- Two real bugs found via localhost testing 2026-07-22 and fixed — see Known
  issues #6 and #8 below.

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

## Known issues (acknowledged, unfixed — do not silently "fix" without approval)

1. **Pass-through donors (RESOLVED 2026-07-22 — closed 2026-07-23, doc had
   drifted).** ~1,192 words entered English via an intermediary: `coffee`
   (Arabic→Turkish→Italian/Dutch→English) resolves proximate=Germanic because
   Dutch was the immediate donor. Same shape: `sugar`, `algebra`, `orange`,
   `zero`, `giraffe`, `sofa`, `tomato` (all proximate=French/Romance,
   interesting origin deeper). Of the three options that were on the table
   (keep strict proximate; skip pass-through donors; add a third "cultural
   origin" view), option 3 was the one implemented: `resolver.py`'s three-mode
   toggle (`_pick_influence`, "Notable Influence" level) — its own docstring
   says it was added "closing out the long-open 'pass-through donor' design
   question." `Direct Source` deliberately stays strict proximate unchanged;
   `Notable Influence` now surfaces the distinctive middle donor instead
   (`coffee`→Turkic). This entry stayed marked "open" after the fix shipped —
   pure documentation drift, caught 2026-07-23 when Joe asked. Note: Joe
   raised whether coffee is Ethiopian — the plant is; the word's documented
   chain is Arabic *qahwa* (the Kaffa link is considered folk etymology).
2. **Chain ordering is approximate — SYSTEMICALLY FIXED 2026-07-23** once the
   raw etymology-db relation table was obtained (see Environment facts).
   Original bug (2026-07-22 investigation, kept for history): `DEPTH_RANK` in
   the old `convert_wikt.py` was a coarse static per-language rank, not real
   per-word structure; non-European donor languages weren't in the table at
   all and silently defaulted to a rank shallower than Latin/Greek, which
   could sort a genuinely deeper donor ahead of a shallower one. Investigating
   the 5 originally-flagged examples (`candy`, `zero`, `sandal`, `die`, `bull`)
   found only `zero` was actually this bug; `candy`/`sandal` were issue
   #6-shaped spurious edges and `die`/`bull` were issue #5-shaped sense-merges
   — all 5 were hand-patched in `corrections.py` at the time.
   **Real fix**: the raw relation table has `group_tag`/`parent_tag`/
   `parent_position` columns that record each word's ACTUAL etymology chain
   straight from Wiktionary's own template parsing (verified directly, e.g.
   `sandal`'s chain sits at `parent_position` 0/1/2/3 as exactly Middle
   English/Old French/Latin/Ancient Greek). `convert_wikt.py` was rewritten to
   walk this real structure — see its module docstring for the full design,
   including two dead-end approaches tried first (segmenting on English-stage
   restarts, and clustering by shared bucket) that both broke on real data
   before landing on the current "flatten everything in recorded order, plus
   a narrow static tiebreak only for un-grouped sibling edges" design. Full
   re-derivation of all 72,784 words confirmed correct against every
   previously-verified test word (`skill`, `table`, `sky`, `law`, `knife`,
   `coffee`, `zero`, etc. — including ones that broke mid-rewrite and were
   fixed, like `could` losing its native-Germanic base when a `has_root` PIE
   pointer was present). **Not perfect**: words with multiple genuinely
   distinct senses sharing one term_id (`die`, `bull` — see issue #6) can
   still blend two chains together; those remain hand-verified
   `corrections.py` entries, same as before. Sample-paragraph coverage rose
   from ~81% to ~98% as a side effect of the richer source data.
3. **`Other` bucket leakage (partially reduced 2026-07-23).** Languages
   missing from `NAME_TO_BUCKET` in `buckets_wikt.py` show up as `Other`
   mid-chain. While rebuilding the pipeline, checked coverage against the raw
   data directly: of 130,688 real ancestry edges, 5,755 (4.4%) had a
   related-language not in the bucket map. Added ~50 of the highest-frequency,
   clearly-classifiable gaps (`Old Latin`→Latin, `Old Italian`/`Old Spanish`
   →Romance (other), `Middle Irish`/`Proto-Brythonic`→Celtic, `Belarusian`
   →Slavic, `Middle Persian`/`Classical Persian`/`Romani`/`Marathi`/`Nepali`/
   `Gujarati`/`Sinhalese`/`Telugu`/`Malayalam`→Indo-Iranian (loosely grouped,
   same tolerated stretch as the existing Tamil entry), `Vietnamese`/`Thai`/
   `Burmese`/`Khmer`/`Tibetan`/`Hokkien`/`Min Nan`→East Asian (practical
   geographic grouping, not a language-family claim), `Javanese`→Austronesian,
   `Old Tupi`/`Cree`→Indigenous American, `Amharic`→Semitic, `Yoruba`/`Zulu`
   →African (other), plus a `Taíno` (with diacritic) alias alongside the
   existing `Taino`). Deliberately left genuine language isolates / unrelated
   families as `Other` rather than force-fitting them: `Basque`, `Georgian`,
   `Sumerian`, `Hungarian`, `Finnish`, `Armenian` (its own small IE branch,
   not really Indo-Iranian), `Translingual` (Wiktionary's pseudo-language for
   symbols — excluded from donor consideration entirely, not bucketed at
   all). Still open: this was the top of the frequency list, not exhaustive.
4. **Coverage is not total.** 72,784 words = what Wiktionary has explicit
   etymology for. Rarer words unresolved. Long-term goal is closing this gap.
5. **Case-merge noise — RESOLVED 2026-07-23.** Was: terms merged case-
   insensitively (`Sky`+`sky`), fixing a clobbering bug but blending
   proper-noun senses into chains. Turned out `term_id` in the raw data is
   already unique per exact-case spelling (verified), so the 2026-07-23
   rewrite stores `wikt_words.json` case-sensitively with no merging at all,
   and `WiktionaryResolver.resolve()` looks up lowercase first, then original
   case, then title case — see known issue #6 for the full story, since this
   turned out to be the actual root cause of most of #6, not a separate
   issue. Genuine same-spelling, same-case sense-merges (`die`, `bull`) are
   a different, narrower problem — still open, see #6.
6. **Cross-language spelling collisions — ROOT CAUSE CORRECTED, MOSTLY FIXED
   STRUCTURALLY 2026-07-23.** Original theory (2026-07-22): Wiktionary pages
   are organized by SPELLING across every language, so etymology-db's page
   parser was assumed to be picking up a stray "donor" edge from a
   coincidental homograph in an unrelated language (e.g. `she` also covering
   a Japanese romanization). **That theory turned out to be wrong** once the
   raw relation table was available to check directly (2026-07-23): `she`
   (lowercase, the pronoun) has a completely clean, 100%-Germanic row set in
   the raw data with zero Mandarin content. The Mandarin edge lives under a
   SEPARATE term_id for `She` (capitalized) — a different Wiktionary entry
   entirely, correctly kept apart by etymology-db/Wiktionary itself. Same
   confirmed for `look`/Cantonese and `said`/Arabic. **The actual bug was in
   this project's own old `convert_wikt.py`**: its `term.lower()` merge key
   (added to fix the case-clobbering bug, issue #5) was merging these
   already-correctly-separate entries back together, blending an unrelated
   proper-noun homograph into the common word's chain. Fixed structurally by
   storing case-sensitively and looking up lowercase-first (see issue #5)
   instead of merging at conversion time — this is a general fix, not a
   per-word patch, and should catch every instance of this exact bug shape
   database-wide, not just the ones already found by hand. Verified: `she`,
   `look`, `said` all resolve correctly now with ZERO entries in
   `corrections.py` needed for them specifically. Re-checked all 95 existing
   `corrections.py` entries (built up over 6 passes below) against the new
   pipeline: **36 of 95 now auto-resolve correctly with no override needed**
   (left in place regardless — harmless redundancy, and they stay as a
   record of what was checked). The remaining 59 still need their override,
   but are a DIFFERENT bug shape than originally diagnosed: mostly genuine
   multi-sense collisions (one Wiktionary term_id legitimately covers several
   unrelated English words/senses, e.g. `die` verb vs. dice-noun, `bull`
   animal vs. papal-document, `as` the conjunction vs. a rare "Roman coin"
   sense borrowed from Latin) rather than cross-language homograph collisions.
   Tried two different structural heuristics to auto-split multi-sense
   term_ids apart (documented in `convert_wikt.py`'s docstring); both were
   reliable enough to break real single-sense words, so this residual class
   is still handled the manual `corrections.py` way, same as before — just a
   smaller, better-understood remainder than the original ~70-word estimate.
   The historical passes below (all still individually valid, kept for
   record) predate this root-cause correction:
   - **Pass 1**: scanned ~110 core closed-class words (pronouns, articles,
     conjunctions, modals). Found and fixed 14: `an, are, as, can, could,
     many, may, mine, must, no, none, or, she, so`. Deliberately did NOT
     "fix" `because` — it looks like the same pattern (French bucket) but is
     actually correct (`by` + `cause`, and `cause` really is from Old
     French).
   - **Pass 2**: Joe caught `look` → East Asian by eye in the running app
     (same bug, but an ordinary content word, not a function word — proof
     the bug isn't confined to closed-class words). Ran a full-database scan
     (all 71,630 words) for the signature "proximate bucket is an
     implausible donor family for core vocabulary (East Asian, Turkic,
     Austronesian, Indigenous American, Afro-Asiatic (other), African
     (other)) AND the word's own chain also contains a real Germanic link
     later on." **37 words matched.** Individually verified and fixed 13 of
     them: `girl, go, kin, nut, ox, roof, sun, chin, beg, woo, lop, wang,
     wall` (`wall` is a special case — genuinely Germanic-proximate since
     English inherited it already Latin-borrowed in the pre-English
     Common-Germanic period, but the deep chain really does run through
     Latin, not straight to PIE — see `corrections.py`). Two scan hits were
     checked and are **correctly NOT bucketed as Germanic**: `aa` (the lava
     term really is a Hawaiian/Austronesian loanword) and `tong` (a genuine
     case of issue #5 below, not #6 — two real senses, tool [Germanic] vs.
     Cantonese secret-society [East Asian], merged into one entry, so
     neither bucket is simply "wrong").
   - **Pass 3**: Joe asked why the remaining 18 scan hits weren't checked
     automatically — fair question, answered directly: the scan signature
     alone isn't reliable (that's exactly what `aa`/`tong` proved), so blind
     bulk-correction would have introduced new errors, not fixed them. Went
     through all 18 individually instead. Only 2 were real bugs and got
     fixed: `ding` (purely onomatopoeic, no foreign donor — collided with a
     Mandarin/Zhuang homograph) and `rie` (obsolete spelling of "rye" —
     Germanic; the live English Wiktionary entry for "rie" has no etymology
     section of its own at all, fully hijacked by other-language homographs
     on the same page). The other 16 were genuinely correct as-is:
     - **Real loanwords** (correctly bucketed): `erekiteru`, `freeter`,
       `ponzu`, `randoseru` (Japanese); `kurus`, `oda` (Turkish); `preman`,
       `proa`, `semur` (Indonesian/Malay); `deel` (Mongolian, bucketed
       Turkic under this project's existing scheme).
     - **Genuine sense-merges**, same shape as `tong`/`aa` (issue #5, not
       #6 — two real different-origin senses collapsed into one entry, so
       no single bucket is "the" right answer): `cun` (Germanic verb +
       Chinese unit of length), `ming` (Old English + Chinese "fate"), `ou`
       (Hawaiian bird + Afrikaans "guy"), `sate` (Old English "satisfy" +
       Malay "satay").
     - **Unverifiable, left as-is**: `betawi` (Wiktionary page 404s — no
       longer exists) and `wie` (no English-language section on the live
       page as of 2026-07-22, despite our database having an entry — likely
       drift since etymology-db's Dec-2023 snapshot).
   - **Pass 4**: broadened the scan to Slavic/Indo-Iranian/Semitic families
     too (excluded from pass 2 since coffee/sugar/algebra are real Semitic
     loanwords, so expected more noise there — correctly so: most of the 70
     new hits were proper nouns, place names, surnames, or genuine
     Jewish/Slavic cultural terms — Herzegovina, Stalin, Pasternak, mohel,
     challah, tsar, commissar, feldscher, etc. — plausible on their face and
     not individually verified, lower priority since they're rare in normal
     prose). Filtered to everyday words and verified all of them: 17 real
     bugs fixed (`bench, bridge, deep, even, iron, moth, pretty, saw, tar,
     tell, lot, ham, bath, ye, ken, brim, cheese`). `cheese` is a `wall`-
     shaped special case (Old English already borrowed it from Latin
     *cāseus* in the Proto-West-Germanic period, pre-dating English itself —
     proximate correctly stays Germanic, deepest correctly goes to Latin).
     One checked and left alone: `jute` is a genuine Bengali loanword;
     its "deepest" showing Germanic is issue #2 (chain ordering), not this.
   - **Pass 5**: found while building the "Notable Influence" (level 2)
     feature — that feature surfaces whatever's in a chain's *interior* as
     the culturally-interesting middle donor, so an interior collision bug
     now produces a wrong answer for level 2, not just level "root" (deepest)
     like before. New scan signature: core-family direct donor + an exotic
     bucket somewhere in the interior + PIE as the root (this is exactly the
     shape that surfaced `increase` → bogus Semitic while designing the
     feature). 81 words matched; checked the ~40 most common individually.
     17 real bugs fixed: `pie, on, lake, baron, get, bark, grab, bun, phase,
     gross, acre, progress, slack, kennel, bar, tap, split`. The other ~20
     checked were genuine, several surprisingly so — `date` (Semitic-adjacent
     per a documented Arabic/Hebrew theory), `rose` (real Old Persian root),
     `mole` (the *culinary sauce* sense really is Nahuatl — another real
     sense-merge like `tong`), `cash` (historical coin sense really is
     Tamil/Sanskrit), `mate` (checkmate sense really is Persian "shah mat"),
     `caravan`/`tulip`/`check`/`musk`/`loot` (genuinely Persian/Turkic/
     Sanskrit/Hindi), `mandarin` (genuinely Sanskrit via Malay/Portuguese),
     `medicine` (the "Indigenous magic" sense really is an Ojibwe calque),
     `compound` (the enclosure sense really is Malay), `apricot`/`genie`/
     `talisman` (genuinely part-Arabic). ~40 of the 81 scan hits (rarer/
     technical words — `azimuth, saga, millet, rugby, turban, háček,
     ganges`, etc.) weren't individually checked this pass.
   - **Pass 6**: Joe asked whether one broad unified scan would've been more
     efficient than rediscovering new scan shapes reactively each time.
     Tried the broadest version first — any word with an exotic bucket
     *anywhere* in its chain — and it produced 11,487 hits, useless (almost
     all genuine loanwords and proper nouns; "exotic" isn't itself a bug
     signal). Tightened to the real signature: chain contains **both**
     Germanic **and** an exotic bucket (a word with a genuine native
     inheritance thread that also picked up a stray foreign edge) — 309
     hits. Most were clusters already implicitly validated by earlier passes
     (real Yiddish/Hebrew cultural terms: `kosher, mohel, shiksa, tuchus`;
     real Slavic loanwords: `pogrom, quark, kludge, knish`; real Malay/
     Turkish terms: `sambal, toko, deel, oda`) and weren't re-checked
     individually. Checked the everyday words not covered by any prior
     pass: 6 real bugs fixed — `boss, soy, stir, coach, gill, ban`. Left
     alone as genuine: `tea` (Dutch←Hokkien Chinese), `tattoo` (**three**
     real senses merged: Polynesian skin-marking, Dutch military-drum, and
     — double-checked specifically since it wasn't obvious — Hindi pony
     breed), `curry`/`junk`/`lime`/`poke`/`rook` (real sense-merges), `monkey`/
     `racket` (documented if disputed Arabic theories), `cravat` (genuinely
     French←German←Serbo-Croatian), `quartz` (genuinely German←West
     Slavic), `amen` (genuinely Hebrew — content is right, ordering is
     known issue #2, not this), `horde` (a genuine multi-hop
     French←German←Polish←Russian←Turkic chain).
   - Caught one more live while re-testing the app right after pass 6: `said`
     (past tense of "say") showed Semitic. Its actual Wiktionary page has
     zero Arabic content at all — purely Old English `sæġde`/`say`+`-ed` —
     so this wasn't even a same-page homograph collision like the others,
     more likely a case-merge with an unrelated Arabic name elsewhere in
     etymology-db's source data (known issue #5). Fixed the same way.
   - **70 words fixed in total across all six passes** (14 + 13 + 2 + 17 + 17 + 6 + 1).
     At the time, judged "not a general fix" and blocked on the raw CSV. That
     turned out to be exactly right — see the root-cause correction above:
     once the raw CSV/parquet arrived 2026-07-23, checking `said` directly
     confirmed the "case-merge with an unrelated Arabic name" guess above was
     correct, and the general structural fix (store case-sensitively, stop
     merging at conversion time) is what actually closed this out for the
     36-of-95 words that no longer need their override.
   - **Caught post-rewrite, 2026-07-23**: `and` showed Norse for Direct
     Source. Same #5-shape as `die`/`bull` (not a new bug class) -- the
     term_id bundles the common conjunction (100% native: Middle English/Old
     English `and` ← Proto-Germanic `*andi` ← PIE `*h₂énti`, verified against
     live Wiktionary, zero Norse content) with two obsolete, genuinely
     Norse-derived senses sharing the same spelling: "ande" (archaic noun
     "breath/zeal/envy," related to Latin *animus*) and "anden" (archaic verb
     "to envy"). Root cause was subtler than a typical merge, though: the
     conjunction's own legitimate Proto-Germanic/PIE content got sorted to
     appear *after* the archaic senses' Old Norse content, because the
     `_DEPTH_HINT` sibling tiebreak (see issue #2) ranks Norse shallower than
     Proto-Germanic -- correct for ordering fragments *within* one sense, but
     meaningless across senses that were never supposed to be compared in the
     first place. Fixed in `corrections.py`. Joe proposed a general rule
     ("always prefer Etymology 1") as the fix -- investigated and pushed
     back: the raw data has no column marking which Etymology-N section a row
     belongs to, and the closest implementable proxy (segment on English-
     stage restarts) is the exact heuristic already tried and rejected while
     building `convert_wikt.py`, because it breaks `law`/`sky`/`skill`/`table`
     (legitimate single-sense words that restart from an English-stage
     spelling citation multiple times). No reliable structural signal found
     yet to tell "restart = new sense" apart from "restart = spelling
     variant" -- multi-sense collisions like this remain a `corrections.py`
     hand-verified fix, not something the general pipeline can safely
     automate.
7. **New "Caribbean" bucket added 2026-07-22.** Joe asked whether Caribbean-
   origin words (`limbo`, `bomboclat`) had a home — they didn't;
   `buckets_wikt.py` had zero Caribbean/Creole/Taino entries, so such words
   fell into the vague `Other` catch-all. Added the bucket to
   `buckets_wikt.py`'s `NAME_TO_BUCKET` (Taino, Jamaican/Haitian/Louisiana
   Creole, Papiamento, Garifuna, etc. — for whenever the raw CSV comes back
   and `convert_wikt.py` can be re-run) and wired 7 individually-verified
   words into `corrections.py` so it's live now: `reggae` (Jamaican Creole),
   `hurricane`/`barbecue`/`canoe`/`cay` (all genuinely Taino via Spanish),
   `voodoo` (Louisiana Creole←Haitian Creole←West African). Found and fixed
   one more collision bug in the process: `calypso`'s deep chain was
   `Greek→PIE`, which turned out to belong to the unrelated Greek
   mythological nymph Calypso, not the music genre — real origin is Ibibio
   (West African) via Trinidad English, now `African (other)`. `bomboclat`
   isn't in the 71,630-word database at all (too recent/informal Jamaican
   Patois slang for this Wiktionary snapshot). `limbo` and `rum`
   deliberately left untouched — `limbo`'s dance-craze sense has no
   confidently documented origin (case-merge with the Latin "in limbo"
   sense, issue #5), and `rum`'s origin is genuinely disputed per Wiktionary
   itself (Dutch/Romani/Latin theories, none established) — inventing a
   confident Caribbean answer for either would be guessing, not verifying.
   Joe then asked for a general list of Caribbean words to try — verified a
   second batch same night, wired in 12 more: `hammock, maize, iguana,
   cannibal, guava, potato, cassava, cacique` (all clean Taino←Spanish),
   `papaya` (Lokono, the Arawakan family Taino belongs to), `irie`
   (Jamaican Creole), plus two good illustrations of the "bucket by donor
   language, not cultural association" rule: `obeah` (Caribbean creole,
   ultimately West African/Igbo — same shape as `voodoo`) and `duppy`
   (strongly Jamaican-associated, but its documented donor is directly Bube,
   Equatorial Guinea — no separate Caribbean-language hop at all, so it's
   `African (other)`, not `Caribbean`). Checked and deliberately NOT added:
   `tobacco` (genuinely disputed in Wiktionary itself — Arabic vs.
   Kari'na/Taino, unresolved), `mangrove` (disputed Arawakan-vs-Cariban,
   "ultimate origin... unconfirmed" per Wiktionary), `buccaneer` (real, but
   traces to Tupi — Brazilian, not Caribbean), `maroon` (traces to Spanish
   *cimarrón*, no indigenous-language hop documented).
8. **Missing inflected forms (mitigated 2026-07-22, revised same night).**
   The database has base forms but not most inflections — `wash` was
   present, `washing`/`washed`/`washes` were not, showing as `Unknown`.
   Fixed with a suffix-stripping fallback (tries common suffixes — `-ing`,
   `-ed`, `-s`, `-es`, `-ly`, `-er`, `-est`, `-ness`, `-ful`, `-less`, `-y`,
   etc. — and English spelling rules for the silent-e/doubled-consonant/
   y-to-i cases, e.g. `hoping`→`hope` vs `hopping`→`hop`, `furry`→`fur`)
   before falling back to Unknown. Raised the "washing machine" test
   sentence from 76.2% → 90.5% coverage. Doesn't catch compounds
   (`outside`) or other non-suffix gaps (`unless`) — those remain honestly
   Unknown. **Architecture bug found and fixed same night**: the stemming
   originally lived inside `WiktionaryResolver` only, so it only ever tried
   stemmed candidates against the Wiktionary table. `canines` → strip to
   `canine` → not in Wiktionary's table (only in the `ety` fallback data) →
   silently gave up as Unknown, even though `canine` alone resolved fine
   (Latin) via `ety`. Moved the stemming into `ChainResolver.resolve()` so a
   stemmed candidate is retried across *every* backend, not just whichever
   one happens to hold the base word.
   **Irregular verbs fixed 2026-07-23** (Joe: "held"/"became"/"upside" read
   Unknown). `held`/`became` are a genuinely different gap than the above --
   suffix-stripping can never reach them (`hold`->`held` is a vowel change,
   not a suffix, so no rule in `_SUFFIXES` would ever propose "hold" as a
   candidate). Added `_IRREGULAR_FORMS`, a direct lookup table of ~100 common
   irregular past-tense/participle forms, checked in `ChainResolver.resolve()`
   before the fuzzier suffix strips. Found and fixed a related bug while
   verifying it: `went` was silently resolving via a coincidental match --
   `WiktionaryResolver`'s title-case fallback (for words that only exist
   capitalized) matched "Went", an unrelated but real surname entry that
   happens to ALSO be native-Germanic, producing a plausible-looking answer
   for the wrong reason, before "went"->"go" (the real match) ever got a
   chance to run. Fixed by checking irregular/stem candidates before
   trusting a bare native-core result, not just on a total miss. `upside` is
   a different gap: a genuine compound word (up + side) with no entry of its
   own in the 72,784-word database at all. **Fixed 2026-07-23, see known
   issue #11** — rather than naive auto-splitting (which really is risky,
   e.g. "cupboard" naively splitting into "cup"+"board" would be a real
   word-shaped answer that's still wrong), built a verified `compounds.py`
   allowlist (736 words, `upside` included) plus a display mechanism that
   shows the two parts side by side instead of silently guessing one answer.
9. **Contractions weren't handled at all (fixed 2026-07-22).** The tokenizer
   splits on non-letters, so `you'll` became two tokens, `you` and `ll` —
   `ll` isn't a word, so it showed as `Unknown`. Worse than it looked,
   though: `don't` → `don` + `t` didn't just produce one `Unknown` token,
   it silently mis-resolved `don` as the real (unrelated) verb "don" (to put
   on clothing) instead of recognizing it as "do". Fixed by expanding
   contractions to their real component words *before* tokenizing
   (`_expand_contractions` in `analyzer.py`): irregular ones (`won't`,
   `can't`, `shan't`, `ain't`) get an explicit lookup table since `can't`
   only has one `n` — the generic rule would wrongly chop it to `ca` + `not`;
   the regular `n't` pattern (`isn't`, `doesn't`, `wasn't`, ...) is handled
   generically; `'ll`/`'ve`/`'re`/`'m` expand to `will`/`have`/`are`/`am`.
   `'s` and `'d` are deliberately left alone — genuinely ambiguous
   (is/has/possessive, would/had) and guessing wrong would misclassify
   possessives more often than it correctly expands a contraction; they
   degrade to a harmlessly-dropped length-1 token, not a wrong word.
10. **"Deepest Root" often means "oldest *attested* ancestor," not "oldest
    ancestor" — found and quantified 2026-07-23.** Joe spotted `cover` showing
    Latin for Deepest Root when etymonline shows a PIE root (`*wer-`, via
    `*op-wer-yo-`). Root cause, verified against both live sources: Wiktionary's
    page for `cover` *does* have the PIE root, but only in a separate
    etymology-tree diagram box — the main prose etymology paragraph (Middle
    English ← Old French ← Late Latin ← Latin `cooperiō`) stops at Latin.
    Both backends this project uses parse/derive from that prose form, not the
    tree box: `wikt_words.json` (via etymology-db) stores `chain: [French,
    Latin]` for `cover`, and the `ety` package independently returns the same
    ceiling (`enm → fro → lat`, confirmed by direct test). Neither backend
    ever queries live Wiktionary/etymonline at runtime — `WiktionaryResolver`
    is a lookup against a static file built once by `convert_wikt.py`, despite
    the name. `patrick` is the same shape at proximate: one-link chain
    (`[Latin]`), Late Latin *Patricius* not chained further to *pater*/PIE.
    **Quantified across the full database**: of 64,311 words with any
    foreign-donor chain, only 9,422 (14.6%) actually reach PIE. **44,165
    (68.7%)** end at an Indo-European branch (Latin 12,009, Germanic 7,235,
    French 6,097, Romance-other 5,933, Greek 5,384, Slavic 2,763,
    Indo-Iranian 1,969, Celtic 1,631, Norse 1,144) without reaching PIE, even
    though inherited IE vocabulary in those branches virtually always has a
    real PIE ancestor. (The remaining 10,724 correctly stop at a genuinely
    non-IE family — Semitic, Turkic, East Asian, etc. — where no PIE ancestor
    is expected.) So this isn't a `cover`-specific bug, it's systemic: for
    roughly two-thirds of resolved words, "Deepest Root" mode is silently
    reporting the oldest attested form rather than the oldest reconstructed
    one. Distinct from issue #2 (chain *ordering*) and #4 (word *coverage*) —
    this is chain *depth*, and it's now measured. **Re-checked 2026-07-23
    against the real raw etymology-db relation table** (not just the old
    prebuilt JSON) now that it's available — `cover` still stops at Latin,
    confirmed directly. So this is a genuine upstream data limitation, not an
    artifact of the old `wikt_words.json`/`ety` build: etymology-db's relation
    rows really don't carry the "etymology-tree diagram" PIE reconstructions
    Wiktionary displays separately from its prose. Getting this would need
    parsing Wiktionary's raw wikitext/tree-diagram templates directly, a
    different and larger source than what's on hand.

    **Joe's decision 2026-07-23**: wants full proto-language coverage rather
    than a UI caveat -- "I want that baseline of every word that has a PIE
    origin." Scoped into two pieces:

    - **Piece 1 — DONE 2026-07-23.** Redesigned "Deepest Root" to surface the
      specific reconstructed/attested form already sitting in data this
      project has, instead of collapsing it into the family bucket (see
      Project vision above and `convert_wikt.py`'s `root_lang`/`root_pie`).
      No new data. Verified on a 500-word closure-rate prototype first (see
      below) before building. As part of this, found and fixed a related bug:
      `convert_wikt.py`'s native-inheritance branch was overwriting the
      Germanic base entirely when a bare `has_root` PIE pointer existed with
      no foreign edge (`could` was showing root-only, no Germanic base).
      Also cleaned up `corrections.py`: 25 of its 95 entries had become fully
      redundant with the rebuilt pipeline (verified by comparing the ENTIRE
      chain, not just p/d, after an earlier pass wrongly flagged 36 including
      several -- like `kin`/`tar`/`get`/`bark` -- that still had a different,
      still-wrong chain interior) and were removed so they stop suppressing
      the new root_lang detail; 70 entries are still genuinely needed.
    - **Color scheme, 2026-07-23 (same request as Piece 2 kickoff).** Joe
      disliked the flat "muted gray" catch-all covering 12 of the 20 buckets
      and asked for every language distinguishable, with proto-languages
      coordinated as a lighter shade of their parent (e.g. Germanic blue ->
      Proto-Germanic light blue). The dataviz skill's categorical palette is
      a hard 8-hue ceiling (its own validator has no passing 9-hue ordering;
      "a 9th series is never a generated hue" is stated as non-negotiable) --
      the original 8 (already validated, unchanged) can't just grow to 20.
      Resolution: added one more lower-chroma "extended tier" hue family
      (hue~205, the largest open gap between the 8 core hues) differentiated
      by an ORDINAL lightness ramp -- not competing new categorical hues --
      for the 5 next-most-common buckets (Slavic, Indo-Iranian, Semitic,
      Turkic, East Asian); the remaining 7 rare buckets still share the flat
      muted tone. Proto-language shades use a validated lighter step of their
      parent hue (Proto-Germanic/Proto-West-Germanic -> Germanic-blue family,
      Proto-Italic -> Latin-yellow family [darker, since yellow was already
      near the light-mode ceiling], Proto-Celtic -> Celtic-violet family,
      Proto-Slavic/Proto-Indo-Iranian -> their own extended-tier hue).
      Node isn't installed on this machine, so the skill's JS validator
      couldn't run directly -- ported its exact math to Python (same OKLab/
      CVD/Machado-simulation formulas) and cross-checked the port against the
      documented default palette's own published numbers (CVD ΔE 9.1 light /
      8.4 dark, normal-vision 19.6/19.3) before trusting it for anything new,
      consistent with the skill's "never eyeball, always compute" rule. Every
      new color and every proto/parent pair passed the ordinal validator
      (monotone lightness, >=0.06 gaps, light-end contrast, single hue) in
      both modes before shipping. Wired into `app.py`'s `BUCKET_SLUGS`/
      `PROTO_SLUGS`/`root_slug()` and the CSS custom properties.
    - **Piece 2 — DONE 2026-07-23.** Before building, prototyped the closure
      rate on the actual top ~500 most common English words (a real
      Wiktionary frequency list, not a guess): 266/500 (53%) already reach
      PIE, 102/500 are the real gap, and of those only 17 (17% of the gap)
      would close via one more hop through a word's own compound/affix
      decomposition (the technique behind Piece 1's data). The dominant
      remaining blocker: **`etymology.parquet` has ZERO source rows for any
      proto-language** (Proto-Germanic, Proto-West Germanic, Proto-Italic,
      Proto-Celtic, Proto-Slavic, Proto-Indo-Iranian all appear only as
      *destinations* other words point to, never as their own entries with
      outgoing edges) — confirmed directly by querying the parquet. Checked
      whether the data exists on live Wiktionary before writing this off:
      it does — `Reconstruction:Proto-Germanic/fram`'s live page has a clean,
      fully-templated etymology section reaching PIE. So etymology-db's
      scraper simply never touched Wiktionary's `Reconstruction:` namespace,
      for any proto-language — a scraper gap in the source, not a missing-data
      problem.
      Built `convert_wikt.py`'s `root_term` field (the exact reconstructed
      spelling at a word's deepest point, e.g. `*handuz`, not just the
      language name) so the right Reconstruction page could be identified,
      then `fetch_reconstructions.py`: found the 1,366 unique proto-forms our
      words actually reference (not blindly all ~18,900 Proto-Germanic/etc.
      pages), fetched each one's raw wikitext, and parsed it for a confirmed
      PIE connection.
      **Caught a real accuracy bug before trusting any result**: the first
      version flagged Proto-Germanic `*handuz` ("hand") as reaching PIE by
      matching any `{{der}}` template, but the actual page opens with
      "origin uncertain" (`{{unc}}`), lists four competing theories, and even
      raises a non-Indo-European origin as a serious possibility -- the match
      was just grabbing one hedged "it has been suggested" sentence and
      reporting a disputed theory as settled fact. Fixed by restricting to
      Wiktionary's `{{root|...}}` template specifically -- its own
      deliberate, curated "the accepted root is X" tag (the same mechanism
      that generates the etymology-tree diagram), not any passing mention --
      plus a belt-and-braces skip of any page opening with `{{unc}}`/`{{unk}}`.
      Verified this correctly resolves `fram` (clean case) and correctly
      declines `handuz`/`wintruz` (genuinely disputed cases, confirmed by
      reading the actual pages) before running the full batch.
      **Full-run result**: of 1,366 targets, 509 (37.3%) were genuine 404s
      (the cited form has no dedicated Reconstruction page -- often an
      inflected/compound citation form, not Wiktionary's lemma spelling); of
      the 857 pages that did fetch, 94 had a confirmed `{{root}}` tag and got
      patched to `root_pie=True` (common words newly correct: `free`, `word`,
      `day`, `head`, `name`, `craft`, `month`, `brown`, `crow`, the weekday
      names). That's a real, honestly-earned ~6.9% closure of the targeted
      proto-language gap, not the dramatic "close the whole gap" outcome --
      consistent with what the prototype already predicted: most of this
      specific gap is genuinely undocumented on Wiktionary itself, not a
      scraper limitation. Re-validated the full test suite (all 16 core
      words, all 3 modes) after patching; all pass. `reconstruction_cache.json`
      persists the fetch results so a re-run doesn't refetch.
11. **Compound-word display (built 2026-07-23, closes the `upside` gap noted
    in issue #8).** Joe: "I want to add the etymology tree feature!" led into
    testing, which surfaced `upside`/`held`/`became` as Unknown (issues #8/#9
    fixed held/became same night); `upside` was different — a genuine
    two-word compound (`up`+`side`) missing entirely from the 72,784-word
    database, not an inflection gap. Design agreed with Joe over several
    turns: **only ever display a word as its two component parts if the
    whole word currently resolves to Unknown on its own** — a word that
    already resolves (even a real compound like `understand` or `husband`)
    is never touched, which structurally sidesteps having to judge whether a
    word's *meaning* is compositional (compounding is a spelling-formation
    question here, not a semantics one).
    - **Scope-finding**: tried auto-mining `compound_of`/`has_affix`/
      `has_confix` relation rows already in `etymology.parquet` for every
      currently-Unknown term first (100,888 candidates) — sampling showed
      most were root+bound-suffix derivatives (`abandonedly`→`abandoned`+
      `ly`), not real word+word compounds, and no clean reltype/spelling
      signal separated the two. Joe redirected to a curated external list
      instead: every single-token entry from
      https://www.proofreadingservices.com/pages/compound-words-list
      (1,522 of them) run through the resolver — **772 already resolved
      fine** (left untouched per the rule above), **749 came back Unknown**
      (one extra, `superchargebowleg`, was a source-page scraping artifact —
      two words concatenated with no separating comma — and discarded, not
      a real word).
    - Of those 749: **630 had a clean split readable straight from the
      word's own `compound_of`/`has_prefix`/`has_affix`/`has_confix` rows**
      in `etymology.parquet` (same real per-word data `convert_wikt.py`
      already uses — these words just never got an entry of their own in
      `wikt_words.json`, only a relation row pointing at their parts).
      Mechanical parsing handled interfix markers (`crafts-man` recorded as
      `craft`+`-s-`+`man`) and sense-tagged terms (`dose#noun`); 23 needed
      hand resolution (infix reconstruction, e.g. `craftsman`→`crafts`+
      `man`; or a missing part fixed elsewhere, see below). **119 had zero
      local data at all** (the `upside` shape) — found by brute-force
      segmentation (every split point where both halves already resolve),
      hand-picking the correct split where more than one candidate existed
      (all straightforward, undisputed compounds — no etymological
      judgment calls, e.g. `bagpipe`→`bag`+`pipe`).
    - **Deliberately excluded, stays Unknown rather than a guessed split**:
      `hijack`/`highjack` — live Wiktionary's actual etymology is "possibly
      a blend of *highway* + *jacker*," explicitly **not** a `hi`+`jack`
      compound, so segmenting it that way (which the brute-force search
      would happily do, since both "hi" and "jack" independently resolve)
      would present a fabricated folk etymology as fact. `bulldozer`/
      `underachiever`/`outlying` — root+suffix words (`bulldoze`+`er` etc.),
      not real two-independent-word compounds, don't fit this feature's
      display shape. `eggnog`/`gridlock`/`longshoreman`/`lumberjack`/
      `shuffleboard`/`surfboard` — clean compound_of data, but the missing
      part (`nog`/`grid`/`longshore`/`lumber`/`shuffle`/`surf`) is itself
      genuinely disputed or undocumented on live Wiktionary (checked each
      individually: `grid` is a clipping of griddle/gridiron with no donor
      language stated; `lumber` is "exact origin unknown" per Wiktionary
      itself; `longshore` is aphesis of "alongshore" with no separate donor
      chain; `nog`'s etymology section is marked missing/incomplete on the
      live page; `shuffle` and `surf` both have stated theories but no
      donor language given/confirmed) — filling any of these in would be
      guessing, not verifying, so their compound words stay honestly
      Unknown. `tomcat`/`grandma` — `tom`/`ma` don't resolve as independent
      words in current data and weren't individually researched this pass
      (low value, only 2 words). `shoephorn` — not a real word, a scraping
      artifact of "shoehorn" (which already resolves fine on its own) in
      the source list.
    - **Two small resolver-level fixes made along the way**, needed as
      compound *parts*: added `dug`→`dig`, `trod`/`trodden`→`tread`,
      `bred`→`breed`, `bitten`→`bite` to `_IRREGULAR_FORMS` (same gap shape
      as issue #8's original held/became fix, just a few forms that pass
      missed); added `selves` to `corrections.py` (irregular f→v plural of
      `self`, needed for `ourselves`/`themselves` — the existing
      suffix-stripper only undoes regular `-es`, not this consonant
      alternation). Also added `zoo` (clipping of "zoological garden" ←
      "zoology" ← Greek) and `plow` (Wiktionary explicitly cross-references
      it as the American spelling of `plough`, whose entry it now mirrors
      exactly) to `corrections.py` — both common words that were missing
      entirely and needed as compound parts (`zookeeper`, `snowplow`),
      verified against live Wiktionary before adding.
    - **Final set: 735 words** (from the curated-list sweep) **+ `upside`**
      itself (the word that started this — not on the external list, added
      directly) **= 736 words** now show a split display instead of
      Unknown. Every entry's parts were confirmed to already resolve to a
      real bucket via the resolver as it stands (not just assumed), and a
      strict `part1+part2 == word` reconstruction check caught 2 bad
      entries before shipping (`headwaters`→`head`+`water` missing the "s";
      `indoor`→`within`+`door`, a related_term value that doesn't literally
      reconstruct the word) — both fixed to the literal spelling.
    - **Architecture**: `compounds.py` holds the `COMPOUND_SPLITS` word→
      (part1, part2) dict (with the full exclusion rationale in its own
      docstring). `ChainResolver.resolve()` (`resolver.py`) checks it only
      as the last fallback, after every real resolution path (direct
      lookup, irregular forms, suffix stemming) has failed — it recurses
      through `self.resolve()` (not `self._try()`) for each part, so a part
      that's itself a known compound resolves too (`outdoorsman`→
      `outdoors`+`man`, and `outdoors` itself →`out`+`doors`), flattening
      nested results into one flat parts list rather than a tree, so the UI
      shows a simple row of component words. `Resolution`/`ResolvedView`
      gained a `parts: Optional[List[ResolvedView]]` field; `analyzer.py`'s
      `analyze()` splits a compound token's weight evenly across its parts'
      buckets (e.g. `upside` contributes 0.5 Germanic + 0.5 Germanic; a
      mixed-origin compound like `purebred` contributes 0.5 Latin + 0.5
      Germanic) rather than counting once under one answer — `counts`/
      `resolved_tokens`/`unknown_tokens` are fractional floats now, not
      just ints. `app.py` renders a split word as the whole word
      (dotted-underlined, bold) followed by each component as its own
      small colored chip joined with "+" — verified visually via direct
      HTTP POSTs to the running dev server in both Direct Source and
      Deepest Root modes (mixed-origin parts render in their own correct
      colors, e.g. `purebred` → Latin `pure` + Proto-Germanic `bred`).
    - **Honest scope note**: this closes the gap for exactly the ~750 words
      the one curated external list surfaced, not compound words in
      general — the broader database almost certainly has many more
      Unknown compounds this list didn't happen to include. Extending
      further would mean either a bigger/different source list or revisiting
      the auto-mined `compound_of` data with a better noise filter than the
      one that failed here.
12. **Bar-graph drill-down, tree redesign, connector/per-word toggles, and a
    batch of Deepest Root bugs — 2026-07-23.** One long session, Joe's own
    laundry list (confirmed back to him numbered before any coding, per his
    explicit request) plus several "while you're at it" additions mid-turn.
    - **Bug: `with`.** Deepest Root stopped at Old Norse. Verified against
      live Wiktionary: Old Norse is cited only as a COGNATE for `with`
      ("an earlier model of this meaning shift exists in cognate Old Norse
      við"), not a real ancestor — the real chain is Middle English <- Old
      English wiþ <- Proto-West Germanic <- Proto-Germanic *wiþrą, no PIE
      connection stated. Fixed via `corrections.py` (the spurious-edge part
      of this bug is a one-off collision, not systemic).
    - **Bug: `low`/`lowest`.** Deepest Root stopped at Old Norse instead of
      reaching PIE. `low` genuinely has 6 separate etymologies on Wiktionary
      sharing one page (adjective, the verb "to moo", etc.) — same #6-shaped
      collision as `and`/`die`/`bull`. Fixed via `corrections.py`.
    - **Bug: `computer`.** Direct Source showed PIE directly — impossible in
      principle (no English word borrows straight from a proto-language).
      Root cause: `computer`'s own raw entry is a bare `has_root` STUB
      (`chain: ["PIE"]`, `prox_kind: "root"` — no real derived_from/
      borrowed_from/inherited_from edge of its own), while the real chain
      (French<-Latin<-PIE) lives at a different term_id, "compute". **Fixed
      generally, not per-word**: `Resolution`/`ChainLink` gained a
      `prox_kind` field (from convert_wikt.py's own field, previously
      computed but not exported to the resolver layer); `ChainResolver.
      resolve()` now only trusts a chain immediately when `prox_kind !=
      "root"` — a bare-stub chain is retried through irregular/stem
      candidates first (same precedence slot as the existing "went"/"Went"
      homograph fix), falling back to the stub only if nothing better
      resolves. Fixes every word with this exact gap shape, not just
      "computer".
    - **General fix: PIE excluded from Notable Influence (level 2).** Joe's
      call: PIE is the shared ancestor of virtually the whole Indo-European
      chain, the opposite of "distinctive," so it should never be the
      "notable middle donor" answer (that's what Deepest Root is for).
      `_pick_influence` (resolver.py) now filters PIE out of the chain
      before applying its existing exotic-family/fallback logic.
    - **General fix: proto-languages can never be non-terminal.** Joe: "the
      broader bug" behind with/low — a reconstructed proto-language can
      never be chronologically shallower than an attested language it's
      ancestral to. Two-part structural fix in `convert_wikt.py` (not a
      per-word patch), applied via a full `wikt_words.json` regeneration:
      (1) **PIE-terminal invariant** in `resolve_term()` — if the "PIE"
      bucket appears anywhere but last in a word's chain, it's moved to the
      true end (root cause is the same open multi-sense-merge problem as
      the `and` writeup, not reliably fixable in general, but THIS specific
      consequence always holds regardless of which sense produced the data).
      **Scoped to PIE specifically, not every proto-tagged bucket** — see
      the regression note below for why. (2) **Fine-grained `_DEPTH_HINT`
      table** — the old table lumped a family's stages into one tier with no
      internal order (Old English and Middle English were BOTH rank 0); the
      new table gives every attested stage its own tier, strictly increasing
      with age, so e.g. Old English now correctly outranks (sorts deeper
      than) Middle English, per family.
    - **Regression caught and fixed the same session, before it shipped**:
      the first version of the depth-table rewrite put modern foreign forms
      (French, German, ...) at the SAME tier as English/Scots. That broke a
      load-bearing property the old table had (accidentally, but
      critically): an English-stage-FIRST branch must always outrank ANY
      foreign-first branch, full stop — found via `back`, which has a real
      (different-sense) `borrowed_from French bac` edge sitting alongside
      its genuine native lineage; the tie let French win node order and
      flip `back`'s Direct Source to French. Fixed by giving English-stage
      names their own reserved low band (0-1) and starting every foreign
      tier at a fixed +10 offset, so English-stage always wins regardless of
      how many foreign sub-tiers exist above it. Also what pushed the
      PIE-terminal invariant (above) to be scoped to PIE only, not every
      proto-tagged bucket: `back`'s real native chain legitimately STARTS at
      a Proto-West-Germanic-tagged edge, and the first (too-broad) version
      of the invariant demoted that whole bucket, letting the French edge
      back in a second way. Full regression suite (all historically-verified
      test words, plus the known multi-sense-collision words with existing
      corrections.py overrides) re-verified clean after each fix.
    - **Bug: `back`'s Deepest Root** (found via the regression testing above,
      not one of Joe's originally-reported bugs, fixed anyway since the
      evidence was already in hand): even after Direct Source was fixed to
      Germanic, root_lang showed "French" — the French collision edge
      happened to sort right before the native branch's own has_root PIE
      pointer, so "closest name before PIE" picked it. Fixed via
      `corrections.py` (clean native-only chain: Middle English <- Old
      English bæc <- Proto-West Germanic *bak <- Proto-Germanic *baką <- PIE
      *bʰogo, confirmed directly from the raw parquet rows).
    - **Bug: `what` showing two "Proto-Indo-European" tree nodes** —
      diagnosed as NOT a bug: `*kʷód` (the reconstructed pronoun stem) has
      its own further `has_root` citation to `*kʷ-` (a deeper root within
      PIE itself), both legitimately labeled "Proto-Indo-European" since
      that's one language stage. Real data, just visually confusing as two
      adjacent same-language boxes in the old flat-list renderer — folded a
      display fix into the tree diagram redesign (below) rather than
      treating it as a separate code bug.
    - **Etymology tree branch ordering** — `build_etymology_trees.py`
      previously applied NO depth ordering to its top-level branches at all
      (raw row order). Now sorts branches shallowest-first by the same
      `_depth_hint` used above (imported from convert_wikt.py), via a stable
      sort that only reorders the top-level list — never merges or nests
      branches together (that was tried and reverted for a different reason,
      see this feature's original 2026-07-23 entry above), so it can't
      fabricate a relationship the data doesn't support.
    - **New feature: free-floating tree diagram.** Joe: "I am thinking a
      free floating look... think of the wiktionary tree or the old google
      result for etymology," clarified further: same-generation forms (e.g.
      every "Old English" node, across whatever branch) share ONE horizontal
      axis; parent->child depth within a single branch runs vertically.
      That's a "row = generation tier (via `_depth_hint`), column = branch"
      layout — `build_diagram()` in `app.py` computes it directly (no JS/
      charting library; renders as plain SVG). Generation tiers are
      compressed to only the ones actually used in a given word's tree (a
      word rarely touches more than 3-5 of the ~19 possible tiers) so the
      diagram doesn't waste height on empty rows. Also applies the `what`
      cosmetic fix above: a node whose only child shares its exact language
      AND is a `has_root` edge merges into ONE box with both terms stacked.
      Static/auto-layout only (Joe chose this over an interactive draggable
      canvas) — added as a **toggle** (List / Diagram) alongside the
      existing indented-list view, not a replacement, per Joe's explicit
      choice. Verified via direct HTTP POSTs: `walk`'s branches correctly
      share rows across columns (`walken`'s and `walkien`'s "Middle
      English"/"Old English" land on identical y-coordinates), and `what`'s
      merge produces one box reading "*kʷód / *kʷ-".
    - **New feature: bar-graph bucket drill-down.** Joe: click a bucket bar
      (e.g. Germanic) to expand a sub-breakdown of the specific languages
      making it up, sized by their share WITHIN that bucket -- not a word
      list. Needed data the pipeline didn't persist: `wikt_words.json` only
      stored the SINGLE deepest specific language name (`root_lang`), not
      the specific donor behind every chain step. Added `chain_langs` (the
      full parallel array) to `convert_wikt.py`'s output; `ChainLink`/
      `ResolvedView` gained a `specific_lang` field threaded through
      `resolver.py`. Rendered as native `<details>/<summary>` disclosure
      elements (no JS needed) -- expanding "Germanic" shows e.g. "Native
      (inherited)" (the dominant case -- most of the Germanic bucket in
      Direct Source mode is native inheritance, not borrowing FROM a
      Germanic language) alongside real cross-Germanic borrowings like
      "Dutch". **Bug caught and fixed during testing**: a word's own
      recorded first edge can legitimately be a bare proto-language name
      (e.g. "with"'s chain_langs[0] is "Proto-West Germanic") even at the
      Direct Source level, which would've shown as if "Proto-West Germanic"
      were a real donor language -- filtered proto-names out of this
      specific breakdown (they still display correctly at the Deepest Root
      level, where naming the proto-form IS the point) and grouped them
      under "Native (inherited)" instead.
    - **Sub-language color shading.** Joe: each specific language within a
      bucket should be a distinguishable shade of that bucket's hue (his
      framing: "Germanic sub-languages: sky blue, dark blue, neon blue...").
      Deliberately a LIGHTER-WEIGHT scope than the main palette: the 8-hue
      categorical palette and the proto-language shades (in the Deepest Root
      color scheme, 2026-07-23 earlier) both went through the dataviz
      skill's full CVD-validated ordinal-ramp process; this instead
      generates shades on the fly in Python (`language_shades()` in
      app.py) by spreading lightness/saturation around the bucket's base
      hue, deterministic per language name, no separate light/dark-mode
      variant. Reasonable for what could be dozens of specific donor
      languages per bucket (impractical to hand-validate each one the same
      way the original 8 were) -- not re-validated against the CVD
      simulator the way the core palette was, so treat it as "visually
      distinct" rather than "accessibility-validated."
    - **New feature: connector/function-word toggle.** A standalone checkbox
      (independent of the Direct/Influence/Root mode tabs, applies to all
      three) that removes closed-class function words (articles,
      prepositions, conjunctions, pronouns, common auxiliary/modal verbs --
      `CONNECTOR_WORDS` in analyzer.py) from the token stream entirely
      before analysis, same as if they were never typed. Deliberately
      conservative -- only genuine closed-class words, no ordinary content
      words even if common.
    - **New feature: per-word list sort/filter.** A dropdown alongside the
      existing "Per word" list: Input order (unchanged default), Language
      group, Alphabetical, Most Distinctive first (rarest/most unexpected
      origins surfaced first -- the two creative additions Joe asked for
      beyond his own two examples), and Frequency (dedupes repeated words,
      shows a `×N` count, most-repeated first -- most useful on long texts/
      whole books). Display-only (`sort_per_word()` in app.py) -- doesn't
      touch `Analysis.per_word` itself, which stays input-order as the
      source of truth for the percentage breakdown.
    - **Status tracking**: Joe asked for a visible task-status readout
      before this round of work started ("Task 1: Done Task 2: in
      progress...") -- used the harness's own task-list tool for this
      (TaskCreate/TaskUpdate) rather than building a custom status display,
      since it already renders a live checklist to Joe directly.
    - Three full `wikt_words.json` regenerations and two `etymology_trees.
      json` regenerations ran over the course of this session (proto-
      invariant + depth-hint fix, the depth-hint regression fix, then the
      `chain_langs` export) -- full regression suite (all historically-
      verified test words, all known multi-sense-collision words with
      existing overrides) re-verified clean after each one.

13. **Native-word drill-down granularity — RESOLVED 2026-07-24.** Joe asked
    (while discussing an external tool, `engsource`) whether the bar-graph
    drill-down (known issue #12) could show specific native stage names --
    "Old English", "Middle English", "modern", "Middle High German" -- when
    you click into the "Germanic" bucket, instead of every native word being
    lumped into one flat "Native (inherited)" label. Investigated `engsource`
    (a Wiktionary-XML-dump etymology extractor) as a possible new data
    source and concluded it **wasn't needed**: the raw `etymology.parquet`
    data already records this detail (e.g. `back`'s own rows literally cite
    Middle English -> Old English -> Proto-West Germanic -> Proto-Germanic)
    -- this project's own pipeline was just discarding it, not missing it.
    Added `english_stage_seq`/`native_stages` to `convert_wikt.py`'s
    `resolve_term()` (the real, deduped, order-preserved sequence of English-
    stage citations for a word) and threaded it through `WiktionaryResolver`
    (native-core words now report the nearest real stage name instead of the
    generic "English (native core)" placeholder) and `app.py`'s
    `bucket_language_breakdown()` (proto-language names filtered out of this
    specific view -- they're not real "donor" languages at the Direct Source
    level -- and grouped under "Native (inherited)" instead).
    **First fix attempt was incomplete**, caught before shipping: it only
    prepended the native stage name when a word's chain had NO foreign
    content at all (the narrow `could`-shaped case, a bare `has_root` PIE
    pointer with nothing else). But the common case (`the`, `walk`, `what`,
    `back`) records its Proto-Germanic-family content as an ordinary
    `inherited_from` edge inside the SAME native-lineage group as the
    Middle/Old English citations -- since only literal English-stage NAMES
    are filtered out of the `foreign` list (not Proto-Germanic-family names),
    `foreign` wasn't empty for these words, so the narrow fix's condition
    never fired and they kept showing the deep proto-name instead of the
    nearest stage. **Real fix**: check `foreign[0]`'s reltype -- if
    `inherited_from` (continuing the SAME native thread), prepend the
    nearest native stage name; if `borrowed_from` (a genuine separate
    foreign donor, e.g. `boss`'s real Dutch/French edges), leave untouched.
    Validated directly against raw parquet rows for a dozen test words
    before each of two full `wikt_words.json` regenerations (both ran
    unusually slowly, ~15-20 min vs. the session's earlier typical 2-4 min --
    monitored via background-process memory checks as a progress heuristic
    since `convert_wikt.py` has no incremental logging; concluded as general
    system slowness, not a hang, no code-level cause found). Verified live
    via HTTP POST: analyzing "the walk was what could be called an old back
    and forth." in Direct Source mode shows the Germanic bucket (91.7%)
    correctly splitting into "Middle English" (63.6%) and "Native
    (inherited)" (36.4%) sub-bars on click.
14. **Bare-PIE-root stubs presented as a direct donor — mostly closed
    2026-07-24, one honest gap remains open (see below).** Joe caught
    `vitamin` showing "PIE" for Direct Source -- impossible in principle, no
    English word borrows straight from a 6,000-year-old proto-language.
    Same shape as `computer` (known issue #12) but a harder-to-catch variant:
    `computer`'s bare `has_root`-only stub (`chain: ["PIE"]`, `prox_kind:
    "root"`) got caught because a FULLER chain existed under a different
    term_id (`compute`) that `ChainResolver`'s existing stem-retry logic
    could find. `vitamin` has no such sibling term_id -- its raw data is
    genuinely just `has_root -> PIE *gʷeyh₃-` plus three
    `etymologically_related_to` mentions (`vital`, `amine`, `amino acid`,
    correctly excluded from the chain as non-ancestry "see also" tags, not
    donor edges) -- so the existing retry fell through and `ChainResolver`
    trusted the bare stub as if it were a real answer. Joe then caught
    `critical` and `growth` showing the identical shape, and a full-database
    scan found **2,158 words** total (`prox_kind == "root"`, chain built
    from nothing but `has_root` pointers). Joe's explicit direction: don't
    hand-patch the words found by the scan -- **eliminate it as an
    invariant** so it can never happen for any word, found today or not.
    Two-part fix, done in that order:
    - **Part 1 (required, general, closes the bug for every word, not just
      the ones found so far)**: `Resolution.view()` (resolver.py) now
      refuses to render a `prox_kind == "root"` chain as a Direct Source or
      Notable Influence answer -- returns the same `Unknown` shape used
      everywhere else for "no real answer" (already correctly handled by
      `analyzer.py`'s existing `Unknown`-bucket aggregation, no analyzer/UI
      changes needed). Deepest Root is deliberately untouched: the PIE
      citation itself is real, verified Wiktionary data, so it still shows
      -- only the false claim that it's an immediate/direct donor goes away.
      This is a single rendering choke-point every backend and fallback path
      flows through, so it's a structural guarantee, not a per-word patch.
    - **Part 2 (recovers a real answer wherever the data actually supports
      one, instead of leaving it at Unknown)**: a new post-processing pass in
      `convert_wikt.py`'s `main()`, run after the main per-term_id loop so
      root words are guaranteed already resolved. Three mechanisms, all
      using relation types already sitting in `etymology.parquet` but never
      previously read by the chain-building code (verified against the raw
      data before trusting any of them -- no guessing):
      - `_patch_root_stubs`: if a stub's raw data ALSO records a
        `has_prefix_with_root`/`has_confix`/`back-formation_from`/
        `clipping_of` pointer to an English word that already resolves to a
        real, non-stub entry (e.g. `growth` -> `grow`; `edit` -> `editor`;
        `demo` -> `demonstration`), the derived word inherits the root's
        ENTIRE resolution (chain, prox_kind, root_lang, etc.) -- a recorded
        native affix or trimmed-off suffix isn't itself a donor language, so
        the root's donor story IS the derived word's donor story. Iterates
        to a fixed point so a chain of derived-from-derived stubs resolves
        too, not just one hop. Priority-ordered (`has_prefix_with_root`/
        `has_confix` checked before the less-specific `has_affix`/
        `has_prefix`) so a real stem (e.g. `postulo` for `expostulate`) wins
        over a bare prefix fragment (`ex`) when a word's data has both --
        the bucket answer is identical either way when both point to the
        same language, this only affects which specific root_term displays.
      - `_patch_foreign_root_stubs`: a smaller population (~11 words, e.g.
        `dipteran`) cite their root DIRECTLY as a foreign-language term
        (Latin/Greek/etc.) rather than through an English intermediate --
        treated as a direct one-hop chain to that language, since the
        language name is explicitly recorded, not inferred.
      - `_extract_auto_compounds`: ~52 words are recorded as a genuine
        `compound_of`/`blend_of` split into two-or-more real English words
        (e.g. `clavinet` = `clavichord` + `clarinet`, a real Hohner
        instrument name) rather than one inheritable root. Doesn't
        synthesize a fake merged chain -- reuses the EXISTING compound-
        display mechanism from known issue #11 instead: removes the stub
        entry entirely (so it falls through to the normal "no chain" path)
        and writes `{term: [part, part, ...]}` into a new top-level
        `auto_compounds` key in `wikt_words.json`, loaded by
        `WiktionaryResolver` and consulted by `ChainResolver`'s existing
        compound fallback (`resolver.py`) alongside -- but kept separate
        from -- `compounds.py`'s 736 hand-verified `COMPOUND_SPLITS`
        entries, since this data comes straight from Wiktionary's own tag,
        not individually hand-researched the way each `compounds.py` entry
        was. Only fires when EVERY named part already resolves on its own.
      **Result, verified against the real regenerated database (72,732
      words) via a database-wide invariant check (zero words with
      `prox_kind == "root"` render a non-Unknown direct/influence bucket)
      and the full regression suite**: of the original 2,158 stubs, **913
      now get a real, correct answer** (850 via root-inheritance, 11 via a
      directly-cited foreign root, 52 via auto-detected compound/blend
      splits). **1,245 words remain honestly `Unknown` for Direct
      Source/Notable Influence** (Deepest Root still correctly shows their
      real PIE citation) -- this is the genuine, currently-open remainder:
      every other relation type in the raw data (`cognate_of`,
      `doublet_with`, `etymologically_related_to`) was checked and found to
      only offer hedged "related to" mentions, not real asserted ancestry,
      for these specific words. Presenting those as fact would be guessing
      (rule 2), so this is where the pipeline honestly stops without either
      (a) accepting a lower-confidence "inferred" tier using
      `etymologically_related_to` data (a philosophy change from "verified
      fact only"), or (b) a different data source entirely (hand-research
      into `corrections.py` one word at a time, or a live etymonline-style
      scrape). **Not yet decided -- Joe's call, asked and awaiting answer**
      as of this entry.
15. **"No entry at all" gap closed for derived words -- 2026-07-24.** Joe
    caught `consistency`/`mindset`/`professional` reading Unknown on Direct
    Source. Three different root causes, each needing its own fix:
    - `consistency`: genuinely absent from etymology-db's snapshot (zero raw
      rows at all) -- `consistent` resolves fine. Closed at the resolver
      layer: `resolver.py`'s suffix-stemmer gained a dedicated `-cy` rule
      (consistency -> consistent, urgency -> urgent, accuracy -> accurate),
      restricted to stems >=5 characters after checking the full 908-word
      "-cy" gap in the raw data directly -- that floor is the exact line
      between 129 genuine hits and real false positives at shorter lengths
      (`chancy` is "chance"+"-y", not related to "chant"; `spacy`/`stacy`/
      `trancy`/`fleecy` were the same shape). Also added `-al` to the
      stemmer (professional -> profession; covered by the existing silent-e
      machinery, no new logic needed).
    - `professional`/`mindset`: real Wiktionary structure exists
      (`has_prefix_with_root profession`, `compound_of mind+set`) but
      `convert_wikt.py`'s three stub-patching passes (`_patch_root_stubs`,
      `_patch_foreign_root_stubs`, `_extract_auto_compounds`, issue #14)
      only ever looked at terms that ALREADY had a thin has_root stub --
      both words had NO entry at all (resolve_term returned None outright),
      so they were silently skipped every time. Widened all three passes'
      guard from "entry is a stub" to "entry is a stub OR doesn't exist".
      **Database-wide effect: 213,123 resolved words, up from 72,732** (+164k
      words closing this exact gap-shape database-wide, not just the 3
      reported).
    - That scale required real guardrails, found while verifying before
      shipping (rule 2): (a) the root-word lookup previously fell back to
      `.lower()`/`.capitalize()` on a miss -- reintroduced the exact "went"/
      "Went" bug (issue #12) at new scale (`forewent` -> "went" ->
      capitalized surname "Went"; `digraph`/`dimer` -> "di" -> the name
      "Di"; `aldrin` -> the tree "alder" instead of chemist Kurt Alder) --
      now requires exact case. (b) hub words used by many derived terms
      (has_prefix_with_root targets like "auto", "tag", "on", "person",
      "phase") turn a PRE-EXISTING one-off collision in the underlying
      database into a much bigger blast radius, since dozens-to-hundreds of
      derived words now inherit that hub's answer. Found and fixed two:
      **`tag`** (etymology-db's data for this term_id only captured the
      rare Aramaic "crown" sense, not the real Germanic "label" sense --
      verified live, fixed in `corrections.py` + `tree_corrections.py`) and
      **`auto`** (a circular `clipping_of autorickshaw` -> `derived_from
      Hindi` artifact was outranking the real `derived_from Ancient Greek
      αὐτός` edge -- same fix, both files). `corrections.py` is now applied
      INSIDE `convert_wikt.py` before the three patches run (previously only
      applied later, at `resolver.py` load time -- too late for a hub fix to
      reach words that inherit from it, e.g. `detag`). A scan for the same
      "exotic-family-first-then-core-family-later" signature CLAUDE.md's own
      issue #6 passes 5/6 used to find these by hand turned up 256 more hub
      words (1,101 derived-term exposure) -- too many to hand-verify one at
      a time, so rather than guess, `_is_reliable_root()` now EXCLUDES any
      hub whose own chain shows that signature from being used as an
      inheritance source at all (derived word stays honestly Unknown). Also
      added an explicit `HUB_EXCLUSIONS` denylist (`corrections.py`) for
      `logy`/`poly` -- a shape the signature check can't catch, since each
      term_id's own correct standalone answer (Dutch "sluggish" adjective;
      Latin plant name) is genuinely correct on its own terms but is a
      different sense than the "-logy"/"poly-" combining form dozens of
      derived words actually need, and the source data has zero ancestry
      info for that combining-form sense under either term_id at all.
    - Full regression suite (all historically-verified test words from
      Current State, all multi-sense-collision corrections including the two
      new ones, the compound-display feature, the issue #14 stub guard) and
      a live HTTP POST re-verified clean after regenerating both
      `wikt_words.json` and `etymology_trees.json`. **Honest residual**:
      the 256 excluded hub words themselves were not individually
      hand-verified beyond the automated signature check -- most are
      probably fine (issue #6 pass 5 found several flagged words were
      genuinely correct on inspection, not bugs), but none were used as an
      inheritance source this run, so no further coverage was gained OR
      risked from them either way.
16. **Every feature must pool from the same database -- structural fix,
    2026-07-24.** Joe (all-caps, repeated, then again as an explicit end-of-
    session goal): "there should be no way that one feature has access to
    information about a word that another feature doesn't." Triggered by
    testing issue #15: `professional`/`mindset`/`consistency` were fixed in
    the analyzer but STILL showed "No recorded etymology data" in the
    Etymology Tree, because neither fix mechanism (data-layer inheritance,
    pure resolver-layer stemming) had any tree-side equivalent --
    `tree_corrections.py` (issue #6/#12's per-word answer to this same
    complaint) doesn't scale to a mechanism that touched ~164,000 words.
    Same session also surfaced three more real bugs while testing:
    - **`ran`** resolved as an unrelated Japanese loanword. Root cause: "ran"
      has no entry of its own at all (verified against the raw parquet);
      WiktionaryResolver's capitalize() fallback landed on "Ran" (a real,
      unrelated Japanese-related entry with a genuine chain). The original
      "went"/"Went" fix (issue #12) only protected a case-fallback match
      that was CHAINLESS -- "Ran" has a real chain, so the old first-check
      trusted it immediately without ever trying "ran"->"run" (already in
      `_IRREGULAR_FORMS`). Fixed generally: `Resolution` gained
      `case_fallback: bool`, set by `WiktionaryResolver` whenever a match
      only succeeded via `.capitalize()`; `ChainResolver.resolve()`'s first
      check now also requires `not r.case_fallback`, so ANY case-fallback
      match (chain or not) reaches the irregular/stem retry loop first.
    - **`meltdown`** showed Unknown -- raw data has only an
      `etymologically_related_to "melt down"` hedge, not a real `compound_of`
      relation, so no automated mechanism could find it. Verified against
      live Wiktionary ("From melt (verb) + down (adverb)...") and hand-added
      to `compounds.py`, same as `upside`.
    - **`generate`** showed Unknown for Direct Source (the bare-has_root-stub
      shape, issue #14) -- raw data has only hedged `etymologically_related_to`
      mentions of Latin `generō`/`genus`, the same residual class issue #14
      left open. Individually verified against live Wiktionary (an ordinary,
      undisputed Latin derivation) and hand-fixed via `corrections.py` +
      `tree_corrections.py`, same as `tag`/`auto` -- NOT a resolution of
      issue #14's broader still-open 1,245-word policy question, just one
      more individually-verified word out of that residual.

    **The structural fix** (not a per-word patch): `resolver.py`'s
    `Resolution` gained two general fields --
    - `root_term`: the exact spelling at `root_lang` (was already computed
      in `convert_wikt.py` for `fetch_reconstructions.py` but never threaded
      through this layer).
    - `inherited_from`: the OTHER word whose data actually produced this
      answer, whenever it isn't the input word's own direct entry. Set by
      (a) `convert_wikt.py`'s `_patch_root_stubs`, which now records which
      root word it copied wholesale (e.g. `professional` -> `profession`),
      and (b) `ChainResolver.resolve()`'s own irregular-form/stemming retry,
      propagated through recursively (`inherited_from=r2.inherited_from or
      cand`) so a multi-hop answer still points at the TRUE underlying
      source, e.g. `consistency` -> `consistent` (found only at the resolver
      layer, no data-file backing at all).

    `app.py` gained a shared module-level `RESOLVER` instance (previously
    every `analyze()` call built a fresh one from scratch, reloading the
    ~14MB `wikt_words.json` every request) and a new `resolve_tree(word)`
    function -- the reference consumer of `inherited_from`: when a word has
    no tree of its own, it asks `RESOLVER.resolve(word)` what it actually
    used and recurses to THAT word's tree (compound parts get one synthetic
    wrapper branch per part, reusing the render_branch/build_diagram
    machinery unchanged since the wrapper nodes are the exact same
    `{"lang","term","branches"}` shape as any other tree node). A last-resort
    single-node synthesis (from `root_lang`/`root_term`) covers the residual
    case where the resolver has SOME real answer but no richer tree anywhere
    to recurse into (e.g. `_patch_foreign_root_stubs` words, or bare-root
    stubs like `vitamin`/`critical`, which now correctly show their real PIE
    citation in the tree -- consistent with Deepest Root mode already doing
    exactly that for the same words).

    **Bug found and fixed the same session while verifying this**:
    `_lookup_tree_direct` (the tree's own case-fallback lookup) had an
    UNCONDITIONAL `.capitalize()` fallback with no awareness of the new
    `case_fallback` protection above -- exactly the "second implementation
    that quietly drifts" failure this whole fix exists to prevent. It
    landed on "Ran"'s Japanese tree directly, bypassing `resolve_tree()`'s
    `inherited_from` check entirely. Fixed by removing the independent
    `.capitalize()` fallback from `_lookup_tree_direct` -- `resolve_tree()`
    now only tries a capitalized entry AFTER confirming (via the resolver)
    that no richer answer exists, at the same lower-trust tier the resolver
    itself uses it.

    **Honest residual, not solved by this fix**: an individual
    `corrections.py` collision fix (like `tag`/`auto` above) still requires
    a hand-maintained parallel `tree_corrections.py` entry -- `resolve_tree()`
    checks `TREES` (which bakes in `tree_corrections.py`) BEFORE consulting
    the resolver at all, so a future `corrections.py`-only fix without a
    matching tree entry would still show stale/wrong raw tree data instead
    of silently deferring to the corrected answer. This structural fix
    closes the COVERAGE-mechanism gap (inheritance, stemming, compounds --
    the actual reported problem, ~164k words) completely; it does not
    (and structurally cannot, without losing real tree richness) fully
    automate away the per-word hand-verification discipline for individual
    collision corrections.
17. **Large-scale coverage audit -- 2026-07-24.** Joe: run real paragraphs
    through the analyzer at scale, find every common word that shouldn't be
    Unknown, diagnose the aggregate pattern(s), then fix the patterns rather
    than whack-a-moling individual words. Full methodology, findings, and
    the fix plan were reported to and approved by Joe before any code
    changed (including a mid-course model-switch attempt that didn't
    succeed -- proceeded under Sonnet 5 per his explicit go-ahead).

    **Corpus**: `randomwordgenerator.com/paragraph.php` turned out to be
    JavaScript-only (no server-rendered text); traced its compiled JS to a
    fixed, static bank of 347 real paragraphs (`json/paragraphs.json`) and
    processed all 347 once (strictly more thorough than repeated sampling
    from the same fixed pool). New tooling: `scripts/scan_unknown_words.py`
    (deterministic corpus scanner, flags likely-proper-nouns as a hint via a
    capitalized-mid-sentence heuristic, never an auto-filter) and the
    `etymology-coverage-scan` skill.

    **Diagnosis**: 191 unique Unknown words across 347 paragraphs, 156 real
    (non-proper-noun) candidates, sorting into six confirmed root causes:
    - **(A) `_IRREGULAR_FORMS` incomplete**: covered ~100 of English's ~200
      common irregular verbs. `hid`, `meant`, `got`/`gotten`, `woke`/`awoke`,
      `swung`, `spun`, `stung`, `sped`, `snuck`, `laid`, `heard`, and ~80
      more added (189 entries total now).
    - **(A2) Data-layer inheritance never tried the resolver's own fallback
      cascade** on a cited root: `hidden` cites root `hid`, which has zero
      raw data of its own and needs the resolver's irregular-form table to
      resolve -- but `convert_wikt.py`'s inheritance patch only checked for
      an exact key match, so this and `unheard`->`hear`,
      `unexplained`->`explain` (regular stemming) all fell through even
      though the resolver could clearly answer them once asked the right
      way. Fixed by importing `_irregular_candidates`/`_stem_candidates`
      (pure functions, no circular dependency) into `convert_wikt.py` and
      trying them when an exact-key lookup fails.
    - **(A3) `has_affix` widening + a real bug caught while verifying it**:
      widening `_ROOT_POINTER_RELS` to include `has_affix` (lower priority
      than `has_prefix_with_root`) caught `unusual`-shaped words (two
      `has_affix` rows: the bound affix itself and the real root). Caught
      before shipping: `unusual` was inheriting from the bound-morpheme
      fragment `"un-"` itself (which has its own, apparently WRONG, entry --
      Latin `ūnus` "one," unrelated to the negative prefix) instead of
      `"usual"`, because `"un-"` happened to resolve and got tried first.
      Checked the scale directly: 26,967 `has_affix` rows across the whole
      dataset point at a bound-morpheme-shaped term. Fixed generally by
      skipping any candidate starting or ending in `-` (Wiktionary/
      etymology-db's own convention for marking a bound affix, not a guess).
    - **(B) No f/v plural-alternation rule**: `wolf`/`wolves`,
      `knife`/`knives`, `shelf`/`shelves` -- same shape already hand-patched
      once for `self`/`selves` in `corrections.py` rather than generalized.
      Verified empirically against all 16 real target pairs plus every
      regular `-fs` plural (roofs/chiefs/beliefs/...) before shipping --
      the two suffixes never overlap, so the collision risk that forced a
      length floor on the earlier `-cy` rule doesn't apply here.
    - **(C) Bare-root-PIE stubs / hedge-only relations**: `incident`,
      `expert`, `metaphor`, `adult`, `puppy`, `presence` -- literally the
      same still-open 1,245-word residual from known issue #14. Joe's
      decision on the standing a/b/c question (asked fresh, given this
      scan's concrete evidence of scale): **(c), pursue a different data
      source for the remainder** -- NOT a blanket lower-confidence-tier
      policy change. Scoped today to hand-verifying the specific words this
      scan surfaced (matching the `generate`/`tag`/`auto` pattern), not
      solving the full 1,245-word class.
    - **(D) Common words entirely absent from the raw snapshot**:
      `previous`, `mom`, `package` -- not rare words, updates the earlier
      assumption that coverage gaps are mostly rare-word territory.
    - **(E) Missing compounds**: `mountainside`, `faraway`, `foothill(s)`,
      `downside(s)`, `earlobe(s)` -- all verified live, both parts already
      resolving on their own.

    Eleven words hand-verified against live Wiktionary and added to
    `corrections.py` + `tree_corrections.py` together (categories C/D):
    `previous`, `mom` (inherits `mama`'s own already-correct PIE-connected
    chain -- `momma` only has a hedge relation to `mama`, but a clipping
    being closely tied to a word with real data is a verifiable claim, not
    a guess, matching the existing `zoo` clipping precedent), `package`
    (inherits `pack`'s chain rather than the "possibly influenced by"
    French/Latin hedge Wiktionary itself doesn't commit to), `incident`,
    `expert`, `metaphor`, `adult`, `puppy`, `presence`, `familiar` (fixing
    this one also fixes `unfamiliar` for free via the existing
    corrections-applied-before-patches ordering), and `unless` (verified to
    NOT actually be a live `un`+`less` compound despite appearances -- a
    single Middle English-internal sound-change formation; compounds.py
    would have fabricated a folk etymology here).

    **Two more real bugs found and fixed while auditing the results, not
    guessed at**: `_is_reliable_root`/case-fallback-shaped bugs are now a
    known FAMILY, not a one-off -- checked the ENTIRE 743-entry
    `compounds.py` table after shipping (A2/A3), not just a sample:
    - **147 of 743** hand-verified compounds started resolving via an
      auto-inherited chain instead of their split -- not factually wrong,
      but a worse, less-complete answer for a genuine two-content-word
      compound (e.g. `mountainside` silently losing `side` and showing only
      `mountain`'s story). Fixed in `resolver.py`: a hand-verified
      `compounds.py` split now wins over an answer whose `inherited_from`
      is set (i.e., not the word's own genuine directly-recorded data) --
      scoped narrowly so a word with real data of its own is untouched,
      preserving `compounds.py`'s own documented design intent.
    - **3 of 743** (`bathrobe`/`bathtub`/`bluebird`) had regressed all the
      way to Unknown -- a PRE-EXISTING bug, unrelated to today's widening:
      `EtyResolver` can cite an ISO code `buckets.py` doesn't map
      (`bucket_for(iso) == "Unknown"`), and `_try()`'s "any non-empty chain
      wins" check trusted that non-answer immediately, permanently blocking
      the compound fallback. Fixed by checking `chain[0]`'s bucket
      specifically (not "any entry" -- `taxicab` has a real chain mixed
      with an Unknown entry, still needed the narrower check to land
      correctly) rather than raw chain truthiness. `test_regression.py`
      gained a check against the FULL 743-entry table, not a sample, since
      the whole point is this must hold for all of them.

    **Result**: 191 -> 139 unique Unknown words, 156 -> 105 real-gap
    candidates across the same 347-paragraph corpus (a single unchanged
    measurement, re-run after the fix) -- roughly a 30% reduction in one
    pass, via 6 structural/generalizable fixes plus 11 individually
    hand-verified words, not per-word patching. `wikt_words.json`: 213,132
    -> 244,094 words. Full regression suite (82 checks, including the new
    full-`compounds.py`-table check) passes. Honest residual: 105 words
    remain, mostly scattered without as strong a shared pattern as the six
    found here (`past`, `favorite`/`favourite`-shaped American-spelling
    variants, a narrow source-data mojibake artifact in 2 of 347
    paragraphs) -- not chased further this pass, consistent with "fix the
    pattern, not every word."

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
