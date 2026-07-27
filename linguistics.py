"""
Shared linguistic vocabulary: the questions this project asks about a language
name over and over, answered in exactly one place.

WHY THIS MODULE EXISTS (2026-07-27 audit)

Four separate modules had each grown their own answer to "is this an English
stage", three to "is this an affix", two to "is this a proto-language", and two
to "which of these two languages is deeper". They did not all agree, and
nothing made them agree -- each copy was written for one caller and drifted
from there. That is the same defect the single database layer was built to
end (known issue #16), reappearing one level down in plain constants.

The copies existed for a real reason, stated in `etymology_db.py`'s own
comment: importing the bucket layer would have created an import cycle. So the
fix is not "pick one of the existing homes" -- it is a module BELOW all of
them. This file imports nothing from this project, and nothing here needs to.
That is a structural guarantee against cycles, not a convention to remember.

RULE FOR FUTURE WORK: if you are about to write `lang.startswith("Proto-")`,
`term.startswith("-")`, or a set of English stage names anywhere else, import
it from here instead. A predicate that lives in two places is a bug with a
delay on it.
"""
from typing import Optional

# --------------------------------------------------------------- English

# The stages of English itself. A donor from one of these is not a foreign
# donor -- it is the same language further back, which is what "native core"
# means in the percentage bars.
ENGLISH_STAGE_NAMES = frozenset({"English", "Middle English", "Old English"})

# The same concept in ISO codes, for the legacy `ety` backend, which speaks
# codes rather than names.
ENGLISH_STAGE_ISO = frozenset({"ang", "enm", "eng"})

# And in wiktextract's own code system, which differs from ISO in two ways
# that matter: modern English is `en` (not `eng`), and SCOTS IS INCLUDED.
#
# That inclusion is a real, pre-existing inconsistency, preserved here rather
# than silently resolved: `convert_wiktextract.py` has always counted Scots as
# an English stage and `_DEPTH_HINT` has always put it in the English band,
# while `ENGLISH_STAGE_NAMES` above has always left it out. Scots is a sister
# language descended from Old English, not a stage of English, so the two
# readings are defensible for different purposes and picking one changes real
# answers. Unifying them is a judgement call for Joe, not a refactor -- it is
# recorded in the audit findings. Naming the sets differently at least makes
# the disagreement visible instead of accidental.
ENGLISH_STAGE_WIKT_CODES = frozenset({"en", "enm", "ang", "sco"})


def is_english_stage(name: Optional[str]) -> bool:
    """True for a stage of English itself, by NAME (not code)."""
    return name in ENGLISH_STAGE_NAMES


# ----------------------------------------------------------- proto forms

# Wiktionary's own naming convention: a reconstructed language is written
# "Proto-<family>". This is a spelling rule of the source data, not an
# inference about the language, which is why matching on the prefix is sound.
_PROTO_PREFIX = "Proto-"

# Both spellings reach this project: the full name from the dump, and the
# short bucket label from `buckets_wikt`.
_PIE_NAMES = frozenset({"Proto-Indo-European", "PIE"})


def is_pie(lang: Optional[str]) -> bool:
    """Proto-Indo-European, under either name this project uses for it."""
    return lang in _PIE_NAMES


def is_proto(lang: Optional[str]) -> bool:
    """
    Any reconstructed proto-language, PIE included.

    A proto-language is never a real DONOR -- no English word was borrowed
    from a reconstruction -- so this is the test that keeps them out of the
    Direct Source view while leaving them visible in Deepest Root, where
    naming the reconstructed form is the entire point.
    """
    return lang is not None and (lang.startswith(_PROTO_PREFIX) or is_pie(lang))


# --------------------------------------------------------------- affixes


def root_key(term: Optional[str]) -> str:
    """
    Normalise a reconstructed form into the key both sides of the root-gloss
    feature look it up by: no surrounding whitespace, no leading asterisk.

    ORDER MATTERS, and getting it wrong is why this is here. Both
    `build_root_glosses.key_for` and `word_trees.root_gloss` had independently
    written `term.lstrip("*").strip()`, which strips the asterisk BEFORE the
    whitespace -- so a form arriving as `"  *deru-  "` keeps its asterisk and
    produces a key nothing can ever match. No key in the current
    `root_glosses.json` is affected (the dump happens not to pad these
    arguments), so this was latent rather than live, but it was written twice
    and wrong twice, which is the failure mode this module exists to stop.

    Hyphens are deliberately KEPT. They are part of how a form is written, and
    `-frī` is a suffix, not a spelling variant of the root `*frī` -- folding
    them together captioned the root of `free` as "-free" (known issue #20).
    The lookup folds a TRAILING hyphen separately, as a fallback.
    """
    return (term or "").strip().lstrip("*").strip()


def is_affix(term: Optional[str]) -> bool:
    """
    Is this written as a bound morpheme -- `-ize`, `pre-`, `-graphy`?

    Wiktionary's own formatting convention, so this reads the source's marking
    rather than guessing at morphology. The length test keeps a bare "-" (and
    stray punctuation) from counting as an affix.

    NOTE the deliberate limit: this answers "is it WRITTEN as an affix", which
    is not the same as "is it a bound morpheme". The dump drops the hyphen
    inconsistently -- `beautiful` records its suffix as `ful`, with no hyphen
    at all -- so `DbResolver._is_bound_affix` layers a curated list on top of
    this for the component-splitting decision. That extra layer is genuinely a
    different question (see known issue #19); it is not a duplicate of this
    one, and should not be folded in here.
    """
    t = (term or "").strip()
    return len(t) > 1 and (t.startswith("-") or t.endswith("-"))


# ---------------------------------------------------------------- depth

# Relative age ordering, used to sort chain steps and tree branches
# shallowest-first. Moved here from `convert_wikt.py` in the 2026-07-27 audit:
# `app.py` was importing it from that module by its PRIVATE name, which meant
# the Flask app loaded a 694-line build script -- and pandas with it -- to
# order tree branches. Same table, same numbers, no behaviour change.
#
# THE LOAD-BEARING PROPERTY (learned by regression, do not "simplify" away):
# English-stage names occupy a reserved LOW band (0-1) and every foreign tier
# starts at +10. An English-stage-first branch must always sort shallower than
# ANY foreign-first branch, however many foreign sub-tiers exist. Flattening
# that gap let a stray `borrowed_from French` edge on `back` tie with, and
# then beat, the word's real native lineage -- see known issue #12.
#
# `languages.csv`'s `era_start` is a second, richer ordering over 111
# languages and is what `wiktextract_shapes.py` uses. It is NOT a drop-in
# replacement: it has no equivalent of the reserved English band above, so
# swapping it in reintroduces the `back` bug. Both are kept, deliberately,
# and the audit records this as the one duplication left standing on purpose.
DEPTH_HINT = {
    # English-stage band: ALWAYS shallower than any foreign entry below.
    "Middle English": 0, "English": 0, "Scots": 0,
    "Old English": 1,
    # Foreign bands start at +10, an unbridgeable gap from the English-stage
    # band above -- tier 10: modern/current stage of a foreign family.
    "French": 10, "German": 10, "Dutch": 10, "Irish": 10, "Modern Greek": 10,
    # Tier 11: "Middle"-period foreign stages.
    "Middle French": 11,
    "Middle High German": 11, "Middle Low German": 11, "Middle Dutch": 11,
    "Middle Irish": 11,
    "New Latin": 11,  # modern scientific/scholarly Latin -- shallow despite the name
    "Byzantine Greek": 11, "Medieval Greek": 11,
    # Tier 12: "Old"-period / earliest-attested foreign stages.
    "Old French": 12, "Anglo-Norman": 12, "Norman": 12, "Old Northern French": 12,
    "Old Norse": 12,
    "Old High German": 12, "Old Saxon": 12, "Old Dutch": 12, "Old Frisian": 12,
    "Old Irish": 12,
    "Medieval Latin": 12,
    # Tier 13: post-Classical but pre-Medieval.
    "Late Latin": 13, "Vulgar Latin": 13, "Koine Greek": 13,
    # Tier 14: Classical-era -- the oldest ATTESTED (non-reconstructed) stage.
    "Latin": 14, "Ancient Greek": 14,
    # Tiers 15-18: reconstructed proto-languages, oldest/deepest.
    "Proto-West Germanic": 15, "Proto-Italic": 15, "Proto-Celtic": 15,
    "Proto-Slavic": 15, "Sanskrit": 15,
    "Proto-Germanic": 16,
    "Proto-Indo-European": 18,
}

# Unlisted foreign languages sit INSIDE the foreign band, not the English one,
# so an unknown donor still always sorts after any English-stage-first branch.
_DEFAULT_DEPTH = 10


def depth_hint(lang: Optional[str]) -> int:
    """Relative age tier for a language name. Lower is shallower/more recent."""
    return DEPTH_HINT.get(lang, _DEFAULT_DEPTH)
