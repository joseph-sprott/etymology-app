r"""
Build `shakespeare_words.json` -- words attributed to Shakespeare.

    python build_shakespeare_words.py

WHY THIS IS A SIDE NOTE AND NOT A BUCKET (Joe, 2026-07-30): "I dont want it to
be in the language bucket or whatever, just something on the side that
basically says 'hey this word was popularized by shakespeare'." So nothing
here touches ancestry, percentages or buckets. It is an annotation.

WHAT "ATTRIBUTED" HONESTLY MEANS. The OED lists Shakespeare as the earliest
known source for roughly 1,700-2,000 words, and that is a claim about
DOCUMENTATION, not invention: Victorian OED readers combed Shakespeare far
more thoroughly than his contemporaries, so he is credited with first uses
that appear in other writers too, and many of these words were surely already
spoken before anyone wrote them down. The label therefore says "popularized
by", never "invented by" -- which is also how Joe framed it.

TWO SOURCES, both recorded per word so the weaker one can be dropped later:

  "wiktionary"  -- the word's OWN etymology in the wiktextract dump asserts
                   Shakespeare. Strongest evidence available offline, and the
                   only one tied to this project's existing data. Requires
                   assertive phrasing (see `asserts_shakespeare`), because 203
                   entries mention him and some mean something else entirely:
                   `bowdlerize` is named after the man who CENSORED him, and
                   `Shakespearean` is just built from his name.
  "curated"     -- published lists. Smaller and less rigorous than the OED's
                   full set, which is not freely enumerable:
                   https://nosweatshakespeare.com/resources/words-shakespeare-invented/
                   http://shakespeare-online.com/biography/wordsinvented.html
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import scriptlib  # noqa: E402  (path bootstrap must run first)

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "shakespeare_words.json")

# Phrasings that ATTRIBUTE the word to him. Deliberately narrow: a false
# "Shakespeare popularized this" on the page is worse than a missing one.
_ASSERTS = re.compile(
    r"(coined|invented|introduced|reintroduced|popularized|popularised|"
    r"first\s+(?:attested|used|recorded)|attested\s+first)"
    r"[^.]{0,60}?Shakespeare"
    r"|Shakespeare[^.]{0,40}?(coined|invented|first\s+(?:used|attested))"
    r"|(?:from|in)\s+[^.]{0,40}?by\s+(?:William\s+)?Shakespeare"
    r"|recorded\s+in[^.]{0,60}?Shakespeare",
    re.IGNORECASE)

# Phrasings that mention him WITHOUT attributing the word to him.
_REJECTS = re.compile(
    r"named\s+after[^.]{0,60}?Shakespeare"
    r"|version\s+of\s+(?:William\s+)?Shakespeare"
    r"|Shakespeare\s*\+|\+\s*Shakespeare",
    re.IGNORECASE)


def asserts_shakespeare(etymology_text: Optional[str]) -> bool:
    """Does this etymology CLAIM the word comes from Shakespeare?"""
    if not etymology_text or "Shakespeare" not in etymology_text:
        return False
    if _REJECTS.search(etymology_text):
        return False
    return bool(_ASSERTS.search(etymology_text))


def _sentence_about_him(text: str) -> str:
    """The one sentence naming him, for display on the hover card."""
    match = re.search(r"[^.]*Shakespeare[^.]*\.", text)
    return (match.group(0) if match else text[:200]).strip()


def from_dump(path: str) -> Dict[str, dict]:
    """Words whose own Wiktionary etymology attributes them to Shakespeare."""
    from wiktextract_dump import stream_english_entries

    found: Dict[str, dict] = {}
    for _line, entry, head in stream_english_entries(path):
        text = entry.get("etymology_text") or ""
        if head.lower() in found or not asserts_shakespeare(text):
            continue
        found[head.lower()] = {"source": "wiktionary",
                               "note": _sentence_about_him(text)}
    return found


def from_curated(words: List[str], existing: Dict[str, dict]) -> Dict[str, dict]:
    """Published-list words, added only where the dump had nothing."""
    added: Dict[str, dict] = {}
    for word in words:
        key = word.strip().lower()
        if not key or key in existing or key in added:
            continue
        added[key] = {"source": "curated", "note": None}
    return added


# Published lists, transcribed verbatim from the two URLs in the docstring.
CURATED = """
accommodation aerial amazement apostrophe assassination auspicious baseless
bloody bump castigate changeful clangor control countless courtship critic
critical dexterously dishearten dislocate dwindle eventful exposure fitful
frugal generous gloomy gnarled hurry impartial inauspicious indistinguishable
invulnerable lapse laughable lonely majestic misplaced monumental
multitudinous obscene palmy perusal pious premeditated radiance reliance road
sanctimonious seamy sportive submerge academe accused addiction advertising
arouse backing bandit bedroom beached besmirch birthplace blanket bloodstained
barefaced blushing bet buzzer caked cater champion circumstantial cold-blooded
compromise dauntless dawn deafening discontent drugged epileptic equivocal
elbow excitement eyeball fashionable fixture flawed gossip green-eyed gust
hint hobnob hurried impede jaded label lackluster lower luggage lustrous
madcap marketable mimic moonbeam mountaineer negotiate noiseless obsequiously
ode olympian outbreak pedant puking rant remorseless savagery scuffle secure
summit swagger torture tranquil undress unreal varied vaulting worthless zany
grovel
""".split()

# Multi-word entries, which the whitespace split above cannot carry.
# From Wiktionary's own CC BY-SA category "English terms coined by William
# Shakespeare" -- checked 2026-07-31, and this is the ONLY one of its 20
# members the dump scan did not already find. The rest of the open ecosystem
# (Wikipedia's ~120 attributed IDIOMS) is deliberately not imported: the
# analyzer tokenizes text into single words, so a phrase can never match a
# token, and the entries would be unreachable clutter.
CURATED_PHRASES = [
    "out-paramour the Turk",
]


def build() -> Dict[str, dict]:
    scriptlib.require_file(scriptlib.ENGLISH_DUMP,
                           "the kaikki English extract is needed for the "
                           "Wiktionary-sourced half")
    words = from_dump(scriptlib.ENGLISH_DUMP)
    words.update(from_curated(CURATED + CURATED_PHRASES, words))
    return words


def main() -> None:
    words = build()
    payload = {"built_from": ["wiktextract dump", "curated published lists"],
               "count": len(words), "words": words}
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
    by_source: Dict[str, int] = {}
    for value in words.values():
        by_source[value["source"]] = by_source.get(value["source"], 0) + 1
    print(f"{len(words):,} words -> {OUT_PATH}")
    for source, count in sorted(by_source.items()):
        print(f"  {count:5,}  {source}")


if __name__ == "__main__":
    main()
