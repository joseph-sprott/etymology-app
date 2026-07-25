# GitHub / External Resource Research — Etymology Analyzer

**Research only — nothing here has been adopted, built, or started.** Compiled
2026-07-24 from two independent research passes against live GitHub/project pages
(not recalled from memory — every entry below was verified by direct
search/fetch). Companion to `FUTURE_FEATURES_AND_RESOURCES.md` (which has the full
feature-idea backlog this maps to); this file stands alone as a resource index.

Priority note: items tagged **[CORE]** would improve the *existing* database's
reliability/coverage (currently built from `droher/etymology-db` + the `ety`
package). Per project rule, core reliability comes before any new feature — read
those first.

Feature-number references below (e.g. "#6") point to the numbered backlog in
`FUTURE_FEATURES_AND_RESOURCES.md`:
1=heat map, 2=per-analysis pie chart, 3=passed-through-language %/loanword %,
4=master pie chart, 5=word-in-donor-language form, 6=cognates, 7=false friends,
8=doublets, 9=frequency per 1000 words, 10=meaning round-trip detection,
11=full etymology tree, 12=single-path arrow view, 13=disputed-origin flagging,
14=AI homonym/heteronym disambiguation, 15=AAVE origins, 16=hover glossary,
17=auto-add unknown words, 18=three-level toggle (already built),
19=proper-noun/name history, 20=guess-the-root game.

---

## Highest-leverage find overall

### [CORE] tatuylonen/wiktextract
https://github.com/tatuylonen/wiktextract
MIT license. Very active (5,100+ commits; bulk data at kaikki.org regenerated
weekly, confirmed fresh as of 2026-07-20). A far richer Wiktionary-dump parser
than what produced `etymology-db`: structured JSON with glosses,
`etymology_text`, `etymology_templates`, `etymology_number` (**per-sense**
etymology — feeds #14), pronunciations, linkages, Wikidata IDs.
**Confirmed it parses Wiktionary's `Reconstruction:` namespace** —
kaikki.org currently lists 1,781 PIE entries with descendant data, something
`etymology-db`'s scraper never touched (zero rows where a proto-language is an
edge's *source*, only ever a destination — this is the current project's known
issue #10, "Deepest Root often means oldest *attested*, not oldest
*reconstructed*").
Underlying engine: **tatuylonen/wikitextprocessor**
(https://github.com/tatuylonen/wikitextprocessor, also active, 1,410+ commits)
— only needed for building a custom extractor, not for consuming wiktextract's
output directly.
Relevance: #10, #11, #18 (PIE/deepest-root coverage), #14 (per-sense
etymology), #15/#19 (category-filterable AAVE and proper-noun entries), #17
(clean legal alternative to scraping etymonline).

---

## [CORE] Proto-language / PIE reconstruction data

- **wiktextract's Reconstruction-namespace output** (above) — primary lead.
- **lexibank/iecor** — https://github.com/lexibank/iecor — CLDF dataset
  (published 2025, *Scientific Data* journal; also on Zenodo,
  DOI 10.5281/zenodo.8089433). 160 Indo-European languages, 170 core meanings,
  25,731 lexemes in 4,981 cognate sets across all major IE clades. Good for
  cross-checking PIE-level cognate sets (#6, #8) within Indo-European
  specifically.
- **PIE Lexicon** (pielexicon.hum.helsinki.fi) and **IELEX**
  (lrc.la.utexas.edu/lex) — real academic PIE databases, confirmed **no GitHub
  presence** — web-only.
- **Tower of Babel / StarLing** (Starostin) — broader than PIE (also
  Sino-Tibetan, Altaic, etc.), confirmed **no GitHub mirror exists**.

## [CORE] Language family / classification

- **glottolog/glottolog** — https://github.com/glottolog/glottolog —
  Actively maintained (2,136 commits, open issues/PRs). Genealogical
  classification of essentially every documented language/dialect/family,
  each with a stable Glottocode, as INI files mirroring the tree. CLDF
  sibling: `glottolog/glottolog-cldf`; Python API: `glottolog/pyglottolog`.
  Relevance: replaces the project's hand-maintained `NAME_TO_BUCKET` map in
  `buckets_wikt.py` (known issue #3 — ~4.4% of ancestry edges fall into
  "Other" for missing language names) with a real, sourced classification.
  Also the natural backbone for #16's language-family primers.

## Cognates (#6)

- **droher/etymology-db** (already in use as the project's primary source) —
  confirmed to include explicit `doublet_with` and `cognate_of` relation
  types in the raw data already on disk (`etymology.parquet`). Worth checking
  whether `convert_wikt.py` currently reads/uses these before reaching for any
  external dataset — may be unused data already present rather than a real
  gap.
- **kbatsuren/CogNet** — https://github.com/kbatsuren/CogNet — 8.1M cognate
  pairs, 338 languages, 91,285 WordNet-synset-keyed concepts, ~94% precision
  (manually evaluated), tab-separated with transliterations. **License: CC
  BY-NC-SA 4.0 — non-commercial only.** Active (76 commits, up to v2.0).
- **lexibank/iecor** (above) — IE-specific, complements CogNet's broader but
  shallower coverage.
- **lexibank/asjp** — https://github.com/lexibank/asjp — CC-BY-4.0, active.
  568,820 lexemes across 11,540 varieties; Swadesh-style similarity wordlists
  rather than pre-tagged cognate pairs — better as raw input for
  computational cognacy inference than a ready list.

## False friends (#7)

**No broad, well-maintained English false-friends dataset exists on GitHub.**
Everything found is narrow academic research code:
- **dhfbk/falsefriends** — https://github.com/dhfbk/falsefriends —
  Italian-pivot pairs vs. English/French only, TSV, unstated license. Has
  some manually-annotated English pairs tagged cognate vs. false-friend
  despite the small size — worth a direct look.
- **mitkonikov/false-friends** — GPL-3.0, Spanish-Portuguese and
  Slovenian-Macedonian only — not English-relevant.
- **cfiltnlp/challengeCognateFF** — Indian-language pairs only.
Real gap; likely a hand-curation task if pursued.

## Etymological doublets (#8)

No pre-scraped dataset for Wiktionary's "Category:English doublets" (~200
pages) or "Appendix:English doublets." Two build-it-yourself paths: (a)
`etymology-db`'s `doublet_with` rows (see Cognates above), or (b) filter
wiktextract's category output for `English doublets` / `Middle English
doublets` / `English piecewise doublets`.

## Word frequency — "per 1,000 words" (#9)

- **rspeer/wordfreq** — https://github.com/rspeer/wordfreq — Apache-2.0 code /
  CC-BY-SA-4.0 data. Actual per-word Zipf-scale frequency numbers (not just
  rank), 40+ languages including English, pip-installable. **Caveat: repo is
  explicitly sunsetted** (`SUNSET.md` — data frozen ~2021, won't be updated
  again) — still the best fit found.
- **SUBTLEX-derived repos** (e.g. `chrplr/openlexicon` mirrors) — 51M-word
  movie-subtitle corpus, ~74k English words, real frequency counts.
- **first20hours/google-10000-english** — rank-only (no counts), explicitly
  marked "Not Maintained" — weaker than the two above, listed since it's the
  most commonly cited option online.

## Loanword / borrowing percentages (#3)

- **lexibank/wold** — https://github.com/lexibank/wold — CC-BY-4.0, CLDF
  dataset from Haspelmath & Tadmor's World Loanword Database. 41 language
  varieties (English included), 1,814 concepts, 64,289 lexemes, each
  annotated with loanword status/source/borrowing age. **Verified caveat: no
  ready "% borrowed from language X" numbers** — per-word annotations only,
  would need aggregating per donor language yourself. Matches #3's
  "passed-through-at-any-point" framing well (loanword annotation ≠
  deepest/primary origin).

## Geographic heat map (#1)

**Language → country mapping:**
- `arash16/countries-languages` — https://github.com/arash16/countries-languages
  — countries mapped to official languages via ISO 639-3.
- `mledoze/countries` — https://github.com/mledoze/countries — popular,
  actively maintained, countries with official languages in
  JSON/YAML/CSV/XML.
- Both are **modern-country-to-modern-language only** — neither maps
  historical/reconstructed languages (Old Norse, Proto-Germanic, PIE) to any
  region. That mapping is inherently a judgment call (e.g. PIE → Pontic-
  Caspian steppe); nothing on GitHub solves it — would need hand-building
  regardless of base dataset.

**Map geometry data:**
- `topojson/world-atlas` — https://github.com/topojson/world-atlas — Natural
  Earth as TopoJSON, ISC license, standard D3 pairing. **Archived
  (read-only since March 2023)** but data is stable/complete.
- `datasets/geo-countries` — https://github.com/datasets/geo-countries —
  GeoJSON country polygons, PDDL/MIT, Leaflet-ready.
- `martynafford/natural-earth-geojson` — more granular admin-boundary options
  across all three Natural Earth scales.

## Tree / path visualization (#11, #12)

Not a data gap, a library note: **d3-hierarchy** (built into D3) is the right
primitive for a lineage tree, not a separate dependency. Purpose-built
"family tree" libraries (e.g. `donatso/family-chart`) are semantically bound
to genealogy concepts (spouses/generations) — real rework needed to fit a
word-lineage tree, skip them.

## Disputed/unclear origin flagging (#13)

No general curated "English words with disputed etymology" list exists on
GitHub. Realistic path: wiktextract already parses Wiktionary's own
`{{uncertain}}`/`{{unknown}}` etymology templates — flagging is a matter of
checking for those template names in extracted data. (`kpsychas/word_etymologist`
has a nice 3-tier confidence-label pattern worth imitating, but it's
Greek-only.)

## AI homonym/heteronym disambiguation (#14)

Checked specifically for datasets linking word *senses* to *different*
etymological roots (the hard part of #14, beyond just picking the right sense
from context):
- `google-research-datasets/WikipediaHomographData` — 162 homographs,
  pronunciation/sense labels, **archived**, confirmed **no etymology/root
  data per sense** — inventory only.
- `danlou/bert-disambiguation` (CoarseWSD-20) — WSD dataset for 20 ambiguous
  nouns, same limitation.
- **Finding: nothing on GitHub links word senses to distinct etymological
  roots.** wiktextract's `etymology_number` field (already sense-partitioned
  at the Wiktionary source — pages like "bow" carry multiple numbered
  etymology sections) is the most promising lead; any WSD dataset would need
  manual cross-walking to it.

## AAVE / Black English origins (#15)

Thin on GitHub specifically (genuinely academic-paper/dictionary territory):
- ORAAL Glossary (https://oraal.github.io/glossary, project at
  github.com/oraal) — real, but a glossary of linguistic *terminology*
  (habitual "be," code-switching, Creole Hypothesis), not individual slang
  etymologies. No entries for "finna"/"talm"/"bruh"/"cool" etc.
- CORAAL / TwitterAAE corpora — transcribed-speech/tweet corpora for NLP
  research, not etymology glossaries.
- Best lead: **Wiktionary's "Category:African-American Vernacular English"**
  — reachable via wiktextract by filtering that category. Beyond that,
  likely needs manual curation from linguistics literature (John Rickford,
  Geneva Smitherman's "Black Talk").

## Hover-glossary / language-family primer content (#16)

No open dataset of jargon definitions (homonym, cognate, false friend,
doublet) exists — small vocabulary (a few dozen terms), hand-writing tooltip
copy is the practical answer. Glottolog (above) covers the larger half —
real family-tree membership data, not prose definitions.

## Auto-add unknown words (#17)

Several small etymonline.com scrapers exist (`nikhilrajaram/etymonline-scrape`,
`WooodHead/etymonline_scraper`, `seanbethard/etymonline_scraper`) — all tiny
(~3 commits), unmaintained, and **none discuss copyright/ToS implications at
all**. Flag directly: etymonline.com is Douglas Harper's commercial reference
work; scraping it carries real, unaddressed legal risk these repos don't
resolve. **wiktextract is the safer default** — Wiktionary's CC-BY-SA/GFDL
licensing is explicitly built for reuse.

## Onomastics / name history (#19)

Checked several name databases — `Debdut/names.io` (Apache-2.0, ~260K
first/last names by country/gender), `sigpwned/popular-names-by-country-dataset`,
`tfmorris/Names` (name-variant matching, e.g. Bill↔William) — **all confirmed
name-list-only, no etymology/origin content.** No GitHub dataset provides
name etymology. Wiktionary carries etymology sections for many given
names/surnames (reachable via wiktextract by filtering proper-noun namespace
entries) — likely the best available lead if pursued.

## Guess-the-root game (#20)

Not a data question — trivially generatable from the language-classification
data above once it exists. One prior-art example:
`SangameshItagi/origin-guesser` (MIT, React) — small/early-stage (roadmap
says "add more questions"), not worth building on, just confirms the concept
has been tried before.

---

## Priority order if any of this is ever acted on

1. **wiktextract / kaikki.org** — strict superset of `etymology-db`, closes
   the PIE/proto-language gap (known issue #10) and the per-sense-etymology
   gap (#14), and gives a legal path for #17.
2. **glottolog** — replaces the hand-maintained language-bucket map (known
   issue #3) with a real, sourced classification.
3. **Check whether `etymology-db`'s `doublet_with`/`cognate_of` rows, already
   on disk, are being read at all** — before adopting any external
   cognate/doublet dataset.
4. **rspeer/wordfreq** for #9 — stale since ~2021 but the best real per-word
   frequency numbers found.
5. **lexibank/wold** for #3 — needs aggregation work, no ready percentages.
6. **CogNet + lexibank/iecor** as cognate-list supplements.
7. Confirmed real gaps with **no good off-the-shelf fix** — flagged honestly
   rather than papered over: English false-friends data (#7), disputed-origin
   lists (#13, buildable from Wiktionary's own uncertainty templates), AAVE
   slang etymology (#15), sense-to-root cross-walks (#14), name etymology
   (#19). All need meaningful hand-curation regardless of base dataset.
