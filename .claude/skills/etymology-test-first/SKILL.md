---
name: etymology-test-first
description: This skill should be used when adding or changing behaviour in the Etymology Analyzer -- a new feature, a bug fix, a refactor -- to work test-first (write the failing test, then the code). Also use when the user asks to "add tests", "raise coverage", or "write a test for X". Not for pure data regeneration (use etymology-regen) or verifying one word's etymology (use etymology-fix-word).
---

# Test-first, in this codebase

Joe's instruction, 2026-07-27: **write the test for what the outcome should be,
then write the code to fit it.** He said explicitly that he knows what TDD is
and suspects it wasn't happening. It wasn't.

This skill exists because the failure it prevents is subtle and already
happened here: on 2026-07-27 the audit wrote code first and tests after, and
**two of the first tests to fail were the TEST's fault, not the code's** — they
had been written by reading the implementation and guessing at intent, so they
asserted what the code did rather than what it should do. Written first, a test
is a statement of intent; written after, it is a photograph of whatever
happened to be there.

## The loop

1. **State the outcome as an assertion.** Put it in the right suite (below).
2. **Run it and watch it FAIL.** A test that passes before you write the code
   is testing nothing — either it's asserting existing behaviour, or it isn't
   reaching the code you think. Read the failure and check it fails for the
   reason you expect.
3. **Write the smallest code that satisfies it.**
4. **Re-run.** Then run `python scripts\verify.py` before moving on.

## When a test fails, decide WHICH is wrong

This is the step that gets skipped, and it is the whole value of the practice.
A red test means the test and the code disagree; it does not say which is
right. **Verify against a real source** — live Wiktionary, the raw database, or
this project's own documented contract in `CLAUDE.md` — before changing either.
Rule 2 applies here as much as anywhere: don't guess.

Three real outcomes from 2026-07-27, one of each kind:

- **The test was wrong (bad guess).** `can't` was asserted to expand to
  "cannot". It expands to "can not", deliberately — the generic `n't` rule
  would chop the single-n form to "ca" + "not". The test became a documented
  assertion of the real rule.
- **The test was wrong (right rule, wrong layer).** `key_for` was asserted to
  fold a trailing hyphen. It doesn't — the BUILD key keeps hyphens and the
  LOOKUP folds them. The failure sent me to read the contract properly.
- **The CODE was wrong.** `key_for("  *deru-  ")` returned `"*deru-"`: the
  docstring promises "no leading asterisk, no surrounding whitespace", but
  `lstrip("*").strip()` strips in the wrong order. Latent (no live key was
  affected), real, and found only because the test asserted the DOCUMENTED
  contract instead of the observed behaviour.

That last one is the argument for the whole practice: it was written twice,
wrong both times, and no amount of after-the-fact testing would have caught it,
because after-the-fact tests are written by reading the code.

## Which suite

| Suite | Answers | Cost | Use when |
|---|---|---|---|
| `test_units.py` | "does this function do what it says" | ~1s, no database | Almost always. Pure logic, parsers, predicates, presentation, Flask routes via `app.test_client()` |
| `test_regression.py` | "is this word's etymology still right" | minutes, full stack | The change affects a real word's ANSWER |
| `test_etymology_db.py` | "is the database structurally sound" | ~40s | Schema or build-time invariants |

Default to `test_units.py`. If a test needs the whole resolver stack to say
something about pure logic, that is usually the design telling you the logic
should take its dependency as an argument.

## Making a thing testable

`analyze()` accepts a `resolver` argument, so a stub returning known buckets
tests the ARITHMETIC — weight splitting, percentages, coverage — in
milliseconds without caring what `table` really means. That pattern is the
one to copy:

```python
class FakeResolver:
    def __init__(self, table): self.table = table
    def resolve(self, word):   return FakeResolution(self.table.get(word, ...))
```

If a new function can only be tested by loading 100MB of JSON, take the
dependency as a parameter instead. Both existing test files use plain
assertions and a `check(label, condition)` helper — there is no pytest in this
project and none is wanted.

## What a good assertion looks like here

Name the BUG or the RULE, not the mechanics. `test_units.py` and
`test_regression.py` both do this, and the labels are how a future reader
learns why the check exists:

```python
check("English band strictly above every foreign tier", english_max < foreign_min)
check("peacemaker: not the Koine Greek phrase it calques", d.bucket != "Greek")
check("a borrowing between CONTEMPORARIES stays one narrative (the knife bug)", ...)
```

Cover both directions whenever a fix has an over-reach risk: the thing that
must now happen, AND the thing that must still not happen. The calque fix
checks that `peacemaker` stops reading Greek and that `trust`/`free`/`brother`
still read Germanic — the second half is what proves the fix didn't overshoot.

## Coverage

One command. It prints TWO numbers on purpose:

```powershell
python .claude\skills\etymology-test-first\scripts\coverage_report.py          # every suite
python .claude\skills\etymology-test-first\scripts\coverage_report.py --fast   # units only, ~1s
python .claude\skills\etymology-test-first\scripts\coverage_report.py --quiet  # just the totals
```

```
  whole codebase : TOTAL   3017  1346  1256  99   52%
  runtime only   : TOTAL   1739   261   710  86   82%
```

Report the first, or both — never the second alone. The 30-point gap is the
build scripts, and omitting them is an omit-list, not an achievement. Joe reads
"coverage" as JUnit/JaCoCo-style line coverage; `--branch` is on because branch
coverage is closer to what he means and much harder to inflate.

The omit lists and suite order live in that script rather than in this prose
precisely so a number stays comparable to the last one.
