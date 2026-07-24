# Etymology Analyzer

Analyzes English text and reports what percentage of words come from each origin
language — readable two ways via a toggle:

- **proximate** — the language English took the word from directly (`skill` → Norse)
- **deepest** — the oldest traceable ancestor (`skill` → PIE)

## Quick start

```python
from analyzer import analyze, format_report

text = "They want to trust the skill of a husband who can take a knife."
print(format_report(analyze(text, mode="proximate")))
print(format_report(analyze(text, mode="deepest")))
```

## Architecture

Three layers, deliberately separated so the data source can change without
touching anything downstream.

| File | Role |
|---|---|
| `buckets.py` | ISO-code → origin bucket (for the `ety` backend) |
| `buckets_wikt.py` | Language-name → origin bucket (for the Wiktionary backend) |
| `resolver.py` | **The swap point.** Backends implement `resolve(word) -> Resolution` |
| `analyzer.py` | Tokenize → resolve → aggregate percentages |
| `convert_wikt.py` | Builds `wikt_words.json` from the etymology-db CSV |

### Resolver stack

`default_resolver()` returns `ChainResolver([WiktionaryResolver(), EtyResolver()])`.

- **WiktionaryResolver** (primary) — 71,630 English words from etymology-db
  (parsed Wiktionary). Correct proximate donors: `skill`→Norse, `table`→French.
- **EtyResolver** (fallback) — Etymological Wordnet, used only for words
  Wiktionary lacks.

Adding another data source means writing one class with a `resolve()` method and
putting it in the list. The analyzer and any UI stay unchanged.

### Reading modes

A `Resolution` holds the *whole* donor chain. `Resolution.view(mode)` renders it
as proximate or deepest, so one analysis pass can be re-rendered both ways
without re-resolving.

## Regenerating the data

```bash
python3 convert_wikt.py    # reads the etymology-db CSV -> wikt_words.json
```

## Coverage

On a sample paragraph: **81% of tokens classified** (up from ~44% with `ety`
alone). Distribution across the full 71,630-word database:

```
Germanic 16021   French 13808   Latin 10862   Romance 6620
Greek 3756   Slavic 2846   East Asian 2667   Semitic 2155
Indo-Iranian 1953   Norse 1671   Celtic 1657   ... 
```

## Known issues

1. **Pass-through donors.** Words that entered English via French (`sugar`,
   `algebra`, `orange`, `coffee`) bucket as French/Germanic under proximate
   mode. Historically accurate, but hides the more interesting deeper origin.
   ~1,192 words show this pattern. Design decision still open.
2. **Chain ordering is approximate.** `DEPTH_RANK` in `convert_wikt.py` is a
   coarse historical ranking, so some chains list ancestors out of true
   chronological order (`candy`, `zero`, `sandal`).
3. **`Other` bucket leakage.** Languages not yet mapped in `buckets_wikt.py`
   appear as `Other` mid-chain. Adding them to `NAME_TO_BUCKET` fixes it.
4. **Coverage is not total.** 71,630 words is what Wiktionary has explicit
   etymology templates for; rarer words remain unresolved.
