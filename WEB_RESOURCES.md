# Web Resource Research — Etymology Analyzer (Non-GitHub)

**Research only — nothing here has been adopted, built, or started.** Compiled
2026-07-24 from three parallel research passes across the live web (APIs,
dictionary sites, academic databases, corpora) — deliberately excluding
anything already covered in `GITHUB_RESOURCES.md` (etymology-db, wiktextract,
glottolog, lexibank, WOLD, CogNet, wordfreq, DBnary, and the per-language
digitized dictionaries found there). Every entry below was verified by an
actual fetch or a search-corroborated check, not recalled from memory — where
a fetch failed (bot protection, connection error), that's noted explicitly
rather than papered over.

Feature-number references (e.g. "#6") point to the backlog in
`FUTURE_FEATURES_AND_RESOURCES.md`: 1=heat map, 2=per-analysis pie chart,
3=passed-through-language %/loanword %, 4=master pie chart, 5=word-in-donor-
language form, 6=cognates, 7=false friends, 8=doublets, 9=frequency per 1000
words, 10=meaning round-trip detection, 11=full etymology tree, 12=single-
path arrow view, 13=disputed-origin flagging, 14=AI homonym/heteronym
disambiguation, 15=AAVE origins, 16=hover glossary, 17=auto-add unknown
words, 18=three-level toggle (already built), 19=proper-noun/name history,
20=guess-the-root game.

---

## Proto-language / PIE reconstruction (#10, #11, #18)

- **StarLing / Tower of Babel** — https://starlingdb.org — Live, but
  development looks stalled (copyright footer only goes to 2013). Hosts the
  core etymological database plus the Global Lexicostatistical Database
  (GLD). Bulk **Excel/PDF exports of the GLD are free** at
  `starlingdb.org/new100/downloads.htm`; the native raw StarLing binary
  format is contributor-only, and browsing it locally needs proprietary
  Windows software plus a special font. Best source for broad multi-family
  comparanda beyond Indo-European.
- **IELEX (Indo-European Lexicon)** — https://lrc.la.utexas.edu/lex (UT
  Austin Linguistics Research Center) — **Confirmed live**, clean tabular
  data: 60,000+ reflex entries, ~70,000 indexed spellings across ~100 IE
  languages/dialects (Family/Language, Reflex, POS/Grammar, Gloss, Source per
  row). Pages are explicitly flagged "under active construction." **No API or
  bulk download** — manual scraping of the tabular pages is the only route;
  `UTLRC@utexas.edu` for anything more. Good second, independently-curated
  IE-reflex source to cross-check wiktextract against.
- **PIE Lexicon** — pielexicon.hum.helsinki.fi — **Could not independently
  verify live** (every fetch attempt returned connection-refused). Per
  secondary sources (Helsinki research portal, Kielipankki), it's Jouna
  Pyysalo's "Pilot 1.1," generating ~100-120 IE daughter-language reflexes
  from PIE roots via sound-law scripts, no indication of an API or bulk
  download even per third-party description. Verify manually before relying
  on it.

## Language classification & geography (#1, #3, #16)

- **[CORE-adjacent] Unicode CLDR — Territory-Language Information** —
  https://unicode.org/cldr/charts/48/supplemental/territory_language_information.html
  (source XML in `unicode-org/cldr`'s `supplementalData.xml`) — **Standout
  find for the heat-map feature (#1).** For every territory, lists each
  language spoken with population %, literacy %, written-language-usage %,
  and official status (official/de facto/regional/recognized) — verified
  directly (e.g. Afghanistan → Persian, official, 20M speakers, 50% of
  population). Available as a browsable chart, raw XML, **and a downloadable
  TSV** (`territory_language_information.tsv`) — genuinely programmatic-
  friendly. Free, permissive Unicode license. Cleaner and more structured
  than the CIA Factbook, not paywalled like Ethnologue — the best-fit source
  for the *modern*-language layer of a heat map.
- **Glottolog website** (glottolog.org, distinct from the GitHub repo) —
  Live, currently serving v5.3. Adds a browsable bibliography (460,382
  references) on top of the GitHub data. **No public REST API on the website
  itself** — programmatic access is still via `pyglottolog` or the release
  downloads (PostgreSQL dump, CSV, BibTeX, RDF, Newick trees, CLDF via
  Zenodo, all CC-BY-4.0). The GitHub/CLDF route already found remains the
  real API surface.
- **WALS (World Atlas of Language Structures)** — wals.info — Live but
  **explicitly a finished/frozen project** ("will no longer be updated,"
  latest data v2020.4). Structural/typological features, not etymology —
  supplementary classification data only, no new ground beyond
  glottolog/lexibank. Bulk data via Zenodo, CC-BY-4.0. No API.
- **Ethnologue** — ethnologue.com — Confirmed **paywalled**: 7 free
  country/language pages/month, then $480/user/year (or a free "Essentials"
  tier limited to World-Bank-defined low/middle-income-country residents).
  Not viable as a bulk source for a personal project.
- **CIA World Factbook — Languages field** — cia.gov/the-world-factbook,
  per-country pages — Free, per-country language list with % where
  available, but **manual-browse only, no API**, and granularity is
  inconsistent country to country. Third-party structurers exist
  (`factbook-fields`/`factbook-readers` Ruby gems, worldfactbookarchive.org)
  if you don't want to scrape it yourself.
- **UNdata** (data.un.org, table 27, "Population by language...") — Real
  UN census-derived data but coverage is uneven depending on which countries
  reported language in their census — not a clean uniform global table.
- **DICL dataset** — "A Dataset on Linguistic Connectivity Across and Within
  Countries" (USITC, published in *Scientific Data*, 2025) — 242
  countries/territories, 6,674 languages, bilateral linguistic-connection
  measures. Possibly the cleanest ready-made structured option if you need
  country-pair/country-language linkage rather than raw Factbook scraping.
- **GeoNames** — geonames.org — Free, 11M+ placenames with a documented API,
  **but confirmed to have no language-tagging data at all** — pure
  geographic/postal data. Not useful for the heat map directly, though its
  boundary/coordinate data could still serve as map substrate alongside the
  Natural Earth/topojson data already found on GitHub.

## Historical / reconstructed-language homelands (#1)

No dedicated dataset or API exists for mapping extinct/reconstructed
languages (Old Norse, Proto-Germanic, PIE) to a region — confirmed genuine
gap, as expected. Best available: **Wikipedia's "Proto-Indo-European
homeland"** article (en.wikipedia.org/wiki/Proto-Indo-European_homeland) —
verified to contain multiple maps (the steppe-hypothesis homeland, a 2025
Caucasus–Lower Volga cline map sourced to Lazaridis et al. 2025, a
Neolithic-expansion map for the Anatolian hypothesis), all Wikimedia-Commons-
hosted and generally CC-licensed (verify per-file license before use).
Practical path: hand-curate a small static proto-language → approximate-
region lookup table seeded from this and similar Wikipedia pages (Old Norse
→ Scandinavia is uncontroversial; Proto-Germanic is usually placed in
southern Scandinavia/northern Germany) — there is no dataset to query here,
only scholarly consensus to encode by hand.

## Loanword / borrowing percentages (#3)

- **WOLD website** (wold.clld.org, distinct from the GitHub CLDF mirror) —
  Live, free, CC-BY 3.0 Germany. 41 recipient-language vocabularies, 395
  languages represented as donors. **Checked directly: no per-language
  borrowed-word percentage is published anywhere on the site** — no
  `/statistics` page exists (404), and the `/language` listing shows no
  percentage column. Aggregate figures (e.g. "English ~42% borrowed") only
  exist in secondary press coverage, not as a site table. Confirms the
  GitHub-side finding: **you'll need to compute per-language borrowing
  percentages yourself** from the underlying vocabulary data.

## Live etymology / lexicographic sources

- **[CORE-adjacent] Wikidata SPARQL endpoint** — query.wikidata.org/sparql —
  **Verified with an actual live query** against property **P5191** ("derived
  from lexeme"): a simple `SELECT ?lexeme ?derivedFrom WHERE { ?lexeme
  wdt:P5191 ?derivedFrom . }` returned real, current lexeme-derivation pairs.
  This is a genuinely usable, queryable, real-time etymology graph — not just
  theoretical — worth building a SPARQL client against as a live
  supplementary/cross-check layer on top of the static wiktextract dump.
  Coverage is inherently partial (lexeme data is one of Wikidata's less
  complete modules); full chains need recursive property paths
  (`wdt:P5191*`), and joining to `P5520`/`P437` on items gets prose
  etymologies too.
- **Wiktionary Action API** — en.wiktionary.org/w/api.php — Live, standard,
  well-documented MediaWiki JSON/XML API, no auth needed for reads. Full page
  content including etymology sections via `action=query`/`action=parse`.
  The best live, on-demand alternative/supplement to a static wiktextract
  dump — directly relevant to #17 (auto-add unknown words): querying this
  API live is a clean, ToS-friendly way to fetch a missing word's etymology
  on demand, using data Wiktionary explicitly licenses for reuse (CC-BY-SA/
  GFDL), unlike scraping etymonline.
- **Merriam-Webster Developer API** — dictionaryapi.com — **Free, verified,
  and a standout find.** 1,000 queries/day/key, **non-commercial use only**
  (commercial requires contacting them). Covers Collegiate Dictionary,
  Thesaurus, Medical, Spanish, ESL, Learner's dictionaries. **The Collegiate
  Dictionary JSON genuinely includes an `"et"` (etymology) field** — verified
  example for "traffic": `"Middle French trafique, from Old Italian
  traffico, from trafficare to trade in coastal waters"`. The strongest
  *legitimate, API-based* etymology source found in this whole pass — rate-
  limited but free and real-time, good as a cross-check/auto-add source
  alongside the Wiktionary API.
- **Etymonline.com itself** — Confirmed live, still THE canonical free
  English etymology reference (Douglas Harper, since 2001; Talia Felix
  co-editor since 2021), no serious free competitor. **No official API or
  bulk-data offering.** Its Terms of Service
  (etymonline.com/legal/terms) assert broad IP ownership but **do not
  explicitly address scraping/API use/bulk extraction at all** — this is
  silence, not permission, which matters since the earlier GitHub research
  pass found several unofficial scrapers that also don't discuss ToS. Decide
  your own reuse stance deliberately rather than inferring one from the
  absence of language either way.

## Non-English live etymology dictionaries (donor-language cross-check, #5)

- **CNRTL** (French) — cnrtl.fr/etymologie/ — Live, free, browsable
  alphabetically. **Note: the current portal is slated for retirement around
  September 1, 2026**, to be replaced by a new interface — worth re-checking
  post-migration. No explicit reuse license found (bare copyright notice) —
  manual-lookup reference only, not a licensed data source.
- **DWDS** (German) — dwds.de — Confirmed to include **real etymology
  content**, not just definitions — verified on "Haus": a full etymology
  section (authored by Wolfgang Pfeifer) tracing it to Old High German
  *hūs*, English/Dutch cognates, and a proposed PIE root. Good quality,
  scholarly-sourced. Corpus search now requires login; individual dictionary
  entries still appear accessible without one. No API.
- **RAE/DLE** (Spanish) — dle.rae.es — Entries carry etymology in a
  parenthetical before the definition (verified format for "casa": "(Del
  lat. casa, choza)"). No official API; **rae-api.com** is a free,
  community-maintained, explicitly-labeled unofficial wrapper — usable but
  not authoritative or guaranteed-stable.
- **Perseus Digital Library** (Latin/Greek) — perseus.tufts.edu — Live,
  free, non-profit, partnered with the "Open Greek and Latin" initiative.
  The Scaife Viewer offers word/phrase-level alignments and integrated
  lexicon/commentary access beyond the static Lewis & Short/LSJ data already
  found on GitHub. Direct fetches of the Word Study/Morphological Analysis
  tools errored (likely need query params) — worth a follow-up with an
  actual word query before relying on it. No documented API.
- **Cologne Digital Sanskrit Lexicon** (live site, distinct from its GitHub
  mirror) — sanskrit-lexicon.uni-koeln.de — Confirmed live: 36+ digitized
  dictionaries (including Monier-Williams), searchable by Sanskrit/English/
  Tamil/Pahlavi, multiple display modes, PDF scans, SLP1 XML downloads. Free.
  Good live-query complement to the GitHub-mirrored static data.

## Dictionary / word-sense APIs for hover-glossary (#16) and deep-dive (#6-#9)

| API | Free tier | Etymology data? | Notes |
|---|---|---|---|
| **Merriam-Webster** (dictionaryapi.com) | Yes, 1,000/day, non-commercial | **Yes** (`"et"` field) | See above — best etymology API found |
| **Wordnik** (developer.wordnik.com) | Yes, confirmed active | Not confirmed present | 800K+ words, 5 dictionary sources, 10M+ example sentences — strong for definitions/examples, etymology field unverified, needs doc-diving |
| **Free Dictionary API** (dictionaryapi.dev) | Yes, no key needed | **No — tested live, not just undocumented.** Despite some blog posts describing an `"origin"` field, live requests for "etymology" and "hello" returned no origin field at all (just word/phonetics/meanings/license/sourceUrls). Wiktionary-sourced (CC BY-SA 3.0), so attribution required regardless. | Definitions/phonetics only — don't rely on it for etymology |
| **Oxford Dictionaries API / OED** | No — confirmed paywalled | — | £50/month+ (Jan 2025 pricing); free-for-academics sandbox capped at 3 months |
| **Collins Dictionary API** | Application-gated, no public pricing shown | — | Deprioritize unless specifically wanting Collins bilingual data |

## Word frequency corpora (#9)

- **Google Books Ngram Viewer / raw dataset** — books.google.com/ngrams —
  Free, live, 1800–2022, multiple languages. Raw n-gram downloads: v3 (Feb
  2020) at storage.googleapis.com/books/ngrams/books/datasetsv3.html
  (gzip records: ngram, year, match count, volume count) — no version newer
  than 2020 exists. Also on BigQuery and AWS Open Data Registry. A
  `google-ngram-downloader` PyPI package exists for programmatic pulls.
- **wordfrequency.info** (Mark Davies) — Direct fetch blocked (403) but
  search-corroborated: top 5,000 words/lemmas from the 450M-word COCA corpus
  freely downloadable (XLSX/TXT) with POS tags and top collocates. Larger
  lists (20K/60K words) are paid.
- **COCA** (english-corpora.org/coca) — Freemium: searching is free for
  registered users, bulk/advanced access is paid.
- **Leipzig Corpora Collection** (corpora.uni-leipzig.de /
  wortschatz.uni-leipzig.de) — Confirmed free (CC BY-4.0) via search
  corroboration (direct fetch hit a bot-challenge screen). 20+ languages
  (broader "Leipzig monolingual dictionaries" effort covers more), three text
  types per language (news/web/Wikipedia), frequency lists 10K-1M words
  downloadable. Good multilingual complement if the project ever extends
  beyond English.
- **SUBTLEX** — institutional homes: Ghent University's Center for Reading
  Research (crr.ugent.be/programs-data/subtitle-frequencies) for SUBTLEX-US,
  University of Nottingham
  (psychology.nottingham.ac.uk/subtlex-uk) for SUBTLEX-UK — **both direct
  fetches returned 404/403**, likely stale paths or bot protection; existence
  and free status is well corroborated by academic citation (van Heuven et
  al. 2014, Brysbaert's lab), but verify the exact download URL by hand in a
  browser before depending on it. Live lookup mirror:
  subtlexus.lexique.org.

## Word-sense disambiguation / homonym resources (#14)

- **Princeton WordNet** — wordnet.princeton.edu — Free, BSD-style license,
  research and commercial use permitted with citation. ~117,000 synsets.
  **No etymology data by design** (purely sense/relation-based) — useful as
  a sense inventory (synsets, hypernymy) for #14, not an etymology source.
- **SemCor** — sense-tagged corpus (352 Brown Corpus docs, 226,040 sense
  annotations mapped to WordNet 3.0). Free download at
  web.eecs.umich.edu/~mihalcea/downloads.html#semcor (Rada Mihalcea's page,
  not GitHub); also mirrored on Kaggle. Gold-standard data if a WSD component
  is ever trained/evaluated.
- **HuggingFace Model Hub — WSD models** (search-corroborated, one fetch
  attempt hit a transient error — re-verify before committing to a specific
  model): `jpwahle/t5-large-word-sense-disambiguation` (T5-large, trained on
  SemCor 3.0), `jpelhaw/t5-word-sense-disambiguation` (~2.75GB), `GAIR/
  rst-word-sense-disambiguation-11b` (11B params, likely overkill for a
  personal project). A community testing Space also exists:
  huggingface.co/spaces/Belligerent/word-sense-disambiguation.

## AAVE / Black English origins (#15) — thin, as expected

- **DARE (Dictionary of American Regional English)** —
  daredictionary.com — Confirmed **subscription-based**: $49/year
  individual, scaled institutional pricing. 30-day free trials for nonprofit
  institutions only. Edited/based at UW-Madison (dare.wisc.edu), digital
  product published/sold by Harvard University Press. dare.wisc.edu itself
  is mostly project/history/FAQ pages, not a free browsable dictionary. No
  free bulk or browse access found.
- **Oxford Dictionary of African American English (ODAAE)** —
  oed.com/discover/odaae/, hutchinscenter.fas.harvard.edu/odaae —
  **Confirmed still in progress, not usable today.** Joint OUP/Harvard
  Hutchins Center project (Henry Louis Gates Jr.); only ~10 sample entries
  publicly unveiled as of its 2025 target release. Bookmark for later, not
  now.
- **Stanford / John Rickford's AAVE page** —
  web.stanford.edu/~rickford/AAVE.html — **Confirmed a dead end**: a static,
  unmaintained 1996 course-syllabus page, no glossary, no word list. His
  academic papers exist (johnrickford.com PDFs) but are scholarly articles,
  not structured reusable data.
- **Bottom line, unchanged from the GitHub pass**: essentially nothing
  freely and immediately usable exists for this feature. Budget for the $49/
  year DARE subscription if it matters, or lean on general corpus/frequency
  data plus manual curation instead.

## False friends (#7)

- **Wiktionary — Appendix:Glossary of false friends** —
  en.wiktionary.org/wiki/Appendix:Glossary_of_false_friends — **Best
  resource found for this feature, better than the GitHub-side academic
  research code.** Confirmed live and substantial: covers English against
  French, German, Spanish, Italian, Polish, Swedish, Dutch, other Slavic
  languages, Finnish, Mandarin, Japanese, Hebrew, Arabic. Structured table
  (non-English word / resembles English / actually means / equivalent word),
  ~300+ written entries plus a separate spoken-homophones section. Freely
  reusable under Wiktionary's CC BY-SA terms.
- **Blog-style lists** (FluentU, Omniglot, myenglishpages.com) — confirmed
  thin/informal as expected: small per-language-pair posts (~20 entries
  each), pedagogically oriented, no systematic dataset. Fine for
  human-readable examples/citations, not for bulk data — prioritize the
  Wiktionary appendix over these.

## Onomastics / name history (#19)

- **Behind the Name** — behindthename.com — **Best onomastics resource
  found, by a wide margin.** Free to browse, genuine per-name etymology
  content (verified depth on a sample entry). **Has a free public API**
  (registration required): name lookup for gender/usage, random names,
  synonyms; rate-limited (2/sec, 400/hr, 4,000/day, 400,000/year).
  Downloadable datasets are **CC BY-SA 4.0 licensed** — explicit, clean reuse
  rights. Sister sites for surnames and place names exist too.
- **Nordic Names** — nordicnames.de — Free-access, 50,000+ Nordic/
  Scandinavian names, historical collections (Old Norse bynames, Viking
  names). **Footer states "All rights reserved"** — no open license, no API.
  Manual-reference use only.
- **Oxford Dictionary of Family Names (Britain & Ireland)** — Confirmed
  **paywalled**, institutional/library access or £115-440 print, only
  sporadic promotional free-access windows. 45,000+ surnames, considered
  authoritative but not viable as an always-on source.

## Unicode Unihan Database (Chinese/Japanese character supplement)

unicode.org/charts/unihan.html + Unihan.zip — Free download. Beyond
radical-stroke indices, contains genuinely etymology-adjacent fields (per
UAX #38): `kTraditionalVariant`/`kSimplifiedVariant`,
`kSemanticVariant`/`kSpecializedSemanticVariant`, `kZVariant`,
`kCompatibilityVariant`, `kPhonetic`, `kFanqie` (ancient Chinese
reading-derivation method), plus cross-reference indices into major
historical sinological dictionaries (`kHanYu`, `kKangXi`, `kMorohashi`,
`kGSR`). **Confirmed genuine added value beyond `makemeahanzi`** (which
mostly covers stroke-order/glyph decomposition) — Unihan's variant-tracking
and dictionary-index fields give a path to character-history/variant lineage
that makemeahanzi doesn't have. Not narrative etymology, but a legitimate
structured supplement.

## Prior-art etymology map / tree visualizations

Found for inspiration only, not as data sources:
- map.kian.im, wordhub.top/etymology, ezspell.app/learning-tools/word-origin-map
  — interactive word-origin-migration maps; none confirmed to cite a specific
  reusable backing dataset (likely hand-curated per word).
- world-languages.com (interactive radial tree, 8,481 languages/26 families)
  and a D3 force-directed language tree sourced from **Glottolog**
  (dr.eamer.dev/datavis/poems/language, 7,370 languages) — reinforces
  Glottolog as the right backbone if a language-family tree visualization is
  ever built.
- Reinforces the earlier finding: a heat-map-with-intermediate-stops feature
  is a genuinely underserved niche — no existing project's dataset is
  reusable — CLDR (modern layer) + a hand-curated proto-language lookup
  table (historical layer) remains the best path.

---

## Bottom line — standout new findings from this pass

1. **Unicode CLDR's territory-language TSV** — the cleanest, free,
   structured modern language-to-country data found anywhere for the heat
   map (#1), better than CIA Factbook or Ethnologue.
2. **Wikidata's live P5191 SPARQL endpoint** — a genuinely queryable,
   real-time supplementary etymology-chain source, worth a client layered on
   top of the static wiktextract dump.
3. **Merriam-Webster's Developer API** — a legitimately free (non-
   commercial), rate-limited, etymology-*bearing* API — rarer than expected
   and the strongest live etymology-lookup option for #17 alongside the
   Wiktionary Action API.
4. **Behind the Name** — a clean, CC-BY-SA-4.0, API-backed onomastics source
   that fully closes the "no name-etymology dataset" gap flagged in the
   GitHub-only pass, for #19.
5. **Wiktionary's own false-friends appendix** — better and more systematic
   than anything found in the GitHub-only pass for #7.
6. **No dataset exists anywhere (GitHub or web) mapping historical/
   reconstructed languages to geographic regions** — confirmed, not just
   unsearched. This piece of #1 will always need hand-curation from
   scholarly sources like the Wikipedia PIE-homeland article.
7. **AAVE etymology (#15) remains a genuine, confirmed dead end** for free
   data across both research passes — DARE is paywalled, ODAAE isn't
   released yet, and academic pages are static/archival. If pursued, this is
   a $49/year subscription or a manual-curation project, not a data-sourcing
   one.
8. Two documentation-folklore corrections worth remembering: **dictionaryapi.dev
   does NOT reliably return etymology** despite some blog posts claiming
   otherwise (tested live), and **etymonline.com's ToS is silent on
   scraping/reuse**, not permissive — don't assume either without
   re-checking.
