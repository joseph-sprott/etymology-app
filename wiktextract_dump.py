"""
Reading the wiktextract dump: one loop, in one place.

Three build scripts had each hand-rolled the same nine lines --
`build_inflections.py`, `convert_wiktextract.py` and
`scripts/wiktextract_coverage_check.py` -- open the file, enumerate, strip,
skip blanks, `json.loads` inside a `try`, drop non-English entries, require a
headword. Identical every time, and none of them tested, because testing any
of them meant handing it a 3.2GB file.

Extracted in the 2026-07-27 cleanup (audit item P4). This module is I/O ONLY:
it decides nothing about etymology, so callers keep their own logic and simply
stop restating the read.

    for line_no, entry, word in stream_english_entries(path):
        ...

WHY `line_no` IS THE TRUE FILE LINE, not a count of yielded entries: every
caller used it for error messages and progress logging against the real file,
so skipped blanks and malformed lines still advance it. A number that didn't
match the file would be worse than no number.

WHY A MALFORMED LINE IS SKIPPED RATHER THAN RAISED: the dump is a 1.4-million
line third-party artifact and a single bad line should not lose a ten-minute
build. All three original loops made that same call independently.
"""
import json
from typing import Iterator, Optional, Tuple

# The dump carries every language; everything downstream of here is about
# English. Kept as a constant so a caller that wants another language has an
# obvious place to look rather than a string buried in a comparison.
ENGLISH = "English"


def stream_english_entries(
    path: str, limit: Optional[int] = None
) -> Iterator[Tuple[int, dict, str]]:
    """
    Yield `(line_no, entry, word)` for each usable English entry in the dump.

    Skipped, silently and by design: blank lines, lines that are not valid
    JSON, entries for other languages, and entries with no headword. `limit`
    stops after that many YIELDED entries -- lines read is always larger --
    which is what makes a partial sanity run meaningful.
    """
    if limit is not None and limit <= 0:
        return
    yielded = 0
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("lang") != ENGLISH:
                continue
            word = entry.get("word")
            if not word:
                continue
            yield line_no, entry, word
            yielded += 1
            if limit is not None and yielded >= limit:
                return
