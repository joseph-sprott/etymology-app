"""
Side notes about a word -- never an origin, always an aside.

Joe, 2026-07-30, on the Shakespeare feature: "I dont want it to be in the
language bucket or whatever, just something on the side." Every note here
obeys that. A `Note` has no bucket and no share, so nothing in this module can
move a percentage; a test asserts it.

FOUR KINDS, all from data already on disk -- no new download, no rebuild:

    coinage    attributed to a named person   (shakespeare_words.json)
    calque     a translated borrowing         (2,437 `calque` edges)
    formation  what the word was built from   (673,240 `formed_from` edges)
    era        when the donor language was spoken (curated `language` rows)

ONE MODULE, NOT FOUR FEATURES. A note is a note. Adding a fifth kind should be
one collector function, not another template block plus another CSS rule plus
another route variable -- which is how the request handler ended up
initialising eleven locals before the 2026-07-31 audit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import coinages
import shakespeare

# What a calque IS, in Joe's own words. Shown in full because the term is
# jargon and a reader who does not know it should still understand the note.
CALQUE_EXPLAINER = (
    "A calque happens when one language borrows an idea from another but "
    "translates it literally, word-for-word, using its own vocabulary. "
    "Instead of adopting the foreign word's sound, it steals the foreign "
    "word's blueprint."
)


@dataclass(frozen=True)
class Note:
    """One aside about a word. Deliberately carries no bucket and no share."""
    kind: str
    icon: str
    text: str
    detail: Optional[str] = None


def _entry(word: str):
    """The word's database entry, or None if the database is unavailable."""
    try:
        import etymology_db

        return etymology_db.get().entry(word)
    except Exception:
        # An annotation is never worth taking the page down for.
        return None


def _coinage_note(word: str, entry) -> Optional[Note]:
    """
    Attributed to a named person.

    Shakespeare is checked FIRST and keeps the softer wording. His list rests
    on the OED naming him the earliest known source, which is a claim about
    documentation rather than invention -- Victorian editors read him far
    harder than his contemporaries. Wiktionary's `coined by` categories are an
    explicit human attribution, so those get the stronger verb.
    """
    if shakespeare.is_shakespearean(word):
        return Note(kind="coinage", icon="&#127917;",
                    text="popularized by Shakespeare",
                    detail=shakespeare.note(word))
    who = coinages.coiner(word)
    if not who:
        return None
    return Note(kind="coinage", icon="&#127917;", text=f"coined by {who}")


def _calque_note(word: str, entry) -> Optional[Note]:
    """
    A translated borrowing: the blueprint crossed over, not the sound.

    These edges are deliberately excluded from ancestry -- a calque transmits
    no material, which is what issue #22 (calques counted as ancestry) fixed.
    That exclusion is exactly what makes them a good ASIDE: real, recorded,
    interesting, and not part of the answer.
    """
    if entry is None or entry.primary is None:
        return None
    source = next((n for n in entry.primary.head.children
                   if n.rel == "calque" and n.lang), None)
    if source is None:
        return None
    term = f" {source.term}" if source.term else ""
    return Note(kind="calque", icon="&#128196;",
                text=f"a word-for-word translation of {source.lang}{term}",
                detail=CALQUE_EXPLAINER)


def _formation_note(word: str, entry) -> Optional[Note]:
    """What the word was built from, when the source records components."""
    if entry is None or entry.primary is None:
        return None
    parts = [n.term for n in entry.primary.head.children
             if n.rel == "formed_from" and n.term]
    if len(parts) < 2:
        return None
    return Note(kind="formation", icon="&#129513;",
                text="built from " + " + ".join(parts))


def _era_note(word: str, entry) -> Optional[Note]:
    """When the donor language was spoken, from the curated era table."""
    if entry is None:
        return None
    donor = _first_donor(entry)
    if donor is None:
        return None
    label = _era_label(donor)
    if not label:
        return None
    return Note(kind="era", icon="&#8987;",
                text=f"English took this from {donor}, spoken {label}")


def _first_donor(entry) -> Optional[str]:
    """The first foreign language in the word's lineage, or None."""
    try:
        import etymology_db

        line = etymology_db.get().lineage(entry)
    except Exception:
        return None
    for node in line[1:]:
        if node.lang not in etymology_db.ENGLISH_STAGES and node.rel != "root":
            return node.lang
    return None


def _era_label(language: str) -> Optional[str]:
    """The curated era label for a language, e.g. "c. 1150-1500"."""
    try:
        import etymology_db

        row = etymology_db.get()._db.execute(
            "SELECT era_label FROM language WHERE name=? AND era_certain=1",
            (language,)).fetchone()
    except Exception:
        return None
    return row[0] if row and row[0] else None


#: Order matters only for display: most surprising first.
_COLLECTORS: List[Callable] = [
    _coinage_note, _calque_note, _formation_note, _era_note,
]


def for_word(word: Optional[str]) -> List[Note]:
    """Every side note that applies to this word, in display order."""
    if not word or not word.strip():
        return []
    word = word.strip()
    entry = _entry(word)
    notes = [collect(word, entry) for collect in _COLLECTORS]
    return [note for note in notes if note is not None]
