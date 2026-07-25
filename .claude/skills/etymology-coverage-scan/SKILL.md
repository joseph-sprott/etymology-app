---
name: etymology-coverage-scan
description: This skill should be used when the user wants to broadly audit the Etymology Analyzer's word coverage (e.g. "scan for words that don't resolve", "how many common words are we missing", "test coverage against a bunch of real text", "check if the fix actually improved coverage"), as opposed to investigating one specific reported word (use etymology-fix-word for that instead).
---

# Auditing database coverage against a real text corpus

Finding SYSTEMATIC coverage gaps (as opposed to one reported word) means
running a large, real corpus through the analyzer and looking for patterns
in what comes back Unknown -- not guessing which categories of words might
be missing.

## 1. Get a real text corpus

Prefer a genuinely diverse, real corpus over anything generated on the fly --
diversity of vocabulary is what surfaces gaps. `randomwordgenerator.com`'s
paragraph generator is JavaScript-driven (no text in the static HTML,
confirmed 2026-07-24), but its underlying data is a fetchable static file:
`https://randomwordgenerator.com/json/paragraphs.json` -- `{"data": [{"paragraph": "..."}, ...]}`,
347 real hand-written paragraphs as of 2026-07-24. Fetching this ONE file
directly (`Invoke-WebRequest -OutFile`) gets the exact raw text, verbatim --
do not use WebFetch for this if verbatim text matters, since WebFetch summarizes
content through a small model rather than returning it unmodified.

For a fresh scan, any similarly diverse real-English corpus works the same
way -- the scan script doesn't care about the source, only the shape
(JSON `{"data":[{"field":"text"}]}` or plain text with blank-line-separated
paragraphs).

## 2. Run the scan

```
python scripts\scan_unknown_words.py --corpus PATH_TO_CORPUS.json --out report.json
```

Runs every paragraph through the exact same tokenizer/resolver the real app
uses, collects every word landing in the Unknown bucket, and separates them
into two groups using a capitalization heuristic (a word capitalized
somewhere that ISN'T the start of a sentence is flagged as a likely proper
noun). This is a HINT, not a filter -- see step 3.

## 3. Review the "likely proper noun" list by hand before excluding it

The capitalization heuristic has real blind spots -- confirmed 2026-07-24,
don't skip this: demonyms/nationality adjectives (e.g. "Egyptian") get
flagged as likely-proper-noun since they're always capitalized, but they
ARE real words with real donor-language etymology, not names to exclude.
Only exclude entries that are genuinely personal names, brand names, or
place names on inspection -- not everything the heuristic flagged.

## 4. Diagnose the real gaps

For each word worth investigating from the "not flagged as proper noun"
list, use the SAME diagnostic tools as the `etymology-fix-word` skill
(`scripts\check_word.py`, `scripts\check_raw_data.py`) -- don't re-derive
this logic here, it's already built and this skill assumes it. Categorize
each finding rather than fixing one at a time; patterns found 2026-07-24
worth checking for specifically:
- Missing irregular verb/noun forms (`_IRREGULAR_FORMS` in `resolver.py` is
  NOT exhaustive -- covers ~100 of English's ~200 irregular verbs).
- Irregular plurals with a consonant alternation the stemmer doesn't handle
  (wolf/wolves, knife/knives, shelf/shelves -- the f/v shift).
- Words whose raw data is ONLY `etymologically_related_to`/`cognate_of`/
  `doublet_with` (hedge relations, not real asserted ancestry) -- this is
  the same shape as known issue #14's still-open residual, not a new bug
  category each time it's found.
- Words genuinely absent from the raw parquet snapshot entirely, even when
  common (see `previous`, known issue #15/#16's write-ups) -- contradicts
  the earlier assumption that gaps are mostly rare words.
- Missing compounds not yet in `compounds.py` or auto-detected.

## Additional resources

- `scripts/scan_unknown_words.py` -- step 2.
- `scripts/check_word.py` / `scripts/check_raw_data.py` (shared with
  `etymology-fix-word`) -- step 4.
