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

import ety
from buckets import bucket_for, APPROXIMATE_BUCKETS
from corrections import WORD_CORRECTIONS
from compounds import COMPOUND_SPLITS

# ISO codes that are stages of English itself, not foreign donors.
ENGLISH_STAGES = {"ang", "enm", "eng"}

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
        if self.compound_parts:
            sub_views = [p.view(mode) for p in self.compound_parts]
            resolved = any(v.resolved for v in sub_views)
            return ResolvedView(self.word, "Compound", None, None, resolved, self.source, parts=sub_views)
        if self.chain:
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
            if mode == "direct":
                link = self.chain[0]
            elif mode == "root":
                link = self.chain[-1]
            elif mode == "influence":
                link = _pick_influence(self.chain)
            else:
                raise ValueError(f"unknown mode: {mode!r} (expected direct/influence/root)")
            depth_lang = link.lang
            if mode == "root" and self.root_lang:
                # Name the actual reconstructed/attested form reached, not
                # just the family bucket -- e.g. "Proto-Germanic (from PIE)"
                # instead of just "PIE". See convert_wikt.py's `resolve_term`
                # for how root_lang/root_pie are derived and their limits
                # (only surfaces names explicitly recorded in the word's own
                # chain, never inferred).
                depth_lang = f"{self.root_lang} (from PIE)" if self.root_pie else self.root_lang
            return ResolvedView(
                self.word, link.bucket, link.iso, depth_lang, True, self.source,
                specific_lang=link.specific_lang,
            )
        # No foreign donor: fall back to English-stage approximation (Path A).
        # Same answer at every level -- a word that never left English has no
        # distinct direct/influence/root story to tell.
        if self.english_stage_iso is not None:
            bucket = bucket_for(self.english_stage_iso)
            return ResolvedView(
                self.word, bucket, self.english_stage_iso,
                self.english_stage_lang, bucket not in APPROXIMATE_BUCKETS,
                self.source,
            )
        return ResolvedView(self.word, "Unknown", None, None, False, self.source)


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
                # Track the deepest English stage seen (for the fallback).
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
    for cand in _fv_candidates(word):
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


# "-ves" plurals with an f/v consonant shift (wolf->wolves, knife->knives,
# shelf->shelves) -- added 2026-07-24 (issue #17, the 347-paragraph coverage
# scan: "wolves" read Unknown despite "wolf" resolving fine; same shape
# already hand-patched once as a one-off for "self"->"selves" in
# corrections.py rather than generalized). No length floor needed here,
# unlike _cy_candidates -- the collision risk is a different shape entirely.
# "-cy" needed a floor because stripping it left an AMBIGUOUS short stem that
# could coincidentally match an unrelated real word (chancy -> chant).
# "-ves" doesn't have that problem: regular f-ending plurals are spelled
# "-fs" (roofs, chiefs, beliefs), never "-ves" -- the two suffixes don't
# overlap, so this rule can never even fire on a word that doesn't undergo
# the alternation. The remaining risk (a word that ends in "-ves" for an
# unrelated reason, e.g. "gives"/"lives" as ordinary "-e"+"s" verb forms, not
# f/v plurals) is already handled by candidate ORDER: the regular "-es"/"-s"
# suffix rules above run first and already correctly resolve "lives"->"live"
# before this function's candidates are even appended, verified directly
# against the raw data before shipping (16 real "-ves" gaps checked; the
# only hits were "myselves"/"theirselves"/"thyselves", harmless non-standard
# variants of "selves").
def _fv_candidates(word: str) -> List[str]:
    if not word.endswith("ves") or len(word) < 4:
        return []
    stem = word[:-3]
    return [stem + "f", stem + "fe"]


# Irregular past tense / past participle forms -- found 2026-07-23 (Joe:
# "held", "became" read Unknown). Suffix-stripping can never reach these:
# "held" doesn't end in "-ed" (hold -> held is a vowel change, not a suffix),
# so no rule in _SUFFIXES/_stem_variants would ever propose "hold" as a
# candidate. This is a fundamentally different gap from regular inflection
# (issue #8) -- English has a closed, well-known set of irregular verbs, not
# a spelling-rule problem, so a direct lookup table is the right fix rather
# than a cleverer stemmer. Not exhaustive (English has ~200); covers the
# common ones likely in everyday prose. Safe to extend -- lookup only fires
# after the exact surface form misses everywhere, so a word that already
# resolves correctly on its own is never affected by being listed here too.
_IRREGULAR_FORMS = {
    "held": "hold", "became": "become", "began": "begin", "begun": "begin",
    "went": "go", "gone": "go", "came": "come", "did": "do", "done": "do",
    "gave": "give", "given": "give", "took": "take", "taken": "take",
    "made": "make", "saw": "see", "seen": "see", "knew": "know", "known": "know",
    "thought": "think", "brought": "bring", "bought": "buy", "caught": "catch",
    "taught": "teach", "sought": "seek", "fought": "fight",
    "wrote": "write", "written": "write", "spoke": "speak", "spoken": "speak",
    "broke": "break", "broken": "break", "chose": "choose", "chosen": "choose",
    "drove": "drive", "driven": "drive", "rode": "ride", "ridden": "ride",
    "rose": "rise", "risen": "rise", "fell": "fall", "fallen": "fall",
    "grew": "grow", "grown": "grow", "flew": "fly", "flown": "fly",
    "drew": "draw", "drawn": "draw", "threw": "throw", "thrown": "throw",
    "blew": "blow", "blown": "blow", "wore": "wear", "worn": "wear",
    "tore": "tear", "torn": "tear", "swore": "swear", "sworn": "swear",
    "bore": "bear", "born": "bear", "borne": "bear",
    "stole": "steal", "stolen": "steal", "froze": "freeze", "frozen": "freeze",
    "sang": "sing", "sung": "sing", "sank": "sink", "sunk": "sink",
    "rang": "ring", "rung": "ring", "swam": "swim", "swum": "swim",
    "ran": "run", "drank": "drink", "drunk": "drink", "ate": "eat", "eaten": "eat",
    "felt": "feel", "kept": "keep", "slept": "sleep", "left": "leave",
    "lost": "lose", "met": "meet", "sent": "send", "spent": "spend",
    "built": "build", "sold": "sell", "told": "tell", "found": "find",
    "bound": "bind", "stood": "stand", "understood": "understand", "won": "win",
    "wound": "wind", "hung": "hang", "shot": "shoot", "shone": "shine",
    "struck": "strike", "stuck": "stick", "read": "read", "led": "lead",
    "bled": "bleed", "fed": "feed", "bent": "bend", "lent": "lend", "sat": "sit",
    "shook": "shake", "shaken": "shake", "wept": "weep", "swept": "sweep",
    "crept": "creep", "slid": "slide",
    # Added 2026-07-23 while building the compound-word split feature: these
    # showed up as the missing half of otherwise-clean compound splits
    # (dugout -> dug+out, downtrodden -> down+trodden, purebred -> pure+bred,
    # frostbitten -> frost+bitten) -- same gap shape as the original
    # held/became fix, just a few forms the first pass didn't cover.
    "dug": "dig", "trod": "tread", "trodden": "tread",
    "bred": "breed", "bitten": "bite",
    # Added 2026-07-24 (Joe: run 347 real paragraphs through the analyzer,
    # find everything that shouldn't be Unknown). This table's own docstring
    # already admitted it wasn't exhaustive ("covers ~100 of English's
    # ~200") -- this scan is what finally quantified the gap: "hid", "meant",
    # "got"/"gotten", "woke"/"awoke", "swung", "spun", "stung", "sped",
    # "snuck", "laid" all showed up as real, common, everyday words reading
    # Unknown, each for this exact reason. "heard" was found the same way
    # but indirectly -- it's what "unheard" needs as its cited root (see
    # convert_wikt.py's widened _patch_root_stubs, issue #17), not something
    # that appeared as Unknown on its own in this scan (it's caught earlier
    # by a different mechanism first). Rest of this batch: not individually
    # confirmed by this specific scan, but the same well-known closed set of
    # common English irregular verbs, added together rather than piecemeal
    # the next time each one happens to show up in someone's paragraph.
    "bit": "bite", "hid": "hide", "hidden": "hide", "meant": "mean",
    "got": "get", "gotten": "get", "woke": "wake", "woken": "wake",
    "awoke": "wake", "awoken": "wake", "swung": "swing", "spun": "spin",
    "stung": "sting", "sped": "speed", "snuck": "sneak", "laid": "lay",
    "lain": "lie", "paid": "pay", "heard": "hear", "dealt": "deal",
    "fled": "flee", "arose": "arise", "arisen": "arise", "spat": "spit",
    "wrung": "wring", "forgot": "forget", "forgotten": "forget",
    "forgave": "forgive", "forgiven": "forgive", "forbade": "forbid",
    "forbidden": "forbid", "foresaw": "foresee", "foreseen": "foresee",
    "undid": "undo", "undone": "undo", "underwent": "undergo",
    "undergone": "undergo", "withdrew": "withdraw", "withdrawn": "withdraw",
    "withstood": "withstand", "mistook": "mistake", "mistaken": "mistake",
    "overtook": "overtake", "overtaken": "overtake", "undertook": "undertake",
    "undertaken": "undertake", "overcame": "overcome", "oversaw": "oversee",
    "overseen": "oversee", "slew": "slay", "slain": "slay",
    "forsook": "forsake", "forsaken": "forsake",
    "strung": "string", "flung": "fling", "clung": "cling", "slung": "sling",
    "sprang": "spring", "sprung": "spring", "shrank": "shrink",
    "shrunk": "shrink", "stank": "stink", "stunk": "stink", "dove": "dive",
    "ground": "grind", "swollen": "swell", "proven": "prove",
    "shown": "show", "sewn": "sew", "sawn": "saw", "mown": "mow",
    "sown": "sow",
}


def _irregular_candidates(word: str) -> List[str]:
    base = _IRREGULAR_FORMS.get(word)
    return [base] if base and base != word else []


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

    def resolve(self, word: str) -> Resolution:
        r = self._try(word)
        # A chain whose only entries are bucket "Unknown" was never a real
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
        has_real_chain = bool(r.chain) and r.chain[0].bucket != "Unknown"
        # Hand-verified compounds.py wins over an AUTO-INHERITED chain
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
        prefer_compound = ((r.inherited_from is not None or r.prox_kind == "root")
                            and word.lower() in COMPOUND_SPLITS)
        if has_real_chain and r.prox_kind != "root" and not r.case_fallback and not prefer_compound:
            return r  # a confirmed chain with a real donor edge is trustworthy immediately
        # Either no chain yet, or `r` is a bare has_root STUB (prox_kind ==
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
        for cand in _irregular_candidates(word.lower()) + _stem_candidates(word.lower()):
            r2 = self._try(cand)
            if r2.chain and r2.prox_kind != "root":
                # A retry-loop match is BY CONSTRUCTION never the word's own
                # direct data (`cand` is always a different surface form,
                # reached only because the word's own lookup already failed)
                # -- so the same `prefer_compound` reasoning above applies
                # unconditionally here too, added 2026-07-24 (issue #17):
                # "outdoors" only resolves this way (stemming to "outdoor",
                # which itself inherits from "door"), so the top-of-function
                # `prefer_compound` (computed from the word's OWN `_try()`
                # result, empty here) never saw it. Checked directly here
                # instead of trying to thread one shared flag through both
                # shapes.
                if word.lower() in COMPOUND_SPLITS:
                    break
                return Resolution(word, r2.chain, r2.english_stage_iso,
                                   r2.english_stage_lang, r2.source,
                                   root_lang=r2.root_lang, root_pie=r2.root_pie,
                                   prox_kind=r2.prox_kind, root_term=r2.root_term,
                                   # Propagate whichever word's data actually
                                   # produced this answer -- `cand`'s own data
                                   # if it's a direct hit, or reuse r2's own
                                   # inherited_from if `cand` was ITSELF
                                   # answered via inheritance, so the chain
                                   # always points at the true underlying
                                   # source, not just one hop back. See
                                   # Resolution.inherited_from's docstring --
                                   # this is what lets app.py's resolve_tree()
                                   # find the SAME real data the analyzer used
                                   # without re-deriving which candidate won.
                                   inherited_from=r2.inherited_from or cand)
            if (not r.chain or r.case_fallback) and r2.english_stage_iso is not None:
                if word.lower() in COMPOUND_SPLITS:
                    break
                return Resolution(word, r2.chain, r2.english_stage_iso,
                                   r2.english_stage_lang, r2.source,
                                   root_lang=r2.root_lang, root_pie=r2.root_pie,
                                   prox_kind=r2.prox_kind, root_term=r2.root_term,
                                   inherited_from=r2.inherited_from or cand)
        if has_real_chain and not prefer_compound:
            return r  # thin has_root stub or case-fallback match, but the best answer we actually have
        # Still nothing (or a hand-verified compound was preferred over an
        # auto-inherited chain, see `prefer_compound` above): try a known
        # two-word compound split (compounds.py),
        # or an auto-detected one (convert_wikt.py's _extract_auto_compounds,
        # 2026-07-24 -- words whose only data was a bare PIE-root stub, but
        # whose raw entry ALSO recorded a compound_of/blend_of split into
        # two-or-more parts that each independently resolve). Hand-verified
        # COMPOUND_SPLITS is checked first and wins on any overlap. Only
        # reached after every real resolution path above has already failed,
        # so a word that resolves on its own -- even a compound like
        # "understand" -- is never touched by this. Recurses through
        # self.resolve() for each part (not self._try()) so a part that's
        # ITSELF a known compound (e.g. "outdoorsman" -> "outdoors"+"man",
        # where "outdoors" -> "out"+"doors") resolves correctly too; nested
        # compound_parts are flattened into one flat list so the UI shows a
        # simple row of component words, not a nested tree.
        split = COMPOUND_SPLITS.get(word.lower()) or self.auto_compounds.get(word.lower()) or self.auto_compounds.get(word)
        if split:
            flat: List[Resolution] = []
            for part in split:
                pr = self.resolve(part)
                if pr.compound_parts:
                    flat.extend(pr.compound_parts)
                else:
                    flat.append(pr)
            return Resolution(word, [], None, None, self.name, compound_parts=flat)
        return r


def default_resolver() -> Resolver:
    """
    The single place that decides the resolver stack.

    Wiktextract (prototype, see WiktextractResolver) is tried first when its
    data file is present -- richer per-word data (470k+ headwords vs 244k),
    added 2026-07-24. WiktionaryResolver (etymology-db, more mature pipeline)
    is next, `ety` last as the final fallback. Each stage degrades gracefully
    if its data file isn't present.
    """
    backends: List[Resolver] = []
    here = os.path.dirname(os.path.abspath(__file__))
    wiktextract_path = os.path.join(here, "wiktextract_words.json")
    if os.path.exists(wiktextract_path):
        backends.append(WiktextractResolver(wiktextract_path))
    wikt_path = os.path.join(here, "wikt_words.json")
    if os.path.exists(wikt_path):
        backends.append(WiktionaryResolver(wikt_path))
    backends.append(EtyResolver())
    return ChainResolver(backends)
