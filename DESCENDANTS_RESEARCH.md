# Descendants, and a re-audit of Cognates & Doublets

**Audience: other agents, and Joe.** Research and measurement only — **no code
was written and none should be from this document without Joe asking.**

Every number below was produced on **2026-07-26** by querying the real
`etymology.db`, scanning the real 3.2 GB wiktextract dump end to end, and
fetching the real kaikki.org/Wiktionary pages. Where something is an estimate,
it says so. This complements `ROOT_RELATIONS_RESEARCH.md` (2026-07-25); that
document's source survey still stands, and its numbers were re-verified here.

---

## 0. The headline, before the detail

Joe's hypothesis was that better cognate/doublet data (topics 1 and 2) would
improve the descendants feature (topic 3). **The measurement points the other
way.** Descendants data is the *superset*: a descendant tree IS a cognate set
(same root, different languages) and, where two branches re-enter English, IS a
doublet. Acquiring the data for topic 3 is the single action that most improves
all three. The reverse is not true — no cognate list will draw Joe's tree.

Three conclusions, each with its number:

1. **Cognates/doublets: we are near the ceiling of the source we have.** The
   English dump can yield at most ~14.5k words with cognates (5.2% of the
   dictionary); we already hold 11.6k. Better parsing buys a few thousand
   words. A step change requires new data, full stop.
2. **The rework quietly stranded both relations.** `etymology.db` contains
   **zero** cognate and **zero** doublet rows. They survive only in the legacy
   `word_info.json`. This is a live inconsistency with the "one database"
   rule, not a future concern.
3. **Root families are already sitting in our own data, unused** — 181,478
   candidate same-root pairs across 1,287 shared roots, derivable today with
   no download at all.

---

## 1. Topic 1 & 2 — Cognates and Doublets: audit

### 1.1 What we hold now

| Metric | Value |
| --- | --- |
| Words in `word_info.json` | 278,131 |
| …with any cognate | 11,602 (**4.2%**) |
| …with any doublet | 8,084 (**2.9%**) |
| Cognate rows / doublet rows | 46,454 / 13,270 |
| **Cognate rows in `etymology.db`** | **0** |
| **Doublet rows in `etymology.db`** | **0** |

`etymology.db`'s `word_relation` table holds ten relation kinds —
`derived_term` (478,619), `related` (94,475), `synonym`, `hyponym`, `antonym`,
`descendant` (17,916), `coordinate`, `meronym`, `hypernym`, `holonym` — and
neither `cognate` nor `doublet` is among them. The Word Search still shows both
because it reads `word_info.json` directly, i.e. the exact per-feature-store
split the rework was built to end. Whatever else is decided here, this is worth
closing.

### 1.2 The ceiling of the data we already have

Full end-to-end scan of the dump (1,481,704 entries):

| | Dump offers | We hold | Headroom |
| --- | --- | --- | --- |
| Words with a `cog` template | 14,548 | 11,602 | ~2,900 words |
| Distinct cognate pairs | 47,664 | 46,454 | marginal |
| Words with a `doublet` template | 8,453 | 8,084 | ~370 words |
| Distinct doublet pairs | 13,614 | 13,270 | marginal |

Top cognate languages in the dump: German 7,125, Dutch 6,323, French 3,972,
Old English 3,898, Swedish 3,883, Danish 3,180, Icelandic 2,969, Frisian 2,623.

**Reading:** extraction is not the bottleneck. Even a perfect parser tops out
near **5% of the dictionary**, because Wiktionary's `{{cog}}` is *pairwise* —
one template, one pair — and editors only write them where they feel relevant.
`father` has **zero** cognates in our data despite being the most cognate-rich
word imaginable, for exactly this reason.

So: is downloading external cognate data worth it? **Only if it is set-shaped.**
That is the property that matters, not volume.

### 1.3 The external options, re-checked

| Source | License | Size | English reach | Verdict |
| --- | --- | --- | --- | --- |
| **IE-CoR** (`lexibank/iecor` v1.2) | **CC-BY-4.0** | 6.4 MB | **169 words**, ~31 cognates each, expert-verified | Cheap, clean, tiny scope |
| **UT Austin IELEX / Pokorny** | **unstated** — ask `UTLRC@utexas.edu` before redistributing | ~104 requests, 5.4 MB each | 13,483 English reflexes, 1,336 etyma | Broad, licence risk |
| **kaikki all-languages dump** | same as current dump | **2.6 GB gz / 23.1 GB raw** | potentially every word with a proto-ancestor | Also solves topic 3 |
| CogNet | non-commercial only | — | 8.1M pairs | Licence blocks it |

IE-CoR at 6.4 MB and CC-BY is close to free to try — but 169 words is a demo,
not coverage. UT Austin is the broad option and carries a real licensing
caveat that needs Joe's decision before anything is redistributed.

**The efficient answer is the third row**, for the reason in §0: descendant
trees produce cognate sets as a by-product, and they're the same download that
makes topic 3 possible at all.

### 1.4 Free win already on disk: root families

Grouping every English word by the root form it cites, straight out of
`etymology.db`:

- English words citing a named root: **11,217**
- Distinct roots: **2,770**; roots shared by 2+ English words: **1,287**
- **Candidate same-root pairs: 181,478**

For comparison, `ROOT_RELATIONS_RESEARCH.md` credits UT Austin with 205,859
such pairs. **We can already compute 88% of that number from data on disk.**
Largest families: `*kap-` (194 words), `*keh₂p-` (183), `*per-` (149),
`*ḱley-` (129), `*h₃reǵ-` (127).

**The caveat from the earlier research applies unchanged and is the whole
game:** same-root is NOT doublet. `*kap-`'s 194 words include `acceptability`,
`acceptable`, `acceptably` — morphological derivatives of one word, not
separate arrivals into English. Presenting those as doublets would put false
claims on screen. "Root family" is the honest label for the wide set, and it is
genuinely new information the app doesn't surface today.

---

## 2. Topic 3 — Descendants

### 2.1 How Wiktionary actually stores it (verified)

The PIE root page `Reconstruction:Proto-Indo-European/bʰréh₂tēr` lists **11
top-level branches** — Anatolian, Armenian, Proto-Balto-Slavic, Proto-Celtic,
Proto-Germanic, Proto-Graeco-Phrygian, Proto-Indo-Iranian, Proto-Italic,
Illyrian, Mysian, Proto-Tocharian — each mostly one level deep, then
**"see there for further descendants."**

The full tree is therefore *distributed across pages*, exactly as Joe observed.
But the hop count is small, because each proto entry carries its whole subtree
nested: the Proto-Germanic `*brōþēr` entry already contains Proto-West Germanic
→ Old English → Middle English → English → Scots/Yola, plus Old Norse and
Gothic, in one entry. **Two levels of fetch reconstruct the whole diagram**:
the PIE root, then each branch's proto entry.

### 2.2 Is it machine-readable? Yes — verified on kaikki

- `bʰréh₂tēr` in Proto-Indo-European: structured descendants present,
  per-entry JSONL **5.3 kB**.
- `brōþēr` in Proto-Germanic: descendants include Proto-West Germanic (with its
  deep subtree), Old Norse, Gothic, Crimean Gothic — per-entry JSONL **11.8 kB**.

### 2.3 What our current data can and cannot do

`etymology.db` already has 17,916 `descendant` rows over 4,306 words, and the
dump scan found 4,547 entries with a descendants field, 20,529 rows total —
but the depth histogram is **18,276 at depth 0, 2,028 at depth 1, 190 at 2, 35
at 3**. Shallow, and pointing the wrong way: these are descendants *of English
words* into creoles and dialects (`brother` → `bredda`, `braddah`, `broda` —
23 rows), not the ancestral chain Joe drew.

**The English-only dump cannot build Joe's tree.** Every node above English
lives on a non-English page we do not have.

### 2.4 Acquisition options

| Option | Cost | Gets |
| --- | --- | --- |
| **All-languages raw dump** | 2.6 GB gz / **23.1 GB** raw, one download | Everything, offline, permanently |
| Per-language extracts | 23 languages only | Not enough — no Proto-Germanic, Old English, Middle English |
| Deprecated PIE extract | 11.5 MB | PIE only, and kaikki says it "will be removed" |
| Per-entry kaikki fetches | 5–12 kB each | Fine for a `brother` prototype; thousands of requests for real coverage |

**Recommended: the all-languages dump**, filtered on ingest to entries that
have a `descendants` field. Disk is the only real cost, and the existing
`build_etymology_db.py` already streams a 3.2 GB JSONL, so the machinery and
the ~10-minute build budget exist.

A `brother`-only prototype off two per-entry fetches (~17 kB total) would prove
the rendering before committing to the download. That is the cheap first step.

### 2.5 Size of the thing being drawn

Joe's pasted Germanic subtree is roughly 90 forms, and Germanic is one of 11
branches (and one of the larger ones). **Estimate: 500–1,000 nodes for a full
common-root tree** — basis: 11.8 kB of JSON for the Germanic subtree at ~60
bytes per descendant row. Treat as an estimate, not a measurement.

This is the number that decides the display, and it is why the MS Paint layout
won't survive contact with the real data: the drawing shows ~15 nodes.

---

## 3. Display — the one real design fork

Joe linked `d3js.org/d3-hierarchy/tree`. d3.tree is the Reingold–Tilford
"tidy" algorithm, linear time, `nodeSize`/`separation` configurable, with a
radial variant (`separation` divided by `a.depth`) and a `cluster` variant for
dendrograms. It is the right algorithm and it is what Wiktionary-style trees
use.

**But adopting it is an architectural first for this project.** `app.py` today
has *no JavaScript at all* — the diagram is server-computed SVG, the drill-down
is `<details>`, the hover cards are pure CSS. That was a deliberate, repeatedly
honoured choice. A 500–1,000 node tree genuinely needs pan, zoom and
collapse-by-default, which server-rendered SVG cannot provide.

The fork, stated plainly because it is Joe's call and not an implementation
detail:

- **(a) Adopt d3** (vendored locally, not from a CDN). Real interactivity —
  collapse/expand, zoom, radial toggle. Cost: the project's first JS
  dependency, and the no-JS property is gone for good.
- **(b) Stay server-rendered.** Implement Reingold–Tilford in Python — it is
  not a large algorithm — and render static SVG, with collapsing done by
  server round-trip (which the existing form-post UI already does naturally).
  Keeps the architecture; a 1,000-node static SVG is unwieldy but a
  *depth-limited* one (say, to Middle English, with "expand" links) is not.
- **(c) Split the difference:** server-rendered SVG for the default depth-3
  view, d3 only on a dedicated full-tree page.

A note that pushes toward keeping trees small regardless of choice: the
existing `build_diagram()` already does row = generation tier, column = branch,
which is most of what Joe drew. The gap is breadth, not layout.

---

## 4. What I would do, in order

1. **Close the stranded-relations gap** — cognates/doublets into `etymology.db`
   from the same dump the rest of it is built from. Small, and it restores the
   one-database rule the rework exists to enforce.
2. **Ship root families from data already on disk** — 181,478 pairs, zero
   download, clearly labelled "root family," never "doublet."
3. **Prototype `brother`** off two kaikki per-entry fetches, to settle the
   display fork against a real tree before any bulk download.
4. **Then** decide the all-languages dump on the strength of that prototype.
5. IE-CoR (6.4 MB, CC-BY) whenever high-confidence cognates for core vocabulary
   are wanted — it is cheap and clean, but it is 169 words and should not be
   mistaken for coverage.

**Open question for Joe, needed before step 3 finishes:** the display fork in
§3. Everything else above can proceed without a decision.
