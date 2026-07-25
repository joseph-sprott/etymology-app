# Root Relations: Cognates, Doublets, and PIE Root Fan-Out

**Audience: other agents working on this project.** Read this before touching
cognate, doublet, or root-relationship features.

**Status: research and measurement only. No code has been written, and none
should be written from this document without the owner asking for it.** Every
number below was produced by fetching and parsing the real sources on
2026-07-25, not recalled from memory. Where something was not verified, it
says so.

---

## 1. The north star

The owner's stated interest, in their own words:

> "the fact that we can trace a bunch of words from around the world to one PIE
> root is incredible. And its very cool that there are multiple words in one
> language that come from a single source like axis, axle, and aisle."

That is two distinct phenomena, and they should be modelled as two distinct
relations. Conflating them is the single easiest mistake to make here:

- **Root fan-out (cross-language).** One ancestral root radiating outward into
  many descendants across many languages. `*wódr̥` → water, Wasser, voda, vatn,
  uisce, ujë, vanduõ. This is the **cognate** relation.
- **Same-language multi-reflex.** Several words in *one* language from a single
  root, arrived by different routes. axis / axle / aisle. This is the
  **doublet** relation, and it is the more surprising of the two because the
  words no longer look related.

Features should serve the *delight of surprising connection*, not
completeness. "aisle and axis are the same word" is the payload.

---

## 2. Current state and measured baseline

Measured against the shipped `word_info.json` on 2026-07-25:

| Metric | Value |
| --- | --- |
| Words in `word_info.json` | 278,131 |
| …with **any** cognate | 11,602 (**4.2%**) |
| …with **any** doublet | 8,084 (**2.9%**) |
| Total cognate rows | 46,454 |
| Total doublet rows | 13,270 |
| Distinct cognate languages | 652 |

Top cognate languages are heavily Germanic: German (4,562), Dutch (3,831),
Swedish (2,499), French (2,432), Danish (2,078), Old English (1,985).

**Why coverage is thin:** the existing sources are *pairwise*. A Wiktionary
`{{cog|nl|water}}` template yields exactly one cognate pair. The two sources
below are *set-shaped* — one cognate set of N members yields cognates for every
member at once. That structural difference, not volume, is what closes the gap.

**Known data-quality wart (pre-existing, unrelated to the new sources):** 69 of
the 652 cognate "language" labels are unresolved bare codes rendered as if they
were language names — `akk-nas`, `alg-pro`, `ber-pro`, `cmn-TW`, `de-AT`,
`en-US`, `fr-CA`, `enm-emi`, `ang-wsx`, etc. Worth fixing whenever cognate
display is next touched.

---

## 3. Source A — UT Austin Indo-European Lexicon

**URL:** https://lrc.la.utexas.edu/lex
**What it is:** UT Austin Linguistics Research Center's digitization of Julius
Pokorny's *Indogermanisches etymologisches Wörterbuch* (1959), with reflexes
across ~104 IE languages.
**License:** No explicit licensing terms stated anywhere on the site. Treat as
**unclear** — fine for personal/local use, but do not redistribute the scraped
data without asking UT (`UTLRC@utexas.edu`). Flag this to the owner before any
public deployment.
**Access:** No API, no bulk download. HTTP fetching only. Pages are marked
"under active construction," so the data will change over time.

### 3.1 The three access surfaces

| Surface | URL pattern | What it gives |
| --- | --- | --- |
| Master etymon list | `/lex/master` | All 2,222 Pokorny etyma; 1,541 link to reflex pages |
| Individual etymon | `/lex/master/0011` | One complete cognate set — every reflex, with PoS, gloss, source |
| **Per-language index** | `/lex/languages/E` | Every reflex in that language, each linked to its etyma |
| Semantic field index | `/lex/semantic` | Roots browsable by meaning (Buck's 1949 scheme, 22 categories) |

### 3.2 THE KEY FINDING — harvest via 104 language indexes, not 1,541 etymon pages

The obvious approach is to scrape all 1,541 etymon pages. **Don't start there.**
There are **104 per-language index pages** (`/lex/languages/<CODE>`), each a
single request returning that language's entire reflex list with every reflex
linked to its etymon number.

Verified measurements:

- `/lex/languages/E` (English) — one 5.4 MB request → **13,483 English reflexes**,
  14,221 reflex→etymon links, across **1,336 distinct etyma**.
- `/lex/languages/Lat` (Latin) — one 3.9 MB request → **9,785 Latin reflexes**
  across 921 etyma.

Because every row carries the etymon number, **joining all 104 indexes on
etymon number reconstructs the complete cognate sets** — in ~104 requests
rather than 1,541. That is the efficient path to the *relationships*.

The 104 codes (verbatim, from `/lex/languages`):

```
Afrik Alb AngFr Arm Att Av Bret BritE Corn CrGo Cz Dan Dor Du E Flem Fr Fris
G Gael Gaul Gheg Gk Go Hesy Hin Hitt Hom Ice Ir It LG LGk LLat Lat Latv Lith
Luw Lyc MDu ME MELat MFr MGk MHG MIr MLG MLat MPers MW Manx NFris NLat NUmb
Norw OArm OCS ODan ODu OE OFr OFris OHG OIce OIr OIt OLG OLat ON ONFr OOcc
OPers OProv OPrus ORuss OS OSlav OSp OSw OW Osc Oss Pala Pali Pers Pol Port
Prak Prov Run Russ SCr ScotE ScotG Skt Sp Sw Toch TochA TochB Umb VLat W Yid
```

**What the language indexes do NOT give:** per-reflex part-of-speech, gloss, or
source citation. Those live only on the etymon pages. So: language indexes for
the relationship graph (cheap), etymon pages for annotation detail (expensive,
and only worth fetching for roots you actually surface).

### 3.3 Language-index row structure

```html
<tr class="searchable_reflex_row">
  <td> <span lang='en'>aardvark</span> </td>
  <td>
    <a title="earth" href='/lex/master/0499#E'>
      <span class='Unicode' lang='ine'>4. er-</span></a>,
    <a title="porker, pig(let)" href='/lex/master/1547#E'>
      <span class='Unicode' lang='ine'> pork̑o-s</span></a>
  </td>
</tr>
```

Note what comes free: the `title` attribute is the **root's gloss**, and the
`<span lang='ine'>` is the **root form**. So one request yields word → (root
form, root gloss, etymon id) for a whole language.

**Compounds map to multiple roots.** `aardvark` = *er- "earth" + *pork̑o-s
"pig" — literally "earth-pig." **724 English words** decompose into 2+ PIE
roots this way. This is a feature waiting to happen (see §6.3). Real examples
from the data:

| Word | Roots |
| --- | --- |
| `triceratops` | "horn, head" + "to see, eye" + "three" |
| `sesquipedalian` | "and" + "foot" + "half, semi-" |
| `triskaidekaphobia` | "to flee, run away" + "ten" + "three" |
| `paramount` | "at, by, to" + "to rise, mount, tower" + "to pass over/beyond" |
| `prosopography` | "to carve, scratch; write" + "to see, eye" + "to pass over" |

### 3.4 Etymon-page structure and its parsing traps

An etymon page (`/lex/master/0011`) is one complete cognate set. Verified:
**367 reflexes across 46 languages**, of which **79 are modern English**.

Header shape:
```html
<p><b>Pokorny Etymon</b>: <span class='Unicode' lang='ine'> ag̑-</span>
   &nbsp; 'to lead, drive, <b>agitate</b>'</p>
<p><b>Semantic Field(s)</b>: <a href="/lex/semantic/field/MO_LE">to Lead</a>, …</p>
```

**Trap 1 — the language cell is STICKY.** Only the first row of a language block
carries its label; continuation rows have an empty `<td></td>` and inherit it.

```html
<tr><td id='OIr'><span class='right'>Old Irish: </span></td>
    <td><span lang='sga'>ag-</span></td><td>vb</td><td>to conduct</td><td>GED</td></tr>
<tr><td></td>                              <!-- still Old Irish -->
    <td><span lang='sga'>ār</span></td><td>vb</td><td>to slaughter</td><td>GED</td></tr>
```
Missing this undercounts by roughly **10×** — a 309-row page reads as ~10 rows.
This was hit and corrected during research; do not rediscover it the hard way.

**Trap 2 — family header rows** (`<td><strong>West Germanic</strong></td>` with
`colspan='4'`) carry no reflex, must be skipped, but *do* reset the current
language.

**Trap 3 — multiple spellings per cell**, comma-separated, each in its own
`<span lang=…>`: `<span lang='ang'>e(a)x</span>, <span lang='ang'>æx</span>`.
All are the same reflex. Parenthesised letters are optional spellings.

**Trap 4 — there is no "Meaning:" label.** The gloss is the single-quoted run
*after* the root span. Searching for a `Meaning`/`Gloss` label instead matches
the reflex table's `Source(s)` column header and silently yields garbage.

**Bonus — `lang` attributes are real ISO 639-3 codes** (`sga`, `ang`, `enm`,
`cy`, `goh`, `got`). This is what makes UT data mergeable with the project's
existing code→name resolution in `wiktextract_langs.py`.

**Quirk worth knowing:** the English index includes literary coinages —
`gentlehobbit`, `Wilderland`, `Frogmorton` (Tolkien). Charming, but they are
not ordinary vocabulary; consider whether to filter.

### 3.5 Measured yield for English

| Metric | Value |
| --- | --- |
| Distinct English reflexes | **13,483** |
| Distinct etyma referenced | 1,336 |
| Words in a root family (2+ English words per etymon) | **13,274** |
| Etyma with 2+ English words | 1,122 |
| Median root-family size | 5 |
| Largest families | 150, 142, 131, 123, 100, 97, 84, 79, 77, 75 |
| Same-root pairs with differing 4-letter stems | **205,859** |
| English words decomposing to 2+ roots | 724 |

For scale: the current doublet total across the whole app is **13,270 rows**.
This one source offers **205,859** same-root pairs before any filtering.

### 3.6 Which roots produced the most English words

Directly usable as a "most productive root" leaderboard:

| English descendants | Root | Gloss | Page |
| --- | --- | --- | --- |
| 150 | *2. dhē- | to do, put, place, set | `/lex/master/0376` |
| 142 | *2a. per- | to pass over/beyond | `/lex/master/1489` |
| 131 | *4. (s)ker- | to cut, shear, score, scribe | `/lex/master/1742` |
| 123 | *stā- | to stand | `/lex/master/1873` |
| 100 | *sed- | to sit, set, settle | `/lex/master/1658` |
| 97 | *1. g̑en- | to bear, produce, generate | `/lex/master/0566` |
| 84 | *leg̑- | to gather, collect | `/lex/master/1131` |
| 79 | *1. pel- | to pour, fill; full | `/lex/master/1471` |
| 77 | *2. pē̆d- | foot | `/lex/master/1458` |
| 75 | *ag̑- | to lead, drive, agitate | `/lex/master/0011` |

**Showcase fan-outs** (verbatim from the data — these are the demo material):

- ***sed-** "to sit" → sit, set, settle, seat, **chair**, **cathedral**,
  **nest**, **niche**, **nick**, **banshee**, **ersatz**, **method**,
  **period**, **episode**, cathode, anode, assess, obsess, possess, preside,
  president, session, siege, subsidy, cease, ancestor, dissident, insidious.
- ***stā-** "to stand" → stand, **cost**, **oust**, **post**, **rest**,
  **arrest**, **establish**, **estate**, **constable**, **Hindustan**,
  **ecstasy**, **obstetric**, statue, static, system, assist, exist, obstacle,
  instant, destitute, armistice, contrast.
- ***ag̑-** "to lead, drive" → act, agent, **axis**, **axle**, **aisle**,
  **agony**, **ambassador**, **embassy**, **squat**, **essay**, **assay**,
  exact, examine, allege, agile, agitate, cache, cogent, litigate, demagogue.

`banshee` and `nest` and `chair` all from "sit"; `ecstasy` and `cost` and
`Hindustan` all from "stand." That is the product.

---

## 4. Source B — IE-CoR (Indo-European Cognate Relationships)

**The eva.mpg.de department page itself is just a portal** — the useful asset it
points to is IE-CoR.

**Repo:** https://github.com/lexibank/iecor (v1.2)
**Browse:** https://iecor.clld.org
**Paper:** *Scientific Data* (2025), "The Indo-European Cognate Relationships dataset"
**License:** **CC-BY-4.0** — cleanly reusable with attribution. Cite the version.
**Download:** verified working — `/archive/refs/tags/v1.2.zip`, **6.4 MB**.
**Scale:** 160 varieties (152 Glottocodes) × 170 core-vocabulary concepts;
25,731 lexemes; **4,981 expert-verified cognate sets**; built by 89 linguists
from 355 cited sources.

### 4.1 Files (CLDF Wordlist)

| File | Rows | Contents |
| --- | --- | --- |
| `forms.csv` | 25,731 | `Language_ID, Parameter_ID, Form, Value, Segments, Gloss, Loan, Source` |
| `cognates.csv` | 25,741 | `Form_ID → Cognateset_ID`, plus `Doubt`, `Alignment` |
| `cognatesets.csv` | 4,981 | `Root_Form, Root_Gloss, Root_Language, Justification, Comment` |
| `languages.csv` | 160 | `Name, Glottocode, ISO639P3code, Latitude, Longitude, Family, Clade, Color` |
| `parameters.csv` | 170 | Concepts, linked to **Concepticon** |
| `loans.csv` | 1,036 | Documented borrowing events |

### 4.2 Measured yield

- **169 distinct English words**, 125 of which have cognates.
- **5,327 cross-language cognate pairs** derivable for English (~31 per word).
- Example — English `water` (concept "water", cognateset 335) → **66 cognates**:
  Gheg `ujë`, Bulgarian `voda`, Czech `voda`, Danish `vand`, Dutch `water`,
  Faroese `vatn`, Flemish `water`, Frisian `wetter`, German `Wasser`,
  Icelandic `vatn`, Irish `uisce`, Lithuanian `vanduõ`, Lower Sorbian `woda`…

Narrow but deep, and it covers exactly the core vocabulary users look up first.
Highest-confidence cognate data available anywhere for IE.

### 4.3 Underrated extras

- **`cognatesets.csv` carries prose `Justification`** — human-readable
  linguistic reasoning with inline citations, e.g. *"Etymology uncertain, cf.
  [Morgenstierne 2003](src-323):78 for suggestions."* Directly displayable as
  "why linguists think these are related," and a ready-made source for the
  disputed-origin flagging idea (backlog #13).
- **`loans.csv`** — 1,036 borrowing events with source language and source
  form, e.g. Cognateset 4 ← Persian `خراب / xarāb`, noted "from Arabic";
  Cognateset 46 ← ?West Semitic, cf. Biblical Hebrew `מֶגֶד`. Borrowing *route*
  is exactly what makes a doublet a doublet.
- **`languages.csv` has lat/long, Glottocode, clade, and a display `Color`** —
  drop-in for the heat-map (#1) and any map view, and the Glottocodes join
  straight to Glottolog.
- **`parameters.csv` links to Concepticon**, so IE-CoR concepts join to CLICS,
  WOLD, and the rest of the CLLD ecosystem.

---

## 5. THE MOST IMPORTANT CAVEAT — same-root ≠ doublet

**Read this before building anything.**

Every English reflex on one etymon page shares that root, so it is tempting to
call them all doublets of each other. **That is wrong and will put false claims
on screen.**

Etymon 0011 (*ag̑-) has 79 English reflexes including `act, action, actor,
actress, actual, actuary, actuate`. Those are **morphological derivatives of
one English word** — `action` is not a doublet of `act`, it is `act` + a
suffix. Meanwhile `aisle`, `axle`, and `axis` on that same page **are** genuine
doublets: separate arrivals into English by different routes.

A defensible three-way split:

| Relation | Definition | Example |
| --- | --- | --- |
| **Cognate** | Same root, *different* language | water / Wasser / voda |
| **Doublet** | Same root, same language, *different route in* | axis / axle / aisle |
| **Root family** | Same root, same language, any relation incl. derivatives | act / action / actor / agent / agile |

Root family is the honest label for the wide set, and it is *new information
the app does not currently have*. It should be presented as its own thing, not
folded into doublets.

Distinguishing true doublets from derivatives automatically is genuinely hard.
A cheap heuristic — require the two words' first ~4 letters to differ — keeps
aisle/axle/axis and drops act/action/actor. It is crude: it wrongly splits
`axis`/`axle` from... nothing, but it *would* wrongly keep `agent`/`agile` as
doublets, and wrongly drop true doublets that happen to share a prefix
(`castle`/`chateau` survives, but `secure`/`sure` does not). **Be conservative:
a wrong doublet is a factual error on screen; a missed one is only a gap.**
The real signal is the *route* (via Old French vs. direct from Latin), which
`loans.csv` and the etymon pages' source citations partially supply.

---

## 6. How this maps to features

Backlog numbering follows `FUTURE_FEATURES_AND_RESOURCES.md`
(6=cognates, 8=doublets, 11=full etymology tree, 13=disputed origins, 20=game).

### 6.1 Fills existing backlog items
- **#6 cognates** — IE-CoR gives ~31 high-confidence cognates for each of 169
  core words; UT gives cross-language sets for 13,483 English words.
- **#8 doublets** — 205,859 candidate pairs vs. 13,270 rows today.
- **#13 disputed origins** — IE-CoR `Justification` + `Doubt` columns.

### 6.2 Root explorer (the headline feature)
Pick a root, see every descendant fanning out — grouped by language family,
with the English descendants highlighted. `*sed-` → 100 English words plus
reflexes across 40+ languages. A radial/sunburst layout suits this; so does a
plain grouped list, which is far cheaper and works server-rendered.

### 6.3 Compound decomposition
724 English words decompose into 2+ PIE roots. `triceratops` = "horn" + "eye"
+ "three." `aardvark` = "earth" + "pig." Show a word broken into its root
atoms with glosses. Small, self-contained, high delight-per-byte.

### 6.4 "Surprising relatives"
The killer feature for this owner. Surface pairs that share a root but look
unrelated — `banshee`/`chair`, `cost`/`ecstasy`, `aisle`/`axis`. Rank by
*dissimilarity* (string distance high, root identical) to auto-find the most
startling pairs. The 205,859-pair set is the raw material; the ranking is what
makes it good.

### 6.5 Most productive roots leaderboard
Straight out of §3.6 — already computed, needs no new data.

### 6.6 Browse by meaning
UT's semantic field index (Buck's 1949 scheme, 22 top-level categories,
`/lex/semantic/category/PW` etc.) lets users explore roots by concept rather
than spelling. Note IE-CoR's Concepticon links do the same job with a modern,
machine-readable vocabulary — prefer Concepticon where both apply.

### 6.7 Map / geography
IE-CoR `languages.csv` ships lat/long + clade + colour for 160 varieties.
Show where a root's descendants are spoken today. Feeds backlog #1 directly.

---

## 7. Integration notes (for whenever code is authorised)

**No code exists for any of this.** These are constraints to respect, not a plan
to execute.

- **Cognates and doublets are SIBLING relations and must stay out of the
  ancestry pipeline.** Three modules independently discard them as "not
  ancestry" (`convert_wikt.py`, `build_etymology_trees.py`,
  `convert_wiktextract.py`). That filtering is correct — a cognate is not an
  ancestor, and letting one into a lineage chain fabricates descent. Any new
  data must go into a *sibling* index alongside, never by loosening that filter.
- **Old English / Middle English reflexes are ancestors of the modern word, not
  siblings.** UT lists them in the same tables as everything else. They belong
  to the lineage pipeline and should be excluded from both cognate and doublet
  output.
- **`word_info.py` is the shared store.** Both the analyzer's hover cards and
  the Word Search page read through it, per the standing rule that every
  feature pools from one store. Anything added there reaches both features at
  once — which is also what the owner's "fix every feature, not just the one
  reported" rule requires.
- **Do not fold a re-scrapeable source into `build_word_info.py`'s output.**
  That builder costs a full scan of the 3.2 GB wiktextract dump; coupling a
  cheap, frequently-refreshed source to it makes every refresh pay that cost.
- **Cap display.** Word Search already caps cognates at 40. Root families reach
  150 members and cognate sets reach 66 — capping and a "…and N more" affordance
  are required, not optional.
- **Licensing asymmetry matters.** IE-CoR is CC-BY-4.0 and safe to redistribute
  with attribution. UT Austin states no licence at all — local use is fine,
  redistribution needs permission. Do not ship a scraped UT dataset publicly
  without raising this with the owner first.
- **Be a polite scraper.** 104 requests with a real User-Agent and a delay is
  neighbourly; 1,541 hammered requests is not. UT is a small academic server.

---

## 8. Verification log

| Claim | How verified |
| --- | --- |
| UT `/lex/languages/E` → 13,483 reflexes | Fetched, parsed |
| UT `/lex/languages/Lat` → 9,785 reflexes | Fetched, parsed |
| UT 104 language codes | Parsed from `/lex/languages` |
| UT etymon 0011 → 367 reflexes, 46 langs, 79 English | Fetched, parsed |
| UT master list → 1,541 etyma with reflex pages | Parsed from `/lex/master` |
| UT full corpus → **1,541 etyma / 73,754 reflexes** | Complete fetch of all 2,222 etymon pages (confirms UT's own "60,000+ reflexes" claim, and that exactly 681 etyma have no reflex page) |
| Root leaderboard, 724 compounds, 205,859 pairs | Computed from `/lex/languages/E` |
| IE-CoR v1.2 zip downloads, 6.4 MB | Downloaded (HTTP 200) |
| IE-CoR counts, English yield, `water` → 66 cognates | Parsed from the CLDF CSVs |
| Baseline coverage percentages | Computed from shipped `word_info.json` |

**Not verified:** UT licensing terms (absent from the site — needs a human to
ask `UTLRC@utexas.edu`); whether UT's "under active construction" pages change
often enough to need periodic re-harvest; PIE Lexicon (Helsinki) still refuses
connections, as `WEB_RESOURCES.md` already notes.

---

## 9. Prior art — the competitive landscape is empty

**Provenance note:** §9 and §10 come from a separate research pass that verified
each claim by fetching. Those findings have *not* been independently re-checked
by the author of §§1–8. Where the two disagree, §§1–8 are the measured ones.

### 9.1 The headline finding: the flagship tool is dead

**Etytree** (`etytree.toolforge.org`) — the first graphical multilingual
etymology dictionary, a Wikimedia grant project — is a **zombie**. The UI still
returns HTTP 200, but its `bundle.js` sends every query to
`etytree-virtuoso.wmflabs.org/sparql`, which returns **HTTP 502** ("This web
service cannot be reached"). The search box returns nothing. Source last pushed
**2019**; underlying data dump is from **September 2017**.

Everything else in the category leaves a gap:

| Tool | Status | Gap it leaves |
| --- | --- | --- |
| **Etymonline** | Alive, de-facto standard | **Zero visualisation** — pure prose. Copyrighted, no bulk download. Cannot ask "show me all English words from this root." |
| **Etymology Explorer** | Alive, mobile-only | Closed source, no web version, no bulk data, **no aggregate/statistical views** |
| **Etymap** (`github.com/zifeo/Etymap`) | Actively touched (2026-07) | Closest sibling — **Flask + D3**, chord/alluvial. But `localhost` only, no public instance; shows *language-to-language* flows, not per-word fan-out |
| **ety-python** | Alive, 154★ | CLI only, ASCII trees, **ancestors only — no descendant fan-out** |
| **Academia Prisca** | Alive | Searchable text dump of Pokorny 1959; no graph, no modern-English linkage |
| **proto-indo-european.org** | **HTTP 530, unreachable** | Could not confirm it works |

**Adjacent precedent worth stealing from:** **CLICS** (`clics.clld.org`) — a
colexification database rendered as a force-directed graph with community
detection. Best-in-class interaction model, applied to a different relation.

**The synthesised gap:** nobody offers a free, working, web-based tool that
(a) visualises root fan-out and (b) treats **same-language doublets as a
first-class object**. The existing cognate tools are all *cross-language*
learner aids. And every existing tool is strictly **per-word lookup** — none
has aggregate views over the whole corpus. Notably, a search for an etymology
equivalent of *Six Degrees of Wikipedia* found **nothing**; that idea appears
genuinely unbuilt.

### 9.2 Independent data confirmations

Checked against the Wiktionary API by that pass:

| Data | Finding |
| --- | --- |
| PIE root → English | **990** categories `English terms derived from the PIE root *X`, **47,729** English entries; median **7** words/root; **323 roots have ≥20** |
| `Category:English doublets` | **8,486 pages** (API `categoryinfo.size`), plus 755 "piecewise doublets" |
| `Appendix:English doublets` | Hand-grouped by source language/process — e.g. *caput / chief / chef / cape / jefe / capo / kaput* |
| Branch-structured descendants | Confirmed on `Reconstruction:PIE/h₂eḱs-` — the axis/axle/aisle root — 43 derived terms grouped by branch |
| First-attestation dates | **The weak one.** No free structured dataset. OED paywalled; Etymonline copyrighted; "EtymoLink" (2024) dataset URL unverifiable |

**Important caveat that pass raised:** raw per-root English counts are
**inflated by productive suffixes** — the top-ranked root's thousands of hits
are largely `-ly` adverbs. A leaderboard needs lemma filtering to be honest,
and **ranking by *breadth* (number of distinct branches reached) is both more
interesting and more defensible** than raw count. This corroborates §3.6, where
UT's counts are naturally lemma-ish and top out at a credible 150.

---

## 10. Feature ideas

Ordered by payoff against confirmed-existing data.

### 10.1 Tier 1 — highest payoff

**Root sunburst / radial fan-out.** Root at centre, ring 2 = daughter branches,
outer ring = modern words, English highlighted. *Difficulty: medium.* This is
the owner's stated fascination rendered as a single image.

**Doublet discovery with a SURPRISE SCORE.** The key insight from that pass:
don't just list relatives — **rank them**. Score ≈ `orthographic distance ×
semantic distance × frequency`, so *axis/aisle* scores high while *act/action*
scores near zero. **The ranking is the feature** — every existing tool dumps
unranked lists, which is why nobody notices the good pairs. *Difficulty:
easy-medium* (edit distance is stdlib; frequency via `wordfreq`). This pairs
exactly with §5's derivative problem: a surprise score solves by *ranking* what
the 4-letter-stem heuristic tries to solve by *filtering*, and is strictly
better.

**Root leaderboard.** §3.6 is already computed. Ship the lemma filter and a
breadth ranking. *Difficulty: easy.*

**Six degrees of etymology.** Two words in, shortest path out, each hop labelled
by relation type. *Difficulty: medium* — the real work is graph hygiene:
prevent paths routing through junk hub nodes (bare affixes) or everything
connects in 3 hops. **Verified as unbuilt; this is the shareable hook.**

### 10.2 Tier 2

**Paragraph analyser upgraded to root level.** Colour by *shared root* instead
of origin bucket — words in the pasted text that secretly share an ancestor get
the same colour and a connecting arc: *"3 hidden relative pairs in this text."*
*Difficulty: easy* — reuses the existing analyser plus the root index.
**Arguably the highest-leverage idea in the list:** it turns the app's existing
front door into a discovery engine, and it satisfies the standing "fixes
propagate to every feature" rule by making the analyser and root data share one
index.

**Doublet quiz.** True pairs from the 8,486, distractors from **false friends** —
pairs that look related but aren't (*island*/*isle* are genuinely unrelated;
*outrage* is not out+rage). *Difficulty: easy-medium.*

**Cognate map.** Glottolog lat/lon (verified downloadable) or IE-CoR's own
coordinates. Bake a simplified world TopoJSON into the repo — no tile server,
preserving the no-CDN constraint. *Difficulty: medium.*

**Reflex comparison table with sound laws.** Hover an English word, see *why* it
looks that way (Grimm's Law: PIE *p → Germanic f, hence *father/paternal*,
*foot/pedal*, *heart/cardiac*). **Sound-law annotations do not exist in
usable machine-readable form** — hand-encode the dozen major laws. *Difficulty:
hard rigorously, medium scoped to Grimm's Law only.* **Refined by §13.5:** a
draft TOML layer *does* exist (2,934 IE rules), but it silently drops Grimm's
and Verner's Laws in parsing and is tagged `unchecked` throughout — so it is a
source-pointer, not an importable dataset, and the advice stands.

### 10.3 Tier 3 — novel

**"The same word twice" — borrowing round-trips.** Sankey view of one source
diverging through intermediate languages and reconverging on modern English:
*chief* (Old French) / *chef* (Modern French) / *caput* (Latin, direct) — same
source, three routes, three meanings. **`borrowed_from` vs `inherited_from` vs
`learned_borrowing_from` are distinct relation types in etymology-db** — the
single most underused field available, and precisely what distinguishes the
routes. This explains the *mechanism* behind doublets, which is the half of the
definition every other tool ignores. *Difficulty: medium.*

**Orphans and only children.** The inverse leaderboard: English words with **no
known relatives** — *dog*, *bird*, *girl*, *boy* are famous etymological
mysteries. Exists as the *absence* of edges. *Difficulty: easy.* Perfect foil:
if the thrill is that everything connects, the words that don't are equally
striking. **Nobody has built this.**

**Root density fingerprint.** Paste a document, get its dominant roots and
Germanic-vs-Latinate ratio; compare two texts. *Difficulty: easy-medium.*

**Root of the day.** Precomputed, cheap, gives a reason to revisit.

**Semantic drift trails.** *bʰeh₂-* "shine" → beacon, banner, phantom,
phenomenon, fantasy. **Drift quantification does not exist** — embedding
distance between glosses is a defensible heuristic but not scholarship; label
it as such. *Difficulty: medium-hard.*

**Doublet timeline — DEFER, but see §13.6.** Weakest data of any feature here;
no free structured attestation dataset exists. **Updated by later research:**
the Historical Thesaurus of English has exactly this data and offers a
**no-cost research licence on application** — that is the real path. Meanwhile
a Google Ngrams frequency-over-time curve is a defensible substitute, provided
it is never labelled "first attested."

---

## 11. Visualisation approach

The no-CDN, server-rendered constraint is **an advantage, not a limitation** —
every good layout here is pure maths that Python can compute and emit as inline
SVG. D3 is a layout engine plus a DOM binder; only the former is needed.

| Technique | Best for | Server-render feasibility |
| --- | --- | --- |
| **Sunburst** | Fan-out *with magnitude* — wedge angle ∝ descendant count | **Excellent** — recursive division of 360° |
| **Radial dendrogram** | One root → all descendants; depth = time-depth | **Excellent** — Reingold–Tilford in polar coords, ~40 lines |
| **Arc diagram** | **Doublets within a linear text** (§10.2 analyser) | **Excellent and underrated** — ~20 lines |
| **Sankey** | Borrowing routes (§10.3) | Good — ~80 lines; skip crossing minimisation at small N |
| **Force-directed** | Exploratory browsing, six-degrees paths | **Poor server-side** — precompute coordinates offline, or ~50 lines of inline vanilla JS |
| **Chord** | Language-to-language volume | Lower value — it's about languages, not words |

Guidance from that pass:

1. **Default to server-rendered inline SVG.** Works with JS off, printable,
   zero-dependency. Put layout maths in a `viz/` module with a shared
   `layout(tree) -> list[Shape]` interface so all features share one renderer.
2. **Add interactivity with ~30 lines of vanilla JS**, not a framework.
3. **Prefer sunburst for the hero view** — it encodes magnitude in the shape
   itself, which is the emotional payload.
4. **Handle the fan-out scale problem.** Some roots have thousands of
   descendants and will not render. Cap at ~150 leaves, aggregate the rest into
   a clickable "+N more", and rank the shown leaves by surprise score.
   **Ranking what to show matters as much as the layout.**
5. **Skip Graphviz/matplotlib** — no control over radial aesthetics, binary
   dependency, raster output.

**Highest-leverage next step identified:** the `root -> [descendants]` index
powers the sunburst, the leaderboard, the paragraph analyser upgrade, and
root-of-the-day. **Build that one shared artifact and four features fall out of
it.** It also aligns with §7's "one shared store" constraint.

---

## 12. Beyond Indo-European — other root systems

Same provenance caveat as §9: verified by a separate pass, not re-checked here.

**The strategic point:** PIE is not the only place this phenomenon happens.
Semitic triliteral roots are arguably a *cleaner* demonstration of "one root,
many words in one language" than PIE is, because the root is still visible in
the modern spelling. A second language family is the cheapest way to make the
app feel like it's about *language*, not just English.

### 12.1 Tier 1 — recommended

**Open Scriptures HebrewLexicon — the top non-IE pick.**
`github.com/openscriptures/HebrewLexicon` — **CC BY-4.0** (cleanest licence of
anything found), bulk XML download, ~8,600 entries. Crucially it ships an
explicit **root → derivatives graph**: `<etym type="main" root="…">child1,
child2…</etym>`. Verified example — root **אבד** "perish" fans out to
`ʾōbēd` "destruction", `ʾăbēdâ` "a lost thing", `ʾăbaddôn` **"Abaddon"** (the
Biblical proper noun), `ʾabdān`, `ʾobdan`. **Fan-out 4/5, doublets 5/5.** No NLP
needed — the links are pre-built.

**Wiktionary doublet categories — the highest-value-per-hour item.**
`Category:English doublets` = **8,486 pages**, confirmed via the MediaWiki API's
`categoryinfo.size`. And it is not English-only:

| Language | Pages | Language | Pages |
| --- | --- | --- | --- |
| English | **8,486** | Italian | 1,397 |
| Portuguese | 1,938 | French | 1,375 |
| Spanish | 1,843 | German | 809 |
| Russian | 620 | Dutch | 602 |
| Japanese | 239 | Latin | 216 |

~17,500 across ten languages, more exist. **CC BY-SA 4.0**, API access, no
scraping. **Caveat: the category is a flat list** — it says a word *is* a
doublet, not *of what*. Pair them by joining against `{{doublet|…}}` template
args or against etymology-db/wiktextract, both already on disk. **This is the
missing index that makes data you already hold usable for doublets** — and it
directly corroborates §2's finding that the current 2.9% doublet coverage is a
join problem, not a data problem.

**Austronesian Comparative Dictionary — `lexibank/acd`.**
**CC BY-4.0**, CLDF CSV, same schema as IE-CoR so one loader serves both.
146,733 lexemes / 1,063 varieties / **10,857 cognate sets** / 8,161 etyma.
**Hidden gem:** `cognates.csv` carries **`Doublet_Set` and `Doublet_Comment`
columns — 1,833 rows across 717 distinct doublet sets**. Non-IE doublets,
explicitly flagged, machine-readable. **Fan-out 5/5** — the largest open non-IE
fan-out dataset in existence. Its smaller sibling `lexibank/mcd` (Micronesian,
1,707 cognate sets, CC BY-4.0) comes free with the same loader.

### 12.2 Tier 2 — good, licence caveats

| Source | Data | Licence |
| --- | --- | --- |
| **Quranic Arabic Corpus** | **130,030 tokens, 1,651 roots**; ك-ت-ب → kataba, kātib, kitāb, kutub. Biggest families: قوم 84 forms, أتي 80 | **GPL** — copyleft on a dataset is awkward; a derived JSON store arguably inherits it |
| **Baxter-Sagart Old Chinese** | 4,959 rows; GSR column encodes **xiesheng phonetic series — 847 series with 2+ members**; largest is 方 *paŋ with 30 | **NONE STATED.** Official site returned **HTTP 403** (Cloudflare); verified only via third-party mirror. Treat as all-rights-reserved |
| **Sanskrit dhātu** (`ashtadhyayi-com/data`) | **2,259 dhātus** with gaṇa, meanings, upasarga combinations; भू "to be" has 11 prefix-derived senses | **NONE** — `LICENSE` returns 404 |
| **Uralonet** (Uralic, UEW digitized) | **1,876 etymologies**, server-rendered HTML, trivially scrapeable, no API | **NOT VERIFIED**; Rédei's UEW is still in copyright |
| **PILA** (`Mythologos/PILA`) | ~3,000 Proto-Italic↔Latin pairs, de Vaan-checked | **CC BY-SA 4.0** |

### 12.3 Avoid or deprioritise

- **BLR3 (Bantu)** — the download works (7.1 MB zip, HTTP 200 verified) but it
  is a **standalone Windows application from 2005**, not a data file.
  Extraction means reverse-engineering a legacy DB. Also: published assessments
  put only **~3–4.5%** of its 10,000 entries as confidently Proto-Bantu.
- **Proto-Algonquian Online Dictionary** — results are JS/POST-gated; a search
  URL returns 64 KB of interface chrome and zero data. Needs a headless browser.
- **MorphyNet** — 225,131 English rows, but it is **derivational, not
  etymological**: it gives "words built from X", not "words from one root by
  different routes." Supporting layer at best.
- **Turkic** — `lexibank/savelyevturkic` exists (CC BY-4.0) but is a
  Swadesh-style phylogenetics set with no Proto-Turkic reconstructions
  surfaced. **No good open Turkic etymological dataset was found.**

### 12.4 Nostratic / long-range — deliberate non-recommendation

No open downloadable Nostratic dataset exists beyond StarLing (already known).
**This is fine.** Nostratic reconstructions (Bomhard, Dolgopolsky,
Illich-Svitych) are **rejected by mainstream historical linguistics** — the
sound correspondences are not regular and the semantic latitude is wide enough
to generate false positives at will. If it's ever added for the "wow" factor it
must sit in a separate, visibly-labelled speculative tier, **never mixed with
PIE/Semitic/Austronesian data.** Milder version of the same caution applies to
Altaic.

### 12.5 Licence summary

- **Cleanly reusable (CC BY / CC BY-SA):** HebrewLexicon, ACD, MCD, PILA,
  savelyevturkic, IE-CoR, Wiktionary (share-alike — attribution required).
- **Copyleft-awkward:** Quranic Arabic Corpus (GPL).
- **No licence at all — local use only, do not redistribute:** Baxter-Sagart,
  ashtadhyayi dhātu, Uralonet, BLR3, **and UT Austin (§3)**.
- Nothing found is paywalled.

### 12.6 Suggested order of work

1. **Wiktionary doublet categories** — highest value per hour; upgrades data
   already on disk, and 8,486 English doublets dwarfs the current 13,270 rows
   in quality if not count.
2. **HebrewLexicon** — CC BY-4.0, pre-built tree, ~an afternoon, instant
   second-family showcase.
3. **`lexibank/acd`** — same CLDF loader as IE-CoR; brings 717 non-IE doublet
   sets and `mcd` for free.
4. **Quranic Arabic Corpus** — resolve the GPL question first.
5. Everything with an absent licence only after the owner decides how to handle
   that.

---

## 13. Why did they diverge — sound change, semantic shift, route

Same provenance caveat as §9. This pass verified counts by downloading and
parsing the actual files.

### 13.1 THE BEST RESULT IN THIS DOCUMENT — the axle/aisle divergence is explainable

The app can not only *state* that `axle` and `aisle` share a root, it can
**explain why they drifted**, with cross-linguistic evidence:

- **Wiktionary's own etymologies** (verified verbatim) give the routes:
  `axle` ← Middle English *axel* ← **Old English *eaxl* "shoulder, armpit"** ←
  PWGmc *ahslu ← PGmc *ahslō ← PIE *h₂eḱs-.
  `aisle` ← Middle English *ele* ← **Anglo-Norman *ele* "wing"** ← Latin *āla*.
- **DatSemShift independently attests those exact metaphors as recurrent
  cross-linguistic polysemies** — queried from its `parameters.csv`:

  | Shift | Evidence |
  | --- | --- |
  | ARMPIT → WING | Polysemy 2 [Indo-European ×2] |
  | SHOULDER → WING | Polysemy 3 [NW Caucasian ×2, Uralic] |
  | SHOULDER → UPPER ARM | Polysemy 6 [IE ×3, Tucanoan, Chocoan, Bora–Huitoto] |
  | WING → FIN | Polysemy 17, Derivation 1 [IE ×4, Austronesian ×8, Uralic ×3, Altaic ×2] |
  | WING → SPOKE OF WHEEL | Polysemy 1 [NE Caucasian] |
  | AXLE → SPINDLE | Polysemy 4 [Uralic ×4] |

  So: *axle* and *aisle* diverged because the same root ran through a
  **body-part metaphor that is typologically regular, not an English accident**
  — and you can cite four language families for it.

- Wiktionary even explains the *spelling*: the modern pronunciation was
  influenced by `isle`, and the spelling was then re-modelled after French
  *aile*. That is the "why does it look like that" detail no other tool shows.

This is the app's most distinctive potential page, and every input for it is
already downloadable.

### 13.2 etymology-db — richer than assumed, and already on disk

`github.com/droher/etymology-db`. **CC-BY-SA 3.0** (⚠️ ShareAlike, inherited
from Wiktionary). The full 143 MB file was downloaded and parsed:
**4,222,599 rows**, 30 relation types. Selected counts:

| Relation | Rows | Relation | Rows |
| --- | --- | --- | --- |
| `has_affix` | 819,183 | `inherited_from` | 330,737 |
| `etymologically_related_to` | 525,656 | `compound_of` | 306,170 |
| `cognate_of` | 372,160 | `borrowed_from` | 223,888 |
| **`doublet_with`** | **23,305** | `calque_of` | 9,914 |
| `learned_borrowing_from` | 6,728 | `unadapted_borrowing_from` | 1,884 |
| `semi_learned_borrowing_from` | 570 | `orthographic_borrowing_from` | 1,311 |

**`doublet_with` = 23,305 edges, 7,451 of them English** (then Portuguese 1,567,
Spanish 1,413, Indonesian 1,258, French 1,178, Italian 1,124). Verified English
pairs straight from the file: `thesaurus/treasure`, `word/verb`, `word/verve`,
`pond/pound`, `noun/name`, `brown/bruin`, `January/Gennaro`, `pie/pica`.

**The route data is pre-computed.** Verified rows:
```
English axle   inherited_from             Old English  eaxl
English axle   inherited_from             Proto-Germanic *ahslō
English axle   etymologically_related_to  PIE *h₂eḱs-
English axle   cognate_of                 Latin axis
English aisle  derived_from               Middle French aisle
English aisle  derived_from               Latin āla
English axis   borrowed_from              Latin axis
English ala    doublet_with               English aisle      ★
```
Five `inherited_from` hops for `axle` vs `derived_from` Latin/French for
`aisle` — **the route contrast that defines a doublet, already in the data.**
Note: release `2023-12`, so the data is ~2.5 years stale but regenerable.

### 13.3 DatSemShift — the semantic half

- **Live site:** `datsemshift.ru` — **10,546 shifts, 51,302 realizations, 2,428
  languages.** Publishes **no licence**; `/about`, `/terms`, `/word_histories`
  all 404.
- **Use the CLDF mirror instead:** `github.com/lexibank/datsemshift` —
  **CC-BY-4.0**, ~16 MB, 1,629 varieties / 4,185 concepts / 55,127 lexemes.
  `parameters.csv` is 6.3 MB; `Linked_Concepts` is embedded JSON carrying
  `Polysemy`/`Derivation` counts, contributing language families, and
  `Polysemy_Shifts` IDs that **deep-link straight to `datsemshift.ru/shift0134`.**
- Data model: a shift is an ordered meaning pair, manifested either as
  **polysemy** (both senses coexist) or **semantic evolution** (B replaces A).
  Each realization carries language, lexeme, direction, citation, and an
  ACCEPTED/NEW curation flag — genuinely scholarly, not crowd-sourced.
- **vs CLICS⁴** (`clics.clld.org`, CC-BY-4.0, 3,447 varieties / 1,730 concepts /
  1.45M lexemes): CLICS gives *synchronic* colexification — a link is
  *plausible*. DatSemShift gives *attested diachronic* shifts with direction and
  citation — it *actually happened*. **DatSemShift is the better fit;** CLICS is
  the statistical backdrop, and its 1,730 concepts are too basic-vocabulary-
  biased to reach AXIS/AISLE specificity.

### 13.4 Concepticon carries Buck — this is the join key to UT Austin

`concepticon/concepticon-data`, **CC-BY-4.0**. `concepticon.tsv` = **4,164
concept sets**, each tagged with a Buck-derived `SEMANTICFIELD`.

Critically, `conceptlists/Buck-1949-1110.tsv` (1,110 rows) **preserves Buck's
original hierarchical numbering mapped to Concepticon IDs**:
```
Buck-1949-1110-4    1.214    dust    2    DUST
```
**§3.1 notes UT Austin's semantic index uses Buck's 1949 scheme.** This file is
therefore the **join key between UT Austin and the entire CLDF ecosystem** —
DatSemShift, CLICS, IDS, IE-CoR. That link was not obvious and is probably the
most architecturally useful single finding in §§9–13.

(Buck's *prose* is still in copyright — U. Chicago Press. Only the headword list
and numbering are open.)

### 13.5 Sound change — usable scaffold, but DO NOT auto-import

`github.com/quilde/indexdiachronica` — machine-readable TOML, **CC BY-NC-SA
4.0** (⚠️ NonCommercial). `indo1319.toml` = 437 KB, **94 changesets, 2,934
sound changes**, including both doublet routes as explicit chains:
PIE→Latin→French, and PIE→Common Germanic→West Germanic→Anglo-Frisian→Old
English→Middle English→Early Modern English.

**⚠️ VERIFIED PARSE BUG — the single most important warning here.** For the
`PIE → Common Germanic` changeset, the raw source text contains Grimm's and
Verner's Laws verbatim, but **the 8 extracted structured blocks contain only
vowel changes — Grimm and Verner never made it into the machine-readable
array.** Every entry is also tagged `["generated","unchecked"]`. The Great
Vowel Shift changeset *did* parse cleanly (13 changes).

**Therefore: use it as a scaffold and source-pointer, hand-curate the ~10 laws
you actually display.** This *refines* rather than contradicts §10.2's claim
that sound laws don't exist in machine-readable form: a draft layer exists, but
it silently drops the most famous laws, so the practical advice is unchanged.

Engines, with licence traps: **Lexurgy** (GPL-3.0 — invoke as a CLI subprocess,
do not link into Flask; note the domain is `.com`, `.net` fails DNS),
**Zompist SCA2** (non-commercial), **LingPy** (GPL-3.0), **LingRex/CoPaR**
(**MIT — safest to embed**), **PyLexibank** (Apache-2.0). **CLTS** normalises
IPA (CC-BY-4.0 per the site, ⚠️ but no LICENSE file in the repo).

**Honest negative:** no ready-made "Latin p ~ Germanic f" correspondence table
exists anywhere. LingRex can *infer* patterns from aligned cognate sets, but for
a personal app, **hardcode the ~15 classic correspondences by hand.**

### 13.6 Chronology — one actionable lead

§9.2 called this the firmest negative. It softens slightly:

- **Historical Thesaurus of English** (`ht.ac.uk`) is exactly the right data —
  800k+ senses ordered by first documented occurrence, dates from the OED.
  Bulk download is **prohibited**, *but* Glasgow operates a **no-cost research
  licence** for projects needing substantial data:
  **`arts-thesauri@glasgow.ac.uk`. A personal etymology app is a plausible
  applicant — this is worth an email**, and it is the only real path to
  attestation dates.
- **Google Books Ngrams v3** (CC-BY 3.0, BigQuery-queryable) is the best open
  proxy. ⚠️ Only ngrams appearing >40 times are included, coverage is thin
  before ~1600, and it measures *first appearance in print*, systematically
  later than true attestation. **Ship it as a frequency-over-time curve per
  doublet — visually better than a single date — and never label it "first
  attested."**
- **EEBO-TCP** — 50,000 hand-keyed TEI XML texts on GitHub (the org's own
  website 404s), covering ~1470–1700, exactly the window Latinate doublets
  flooded in. A corpus, not a dictionary; you'd index it yourself.
- **Middle English Dictionary** — open access with dated quotations, but the
  headword file list is behind a Cloudflare JS challenge. **Email U-M Library
  rather than scraping.**
- **Etymonline — avoid ingesting.** Great dates, copyrighted, no bulk export.
  Link out; don't scrape.

### 13.7 Kaikki per-word fetch — no bulk download needed

`kaikki.org/dictionary/English/meaning/a/ai/aisle.jsonl` → **HTTP 200, 22 KB**.
So route rendering does not require the 23 GB dump. `etymology_templates` is
the structured gold — an *ordered* array that parses directly into a directed
path with glosses attached:
```json
{"name":"root","args":{"1":"en","2":"ine-pro","3":"*h₂eḱs-"}}
{"name":"inh","args":{"1":"en","2":"enm","3":"ele"}}
{"name":"der","args":{"1":"en","2":"xno","3":"ele","t":"wing"}}
{"name":"der","args":{"1":"en","2":"la","3":"āla"}}
```
`root`/`inh`/`der`/`cog` with ISO codes. Recommendation: **etymology-db for bulk
graph queries and precomputed `doublet_with`; Kaikki for fresh, gloss-rich
per-word route rendering.**

### 13.8 Licence traps introduced by this section

| Resource | Licence | Constraint |
| --- | --- | --- |
| DatSemShift CLDF, CLICS⁴, Concepticon, IDS | CC-BY-4.0 | Attribution only ✅ |
| Google Ngrams, WOLD | CC-BY 3.0 | Attribution only ✅ |
| LingRex (CoPaR) | MIT | Safest to embed ✅ |
| **etymology-db, Kaikki/Wiktionary** | **CC-BY-SA 3.0** | ⚠️ **ShareAlike — derived data must be SA** |
| **Index Diachronica TOML** | **CC BY-NC-SA 4.0** | ⚠️ **NonCommercial** |
| **Lexurgy, LingPy** | **GPL-3.0** | ⚠️ Viral — subprocess only |
| **Historical Thesaurus** | Proprietary | ⛔ Bulk download prohibited; free research licence on application |

**Net effect:** for a personal, non-commercial app that attributes and
ShareAlikes its derived data, everything here is usable. Monetising would
require dropping Index Diachronica and Zompist SCA.

### 13.9 Suggested build order for this section

1. **Ingest `etymology.parquet`** — already on disk at
   `Etymology Project/etymology.parquet`. Filtering to English gives 7,451
   doublet pairs and full route chains immediately.
2. **Add Kaikki per-word fetch** for gloss-rich live route rendering.
3. **Layer DatSemShift** keyed on Concepticon ID; when two doublets' senses map
   to linked concepts, show the shift and deep-link to `datsemshift.ru`.
4. **Hand-curate ~10 sound laws.** Do not auto-import (§13.5).
5. **Chronology last** — email Glasgow; ship Ngrams curves meanwhile.

**Architectural note that pass raised, consistent with §7:** steps 1–3 are the
same shape three times — download a file, key it on an ID, join. That shape
recurs for every future CLDF dataset. **One small `cldf_loader` (fetch → cache →
normalise → join on Concepticon/Glottolog ID) beats three bespoke ingest
scripts**, and CLICS, IDS, ACD (§12.1) and IE-CoR (§4) all drop straight into it.
