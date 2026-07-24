# Etymology Analyzer

Analyzes English text and reports what percentage of words come from each origin
language — readable **three ways** via a toggle:

- **Direct Source** — the language English took the word from directly
  (`skill` → Norse, `table` → French)
- **Notable Influence** — the most distinctive language the word passed
  through along the way (`coffee` → Turkic, the Ottoman Turkish leg that
  both Direct Source [Germanic/Dutch] and Deepest Root [Semitic/Arabic] skip
  past)
- **Deepest Root** — the oldest traceable ancestor, naming the specific
  reconstructed/attested form where the data supports it
  (`skill` → Proto-Indo-European, `sky` → Proto-Germanic (from PIE))

Plus a separate per-word **etymology tree** view showing every recorded
branch, not just the one answer the percentage breakdown needs.

## Quick start

```python
from analyzer import analyze, format_report

text = "They want to trust the skill of a husband who can take a knife."
print(format_report(analyze(text, mode="direct")))
print(format_report(analyze(text, mode="influence")))
print(format_report(analyze(text, mode="root")))
```

Or run the local test UI:

```bash
python app.py    # then open http://localhost:5000
```

## Architecture

Layers deliberately separated so the data source can change without touching
anything downstream.

| File | Role |
|---|---|
| `analyzer.py` | Tokenize text → resolve each word → aggregate percentages |
| `resolver.py` | **The swap point.** Backends implement `resolve(word) -> Resolution`; `Resolution.view(mode)` renders `"direct"`/`"influence"`/`"root"` from one pass |
| `buckets_wikt.py` | Language-name → origin bucket (Wiktionary backend) |
| `buckets.py` | ISO-code → origin bucket (legacy `ety` fallback backend) |
| `convert_wikt.py` | Rebuilds `wikt_words.json` from etymology-db's raw relation table (`etymology.parquet`) |
| `corrections.py` | Manual overrides for confirmed bad entries, applied by `WiktionaryResolver` at load time |
| `compounds.py` | Word→(part, part) allowlist for words that resolve to Unknown on their own but are verified compounds |
| `build_etymology_trees.py` | Builds `etymology_trees.json` — a per-word nested tree (every branch preserved) for the etymology-tree UI |
| `tree_corrections.py` | Manual overrides for the etymology-tree feature |
| `fetch_reconstructions.py` | One-off enrichment pass against live Wiktionary's Reconstruction namespace to close the proto-language coverage gap |
| `app.py` | Local Flask test UI (`localhost:5000`) — paragraph analyzer plus single-word etymology-tree lookup |

### Resolver stack

`default_resolver()` returns `ChainResolver([WiktionaryResolver(), EtyResolver()])`.

- **WiktionaryResolver** (primary) — ~72,700 English words from etymology-db
  (parsed Wiktionary). Correct proximate donors: `skill`→Norse, `table`→French.
- **EtyResolver** (fallback) — Etymological Wordnet, used only for words
  Wiktionary lacks.

Adding another data source means writing one class with a `resolve()` method and
putting it in the list. The analyzer and any UI stay unchanged.

### Reading modes

A `Resolution` holds the *whole* donor chain. `Resolution.view(mode)` renders it
as `"direct"`, `"influence"`, or `"root"`, so one analysis pass can be
re-rendered all three ways without re-resolving.

## Regenerating the data

```bash
python3 convert_wikt.py    # reads etymology.parquet -> wikt_words.json
python3 build_etymology_trees.py    # reads etymology.parquet -> etymology_trees.json
```

Both read a local `etymology.parquet` (not included in this repo — ~140MB,
sourced from [etymology-db](https://github.com/droher/etymology-db)) rather
than anything fetched at runtime.

## Coverage

On a sample paragraph: **~98% of tokens classified** (up from ~44% with `ety`
alone). ~72,700-word database.

## Known issues

The full, actively-maintained list of known issues and design decisions
(including the one currently open — what to do with ~1,245 words that have
no recorded ancestry beyond a coincidental PIE root citation) lives in
`CLAUDE.md`, not duplicated here to avoid the two drifting apart.
