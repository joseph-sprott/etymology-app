"""
Resolver layer: word  ->  full origin chain, read at any of THREE depths.

THIS IS THE SWAP POINT for Path A -> Path B.

The rest of the app talks only to `Resolver.resolve(word)`. Today the concrete
implementation is `EtyResolver` (Etymological Wordnet via the `ety` package).
Tomorrow you add `WiktionaryResolver` with the same `.resolve()` signature and
`ChainResolver` will prefer it, falling back to ety. No analyzer/UI code changes.

MODE TOGGLE -- three levels (added 2026-07-22, closing out the long-open
"pass-through donor" design question in CLAUDE.md by adding the third view
Joe asked to see more evidence for):
    A resolver captures the ENTIRE foreign-donor chain, not a single language.
    The `Resolution` then answers any of three questions on demand:
      - "direct":    the FIRST foreign language English drew from (e.g.
        government -> French). Best for "how French is this text."
      - "influence": the most NOTABLE language the word passed through along
        the way -- exactly the thing the pass-through-donor issue was about
        (e.g. coffee -> Turkic, surfacing the Ottoman Turkish leg that
        "direct" (Germanic/Dutch) and "root" (Semitic/Arabic) both skip past).
        See `_pick_influence` below for the exact rule.
      - "root":      the LAST/oldest traceable ancestor (e.g. government ->
        Greek, or PIE). The etymonline-style deepest view. As of 2026-07-23,
        its display name (`ResolvedView.depth_lang`) names the actual
        reconstructed/attested form reached where the data supports it (e.g.
        "Proto-Germanic (from PIE)") rather than just the family bucket --
        see `Resolution.view()` and convert_wikt.py's `root_lang`/`root_pie`.
    Mode is chosen at read time via Resolution.view(mode), so a single analysis
    pass can be re-rendered all three ways without re-resolving.

`resolve()` returns a Resolution holding:
    chain:       ordered list of ChainLink from direct -> root (foreign
                 donors only; English stages OE/ME are recorded separately)
    english_stage_iso: deepest English-stage code reached, if the chain never
                 left English (drives the Path-A Germanic approximation)
    source:      which resolver produced this (provenance once B is added)
"""

from dataclasses import dataclass
from typing import Optional, List
import json
import os
import re
import sys

import ety
import linguistics
from buckets import bucket_for, APPROXIMATE_BUCKETS
from buckets_wikt import bucket_for_name
from corrections import WORD_CORRECTIONS
from compounds import COMPOUND_SPLITS
# Data-driven inflected-form -> base-word lookup (2026-07-25), replacing the
# hand-typed _IRREGULAR_FORMS table that used to live in this file. Shared
# with convert_wikt.py's build-time inheritance patching so query time and
# build time can never disagree about what's resolvable -- see inflections.py.
from inflections import inflection_candidates

# ISO codes that are stages of English itself, not foreign donors.
# Owned by `linguistics`; this name is kept because it is part of this
# module's existing surface.
ENGLISH_STAGES = linguistics.ENGLISH_STAGE_ISO

# The "top 8" bucket families that are common enough in everyday English to
# get their own color in app.py. Used here too: a family OUTSIDE this set is
# what makes a mid-chain waypoint worth calling out as the "influence" level
# rather than the mundane middle of a French/Latin/Germanic chain.
_CORE_FAMILIES = {"Germanic", "Norse", "French", "Latin", "Greek",
                   "Romance (other)", "Celtic", "PIE"}
# Never informative as a pick -- these mean "we don't know", not a language.
_UNINFORMATIVE = {"Other", "Unknown"}


@dataclass
class ChainLink:
    iso: str
    lang: str
    bucket: str
    # The specific donor language behind this step (e.g. "Dutch"), when known
    # -- added 2026-07-23 for the bar-graph drill-down feature. `lang` above
    # stays the bucket name (existing contract, unchanged); this is additive.
    # None for EtyResolver (no such data) and for wikt_words.json entries
    # that didn't carry a chain_langs array (see convert_wikt.py).
    specific_lang: Optional[str] = None


@dataclass
class ResolvedView:
    """One reading (direct / influence / root) of a Resolution."""
    word: str
    bucket: str
    donor_iso: Optional[str]
    depth_lang: Optional[str]
    resolved: bool
    source: str
    # Set only when this word doesn't resolve on its own but is a known
    # compound (see compounds.py) -- each element is one component word's
    # own ResolvedView at the same mode. `bucket` above is the placeholder
    # "Compound" in that case; real per-word aggregation reads `parts`.
    parts: Optional[List["ResolvedView"]] = None
    # The specific donor language behind THIS view's answer (e.g. "Dutch"
    # for a Germanic-bucket word actually borrowed from Dutch), when known --
    # added 2026-07-23 for the bar-graph drill-down feature. None for a
    # native-core word (there's no donor; group it under `depth_lang`
    # instead, e.g. "English (native core)") or when the underlying data
    # didn't carry this detail.
    specific_lang: Optional[str] = None


def _pick_influence(chain: List["ChainLink"]) -> "ChainLink":
    """
    Level 2 ("influence"): the most notable language the word passed through
    on its way from direct donor to deepest root -- not just the positional
    middle, but whichever waypoint is most worth calling out.

    Rule: look at the chain's INTERIOR (excluding the direct-donor and root
    ends -- those already have their own views). If any interior link belongs
    to a family outside the common European core (Slavic, Indo-Iranian,
    Semitic, Turkic, East Asian, Austronesian, Indigenous American, etc.),
    pick the one closest to the root -- that's the distinctive, easy-to-miss
    leg of the journey. Otherwise pick the innermost interior link (still a
    real waypoint, just not an exotic one). With no interior at all (chain
    length <= 2 -- a direct 1- or 2-hop word like "table" or "algebra"),
    there's no separate middle to show, so this falls back to the root --
    with only two real stops, the deeper one is usually the more telling of
    the two (that's the whole idea behind the pass-through-donor issue).

    PIE is never returned as the "notable influence" (Joe, 2026-07-23): it's
    the shared ancestor of virtually the entire Indo-European chain, the
    opposite of "distinctive" -- surfacing it as the culturally-interesting
    middle donor defeats the point of this level (that's what Deepest Root is
    for). Filtered out of the chain up front; the existing rule then runs
    over whatever real waypoints are left.
    """
    non_pie = [link for link in chain if link.bucket != "PIE"]
    if not non_pie:
        return chain[-1]  # degenerate: chain is PIE-only, nothing else to show
    if len(non_pie) <= 2:
        return non_pie[-1]
    interior = non_pie[1:-1]
    notable = [link for link in interior
               if link.bucket not in _CORE_FAMILIES and link.bucket not in _UNINFORMATIVE]
    if notable:
        return notable[-1]
    informative = [link for link in interior if link.bucket not in _UNINFORMATIVE]
    return (informative or interior)[-1]


@dataclass
class Resolution:
    word: str
    chain: List[ChainLink]          # direct -> root, foreign donors only
    english_stage_iso: Optional[str]
    english_stage_lang: Optional[str]
    source: str
    # Added 2026-07-23 for the "Deepest Root" redesign: the specific deepest
    # attested-or-reconstructed language name (e.g. "Proto-Germanic", not
    # just the "Germanic" bucket it maps to), and whether that name itself
    # goes on to connect to PIE. Only WiktionaryResolver populates these
    # (from convert_wikt.py's `root_lang`/`root_pie` -- see that module for
    # exactly what they mean and their limits); EtyResolver leaves them at
    # the defaults, so `.view("root")` falls back to its normal behavior.
    root_lang: Optional[str] = None
    root_pie: bool = False
    # Added 2026-07-23 (Joe's bug report on "computer"): which kind of edge
    # produced this chain -- "root" means the word's OWN raw entry has
    # NOTHING but a bare has_root pointer (no real derived_from/borrowed_from/
    # inherited_from edge of its own), e.g. "computer"'s data is just a stub
    # citing PIE *pewH- while the real story (French<-Latin<-PIE, via
    # "compute") lives at a different term_id entirely. Only WiktionaryResolver
    # populates this (from convert_wikt.py's `prox_kind`); used by
    # ChainResolver.resolve() to prefer a stemmed candidate's REAL chain over
    # trusting a thin stub. EtyResolver/corrections without this field default
    # to None, which is never treated as a stub.
    prox_kind: Optional[str] = None
    # Set only when this word resolved via a compounds.py split rather than
    # a real lookup -- see ChainResolver.resolve(). Each element is the
    # Resolution of one component word (already flattened -- a component
    # that's itself a compound has its own parts spliced in directly, so a
    # 3-part word like "outdoorsman" shows 3 flat parts, not a nested tree).
    compound_parts: Optional[List["Resolution"]] = None
    # True when this word HAS a recorded formation but the affix filter left
    # fewer than two real components, so it shows no split. Lets a
    # hand-verified `compounds.py` entry override for `overactive` (genuinely
    # over- + active) without overriding `muskrat`, which has no formation at
    # all -- it is borrowed from Algonquian and "musk + rat" is folk
    # etymology. Added 2026-07-30 with `ety_node.is_affix` (issue #19 -- word
    # endings counted as component words).
    affix_collapsed: bool = False
    # Set when this Resolution came from WiktionaryResolver's lowercase-miss
    # case-fallback (word.capitalize() or original-case, not a genuine exact-
    # case hit). Added 2026-07-24 (Joe: "ran" resolved as an unrelated
    # Japanese loanword). Same root shape as the "went"/"Went" bug (issue
    # #12) -- a lowercase miss falling back to an unrelated capitalized
    # homograph -- but that fix only covered the case where the fallback
    # match was CHAINLESS (native-core); "Ran" (a real Japanese-related
    # entry) has a genuine foreign chain, so the old check (`if r.chain and
    # r.prox_kind != "root": return r`) trusted it immediately without ever
    # reaching the irregular-form retry that would have found "ran"->"run".
    # `case_fallback=True` lets ChainResolver.resolve() apply the exact same
    # lower-trust treatment to ANY case-fallback match, chain or not.
    case_fallback: bool = False
    # The exact spelling recorded at `root_lang` (e.g. "*handuz"), when
    # convert_wikt.py's data carries one -- was already computed there
    # (used by fetch_reconstructions.py) but never threaded through this
    # layer until now. Added 2026-07-24 alongside `inherited_from` (all-caps,
    # Joe: every feature must pool from the same database) so any consumer
    # of Resolution -- not just the bucket/chain pipeline -- can reach the
    # same specific-spelling detail, e.g. app.py's resolve_tree() building a
    # one-node tree branch for a word whose only data is a direct foreign-
    # root citation (see convert_wikt.py's _patch_foreign_root_stubs).
    root_term: Optional[str] = None
    # The OTHER word whose data actually produced this Resolution's chain,
    # whenever it isn't the input word's own direct entry -- set by
    # WiktionaryResolver from convert_wikt.py's data-layer `inherited_from`
    # field (e.g. "professional" inherited "profession"'s whole entry), AND
    # by ChainResolver.resolve()'s own irregular-form/stemming retry (e.g.
    # "consistency" answered via "consistent", found only at the resolver
    # layer with no data-file backing at all). Added 2026-07-24 (Joe,
    # all-caps: every feature must pool from the same database, full stop --
    # not just today's two words). This is THE general mechanism: any
    # feature that needs richer per-word data than a Resolution carries (the
    # etymology tree today; anything added later) can call
    # RESOLVER.resolve(word), check `.inherited_from`, and look up ITS data
    # in whatever richer store it has -- instead of re-deriving "where did
    # this word's real answer actually come from" with separate logic that
    # could quietly drift from what the resolver itself decided. See
    # app.py's resolve_tree() for the reference consumer.
    inherited_from: Optional[str] = None

    def view(self, mode: str = "direct") -> ResolvedView:
        """Render this resolution at the "direct", "influence", or "root" level."""
        # Component chips are DISPLAY; they no longer decide the bucket.
        #
        # Before, having components at all forced bucket="Compound", which
        # hid every compound's real donor languages inside one catch-all bar.
        # Now the "Compound" bucket is used only when the word has NO history
        # of its own -- the original case, where the components genuinely ARE
        # the only answer. When the word does have a chain, that chain sets
        # the bucket and the components ride along for the word list to draw.
        # (Joe, 2026-07-26: show the pieces, keep the accurate bars.)
        sub_views = ([p.view(mode) for p in self.compound_parts]
                     if self.compound_parts else None)
        if sub_views and not self.chain and self.english_stage_iso is None:
            resolved = any(v.resolved for v in sub_views)
            return ResolvedView(self.word, "Compound", None, None, resolved, self.source, parts=sub_views)
        if self.chain:
            return self._chain_view(mode, sub_views)
        # No foreign donor: fall back to English-stage approximation (Path A).
        # Same answer at every level -- a word that never left English has no
        # distinct direct/influence/root story to tell.
        if self.english_stage_iso is not None:
            bucket = bucket_for(self.english_stage_iso)
            return ResolvedView(
                self.word, bucket, self.english_stage_iso,
                self.english_stage_lang, bucket not in APPROXIMATE_BUCKETS,
                self.source, parts=sub_views,
            )
        return ResolvedView(self.word, "Unknown", None, None, False, self.source,
                            parts=sub_views)

    def _link_for(self, mode: str) -> "ChainLink":
        """Which step of the chain this mode reads."""
        if mode == "direct":
            return self.chain[0]
        if mode == "root":
            return self.chain[-1]
        if mode == "influence":
            return _pick_influence(self.chain)
        raise ValueError(f"unknown mode: {mode!r} (expected direct/influence/root)")

    def _chain_view(self, mode: str, sub_views) -> ResolvedView:
        """This resolution read at one level, for a word that has a chain."""
        if mode in ("direct", "influence") and self.prox_kind == "root":
                # Added 2026-07-24 (Joe: "vitamin"/"critical" showed PIE for
                # Direct Source -- same impossible shape as the "computer" bug
                # (issue #12), just without a sibling term_id for
                # ChainResolver's stem-retry to fall back on. prox_kind ==
                # "root" means (per convert_wikt.py's resolve_term()) this
                # word's ENTIRE chain came from bare has_root pointers -- no
                # real derived_from/borrowed_from/inherited_from/English-stage
                # edge exists anywhere in its own data. There is no honest
                # direct-donor or notable-influence answer for a word shaped
                # like that, so both views report Unknown -- the same shape
                # already used everywhere else for "no real answer" (see the
                # final fallback below), which analyzer.py already aggregates
                # correctly. Deepest Root is untouched below: the PIE citation
                # itself is real, verified data (Wiktionary's own `has_root`
                # tag) -- only the false claim that it's an immediate donor
                # goes away.
            return ResolvedView(self.word, "Unknown", None, None, False, self.source)
        link = self._link_for(mode)
        depth_lang = link.lang
        if mode == "root" and self.root_lang:
            # Name the actual reconstructed/attested form reached, not just
            # the family bucket -- "Proto-Germanic (from PIE)" rather than a
            # bare "PIE" that says nothing about which branch it came down.
            # Only surfaces names explicitly recorded in the word's own chain,
            # never inferred.
            depth_lang = (f"{self.root_lang} (from PIE)" if self.root_pie
                          else self.root_lang)
        return ResolvedView(
            self.word, link.bucket, link.iso, depth_lang, True, self.source,
            specific_lang=link.specific_lang, parts=sub_views,
        )


class Resolver:
    """Interface. Every backend implements resolve()."""
    name = "base"

    def resolve(self, word: str) -> Resolution:
        raise NotImplementedError


class EtyResolver(Resolver):
    """Path A backend: Etymological Wordnet via `ety`."""
    name = "ety"

    def resolve(self, word: str) -> Resolution:
        try:
            origins = ety.origins(word, recursive=True)
        except Exception:
            origins = []

        chain: List[ChainLink] = []
        english_iso = english_lang = None
        for o in origins:
            iso = o.language.iso
            if iso in ENGLISH_STAGES:
                # Track the deepest English stage seen (for the fallback) --
                # but MODERN English is not evidence of descent. `ety` returns
                # ('eng', 'English') for `lithology` and `photophore`, which
                # are litho-/photo- + -ology/-phore: a FORMATION citing the
                # same language, not a native thread. Treating it as evidence
                # made them Germanic, a confident wrong answer where Unknown
                # was honest. Real native words cite an older stage --
                # `water` gives enm/ang, `trust` gives enm. Same rule issue
                # #22 already applies in `DbResolver` (a native claim needs an
                # `inherited` edge); this backend never got it.
                if iso != "eng":
                    english_iso, english_lang = iso, o.language.name
                continue
            chain.append(ChainLink(iso, o.language.name, bucket_for(iso)))

        return Resolution(word, chain, english_iso, english_lang, self.name)


# Suffixes tried, longest/most-specific first, when a word isn't found as-is.
# "al" added 2026-07-24 (Joe: "professional" read Unknown) -- covered by the
# existing _stem_variants machinery with no special-casing needed, since it
# always tries the unmodified stem too (professional -> "profession", exact
# match; cultural -> "cultur" + the existing silent-e rule -> "culture").
# "cy" is NOT added here -- see _stem_candidates below for why it needs its
# own dedicated handling instead of going through the generic path.
_SUFFIXES = ["ness", "ment", "tion", "sion", "able", "ible", "ful", "less",
             "ing", "edly", "ed", "est", "er", "es", "ly", "al", "y", "s"]


def _is_consonant(ch: str) -> bool:
    return ch.isalpha() and ch not in "aeiou"


def _stem_variants(stem: str) -> List[str]:
    """Candidate base forms for a suffix-stripped stem, most likely first.

    Mirrors the English spelling rules that caused the suffix to be added in
    the first place: a doubled final consonant is undone (hopp- -> hop, from
    "hopping"); a single consonant after a single vowel usually means a
    dropped silent e (hop- -> hope, from "hoping"); a trailing i usually
    means a y was swapped in (tri- -> try, from "tries").
    """
    variants = []
    if len(stem) >= 3 and stem[-1] == stem[-2] and _is_consonant(stem[-1]):
        variants.append(stem[:-1])
    elif (len(stem) >= 2 and _is_consonant(stem[-1]) and stem[-1] not in "wxy"
          and not _is_consonant(stem[-2])):
        variants.append(stem + "e")
    if stem.endswith("i") and len(stem) >= 2:
        variants.append(stem[:-1] + "y")
    variants.append(stem)
    variants.append(stem + "e")
    return variants


def _stem_candidates(word: str) -> List[str]:
    """Base-form candidates to try when `word` has no direct entry."""
    seen = set()
    out = []
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 2:
            stem = word[: -len(suf)]
            for cand in _stem_variants(stem):
                if cand and cand != word and cand not in seen:
                    seen.add(cand)
                    out.append(cand)
    for cand in _cy_candidates(word):
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
    return out


# "-cy" needs its own rule, not the generic _stem_variants path: the noun-
# forming suffix "-cy" doesn't just strip cleanly off an adjective, it
# REPLACES a "-t"/"-te" ending (consistent -> consistency, private ->
# privacy) -- a bare strip-and-retry (what "-y" already tries) leaves a stem
# one letter short ("consistenc", not "consistent"). Added 2026-07-24 (Joe:
# "consistency" read Unknown; verified its raw etymology-db data has ZERO
# rows at all -- unlike "professional"/"mindset", no amount of convert_wikt.py
# data-pipeline work can fix this specific word, since Wiktionary's own
# snapshot here just doesn't have a page for it. "consistent" resolves fine,
# so this closes the gap at the resolver layer instead, the same place
# _IRREGULAR_FORMS already lives for a similar "no raw data, but a related
# word already resolves" shape).
#
# Verified 2026-07-24 against the full set of missing "-cy" words in the raw
# data (908 candidates, 141 would match) before shipping: a bare `len(word)
# > 4` guard produces real false positives at SHORT stripped-stems --
# "chancy" (unrelated to "chant"; it's "chance"+"-y") -> "chant", "spacy" ->
# "spat", "trancy" -> "trant", "fleecy" -> "fleet", "stacy" -> "stat" were
# all wrong. Every stripped stem of length >= 5 in that same scan was a
# genuine match (patency->patent, urgency->urgent, accuracy->accurate,
# self-sufficiency->self-sufficient, etc., 129 of the 141) -- so the length-5
# floor is not an arbitrary safety margin, it's the exact line the real data
# draws between the two.
def _cy_candidates(word: str) -> List[str]:
    if not word.endswith("cy"):
        return []
    stem = word[:-2]
    if len(stem) < 5:
        return []
    return [stem + "t", stem + "te"]


# NOTE (2026-07-25): `_fv_candidates` -- a hand-written rule for "-ves"
# plurals with an f/v consonant shift (wolf->wolves, knife->knives) -- used to
# live here, and before that the same shape was hand-patched one word at a
# time in corrections.py ("self"->"selves"). Both are gone: wiktextract
# records `wolves` as a `plural`-tagged form of `wolf` outright, so this is
# now real data rather than an inferred spelling rule. See inflections.py.
# NOTE (2026-07-25): `_IRREGULAR_FORMS` -- a hand-typed table of 189 irregular
# forms (held->hold, hid->hide, ...) -- and its `_irregular_candidates()`
# accessor used to live here. Both are gone, replaced by real tagged data:
# see inflections.py / build_inflections.py. The table's own comment admitted
# it covered only "~100 of English's ~200" irregular verbs and was "not
# exhaustive", and every gap in it surfaced as a common word reading Unknown
# (hid/meant/got/snuck/laid were each found that way, one coverage scan at a
# time). Wiktionary records these outright -- 663,494 inflected forms -- so
# `inflection_candidates()` now answers from data instead of a hand list.
#
# What did NOT move: the derivational stemmer below/above (_SUFFIXES,
# _stem_variants, _cy_candidates). Wiktionary's `forms` field records
# INFLECTION (plural/past/participle/comparative/superlative) only, never
# derivation, so -ness/-ment/-tion/-able/-ly/-al/-cy still need real rules.
# Deleting those would regress `critical` (-al -> critic), `professional`
# (-al -> profession) and `consistency` (-cy -> consistent).



class WiktionaryResolver(Resolver):
    """
    Path B backend: etymology-db (parsed from Wiktionary), ~73k English words.

    Loads the JSON produced by convert_wikt.py. That file already stores, per
    word, the resolved proximate bucket, deepest bucket, and the bucket chain --
    so this resolver is a lookup, not a graph walk.

    Storage is EXACT-CASE as of the 2026-07-23 rewrite (see convert_wikt.py):
    'she' and 'She' are separate keys, not merged. That used to be merged
    case-insensitively, which is what caused most of issue #6 -- a same-
    spelling-but-capitalized homograph in an unrelated sense ('She' as a
    Mandarin-derived surname, 'Look'/'Said' likewise) got silently blended
    into the common word's chain. Since analyzer.py already lowercases every
    token before resolving, looking up the lowercase form first naturally
    prefers the common-word entry over a capitalized proper-noun homograph;
    the original-case and title-case fallbacks below only matter for a word
    that exists ONLY capitalized (e.g. a place name typed at sentence start).

    Note on the contract: upstream (EtyResolver) fills ChainLink with ISO codes
    and language names. This dataset works in bucket names, so we put the bucket
    in all three fields. Downstream code only reads `.bucket` for classification
    and `.lang` for display, so the contract holds.
    """
    name = "wiktionary"

    def __init__(self, path: str = "wikt_words.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.words = data["words"]
        # Patch confirmed false positives (cross-language spelling collisions
        # and same-term_id sense-merges in the source dataset) -- see
        # corrections.py for the verified cases.
        self.words.update(WORD_CORRECTIONS)
        # Auto-detected compound_of/blend_of splits (convert_wikt.py's
        # _extract_auto_compounds) -- added 2026-07-24 for "total coverage"
        # of bare-PIE-root stubs. Kept separate from compounds.py's hand-
        # verified COMPOUND_SPLITS; ChainResolver consults both, see below.
        self.auto_compounds = data.get("auto_compounds", {})

    def resolve(self, word: str) -> Resolution:
        e = self.words.get(word.lower())
        if e is None and word != word.lower():
            e = self.words.get(word)
        # Only word.lower() and the as-typed original case count as a real,
        # intentional match -- word.capitalize() is a genuine coincidental
        # fallback (the word only exists spelled differently), so it's the
        # one flagged as `case_fallback` below (see Resolution.case_fallback
        # docstring for why: "Ran" the Japanese-related entry has a real
        # chain, unlike "Went" the surname, so ChainResolver needs this flag
        # to know to double-check rather than trust it immediately).
        case_fallback = False
        if e is None:
            e = self.words.get(word.capitalize())
            case_fallback = e is not None
        if e is None:
            return Resolution(word, [], None, None, self.name)

        chain_buckets = e.get("chain") or []
        if not chain_buckets:
            # Native core: never left the English stages. Represent it the same
            # way EtyResolver does, so `.view()` applies the Germanic fallback.
            # Uses the real nearest recorded stage name (e.g. "Middle English",
            # "Old English") when available -- added 2026-07-24 (prompted by
            # discussing engsource -- see CLAUDE.md -- which turned out not to
            # be needed since the raw data already had this, just discarded)
            # -- instead of the generic "English (native core)" label, so
            # Direct Source mode and the bar-drill-down can distinguish native
            # words by how far back they're actually attested, not lump every
            # native word into one flat answer. Falls back to the old generic
            # label only if no stage was recorded at all (rare).
            native_stages = e.get("native_stages")
            stage_lang = native_stages[0][0] if native_stages else "English (native core)"
            return Resolution(word, [], "eng", stage_lang, self.name, case_fallback=case_fallback)

        # Trust `chain` itself as ground truth for "root" (chain[-1]), not the
        # separately-stored `d` field. Found 2026-07-22: they sometimes
        # disagree -- e.g. coffee's `d` says Germanic even though its own
        # chain runs Germanic->Romance->Turkic->Semitic. Root cause in
        # convert_wikt.py: `d` is picked via `max(all_foreign, key=depth)` on
        # the raw (non-deduped) edge list, while `chain` is built from
        # `sorted(set(all_foreign), key=depth)` -- two different tie-breaks
        # over the same "depth 4" default bucket that most non-European
        # donor languages fall into, so ties between e.g. Turkic and Semitic
        # get broken differently by each. `chain` is deduped and explicitly
        # ordered shallow->deep already, so it's the more reliable source;
        # previously this code patched `d` onto the end of `chain` when they
        # disagreed, which is exactly backwards. Not appending `d` here also
        # fixes the same bug for the new "influence" (level 2) reading, which
        # depends on `chain`'s interior being accurate.
        chain_langs = e.get("chain_langs")
        chain = [
            ChainLink(b, b, b, specific_lang=(chain_langs[i] if chain_langs else None))
            for i, b in enumerate(chain_buckets)
        ]
        return Resolution(word, chain, None, None, self.name,
                           root_lang=e.get("root_lang"), root_pie=e.get("root_pie", False),
                           prox_kind=e.get("prox_kind"), case_fallback=case_fallback,
                           root_term=e.get("root_term"), inherited_from=e.get("inherited_from"))


class WiktextractResolver(Resolver):
    """
    Prototype Path C backend: kaikki.org's wiktextract JSONL extract, parsed
    by convert_wiktextract.py into the exact same {p, d, chain, prox_kind,
    root_lang, root_pie, root_term, chain_langs, native_stages} shape
    WiktionaryResolver already reads -- see that class's docstring for what
    each field means; the contract is identical, only the build pipeline
    differs. Added 2026-07-24 after the prototype-phase coverage measurement
    (CLAUDE.md) found wiktextract resolves real etymology data for roughly
    half of a real corpus's still-Unknown words that etymology-db lacks
    entirely, plus a near-doubling of total headword coverage.

    Deliberately loaded FIRST in ChainResolver's backend list (see
    default_resolver): a first-implementation-pass build (structured
    inh/der/bor templates only -- no sense-splitting, no word-formation-
    template inheritance-following yet, see convert_wiktextract.py's
    docstring for exactly what's deferred) is not yet a full replacement for
    WiktionaryResolver's more mature pipeline, but ChainResolver's existing
    "first backend with a real chain wins, otherwise fall through" logic
    (see `_try` below) already handles a backend that sometimes has nothing
    -- this file just needs to exist and answer honestly (empty chain, no
    English stage) when it doesn't know a word, which it does by construction
    (same `words.get(...)` miss shape as WiktionaryResolver).

    Applies WORD_CORRECTIONS the same way WiktionaryResolver does -- caught
    2026-07-24 before this was wired into ChainResolver at top priority:
    without this, a word with a hand-verified corrections.py override (die,
    bull, tag, previous, ...) would have that override silently bypassed
    whenever wiktextract's own (unverified, possibly wrong in the same or a
    different way) chain answered first, defeating the whole point of those
    corrections. HUB_EXCLUSIONS is NOT applied here -- it gates
    convert_wikt.py's build-time inheritance-patching specifically, which
    this phase-1 pipeline doesn't do yet (see module docstring).
    """
    name = "wiktextract"

    def __init__(self, path: str = "wiktextract_words.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.words = data["words"]
        self.words.update(WORD_CORRECTIONS)

    def resolve(self, word: str) -> Resolution:
        e = self.words.get(word.lower())
        case_fallback = False
        if e is None and word != word.lower():
            e = self.words.get(word)
        if e is None:
            e = self.words.get(word.capitalize())
            case_fallback = e is not None
        if e is None:
            return Resolution(word, [], None, None, self.name)

        chain_buckets = e.get("chain") or []
        if not chain_buckets:
            native_stages = e.get("native_stages")
            stage_lang = native_stages[0][0] if native_stages else "English (native core)"
            return Resolution(word, [], "eng", stage_lang, self.name, case_fallback=case_fallback)

        chain_langs = e.get("chain_langs")
        chain = [
            ChainLink(b, b, b, specific_lang=(chain_langs[i] if chain_langs else None))
            for i, b in enumerate(chain_buckets)
        ]
        return Resolution(word, chain, None, None, self.name,
                           root_lang=e.get("root_lang"), root_pie=e.get("root_pie", False),
                           prox_kind=e.get("prox_kind"), case_fallback=case_fallback,
                           root_term=e.get("root_term"))


# `_BOUND_SUFFIXES` -- a curated list of 40 hyphen-less endings -- lived here
# until 2026-07-30. It existed only because the builder collapsed
# {{suffix}} and {{compound}} into one relation, so the affix/component
# distinction had to be guessed from spelling at lookup time (known issue #19).
# `ety_node.is_affix` now carries Wiktionary's own answer, which also covers
# the ~92,000 PREFIX templates the list could never reach, so it is deleted
# rather than extended.


# Edge kinds that evidence DESCENT through the English stages, as opposed to
# formation (`formed_from`) or citation (`root`). See `_native_answer`.
_NATIVE_DESCENT_RELS = frozenset({"inherited", "derived"})


@dataclass(frozen=True)
class _Provenance:
    """
    How an answer was reached -- the four fields every `DbResolver` result
    carries regardless of which branch produced it.

    A record rather than four repeated keyword arguments: the three
    `Resolution` constructions in `_resolve` each listed all four, and keeping
    them in step was manual. Adding a fifth meant remembering three places.
    """
    case_fallback: bool
    inherited_from: Optional[str]
    compound_parts: Optional[List["Resolution"]]
    affix_collapsed: bool

    def kwargs(self) -> dict:
        return {"case_fallback": self.case_fallback,
                "inherited_from": self.inherited_from,
                "compound_parts": self.compound_parts,
                "affix_collapsed": self.affix_collapsed}


class DbResolver(Resolver):
    """
    Path C backend: etymology.db, via etymology_db.py.

    This is the one that ends the divergence. Every other backend on this
    stack answers from its OWN file with its OWN case policy and its OWN
    fallbacks, which is why the paragraph analyzer and the Word Search could
    disagree eleven different ways about the same word. This one asks the
    shared access layer, and the Word Search renders the SAME `Entry` object
    that produced this Resolution -- so there is no second derivation left to
    drift.

    It deliberately owns no lookup logic. Case folding, inflected forms,
    stemming and compound splits were all resolved at BUILD time into
    `surface_form`, so `entry()` is one indexed query with no branching.
    `compound_parts` is likewise never set: `lineage()` already follows a
    formation into its components, so a compound arrives as an ordinary
    chain instead of a special case the caller has to know about.
    """
    name = "db"

    def __init__(self, path: Optional[str] = None):
        import etymology_db
        self._db = etymology_db.get(path) if path else etymology_db.get()
        self._english = etymology_db.ENGLISH_STAGES
        # Shared with `lineage()` rather than restated here: the two used to
        # disagree about what a donor is, which is the exact drift the single
        # access layer exists to prevent.
        self._donor_rels = etymology_db.DONOR_RELS
        self._affix_cache: dict = {}

    def resolve(self, word: str) -> Resolution:
        return self._resolve(word, 0)

    def _is_bound_affix(self, node) -> bool:
        """
        Is this formation part a bound morpheme (`-ness`) rather than a word?

        A component chip and a percentage share are claims about a WORD. The
        dump's formation templates list affixes alongside real components, so
        without this `darkness` splits into `dark` + `ness` -- and `ness` is a
        real word (a headland), so half of `darkness` was being counted under
        that unrelated word's bucket. `beautiful` lost half its weight to
        `ful`, which resolves to nothing at all.

        Wiktionary's own template is the answer, recorded at build time as
        `ety_node.is_affix` (known issue #19 -- word endings counted as
        component words). `{{suffix|en|dark|ness}}` states that `ness` is an
        ending; that it is ALSO a word (a headland) is a coincidence this no
        longer has to reason about.

        This replaced `_BOUND_SUFFIXES`, a curated list of 40 hyphen-less
        endings. Two weaker spelling rules were tried against the 742-entry
        `compounds.py` table before that list and rejected by measurement:
        "`-term` exists as an entry, any position" cost 263 splits (`up-`,
        `back-`, `over-` are real prefixes AND real first components), and the
        same test in final position only still cost 134 (Wiktionary carries
        `-ball`, `-woman`, `-work`, `-man` suffix entries). No spelling test
        could work, because ~98% of affixes reach us WITHOUT their hyphen --
        and the list never covered prefixes at all, so `rewrite` was counted
        half-Latin via `re`.

        The one surviving spelling rule is Joe's call (2026-07-30): an
        EXPLICITLY hyphenated part whose bare form is a real word stays a
        component, so `craftsman` still reads crafts + man and the 742
        hand-verified splits are untouched. Position-derived affixes get no
        such escape -- the template asserted the role outright.

        The whole word keeps its own answer either way: `parts` is display and
        weight-splitting only, and `lineage()` still walks the formation to
        build the chain, so dropping a part costs richness, never coverage.
        """
        term = node.term or ""
        bare = term.strip("-")
        if not bare:
            return True
        # Two statements by Wiktionary, both trusted outright: the template's
        # position (`ety_node.is_affix`) and the hyphen it printed. Neither is
        # second-guessed by asking whether the bare spelling happens to be a
        # word -- `ness` (a headland) and `man` both are, and that coincidence
        # is exactly what the old curated list existed to paper over.
        #
        # Dropping every hyphenated part used to cost 76 hand-verified splits,
        # which is why an "unless the bare form resolves" escape hatch lived
        # here. It has moved to where it belongs: `ChainResolver` now lets a
        # `compounds.py` entry win whenever the database answer has no parts,
        # so `craftsman` keeps crafts + man by being hand-verified rather than
        # by a spelling rule that also protected `-ness` and `-ion`.
        return bool(getattr(node, "is_affix", False)) or term != bare

    def _part_resolution(self, node, depth: int) -> Resolution:
        """
        One component's own answer, read in the language it was RECORDED in.

        Only a modern-English component is looked up as a word. `about` is
        recorded as Old English `on` + `būtan` + `be` + `ūtan`; looking those
        up as modern English matched `on` and `be` by coincidence and found
        nothing for `būtan`/`ūtan`, so half of an extremely common word was
        counted as Unknown. A part already carries its language -- `būtan` IS
        Old English, and that is the answer without any lookup.

        A modern English part is still followed into its own history, which is
        the entire reason parts are resolved rather than just bucketed:
        `bagpipe`'s `pipe` has to reach Latin.
        """
        term = (node.term or "").strip("-") or node.term
        if node.lang == "English":
            return self._resolve(term, depth + 1)
        bucket = bucket_for_name(node.lang)
        link = ChainLink(bucket, bucket, bucket, specific_lang=node.lang)
        return Resolution(term, [link], None, None, self.name,
                          root_lang=node.lang, root_term=node.term)

    def _donor_nodes(self, line: List) -> List:
        """
        The foreign steps in a lineage that actually transmitted the word.

        A ROOT IS NOT A DONOR. `trust` runs English -> Middle English -> Old
        English -> PIE *deru-: its only foreign node is a reconstructed root,
        so the honest direct-source answer is "native Germanic", not "PIE".
        Counting the root as a donor is the same false claim as drawing
        `mile`'s Middle-English-to-PIE edge, just in the bar chart instead of
        the tree.
        """
        return [n for n in line[1:]
                if n.lang not in self._english and n.rel in self._donor_rels]

    def _native_answer(self, word: str, line: List,
                       found: "_Provenance") -> Resolution:
        """
        A native-core identification -- or a MISS, when nothing evidences it.

        NATIVE DESCENT IS A CLAIM, AND IT NEEDS EVIDENCE. This used to fire on
        "no foreign donor found", which treats absence of evidence as
        evidence. True for `trust` (a real inherited thread through the
        English stages) and false for `movie`, whose entire recorded formation
        is the suffix `ie` because the builder lost `move`, and for
        `zoophysiologist`, which is Greek but whose parts are absent from the
        database so the walk dead-ended inside English.

        The evidence required is a DESCENT edge from an English stage --
        `inherited` or `derived`. Without one this is a miss, and a miss lets
        the gap-fillers and `compounds.py` have their turn, which is how
        `peacemaker` gets back to peace + maker. Reporting Germanic instead
        both stated a falsehood and blocked every backend behind it.

        `derived` was added 2026-07-31. Requiring `inherited` alone was too
        narrow: Wiktionary records plenty of ordinary native descent as
        derivation -- `lose` <- Middle English `losen`, `start` <- Middle
        English `stert` -- and those words were being missed here. It went
        unnoticed because the legacy file-backed backends answered them, which
        is a fallback MASKING a defect rather than filling a gap.

        `formed_from` is deliberately NOT descent: it is how a word was BUILT,
        not where it came from, and accepting it would re-admit `movie` (whose
        whole recorded formation is the suffix `ie`) and `zoophysiologist`.
        """
        if not any(n.rel in _NATIVE_DESCENT_RELS and n.lang in self._english
                   for n in line):
            return Resolution(word, [], None, None, self.name, **found.kwargs())
        stages = [n for n in line if n.lang in self._english]
        stage = stages[-1].lang if len(stages) > 1 else "English (native core)"
        return Resolution(word, [], "eng", stage, self.name, **found.kwargs())

    def _donor_answer(self, word: str, foreign: List, prox_kind: Optional[str],
                      found: "_Provenance") -> Resolution:
        """
        A real foreign chain, plus the deepest form to name for Deepest Root.

        Deepest Root names the deepest ATTESTED-or-reconstructed language and
        flags separately whether it goes on to PIE, so a Germanic word reads
        "Proto-Germanic (from PIE)" rather than collapsing to a bare "PIE"
        that says nothing about which branch it came down.
        """
        chain = [ChainLink(bucket_for_name(n.lang), bucket_for_name(n.lang),
                           bucket_for_name(n.lang), specific_lang=n.lang)
                 for n in foreign]
        deepest = foreign[-1]
        non_pie = [n for n in foreign if not _is_pie(n.lang)]
        root_pie = bool(non_pie) and _is_pie(deepest.lang)
        root_node = non_pie[-1] if root_pie else deepest
        return Resolution(word, chain, None, None, self.name,
                          root_lang=root_node.lang, root_pie=root_pie,
                          prox_kind=prox_kind, root_term=root_node.term,
                          **found.kwargs())

    def _resolve(self, word: str, depth: int) -> Resolution:
        entry = self._db.entry(word)
        # No tree means NO ANSWER -- never a native-core claim. `entry` exists
        # whenever a surface form points here, but a database that is still
        # building (or was built without its tree cache) has rows with no
        # etymology attached. Falling through to the native-core branch there
        # made every word report "English (native core)", and because
        # ChainResolver treats a native-core identification as a real answer,
        # it also blocked every legacy backend behind it. A miss must look
        # like a miss.
        if entry is None or not entry.etymologies:
            return Resolution(word, [], None, None, self.name)

        # The word we actually answered from, when it isn't the typed one.
        inherited = (entry.headword if not entry.is_exact else None)
        case_fallback = entry.match_kind == "case"

        # A stub is a word whose ONLY ancestor is a dotted root pointer. The
        # citation is real but it is not a donor, so `prox_kind="root"` makes
        # view() report Unknown for direct/influence exactly as it already
        # does for the old data's bare-root stubs -- while Deepest Root still
        # shows the root, which is the honest split.
        prox_kind = "root" if entry.status == "stub" else None

        # Components, for the word list to draw as chips. Only one level deep:
        # these exist to SHOW what a compound is made of, and a part's own
        # parts would be noise. The depth guard also stops `x = x + y` style
        # self-reference from recursing.
        # Decided by STRUCTURE, not by the shape label. A tree built from the
        # `ety` template is tagged shape="rendered" whether it describes a
        # chain or a formation, so gating on shape in ("fork","mixed") missed
        # 142 real compounds -- `mountainside`, `armchair`, `mindset` all have
        # their components right there as formed_from children.
        parts = None
        affix_collapsed = False
        if depth == 0 and entry.primary:
            children = [c for c in entry.primary.head.children
                        if c.rel == "formed_from" and c.term]
            terms = [c.term for c in children if not self._is_bound_affix(c)]
            # Did the affix filter -- not the source data -- take this word's
            # split away? `overactive` really is recorded over- + active, so
            # dropping the prefix leaves one part and no split at all. That is
            # the only case where a hand-verified `compounds.py` entry should
            # override, and `ChainResolver` needs to be able to tell it apart
            # from `muskrat`, which never had a formation to begin with: it is
            # BORROWED from Algonquian, and "musk + rat" is folk etymology.
            affix_collapsed = len(children) >= 2 and len(terms) < 2
            if len(terms) >= 2:
                # Show the chip as the WORD. A surviving part is one whose bare
                # spelling is a real entry (that is what got it past the affix
                # check), so `crafts` + `-man` should read "man", not "-man".
                kept = [c for c in children if not self._is_bound_affix(c)]
                parts = [self._part_resolution(c, depth) for c in kept]

        found = _Provenance(case_fallback=case_fallback, inherited_from=inherited,
                            compound_parts=parts, affix_collapsed=affix_collapsed)
        line = self._db.lineage(entry)
        foreign = self._donor_nodes(line)
        if not foreign:
            return self._native_answer(word, line, found)
        return self._donor_answer(word, foreign, prox_kind, found)


# Owned by `linguistics` -- `app.py` had grown its own, differently-worded
# copy of this same test.
_is_pie = linguistics.is_pie


class ChainResolver(Resolver):
    """
    Tries backends in priority order, returns the first that `resolved` True;
    otherwise returns the best (last) approximate answer.

    Path B: construct as ChainResolver([WiktionaryResolver(), EtyResolver()]).
    Today: ChainResolver([EtyResolver()]).
    """
    name = "chain"

    def __init__(self, backends: List[Resolver]):
        self.backends = backends
        # Merge in any backend's auto-detected compound splits (currently
        # only WiktionaryResolver has these -- see its __init__) so the
        # compound fallback below can consult them alongside compounds.py's
        # hand-verified COMPOUND_SPLITS.
        self.auto_compounds = {}
        for b in backends:
            self.auto_compounds.update(getattr(b, "auto_compounds", {}) or {})

    def _try(self, word: str) -> Resolution:
        """One pass across all backends for a single surface form."""
        # Widened 2026-07-24 (WiktextractResolver, now the top-priority
        # backend): this used to trust the FIRST backend with ANY non-empty
        # chain immediately, full stop -- fine when there was only one real
        # data-rich backend ahead of EtyResolver's much weaker fallback, but
        # now a thin prox_kind=="root" stub from wiktextract (a word whose
        # ONLY evidence is a bare deepest-root pointer, no real donor edge of
        # its own -- same shape as the "computer"/"vitamin" bug) could win
        # here and permanently block WiktionaryResolver from ever being
        # tried for that SAME word, even when it has perfectly good real
        # data. Found via real regressions this exact change introduced
        # ("react"/"eventually"/"smartphone" went from resolving correctly
        # to Unknown): a stub is no longer trusted outright -- it's kept as
        # a fallback candidate while later backends still get a chance to
        # supply something real. Only genuinely empty results (no chain at
        # all) fall through further, to `fallback`, unchanged from before.
        best_stub = None
        fallback = None
        for backend in self.backends:
            r = backend.resolve(word)
            if r.chain:
                if r.prox_kind != "root":
                    return r  # a real donor edge -- trustworthy immediately
                if best_stub is None:
                    best_stub = r
                continue  # thin stub -- keep checking other backends first
            # A backend that positively identified the word as native core
            # wins -- that's a real answer, not a miss, and outranks any
            # stub seen so far (a genuine identification beats a non-answer).
            if r.english_stage_iso is not None:
                return r
            if fallback is None:
                fallback = r
        return best_stub or fallback or Resolution(word, [], None, None, self.name)

    def _has_usable_chain(self, r: Resolution) -> bool:
        """
        Does this result carry a chain that actually answers anything?

        A chain whose FIRST entry is bucket "Unknown" was never a real
        # answer -- found 2026-07-24 (issue #17) while auditing ALL 743
        # compounds.py entries after widening convert_wikt.py's inheritance
        # patches: "bathrobe"/"bathtub"/"bluebird" (none touched by today's
        # data changes) regressed from a working compound split to flatly
        # Unknown. Root cause, unrelated to today's widening: EtyResolver
        # (the fallback Path-A backend) can return a chain citing an ISO
        # code `buckets.py` doesn't map, producing `bucket_for(iso) ==
        # "Unknown"` -- `_try()`'s "any non-empty chain wins" check then
        # trusted this non-answer immediately, permanently blocking the
        # compound-split fallback below from ever being reached. Treating it
        # as equivalent to no chain lets those words fall through correctly.
        # Checks chain[0] specifically (not "any entry"): that's the one
        # Direct Source mode actually reads. Narrowed to this 2026-07-24
        # after finding "taxicab" (1 of the 743 compounds.py entries) has an
        # EtyResolver chain that mixes Unknown with real buckets in an
        # undeduped order -- an `any()` check called it "real" while Direct
        # Source mode still displayed the Unknown entry sitting at position 0.
        """
        return bool(r.chain) and r.chain[0].bucket != "Unknown"

    def _is_trustworthy(self, r: Resolution) -> bool:
        """
        Can this result be returned immediately, without trying other forms?

        Three ways it cannot, each a real bug this guard exists to stop:
          * a bare `has_root` STUB (`prox_kind == "root"`) is a deepest-root
            citation with no donor edge of its own. `computer` showed Direct
            Source == PIE, impossible in principle, because its own entry was
            a stub while the real French/Latin chain sat under `compute`.
          * a CASE-FALLBACK match is a same-spelling-different-case
            coincidence. `went` has no lowercase entry and fell through to the
            surname `Went`, which is also native-Germanic and so looked right
            for the wrong reason; `ran` fell through to the Japanese-related
            `Ran`, which has a real chain and so had to be excluded by the
            flag rather than by chainlessness.
          * no usable chain at all.
        """
        return (self._has_usable_chain(r)
                and r.prox_kind != "root"
                and not r.case_fallback)

    def _prefers_hand_verified_split(self, word: str, r: Resolution) -> bool:
        """
        Should `compounds.py`'s hand-verified split beat the answer we have?

        Only ever for a word IN that table, and only when the answer is not
        the word's own genuine data. Hand-verified compounds.py wins over an AUTO-INHERITED chain
        # specifically -- also found 2026-07-24, auditing the same 743
        # entries: widening convert_wikt.py's inheritance patches gave 147 of
        # them a real chain for the first time, but for a genuine two-
        # content-word compound (e.g. "mountainside" -- verified live as
        # "mountain" + "side", both independently meaningful), silently
        # inheriting just ONE part's whole story and dropping the other is a
        # worse, less complete answer than the hand-verified split, even
        # though it isn't factually WRONG. Scoped narrowly to
        # `inherited_from` being set (this ISN'T the word's own directly-
        # recorded data, just borrowed from elsewhere) so a word with
        # genuinely good data of its own is untouched -- compounds.py's own
        # docstring is explicit that it should never override a word that
        # "resolves on its own," and that design intent still holds here.
        # Widened 2026-07-24 (WiktextractResolver): a bare prox_kind=="root"
        # stub is ALSO not the word's own genuine resolution (it displays as
        # Unknown for direct/influence regardless -- see Resolution.view()),
        # so it shouldn't block a hand-verified compound split either, same
        # reasoning as the inherited_from case above. Found via
        # test_regression.py: "breakwater"/"headset"/"threadbare" (each a
        # real compounds.py entry) now get a bare PIE-root-stub "chain" from
        # wiktextract's data (a `root` template with no real inh/der/bor
        # edge of their own) -- has_real_chain treats this as real enough to
        # short-circuit past the compound fallback below, even though the
        # word never actually resolves to anything but Unknown on its own.
        # Third case added 2026-07-30 with `ety_node.is_affix` (known issue #19
        # -- word endings counted as component words): Wiktionary genuinely
        # records `overactive` as over- + active and `classmate` as class +
        # -mate, so the affix filter now drops one half and the word answers
        # with NO split at all. That is a correct reading of the source and
        # still the wrong output, because these are hand-verified two-word
        # compounds. Joe's call this session: the 742 entries win. So a word in
        # that table whose database answer carries no parts falls through to
        # the split below -- it is the exact case the table exists for.
        """
        if word.lower() not in COMPOUND_SPLITS:
            return False
        return (r.inherited_from is not None
                or r.prox_kind == "root"
                or r.affix_collapsed)

    def _as_answer_for(self, word: str, found: Resolution,
                       candidate: str) -> Resolution:
        """
        Re-badge another surface form's result as this word's answer.

        `inherited_from` records which word's data actually produced it --
        `found`'s own source if that word was itself answered by inheritance,
        so a multi-hop answer still points at the TRUE origin rather than one
        hop back. `word_trees.resolve_tree` relies on this to show the same
        data the analyzer used without re-deriving which candidate won.
        """
        return Resolution(word, found.chain, found.english_stage_iso,
                          found.english_stage_lang, found.source,
                          root_lang=found.root_lang, root_pie=found.root_pie,
                          prox_kind=found.prox_kind, root_term=found.root_term,
                          inherited_from=found.inherited_from or candidate)

    def _retry_other_forms(self, word: str, own: Resolution) -> Optional[Resolution]:
        """
        Try inflected and stemmed forms of the word. None if none does better.

        Reached whenever the word's own result is not trustworthy -- see
        `_is_trustworthy` for the three reasons. A real match on a different
        surface form beats a case coincidence or a thin stub.

        Returns None (rather than a split) for a word in `compounds.py`: the
        hand-verified split wins, and it is applied by the caller. `outdoors`
        only resolves via this loop -- stemming to `outdoor`, which inherits
        from `door` -- so the caller's own `_prefers_hand_verified_split`
        check, computed from the word's OWN result, never sees it.
        """
        # Either no chain yet, or `own` is a bare has_root STUB (prox_kind ==
        # "root" -- the word's own raw entry has nothing but a root pointer,
        # no real derived_from/borrowed_from/inherited_from edge of its own).
        # Caught 2026-07-23 (Joe: "computer" showed Direct Source == PIE,
        # which should be impossible -- no English word borrows directly from
        # a proto-language). Root cause: "computer"'s own wikt_words.json
        # entry is just a stub citing PIE *pewH-, while the real chain
        # (French<-Latin<-PIE) lives at a different term_id, "compute" --
        # ChainResolver used to trust ANY non-empty chain immediately and
        # never tried stemming down to it. `r` might ALSO still be a genuine
        # native-core identification (english_stage_iso set) -- but it might
        # be a coincidental capitalized-homograph match: WiktionaryResolver's
        # title-case fallback (for words that only exist capitalized) can
        # silently match an unrelated proper noun. Caught 2026-07-23: "went"
        # has no lowercase entry, so it fell through to "Went" -- a real but
        # unrelated surname entry that happens to ALSO be native-Germanic,
        # producing a coincidentally-plausible-looking answer for the wrong
        # reason, before "went" -> "go" (a real, precise match) ever got a
        # chance to run. So irregular/stem candidates are checked BEFORE
        # trusting a bare native-core result or a thin stub, not just on a
        # total miss -- a real match elsewhere in the data is more
        # trustworthy than a same-spelling-different-case coincidence or an
        # incomplete stub. Falls back to `r` unchanged if no candidate does
        # better.
        #
        # Widened 2026-07-24 (Joe: "ran" resolved as an unrelated Japanese
        # loanword) -- the original "went" fix above only covered a case-
        # fallback match that was CHAINLESS (a native-core surname). "Ran"
        # (capitalized) has a genuine foreign chain (Japanese), so the FIRST
        # check up top used to trust it immediately without ever reaching
        # here. `Resolution.case_fallback` (set by WiktionaryResolver) now
        # makes the first check skip ANY case-fallback match, chain or not,
        # so it always reaches this retry loop -- same logic below, just
        # reachable for a chain-having case-fallback match too now.
        is_hand_verified = word.lower() in COMPOUND_SPLITS
        wants_native = not own.chain or own.case_fallback
        for candidate in (inflection_candidates(word.lower())
                          + _stem_candidates(word.lower())):
            found = self._try(candidate)
            has_donor = found.chain and found.prox_kind != "root"
            is_native = found.english_stage_iso is not None
            if not (has_donor or (wants_native and is_native)):
                continue
            if is_hand_verified:
                return None
            return self._as_answer_for(word, found, candidate)
        return None

    def resolve(self, word: str) -> Resolution:
        """
        The full cascade, in order: own data, other forms, then a known split.

        Each step is one named question, because the order between them is
        load-bearing and every reordering has previously shipped a bug.
        """
        own = self._try(word)
        prefer_split = self._prefers_hand_verified_split(word, own)
        if self._is_trustworthy(own) and not prefer_split:
            return own
        retried = self._retry_other_forms(word, own)
        if retried is not None:
            return retried
        if self._has_usable_chain(own) and not prefer_split:
            return own  # a thin stub or case match, but the best we actually have
        return self._split_into_parts(word) or own

    def _split_into_parts(self, word: str) -> Optional[Resolution]:
        """
        A known two-word compound shown as its components, or None.

        Only reached after every real resolution path has failed, so a word
        that resolves on its own -- even a real compound like `understand` --
        is never touched. That is `compounds.py`'s own documented design rule.

        Two sources, hand-verified first and winning on any overlap:
        `compounds.py`'s COMPOUND_SPLITS, and the auto-detected
        compound_of/blend_of splits from `convert_wikt._extract_auto_compounds`
        (words whose only data was a bare PIE-root stub but whose raw entry
        also recorded a split whose parts each independently resolve).

        Recurses through `self.resolve` for each part, NOT `self._try`, so a
        part that is itself a known compound resolves too -- `outdoorsman` ->
        `outdoors` + `man`, where `outdoors` -> `out` + `doors`. Nested parts
        are FLATTENED into one list so the UI shows a simple row of components
        rather than a tree.
        """
        split = (COMPOUND_SPLITS.get(word.lower())
                 or self.auto_compounds.get(word.lower())
                 or self.auto_compounds.get(word))
        if not split:
            return None
        flat: List[Resolution] = []
        for part in split:
            resolved = self.resolve(part)
            flat.extend(resolved.compound_parts or [resolved])
        return Resolution(word, [], None, None, self.name, compound_parts=flat)


_SHARED: Optional[Resolver] = None


def shared_resolver() -> Resolver:
    """
    The one resolver instance for this process. Use this, not `default_resolver`.

    Building a resolver loads ~100MB of JSON, so a second instance is slow;
    but the reason this exists is correctness, not speed. `app.py` used to
    hold the only shared instance in a module global that nothing else could
    reach, so any new feature had two options -- import from `app` (a web
    module) or build its own stack. The second is how a feature ends up
    answering differently from the analyzer, which is known issue #16 in one
    sentence.

    `default_resolver()` still builds a fresh stack, deliberately: tests that
    need an isolated one, or a different `ETYMOLOGY_DB` setting, should keep
    using it.
    """
    global _SHARED
    if _SHARED is None:
        _SHARED = default_resolver()
    return _SHARED


def default_resolver() -> Resolver:
    """
    The single place that decides the resolver stack.

    DbResolver (etymology.db) is tried first when the database is present:
    it is the only backend the Word Search also reads, so any word it answers
    is answered identically in both features -- which is the whole point of
    the 2026-07-25 rework. The older file-backed backends stay BELOW it as
    gap-fillers, because ~151 words per 150,000 exist in etymology-db or
    Etymological Wordnet but not in the wiktextract dump. They can only add
    coverage where the database has none; they can never override it.

    Set ETYMOLOGY_DB=0 in the environment to drop back to the old stack.

    Each stage degrades gracefully if its data file isn't present.
    """
    backends: List[Resolver] = []
    here = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(here, "etymology.db")
    if os.path.exists(db_path) and os.environ.get("ETYMOLOGY_DB") != "0":
        try:
            backends.append(DbResolver())
        except Exception as exc:      # a half-built db must not break the app
            print(f"DbResolver unavailable ({exc}); using file backends",
                  file=sys.stderr)
    wiktextract_path = os.path.join(here, "wiktextract_words.json")
    if os.path.exists(wiktextract_path):
        backends.append(WiktextractResolver(wiktextract_path))
    wikt_path = os.path.join(here, "wikt_words.json")
    if os.path.exists(wikt_path):
        backends.append(WiktionaryResolver(wikt_path))
    backends.append(EtyResolver())
    return ChainResolver(backends)
