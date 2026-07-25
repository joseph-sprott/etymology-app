# Future Features & External Resource Research

**Status: research only — nothing in this file has been built or started.**
Compiled 2026-07-24 at Joe's request: (1) capture every feature idea from his notes
in one referenceable place, and (2) exhaustively check GitHub/linguistics-data
sources for anything that could either strengthen the core database or supply data
for a future feature. Per Joe's own stated priority: **none of Part 2 is worth
touching until the core database (Part 3's "core reliability" items) is as solid as
it can be** — new features sit on top of that foundation, not the other way around.

---

## Part 1 — Feature idea backlog

Numbered and grouped from Joe's raw notes-app list, wording lightly cleaned up but
not reinterpreted. Grouping is mine; nothing here is scoped, sequenced, or
committed to.

### A. Graphs / charts / maps

1. **Origin heat map** — a world map where the word's main origin language's
   region is hottest, and any regions it passed through en route to English are
   still visible but cooler (e.g. main origin French → France hottest; whatever
   intermediate hops it took still show up dimmer).
2. **Per-analysis pie chart** — percentage of each origin language for a given
   paragraph/text, chart form.
3. **"Passed through at any point" percentage** — not the primary or deepest
   origin, but whether a word was ever touched by a given language (French,
   German, etc.) anywhere in its chain, as its own stat.
4. **Master pie chart of all English** — percentage of every language that has
   contributed to English overall (not per-paragraph) — envisioned as the main,
   eye-catching visual on the homepage.

### B. Single-word deep dive

5. **Word in modern donor-language form** — show what the word looks like today
   in the language it was borrowed from, including connotation differences
   (e.g. English "demand" reads harsher than French "demander," which is just a
   simple ask).
6. **Cognates** — words in other languages sharing the same root, most-related
   first.
7. **False friends** — words that look similar across languages but mean
   something different (e.g. Spanish "emocionada" looks like "emotional" but
   means "excited").
8. **Etymological doublets** — words from the same root that ended up with
   different meanings (e.g. travel/travail). Wants a toggle for PIE-level
   doublets specifically (can get sprawling), plus seeing what other words
   share the same PIE root, same French root, same German root, etc.
9. **Frequency** — how often a word appears per 1,000 words of English usage.
10. **Meaning round-trip detection** — flag when a word shifted meaning crossing
    from one language to another, and (optionally) shifted again coming back to
    the original language with a new sense.
11. **Full etymology tree** — up to ~50 nodes, visualizing the full path a word
    took. *(Note: a per-word etymology tree already exists and works —
    `build_etymology_trees.py` / `etymology_trees.json`, served from `app.py`.
    This idea may already be substantially satisfied; worth comparing before
    treating it as new scope.)*
12. **Single-path arrow view** — like Google's etymology arrow: click a word,
    see one clean linear path (e.g. PIE → Greek → French → English).
    *(Note: the existing three-mode toggle — Direct Source / Notable Influence /
    Deepest Root — already covers a good chunk of this idea's intent.)*

### C. Other

13. **Disputed-origin flagging** — clearly mark words whose origin isn't settled
    (examples given: bad, dog, pig, bird, big, jazz).
14. **AI homonym/heteronym disambiguation** — a model that picks the right sense
    of a word from context (e.g. "to bow" [bend] vs. "a bow" [ribbon/weapon]).
    Explicitly noted: same-spelling senses don't always share a root (e.g. "to
    lead" vs. the metal "lead" have different ancestors) — the feature needs to
    be sure, not just guess.
15. **AAVE / Black English origins** — etymology/history of terms like "finna,"
    "talm," "bruh," "cool."
16. **Hover-definitions for jargon** — hovering a term like "homonym," "false
    friend," "cognate" shows a definition + easy example; also cover
    higher-level language-family primers (what "Semitic," "Germanic," etc. mean
    and which languages belong to each).
17. **Auto-add unknown words** — once the database is otherwise finalized, let a
    user-submitted word that's missing get looked up (etymonline or AI) and
    added.
18. **Three-level origin toggle** — Level 1: direct English borrowed-from
    language; Level 2: highest level of influence; Level 3: deepest root.
    **This already exists and is built/working** (Direct Source / Notable
    Influence / Deepest Root in `resolver.py`) — flagging so it isn't
    re-scoped as new work by mistake.
19. **Proper-noun / name detection** — detect pronouns/proper nouns, with a
    possible future "name history" (onomastics) feature.

### D. Games

20. **Guess-the-root game** — given a list of words and a target language, guess
    which words actually come from that language.

---

## Part 2 — External resource research

Everything below was checked by two research passes against live GitHub/project
pages (not recalled from memory) on 2026-07-24. Each entry notes what it actually
contains, license, and rough activity level where visible, plus which idea(s)
above it would serve. Items are flagged **[CORE]** if they'd improve the
underlying database's reliability/coverage rather than only enabling a specific
future feature — those are the highest-priority reads per Joe's own stated rule.

### Highest-leverage find overall

- **[CORE] tatuylonen/wiktextract** — https://github.com/tatuylonen/wiktextract
  MIT. Very active (5,100+ commits; bulk data at kaikki.org regenerated weekly,
  confirmed fresh as of 2026-07-20). A far richer Wiktionary-dump parser than
  what produced etymology-db: structured JSON with glosses, `etymology_text`,
  `etymology_templates`, `etymology_number` (**per-sense** etymology — see idea
  #14), pronunciations, linkages, Wikidata IDs. **Confirmed it parses
  Wiktionary's `Reconstruction:` namespace** — kaikki.org currently lists 1,781
  PIE entries with descendant data, something etymology-db's scraper never
  touched at all (etymology-db has zero rows where a proto-language is an
  edge's *source*, only ever a destination — this is exactly the gap behind
  known issue #10 in `CLAUDE.md`, the "Deepest Root often means oldest
  *attested*, not oldest *reconstructed*" problem). Underlying engine:
  **tatuylonen/wikitextprocessor** (also active, 1,410+ commits) — only needed
  if building a custom extractor rather than consuming wiktextract's output
  directly.
  Relevance: **#10, #11, #18** (deepest-root/PIE coverage gap), **#14**
  (per-sense etymology — the actual blocker for homonym-aware root data),
  **#15/#19** (proper-noun and AAVE-labeled entries reachable via category
  filtering), **#8** (doublets — see below), **#17** (a legitimate, ToS-clean
  alternative to scraping etymonline).

### [CORE] Proto-language / PIE reconstruction

- **wiktextract's Reconstruction-namespace output** (above) — primary lead.
- **lexibank/iecor** — https://github.com/lexibank/iecor — CLDF dataset
  (published 2025, Scientific Data journal; also on Zenodo). 160 Indo-European
  languages, 170 core meanings, 25,731 lexemes in 4,981 cognate sets across all
  major IE clades. Strong for cross-checking PIE-level cognate sets (#6, #8)
  specifically within Indo-European.
  - PIE Lexicon (Helsinki) and IELEX (UT Austin) are real academic PIE
    databases but have **no GitHub presence** — web-only, would need manual
    reference rather than a data pull.
  - Tower of Babel / StarLing (Starostin) — real and broader than PIE (also
    covers Sino-Tibetan, Altaic, etc.) but **confirmed no GitHub mirror
    exists** — original site/software only.

### [CORE] Language family / classification

- **[CORE] glottolog/glottolog** — https://github.com/glottolog/glottolog —
  Actively maintained (2,136 commits, open issues/PRs). Comprehensive
  genealogical classification of essentially every documented language,
  dialect, and family, each with a stable Glottocode; data as INI files
  mirroring the classification tree. CLDF-formatted sibling repo:
  `glottolog/glottolog-cldf`; Python API: `glottolog/pyglottolog`.
  Relevance: directly replaces/augments the project's current hand-maintained
  `NAME_TO_BUCKET` map in `buckets_wikt.py` (known issue #3 — ~4.4% of
  ancestry edges currently fall into a vague "Other" bucket for missing
  language names) with a real, sourced classification instead of ad hoc
  additions. Also the natural backbone for #16's "what is Germanic/Semitic"
  primers — real family-tree data, not hand-written prose.

### Cognates (#6)

- **droher/etymology-db** (already in use) — confirmed to include explicit
  `doublet_with` and `cognate_of` relation types already in the raw data
  Joe has on disk (`etymology.parquet`) — worth checking whether
  `convert_wikt.py` is currently reading/using these relation types at all,
  since the data may already be sitting there unused.
- **kbatsuren/CogNet** — https://github.com/kbatsuren/CogNet — 8.1M cognate
  pairs, 338 languages, 91,285 WordNet-synset-keyed concepts, ~94% precision
  (manually evaluated), tab-separated with transliterations. **License: CC
  BY-NC-SA 4.0 — non-commercial only**, matters if this project is ever
  monetized. Active (76 commits, up to v2.0).
- **lexibank/iecor** (above) — IE-specific, complements CogNet's broader but
  shallower coverage.
- **lexibank/asjp** — https://github.com/lexibank/asjp — CC-BY-4.0, active.
  568,820 lexemes across 11,540 varieties, but Swadesh-style similarity
  wordlists rather than pre-tagged cognate pairs — more useful as raw input
  for computational cognacy inference than a ready list.

### False friends (#7)

Honest finding: **no broad, well-maintained English false-friends dataset
exists on GitHub.** Everything found is narrow academic research code:
- **dhfbk/falsefriends** — https://github.com/dhfbk/falsefriends — Italian-pivot
  pairs vs. English/French only, TSV, unstated license, essentially a single
  research artifact (has some manually-annotated English word pairs tagged
  cognate vs. false-friend — worth a direct look despite small size).
- **mitkonikov/false-friends** — GPL-3.0, Spanish-Portuguese and
  Slovenian-Macedonian only — not English-relevant.
- **cfiltnlp/challengeCognateFF** — Indian-language pairs only.
This gap is real; nothing off-the-shelf covers it well for English's donor
languages (French, German, Spanish, etc.). Likely a hand-curation task if
pursued.

### Etymological doublets (#8)

No pre-scraped dataset found for Wiktionary's own "Category:English doublets"
(~200 pages) or "Appendix:English doublets." Two viable paths, both build-it-
yourself rather than a ready download: (a) etymology-db's `doublet_with` rows
(see Cognates above — may already be on disk and unused), or (b) filter
wiktextract's category output for `English doublets` / `Middle English
doublets` / `English piecewise doublets`.

### Word frequency — "per 1,000 words" (#9)

- **[CORE-adjacent] rspeer/wordfreq** — https://github.com/rspeer/wordfreq —
  Apache-2.0 code / CC-BY-SA-4.0 data. Actual per-word Zipf-scale frequency
  numbers (not just rank), 40+ languages including English, pip-installable.
  **Caveat: repo is explicitly sunsetted** (`SUNSET.md` states data is frozen
  at ~2021 usage patterns and won't be updated again) — still the best fit
  found despite being stale.
- **SUBTLEX-derived repos** (e.g. `chrplr/openlexicon` mirrors) — 51M-word
  movie-subtitle corpus, ~74k English words, real frequency counts.
- **first20hours/google-10000-english** — rank-only (no counts), explicitly
  marked "Not Maintained" — weaker than the two above, listed for completeness
  since it's the most commonly cited option online.

### Loanword / borrowing percentages (#3)

- **[CORE-adjacent] lexibank/wold** — https://github.com/lexibank/wold — CC-BY-4.0,
  CLDF dataset from Haspelmath & Tadmor's World Loanword Database. 41 language
  varieties (English included), 1,814 concepts, 64,289 lexemes, each annotated
  with loanword status/source/borrowing age. **Important caveat, verified
  directly: does not ship ready "% borrowed from language X" numbers** — gives
  per-word annotations that would need aggregating per donor language yourself.
  Directly matches idea #3's "passed through at any point" framing (loanword
  annotation ≠ deepest/primary origin, same distinction Joe described).

### Geographic heat map (#1)

- **Language → country mapping:**
  - `arash16/countries-languages` — https://github.com/arash16/countries-languages
    — countries mapped to official languages via ISO 639-3.
  - `mledoze/countries` — https://github.com/mledoze/countries — popular,
    actively maintained, countries with official languages in
    JSON/YAML/CSV/XML.
  - Both are **modern-country-to-modern-language only** — neither maps
    historical/reconstructed languages (Old Norse, Proto-Germanic, PIE) to any
    region. That mapping is inherently a judgment call (e.g. PIE → Pontic-
    Caspian steppe) with nothing on GitHub solving it — would need to be
    hand-built regardless of which base dataset is used.
- **Map geometry data:**
  - `topojson/world-atlas` — https://github.com/topojson/world-atlas — Natural
    Earth as TopoJSON, ISC license, standard D3 pairing. **Archived
    (read-only since March 2023)** but data is stable/complete.
  - `datasets/geo-countries` — https://github.com/datasets/geo-countries —
    GeoJSON country polygons, PDDL/MIT, Leaflet-ready.
  - `martynafford/natural-earth-geojson` — more granular admin-boundary
    options across all three Natural Earth scales.

### Tree / path visualization (#11, #12)

Not a data gap — a library note: **d3-hierarchy** (built into D3) is the right
primitive for a lineage tree, not a separate dependency. Purpose-built
"family tree" libraries (e.g. `donatso/family-chart`) are semantically bound
to genealogy concepts (spouses/generations) and would need real rework to fit
a word-lineage tree — not a clean match, skip them.

### Disputed/unclear origin flagging (#13)

No general curated "English words with disputed etymology" list exists on
GitHub. Realistic path: wiktextract already parses Wiktionary's own
`{{uncertain}}`/`{{unknown}}` etymology templates — flagging is a matter of
checking for those template names in extracted data, not sourcing an external
list. (`kpsychas/word_etymologist` has a nice 3-tier confidence-label pattern
worth imitating, but it's Greek-only, not a general solution.)

### AI homonym/heteronym disambiguation (#14)

Checked specifically for datasets linking word *senses* to *different*
etymological roots — this is the hard part of idea #14, not just picking the
right sense from context.
- `google-research-datasets/WikipediaHomographData` — 162 homographs,
  pronunciation/sense labels, **archived**, and confirmed to carry **no
  etymology or root data per sense** — inventory only.
- `danlou/bert-disambiguation` (CoarseWSD-20) — WSD dataset for 20 ambiguous
  nouns, same limitation: senses, not roots.
- **Finding: nothing on GitHub links word senses to distinct etymological
  roots.** wiktextract's `etymology_number` field (already sense-partitioned
  at the Wiktionary source, since pages like "bow" carry multiple numbered
  etymology sections) is the most promising lead — any WSD dataset would need
  manual cross-walking to it; no existing repo does that cross-walk.

### AAVE / Black English origins (#15)

Thin, as expected for GitHub specifically (this is genuinely academic-paper
and dictionary-entry territory):
- ORAAL Glossary (https://oraal.github.io/glossary, project at
  github.com/oraal) — real, but a glossary of linguistic *terminology*
  (habitual "be," code-switching, Creole Hypothesis), not individual slang
  etymologies. No entries for "finna"/"talm"/"bruh"/"cool" etc.
- CORAAL / TwitterAAE corpora — transcribed-speech/tweet corpora for NLP
  research, not etymology glossaries.
- Best lead: **Wiktionary's own "Category:African-American Vernacular
  English"** — already reachable through wiktextract by filtering that
  category, rather than a separate dataset. Beyond that, likely needs manual
  curation from linguistics literature (John Rickford, Geneva Smitherman's
  "Black Talk") rather than scraping.

### Hover-glossary / language-family primer content (#16)

No open dataset of *jargon definitions* (homonym, cognate, false friend,
doublet) exists — small enough vocabulary (a few dozen terms) that hand-
writing tooltip copy is the practical answer regardless. Glottolog (above)
covers the larger, harder half of this idea — real family-tree membership
data, not prose definitions.

### Auto-add unknown words (#17)

Several small etymonline.com scrapers exist (`nikhilrajaram/etymonline-scrape`,
`WooodHead/etymonline_scraper`, `seanbethard/etymonline_scraper`) — all tiny
(3 commits or so), unmaintained, and **none discuss copyright/ToS
implications at all**. Flagging directly: etymonline.com is Douglas Harper's
commercial reference work; scraping it would carry real, unaddressed legal
risk that these repos don't resolve. **wiktextract is the safer default** for
this feature — Wiktionary's CC-BY-SA/GFDL licensing is explicitly built for
reuse, and it's already the top recommendation above for other reasons.

### Onomastics / name history (#19)

Checked several name databases (`Debdut/names.io`, 260K first/last names by
country/gender; `sigpwned/popular-names-by-country-dataset`;
`tfmorris/Names` for name-variant matching like Bill↔William) — **all
confirmed name-list-only, no etymology/origin content.** No GitHub dataset
provides name etymology. Wiktionary does carry etymology sections for many
given names/surnames (reachable via wiktextract by filtering proper-noun
namespace entries) — likely the best available lead if this is ever pursued.

### Guess-the-root game (#20)

Not really a data question — trivially generatable from the language-
classification data above once it exists. One prior-art example found,
`SangameshItagi/origin-guesser` (MIT, React), but it's small/early-stage
(roadmap literally says "add more questions") — not worth building on, just
confirms the concept has been tried before.

---

## Part 3 — Bottom line

**If/when Joe wants to act on any of this** (not now — this file is pure
research per his instruction), the priority order that falls out of the
findings above, core-database-first:

1. **wiktextract / kaikki.org** — single highest-leverage item. Strict
   superset of what etymology-db currently provides, plus the proto-language
   Reconstruction-namespace data that closes known issue #10, plus per-sense
   etymology (`etymology_number`) that idea #14 actually needs, plus a
   legitimate low-risk path for idea #17.
2. **glottolog** — replaces the hand-maintained language-bucket map
   (known issue #3) with a real, sourced, actively-maintained classification.
3. **Check whether etymology-db's `doublet_with`/`cognate_of` rows, already on
   disk in `etymology.parquet`, are being read at all** — before reaching for
   any external cognate/doublet dataset, since this may be a "the data's
   already sitting there" situation rather than a real gap. Worth a direct
   check, not an assumption either way.
4. **rspeer/wordfreq** for frequency-per-1000 (#9) — stale since ~2021 but the
   best real per-word frequency numbers found.
5. **lexibank/wold** for loanword/borrowing-percentage data (#3) — needs
   aggregation work, no ready percentages.
6. **CogNet + lexibank/iecor** as cognate-list supplements to whatever
   etymology-db/wiktextract already carry natively.
7. Confirmed real gaps with **no good off-the-shelf fix**, flagged honestly
   rather than papered over: English false-friends data (#7), disputed-origin
   lists (#13, buildable from Wiktionary's own uncertainty templates),
   AAVE slang etymology (#15), sense-to-root cross-walks (#14), and name
   etymology (#19) — all would need meaningful hand-curation regardless of
   which base dataset is chosen.
