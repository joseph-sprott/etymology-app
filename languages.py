"""
Language reference data: era ranges, family, bucket, and code/name aliases.

Loads languages.csv (~110 hand-curated rows). Bounded by the number of
LANGUAGES, not by vocabulary size -- unlike the 189-entry irregular-verb
table deleted 2026-07-25, this does not grow as the dictionary grows. Top 50
rows cover 95.5% of every chain step in the database; top 100 cover 98.4%.

WHY ERA DATA EXISTS (2026-07-25): two jobs, one table.
  1. ORDERING. `era_start` is the depth ordering. A step whose language is
     YOUNGER than one already reached cannot be a continuation of descent --
     that's the monotonicity guard that stops `October`'s Latin-word
     decomposition being read as "Latin came from PIE and then back to
     Latin". This replaces convert_wikt.py's `_DEPTH_HINT`, which had no
     real dates and whose tiers were only comparable WITHIN one family (the
     bug that made `mile` credit Proto-West Germanic with PIE descent).
  2. LAYOUT. Rows on the timeline, and whether two nodes are contemporaries
     (dotted edge) or in a proven parent/child line (solid edge).

Deliberately NO separate `stage_rank` column: `era_start` already is the
rank. A second field encoding the same ordering is a second thing that can
disagree with the first.

DATE CONFIDENCE is explicit, not implied. `era_certain=0` marks a range that
is contested or estimated -- every proto-language, plus a few undated ones
(Proto-West Germanic has no date on Wikipedia at all; it is bracketed
between Proto-Germanic and Old English here and flagged). Renderers must
show "c." for these and must never imply precision the sources don't have.
Proto-Indo-European's own Wikipedia article says the dating is contested and
that other estimates run "more than a thousand years later" -- so a single
year for PIE would be a fiction.
"""
import csv
import os
from dataclasses import dataclass
from typing import Dict, Optional

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages.csv")

# Sentinel for "still spoken" -- keeps era_end an int everywhere so ordering
# comparisons never special-case None.
PRESENT = 9999


@dataclass(frozen=True)
class Language:
    name: str
    wikt_code: Optional[str]
    bucket: str
    family: Optional[str]
    era_start: int
    era_end: int
    era_label: str
    era_certain: bool
    is_proto: bool
    is_english_stage: bool
    source: str

    @property
    def is_living(self) -> bool:
        return self.era_end >= PRESENT


class LangIndex:
    """Name/code -> Language, plus the ordering helpers callers actually need."""

    def __init__(self, rows):
        self.by_name: Dict[str, Language] = {}
        self.by_code: Dict[str, Language] = {}
        for lang in rows:
            self.by_name[lang.name.lower()] = lang
            if lang.wikt_code:
                self.by_code[lang.wikt_code] = lang

    def get(self, name_or_code: str) -> Optional[Language]:
        if not name_or_code:
            return None
        return (self.by_code.get(name_or_code)
                or self.by_name.get(name_or_code.lower()))

    def era_start(self, name_or_code: str) -> Optional[int]:
        lang = self.get(name_or_code)
        return lang.era_start if lang else None

    def same_family(self, a: str, b: str) -> bool:
        la, lb = self.get(a), self.get(b)
        return bool(la and lb and la.family and la.family == lb.family)

    def contemporaries(self, a: str, b: str) -> bool:
        """Do these two languages' spoken periods overlap at all?

        Drives the dotted 'same era' edge. Deliberately a plain range
        overlap: any shared span counts, because two languages that coexisted
        for even a century could plausibly have interacted, and claiming
        otherwise would need evidence we don't have.
        """
        la, lb = self.get(a), self.get(b)
        if not (la and lb):
            return False
        return la.era_start <= lb.era_end and lb.era_start <= la.era_end

    def display_name(self, name_or_code: str) -> str:
        """
        Human-readable name for a language, curated or not.

        Only ~111 languages carry era data, but the dump cites over 1,500.
        Without this an uncurated node renders as the bare code -- the tree
        for a word borrowed from Hungarian showed a box labelled `hu`.
        Falling back to wiktextract's own code table fixes the LABEL without
        inventing era data: those rows still arrive with era_certain=0, so
        nothing downstream mistakes them for dated languages.
        """
        lang = self.get(name_or_code)
        if lang:
            return lang.name
        # Imported lazily: wiktextract_langs is a dump-derived lookup table,
        # and importing it at module load would make this reference data
        # depend on the extractor.
        from wiktextract_langs import name_for_wikt_code
        return name_for_wikt_code(name_or_code) or name_or_code

    def __len__(self) -> int:
        return len(self.by_name)

    def __contains__(self, name_or_code: str) -> bool:
        return self.get(name_or_code) is not None


_INDEX: Optional[LangIndex] = None


def load(path: str = _PATH) -> LangIndex:
    global _INDEX
    if _INDEX is None:
        rows = []
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if not r.get("name"):
                    continue
                rows.append(Language(
                    name=r["name"],
                    wikt_code=r["wikt_code"] or None,
                    bucket=r["bucket"],
                    family=r["family"] or None,
                    era_start=int(r["era_start"]),
                    era_end=int(r["era_end"]),
                    era_label=r["era_label"],
                    era_certain=r["era_certain"] == "1",
                    is_proto=r["is_proto"] == "1",
                    is_english_stage=r["is_english_stage"] == "1",
                    source=r["source"],
                ))
        _INDEX = LangIndex(rows)
    return _INDEX
