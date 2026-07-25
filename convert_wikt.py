"""
Convert the etymology-db (Wiktionary) raw relation table into the resolver's
word->chain JSON.

REWRITTEN 2026-07-23 to use the real per-word graph structure (`group_tag` /
`parent_tag` / `parent_position`) instead of a static per-language depth
table. Investigation (see CLAUDE.md known issues #2/#6) found:

  - `group_tag`/`parent_tag`/`parent_position` encode the ACTUAL recorded
    chronological chain for a given etymology thread, straight from
    Wiktionary's own etymology template parsing -- e.g. for "sandal", one
    group's rows at parent_position 0/1/2/3 are exactly Middle English/Old
    French/Latin/Ancient Greek, in that true order. This replaces the old
    `DEPTH_RANK` heuristic (issue #2) with recorded fact instead of a guess.
  - `term_id` is unique per exact-case English spelling (verified: unique
    term_id count == unique term-string count for lang=='English'). The old
    converter's `term.lower()` merge key -- added to fix a *different* case-
    clobbering bug -- was blending unrelated homographs into common words'
    chains (`she`+Mandarin "畲", `look`+Cantonese "陸", `said`+Arabic "سَعِيد"
    all turned out to be a SEPARATE, correctly-separate term_id in the raw
    data; our own lowercasing merged them back together). That was the real
    root cause of most of issue #6, not an upstream Wiktionary/etymology-db
    scraping bug as originally suspected. Fix: key output by exact-case
    spelling, no merging at conversion time; the resolver looks up the
    lowercase form first (see resolver.py), which naturally prefers the
    common-word entry over a same-spelling-but-capitalized proper noun.
  - A single term_id can carry MULTIPLE independent etymology narratives
    (distinct Wiktionary "Etymology N" sections for different senses, e.g.
    "die" the verb vs. "die" the dice-cube noun; "bull" the animal vs.
    "papal bull"). Tried multiple heuristics to auto-split these at
    conversion time (segment on English-stage restarts; cluster top-level
    groups by shared foreign bucket) -- both broke *single*-sense words that
    legitimately restart from an English-stage spelling variant multiple
    times (`law`, `sky`, `skill`, `table` all cite several Middle/Old English
    spelling variants for ONE narrative; splitting on that over-fragmented
    them) or falsely merged unrelated senses that happen to both end at a
    common bucket like PIE. Neither heuristic was reliable enough to trust
    across ~360k terms. Given that, this converter does NOT attempt sense
    splitting: it flattens ALL of a term_id's ancestry edges into one
    sequence, in their original recorded order (which reliably reflects true
    depth within any single narrative -- verified for `sandal`/`zero`/`law`/
    `sky`/`skill`/`table`/`coffee`). For the minority of words with genuinely
    distinct senses sharing one term_id, this can still blend two chains
    together, same failure shape as the old converter -- those are handled
    the same way issue #6 was: hand-verified, individually-checked entries
    in `corrections.py` (see `die`, `bull`).

Output shape (resolver.py contract; `root_lang`/`root_pie`/`root_term` added
2026-07-23 for the "Deepest Root" display redesign and its Piece 2 -- see the
comment above the `root_lang`/`root_pie`/`root_term` assignment in
`resolve_term()` for what they mean and why):
  {"buckets": {name:bucket}, "words": {term: {p, d, chain, prox_kind,
                                               root_lang, root_pie, root_term}}}
  - p:         proximate bucket (first foreign donor)
  - d:         deepest bucket (last entry in chain)
  - chain:     ordered bucket list proximate->deepest (deduped, foreign only)
  - prox_kind: 'borrowed' | 'inherited' | 'derived' | 'root' | 'core'
  - root_lang: the specific deepest language name reached (may be a proto-
               language, e.g. "Proto-Germanic", or an ordinary attested
               language, e.g. "Latin", if no proto-language step is recorded)
  - root_pie:  whether `root_lang` itself connects further to PIE
  - root_term: the exact spelling recorded at `root_lang` (e.g. "*handuz"),
               when known -- omitted otherwise. Used by fetch_reconstructions.py
               (Piece 2) to look up the right Wiktionary Reconstruction page.

Also top-level "auto_compounds": {term: [part, part, ...]} -- added 2026-07-24
(Joe: "I need total coverage of those 1300 [bare-PIE-root] words"). Separate
from "words": these are stubs with no inheritable single root, but a real
compound_of/blend_of relation naming two-or-more parts that each already
resolve on their own (see `_extract_auto_compounds`). Consulted by
ChainResolver as an auto-derived counterpart to compounds.py's hand-verified
COMPOUND_SPLITS, not merged into it -- see that function's docstring.
"""
import json
import sys

import pandas as pd

sys.path.insert(0, ".")
from buckets_wikt import bucket_for_name, ENGLISH_STAGE_NAMES, NAME_TO_BUCKET, BUCKET_ORDER
from corrections import WORD_CORRECTIONS, HUB_EXCLUSIONS
# Pure string-transformation helpers only (no dependency on a live resolver
# or the words dict) -- imported 2026-07-24 so the inheritance patches below
# can try the SAME candidate forms the resolver itself would try at query
# time, instead of only accepting an exact-string match against a cited
# root. See _patch_root_stubs's docstring for why this was needed (issue #17).
from resolver import _irregular_candidates, _stem_candidates
from etymology_chain import build_chain

PARQUET_PATH = r"C:\Users\Josep\Desktop\Etymology Project\etymology.parquet"

# Relations that express vertical descent or borrowing -- the ancestry we
# want. Same set as before; verified complete against the real reltype
# distribution in the raw data (no ancestry-shaped reltype was missed).
TRUE_BORROW_RELS = {
    "borrowed_from", "learned_borrowing_from", "semi_learned_borrowing_from",
    "orthographic_borrowing_from", "unadapted_borrowing_from", "calque_of",
}
DERIVED_RELS = {"derived_from"}
INHERIT_RELS = {"inherited_from"}
ROOT_RELS = {"has_root"}  # "root"/"has_root" in the old set -- only has_root exists in real data
ANCESTRY_RELS = TRUE_BORROW_RELS | DERIVED_RELS | INHERIT_RELS | ROOT_RELS

# Rows that open a new (possibly nested) relation group rather than being an
# edge themselves -- their own related_lang/related_term are null.
GROUP_MARKER_RELS = {"group_derived_root", "group_related_root", "group_affix_root"}

# Wiktionary's pseudo-language for symbols/international terms -- not a real
# donor, never bucket it.
NON_DONOR_LANGS = {"Translingual"}

# `parent_position` gives real, recorded depth order WITHIN one group (e.g.
# sandal's Middle English/Old French/Latin/Ancient Greek chain, verified
# against live Wiktionary) -- but SEPARATE top-level items (not tied together
# by any group) have no ordering signal between them at all: `position` is
# always 0 for ungrouped rows (verified against `table`'s Latin/Old French
# edges, which are two independent top-level rows with no structural order,
# even though French must be shallower). This coarse table is used ONLY to
# order such siblings relative to each other -- a much narrower job than the
# old DEPTH_RANK, which drove ordering for an entire chain. Within-group order
# always wins; this is a last-resort tiebreak.

# Rewritten 2026-07-23 (Joe: "make sure Middle English is never listed as
# the deepest root when Old English is mentioned in the same sentence...
# for every language where there's a clear lineage"). The original table
# lumped a family's different historical stages into ONE tier with no
# internal ordering (Old English and Middle English were BOTH rank 0, with
# no signal that Old English is the older/deeper of the two) -- this gives
# every attested stage its own tier instead, strictly increasing with age,
# per family. Reconstructed proto-languages stay at the top (deepest) as
# before -- and are now ALSO enforced by the separate proto-depth invariant
# below regardless of this table, so this ordering only matters for
# proto-vs-proto relative order (e.g. Proto-Germanic before PIE).
#
# REGRESSION caught and fixed same day: a first version of this rewrite put
# modern foreign forms (French, German, ...) at the SAME tier (0) as English/
# Scots. That broke a load-bearing property the OLD table had (accidentally,
# but critically): an English-stage-FIRST branch must ALWAYS outrank ANY
# foreign-first branch, no matter how "shallow" that foreign language is --
# because starting from an English-stage citation is the strongest available
# signal that a branch is the word's real, primary lineage, not a stray
# collision edge. Caught via "back", which has a genuine (different-sense)
# `borrowed_from French bac` row sitting alongside its real native-Germanic
# branch (Middle English -> Old English -> Proto-West Germanic -> Proto-
# Germanic -> PIE) -- putting French at tier 0 let that stray edge tie with,
# and win node order, over the real native branch, flipping "back" to show
# French as its Direct Source. Fixed by giving English-stage names their own
# reserved LOW band (0-1) and starting every foreign tier at a fixed +10
# offset -- English-stage always wins regardless of how many internal
# foreign sub-tiers exist above it.
_DEPTH_HINT = {
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


def _depth_hint(lang):
    # Default (unlisted foreign languages) sits inside the foreign band, not
    # the English-stage band -- so an unlisted donor language still always
    # sorts after any English-stage-first branch, same guarantee as above.
    return _DEPTH_HINT.get(lang, 10)



def _prox_kind_for(reltype: str) -> str:
    if reltype in TRUE_BORROW_RELS:
        return "borrowed"
    if reltype in DERIVED_RELS:
        return "derived"
    if reltype in INHERIT_RELS:
        return "inherited"
    return "root"


def _expand(row, children_by_group):
    """
    Recursively expand one row into a flat, depth-ordered list of
    (reltype, related_lang, related_term) ancestry tuples, walking into
    nested groups. Any row can anchor a nested group (not just
    group_derived_root/group_related_root/group_affix_root rows -- e.g. a
    `has_root` row can itself carry a group_tag that further rows nest
    under, seen in `law`), so children are always checked regardless of
    this row's own reltype. `has_root` entries are pulled out and returned
    separately so the caller can place them at the true end of the sequence
    (their recorded position doesn't reflect depth -- see module docstring
    / CLAUDE.md). `related_term` is carried along (not just `related_lang`)
    so the deepest step's exact spelling is available for `root_term` --
    needed to look up the right Wiktionary Reconstruction page for issue
    #10's Piece 2 (see fetch_reconstructions.py).
    """
    reltype = row.reltype
    own_seq, own_roots = [], []
    if reltype in ANCESTRY_RELS and pd.notna(row.related_lang) and row.related_lang not in NON_DONOR_LANGS:
        term = row.related_term if pd.notna(row.related_term) else None
        if reltype in ROOT_RELS:
            own_roots = [(row.related_lang, term)]
        else:
            own_seq = [(reltype, row.related_lang, term)]
    elif reltype not in GROUP_MARKER_RELS:
        return [], []  # non-ancestry, non-marker leaf row -- irrelevant

    child_seq, child_roots = [], []
    if pd.notna(row.group_tag):
        for child in children_by_group.get(row.group_tag, []):
            s, r = _expand(child, children_by_group)
            child_seq.extend(s)
            child_roots.extend(r)
    return own_seq + child_seq, own_roots + child_roots


def resolve_term(rows):
    """
    rows: list of row records for one term_id, original file order.
    Flattens every top-level ancestry edge (and its nested descendants) into
    one ordered sequence -- see module docstring for why this doesn't try to
    split multiple senses apart. Returns the p/d/chain/prox_kind dict, or
    None if the term has no ancestry data at all.
    """
    children_by_group = {}
    top_level = []
    for row in rows:
        if pd.notna(row.parent_tag):
            children_by_group.setdefault(row.parent_tag, []).append(row)
        elif pd.notna(row.group_tag) or row.reltype in ANCESTRY_RELS:
            top_level.append(row)
        # else: a non-ancestry, non-group top-level row (cognate_of, doublet_with,
        # has_affix, etc.) -- irrelevant to chain-building, skip.

    # Expand each top-level item first, then order the ITEMS (not their
    # internal contents, which are already correctly ordered by real
    # structure) via the depth hint -- a stable sort, so items that tie
    # (most commonly: several genuinely-sequential group continuations)
    # keep their original relative order.
    expanded = [_expand(row, children_by_group) for row in top_level]

    def _item_key(item):
        s, r = item
        lang = s[0][1] if s else (r[0][0] if r else None)
        return _depth_hint(lang) if lang is not None else 99

    seq, roots = [], []
    for s, r in sorted(expanded, key=_item_key):
        seq.extend(s)
        roots.extend(r)

    has_english_stage = any(lang in ENGLISH_STAGE_NAMES for (_, lang, _t) in seq)
    foreign = [(rt, lang, t) for (rt, lang, t) in seq if lang not in ENGLISH_STAGE_NAMES]

    # Native English-stage sequence (Middle English, Old English, etc.),
    # kept separately from `chain`/`chain_langs` -- added 2026-07-24 (Joe:
    # wants the bar-drill-down to show "Old English"/"Middle English" etc.
    # for native words instead of one flat "native core" label -- prompted
    # by discussing engsource, which turned out NOT to be needed for this:
    # the raw data already has this detail, e.g. "back"'s own rows literally
    # record Middle English -> Old English -> Proto-West Germanic -> Proto-
    # Germanic; this project's OWN pipeline was just discarding it).
    # `chain`/`chain_langs` stay ONE ENTRY PER BUCKET (root_lang's existing
    # logic depends on that), so this per-stage detail needs its own field.
    # Deduped by lang, real (parent_position-driven) order preserved.
    english_stage_seq = []
    seen_stages = set()
    for (_rt, lang, t) in seq:
        if lang in ENGLISH_STAGE_NAMES and lang not in seen_stages:
            seen_stages.add(lang)
            english_stage_seq.append([lang, t])

    # The actual chain-assembly rules (PIE-terminal invariant, root_lang/
    # root_term/root_pie derivation, the native-stage-vs-foreign-branch
    # distinction) now live in etymology_chain.build_chain -- extracted
    # 2026-07-24 so convert_wiktextract.py's build pipeline can share this
    # exact, already-debugged logic instead of a second copy quietly
    # drifting apart from this one. See that module for the full rationale
    # of each rule (moved there verbatim, not lost). `foreign`'s raw
    # reltype strings are normalized to the source-agnostic prox_kind
    # vocabulary ("borrowed"/"derived"/"inherited") right here, at the one
    # point in this file that still knows etymology-db's own reltype names.
    foreign_normalized = [(_prox_kind_for(rt), lang, term) for (rt, lang, term) in foreign]
    return build_chain(foreign_normalized, roots, has_english_stage, english_stage_seq)


# Relation types that name an actual English root/base word a derived word
# was built from (a bound prefix/confix, not the root itself) -- used only by
# _patch_root_stubs below, deliberately not folded into ANCESTRY_RELS: these
# aren't donor-language edges (see resolve_term's docstring on why has_affix-
# family relations are excluded from chain-building), just a "this word's
# real content lives at that OTHER word" pointer. `back-formation_from`/
# `clipping_of` added 2026-07-24 (Joe: "I need total coverage of those 1300
# words") -- same shape: "X" is really just "Y" with something trimmed off
# (a back-formation removes what looks like a suffix, e.g. "edit" from
# "editor"; a clipping shortens a longer word, e.g. "flu" from "influenza"),
# so the real donor story is Y's story, same reasoning as has_prefix_with_root.
_ROOT_POINTER_RELS = {"has_prefix_with_root", "has_confix",
                       "back-formation_from", "clipping_of"}

# Lower-priority than _ROOT_POINTER_RELS above -- added 2026-07-24 (issue
# #17, the 347-paragraph coverage scan). "unusual" showed Unknown despite
# "usual" resolving fine on its own: its raw data uses plain `has_affix`
# rather than `has_prefix_with_root` (two rows -- one naming the bound
# affix itself, "un-", which will never resolve as a word; one naming the
# real root, "usual"). `has_affix` is deliberately kept OUT of
# _ROOT_POINTER_RELS proper and only consulted after it, mirroring
# _patch_foreign_root_stubs's existing priority-ordering reasoning: it's
# less precise (can hand back a bare fragment instead of a real stem), so a
# higher-priority relation should win whenever both exist for the same word.
_LOW_PRIORITY_ROOT_POINTER_RELS = {"has_affix"}


def _root_candidates_by_term(eng, reltypes):
    rows = eng[eng["reltype"].isin(reltypes)]
    candidates = {}
    for row in rows.itertuples():
        if pd.isna(row.related_lang) or row.related_lang != "English" or pd.isna(row.related_term):
            continue
        candidates.setdefault(row.term, []).append(row.related_term)
    return candidates

# Same "exotic proximate + a real core family later in the chain" bug
# signature CLAUDE.md known issue #6 (passes 5/6) used to find real same-
# term_id sense collisions by hand (e.g. "increase" -> bogus Semitic). Reused
# here as an automated SAFETY FILTER, added 2026-07-24 while widening
# _patch_root_stubs/_extract_auto_compounds to no-entry terms: that widening
# turns a handful of "hub" words (auto, tag, logy, poly, on, person, phase,
# ...) into the inheritance source for dozens-to-hundreds of derived terms
# each, so a PRE-EXISTING collision bug in one hub word (most were never
# individually checked before, since nobody happened to look up "person" or
# "phase" on their own) now gets amplified into every word that points to
# it, instead of staying a one-off. Verified concretely for several: "tag"
# (Aramaic "crown" sense colliding with the real Germanic "label" sense --
# confirmed against live Wiktionary), "auto" (a circular clipping_of
# autorickshaw -> derived_from Hindi edge outranking the real derived_from
# Ancient Greek edge), "poly"/"logy" (their term_id only has an unrelated
# sense recorded -- Latin plant name / Dutch "sluggish" adjective -- with no
# ancestry data for the actual Greek-derived combining-form sense used in
# compounds at all). A scan of just the top hub words turned up 256 more
# with this exact shape (1,101 derived-term exposure) -- too many to hand-
# verify individually, and this widening's whole point is to stop requiring
# that. Rather than guess which are real bugs vs. genuinely complex but
# correct chains (issue #6 pass 5 found some flagged words, like "date"/
# "rose"/"mole", were genuinely correct on inspection), this conservatively
# EXCLUDES any hub whose own chain has the signature from being used as an
# inheritance source at all -- the derived word stays honestly Unknown
# rather than risk inheriting a collision, per CLAUDE.md rule 2. A real fix
# for any specific flagged hub word (like tag/auto/logy today) still belongs
# in corrections.py, verified against live Wiktionary same as always.
_CORE_FAMILIES_FOR_HUB_CHECK = {"Germanic", "Norse", "French", "Latin", "Greek",
                                 "Romance (other)", "Celtic", "PIE"}


def _is_reliable_root(key, entry):
    # Explicit denylist first (corrections.py's HUB_EXCLUSIONS) -- catches
    # hub words whose own answer is correct on its own terms but wrong for
    # the sense derived words actually need (see HUB_EXCLUSIONS docstring
    # for "logy"/"poly"), a shape the chain-signature heuristic below can't
    # detect since these hubs' own chains don't look exotic at all.
    if key in HUB_EXCLUSIONS:
        return False
    chain = entry.get("chain") or []
    if not chain:
        return True  # native-core placeholder entries carry no exotic risk
    p = chain[0]
    if p not in _CORE_FAMILIES_FOR_HUB_CHECK and any(b in _CORE_FAMILIES_FOR_HUB_CHECK for b in chain[1:]):
        return False
    return True


def _patch_root_stubs(words, eng):
    """
    Closes the "vitamin"/"critical"/"growth" bug (Joe, 2026-07-24): a bare
    has_root-only stub (prox_kind == "root" -- the word's ENTIRE chain came
    from a has_root pointer, no real derived_from/borrowed_from/inherited_from/
    English-stage edge anywhere in its own data) has no honest direct-donor
    answer of its own. resolver.py's Resolution.view() now refuses to present
    such a stub's PIE citation as a direct/influence answer (the required,
    general fix -- closes the bug for every stub, not just these). This
    function is the improvement half: for a stub whose OWN raw data also
    records a `has_prefix_with_root`/`has_confix` pointer to a real English
    root word (e.g. "growth" -> "grow"), and that root already resolves to a
    real, non-stub entry, the derived word's real donor story IS the root's
    story -- a recorded native prefix/suffix isn't itself a donor language.
    Inherits the root's entire entry (chain, prox_kind, root_lang, etc.)
    rather than guessing anything not already in the data.

    Runs as a separate pass AFTER `words` is fully built (order within the
    main per-term_id loop isn't dependency-sorted, so a root word needed here
    might not have been resolved yet when its derived word was processed).
    Iterates to a fixed point so a chain of derived-from-derived stubs (a
    root that was itself just patched this same run) resolves too, not just
    one hop. Skips (leaves as resolver.py's Unknown fallback) whenever the
    root doesn't resolve to real data -- no guessing beyond what's recorded,
    per CLAUDE.md rule 2.

    Widened 2026-07-24 (Joe: "professional" showed Unknown -- its raw data
    has NO ancestry edge of any kind, only has_prefix_with_root -> "profession"
    and has_suffix -> "al", so resolve_term() returned None and it never even
    became a bare-root STUB in the first place -- it had no entry in `words`
    at all). The original condition here only patched terms that already had
    a thin has_root-derived stub, silently skipping this much larger sibling
    population that has zero ancestry data AND zero has_root pointer, but
    DOES have a real has_prefix_with_root/has_confix/back-formation_from/
    clipping_of pointer to a root that resolves. That's the exact same "a
    recorded native affix isn't itself a donor language, so inherit the
    root's story" reasoning as the stub case -- the only thing different is
    which (non-)answer resolve_term() happened to leave behind first, which
    was never a meaningful trust signal. Verified against the raw data before
    widening: of the missing "-al" words alone, 5,310 have a
    has_prefix_with_root/has_confix pointer to an already-resolving root.

    Widened again 2026-07-24 (issue #17, the 347-paragraph coverage scan):
    the root-lookup below used to require the cited root to be an EXACT key
    in `words` -- but "unheard" cites "heard" (has_prefix_with_root), and
    "heard" has zero raw ancestry data of its own (only resolvable via
    resolver.py's _IRREGULAR_FORMS, a resolver-layer mechanism this
    build-time pass never consulted); "unexplained" cites "explained", which
    has zero raw data either but resolves fine at query time via ordinary
    suffix stemming ("explained" -> "explain"). Both were falling through
    even though the resolver itself could clearly answer them. Now falls
    back to the SAME candidate-generation the resolver uses at query time
    (`_irregular_candidates` then `_stem_candidates`, imported from
    resolver.py -- pure string functions, no circular dependency) when the
    cited root isn't a literal key, so convert_wikt.py's build-time
    inheritance and the resolver's query-time fallback cascade can no longer
    silently diverge on what counts as "resolvable."
    """
    high = _root_candidates_by_term(eng, _ROOT_POINTER_RELS)
    low = _root_candidates_by_term(eng, _LOW_PRIORITY_ROOT_POINTER_RELS)
    candidates = {}
    for term in set(high) | set(low):
        # High-priority relation's candidates always come first in the list,
        # so a real stem wins over a same-word's own noisier has_affix rows.
        candidates[term] = high.get(term, []) + low.get(term, [])

    patched = 0
    changed = True
    while changed:
        changed = False
        for term, roots in candidates.items():
            entry = words.get(term)
            if entry is not None and entry.get("prox_kind") != "root":
                continue  # already resolved to a real (non-stub) entry
            for root_term in roots:
                root_key = root_term.split("#")[0].strip()
                # Skip bound-morpheme fragments -- verified 2026-07-24 while
                # widening candidate sources to include has_affix (issue
                # #17): "unusual"'s has_affix rows name BOTH "un-" (the bound
                # prefix itself) and "usual" (the real root), and "un-" turned
                # out to have its own (wrong -- Latin "unus", unrelated to the
                # negative prefix) entry in the data, so it was winning as
                # the first-tried candidate and inheriting a bogus answer
                # into "unusual" instead of ever trying "usual". Checked the
                # scale directly: 26,967 has_affix rows across the whole
                # dataset point at a bound-morpheme-shaped term ("-ite",
                # "-o-", "-er", "un-", "-ing", ...) -- Wiktionary/etymology-db's
                # own convention marks these with a leading or trailing
                # hyphen, so filtering on that is a real signal, not a guess.
                if root_key.startswith("-") or root_key.endswith("-"):
                    continue
                # EXACT case only -- verified 2026-07-24 while widening this
                # function to no-entry terms: a lower()/capitalize() fallback
                # here reintroduces the exact "went"/"Went" bug shape known
                # issue #12 already fixed at the resolver layer (a same-
                # spelling-different-case coincidence, e.g. "forewent"'s
                # pointer "went" falling back to the unrelated capitalized
                # surname "Went", or "digraph"'s pointer "di" matching the
                # name "Di") -- except THIS bulk pass has no per-word
                # verification to catch it, unlike the resolver's irregular-
                # form precedence check. A handful of genuine capitalized
                # eponym roots (vandalize->Vandal, hertz->Hertz) are lost by
                # requiring exact case, but that's the safer default per
                # CLAUDE.md rule 2 -- not individually hand-verified at this
                # scale, so no guessing.
                root_entry = words.get(root_key)
                resolved_key = root_key
                if root_entry is None:
                    # The cited root isn't a literal key -- try the SAME
                    # candidates the resolver tries at query time (irregular
                    # forms first, then regular suffix stemming), added
                    # 2026-07-24 (issue #17). Exact case only, same reasoning
                    # as above -- these candidate functions lowercase their
                    # input regardless, so this only ever matches a genuine
                    # lowercase entry, never a capitalize() coincidence.
                    for cand in _irregular_candidates(root_key.lower()) + _stem_candidates(root_key.lower()):
                        cand_entry = words.get(cand)
                        if cand_entry is not None and cand_entry.get("prox_kind") != "root":
                            root_entry, resolved_key = cand_entry, cand
                            break
                if root_entry is None or root_entry.get("prox_kind") == "root":
                    continue  # root itself unresolved or still a stub
                if not _is_reliable_root(resolved_key, root_entry):
                    continue  # exotic-first-then-core signature, or an explicit HUB_EXCLUSIONS entry
                words[term] = dict(root_entry)
                # `inherited_from` -- added 2026-07-24 (Joe, all-caps: every
                # feature must pool from the same database). Records WHICH
                # term this entry's whole story was copied from, so any
                # OTHER feature reading word data (the etymology tree today;
                # anything added later) can look up the SAME root and derive
                # a consistent answer, instead of only the bucket-chain
                # pipeline knowing about this inheritance. See app.py's
                # resolve_tree() for the tree feature's consumer of this.
                # Uses `resolved_key` (the word that ACTUALLY had the data),
                # not `root_key` (what was literally cited) -- when they
                # differ (e.g. "explained" cited, "explain" actually
                # resolved), pointing at the real source is what lets
                # resolve_tree() successfully recurse to a real tree.
                words[term]["inherited_from"] = resolved_key
                patched += 1
                changed = True
                break
    print(f"  patched {patched} bare-root stubs and no-entry-at-all terms via has_prefix_with_root/has_confix/back-formation/clipping", file=sys.stderr)


def _patch_foreign_root_stubs(words, eng):
    """
    Second coverage extension (Joe, 2026-07-24, same "total coverage" push).
    A handful of remaining stubs cite their root DIRECTLY as a foreign-
    language term via has_prefix_with_root/has_confix/has_affix/has_prefix
    (e.g. a word whose recorded root/confix/affix is a Latin term, not an
    English one) rather than through an English intermediate word that
    `_patch_root_stubs` could chase. That foreign-language citation IS real
    ancestry evidence -- the same shape as a `derived_from` edge, just
    tagged with a different reltype in this corner of the data -- so it's
    treated as one here: a direct, single-hop chain to that language's
    bucket. Checked directly against the raw data: a small population (a
    dozen or so words), but zero guessing -- the language name is explicitly
    recorded, not inferred.
    """
    # Priority order, not just a set: has_prefix_with_root/has_confix name the
    # actual root/stem (the meaningful part), while has_affix/has_prefix can
    # also fire on a bare prefix fragment (e.g. "ex-") sharing a term with a
    # more informative has_prefix_with_root row for the same word -- process
    # the more specific relations first so a real stem wins over a bare
    # prefix when both exist (found via "expostulate": has_prefix "ex" and
    # has_prefix_with_root "postulo" both present; "postulo" is the real
    # root). Bucket answer (the only correctness-critical part) is identical
    # either way when both point to the same language -- this only affects
    # which specific root_term gets displayed.
    # Widened 2026-07-24 alongside _patch_root_stubs, same reasoning: a term
    # with a directly-cited foreign root but ZERO ancestry data of its own
    # (no entry in `words` at all, not just a has_root stub) deserves the
    # same treatment -- the pointer's trustworthiness never depended on
    # whether the term also happened to have a bare has_root edge.
    rel_priority = ["has_prefix_with_root", "has_confix", "has_affix", "has_prefix"]
    patched = 0
    for rel in rel_priority:
        rows = eng[eng["reltype"] == rel]
        for row in rows.itertuples():
            entry = words.get(row.term)
            if entry is not None and entry.get("prox_kind") != "root":
                continue  # already resolved (real entry, or patched by a higher-priority relation)
            lang = row.related_lang
            if pd.isna(lang) or lang == "English" or lang in NON_DONOR_LANGS:
                continue
            b = bucket_for_name(lang)
            out = {"p": b, "d": b, "chain": [b], "prox_kind": "derived",
                   "root_lang": lang, "root_pie": False, "chain_langs": [lang]}
            term_spelling = row.related_term if pd.notna(row.related_term) else None
            if term_spelling:
                out["root_term"] = term_spelling
            words[row.term] = out
            patched += 1
    print(f"  patched {patched} bare-root stubs via a directly-cited foreign root", file=sys.stderr)


def _extract_auto_compounds(words, eng):
    """
    Third coverage extension (same push). A handful of remaining stubs are
    recorded as a `compound_of`/`blend_of` two-or-more real English words
    (e.g. a coined word built by combining two independent existing words)
    rather than a single inheritable root. Unlike `_patch_root_stubs` (one
    root -> inherit its whole story), a compound genuinely has more than one
    origin, so this does NOT synthesize one fake merged chain -- it reuses
    the EXISTING compound-display mechanism (compounds.py's COMPOUND_SPLITS,
    ChainResolver's compound fallback in resolver.py) already built for
    exactly this shape (known issue #11). Removes the word's stub entry
    entirely (so it falls through to the normal "no chain" path) and returns
    {term: [part, part, ...]} for ChainResolver to consult as a SEPARATE,
    clearly-labeled auto-derived source -- kept apart from compounds.py's
    736 hand-verified entries (this data comes straight from Wiktionary's
    own compound_of/blend_of tag, not hand research, so it wasn't
    individually eyeballed the way each compounds.py entry was). Only fires
    when EVERY named part already resolves to a real, non-stub entry -- no
    guessing at a split the data doesn't assert.
    """
    rels = {"compound_of", "blend_of"}
    rows = eng[eng["reltype"].isin(rels)]

    def resolves(term):
        if not isinstance(term, str):
            return False
        key = term.split("#")[0].strip()
        # EXACT case only -- same "went"/"Went" collision risk as
        # _patch_root_stubs, see its comment for the full reasoning. Also
        # requires the part to be a reliable (non-collision-shaped) source,
        # same _is_reliable_root filter and reasoning as _patch_root_stubs --
        # a compound whose part is itself a hub-shaped collision (e.g. some
        # part happens to be "on" or "person") shouldn't silently inherit
        # that part's questionable chain into the compound's own display.
        e = words.get(key)
        return e is not None and e.get("prox_kind") != "root" and _is_reliable_root(key, e)

    # Widened 2026-07-24 (Joe: "mindset" showed Unknown -- its raw data is a
    # clean compound_of split into "mind"+"set", both already resolving, but
    # "mindset" itself has NO ancestry edge of any kind, so it never got a
    # stub entry for the original version of this function to find). Same
    # reasoning as _patch_root_stubs's widening -- the split's
    # trustworthiness never depended on the term also having a stub. `del`
    # is now guarded since a no-entry term was never a key in `words`.
    auto_compounds = {}
    for term, group in rows.groupby("term"):
        entry = words.get(term)
        if entry is not None and entry.get("prox_kind") != "root":
            continue  # already resolved to a real (non-stub) entry
        parts = [rt.split("#")[0].strip() for rt in group["related_term"] if pd.notna(rt)]
        if len(parts) < 2 or not all(resolves(p) for p in parts):
            continue
        auto_compounds[term] = parts
        if term in words:
            del words[term]
    print(f"  extracted {len(auto_compounds)} auto-detected compound/blend splits", file=sys.stderr)
    return auto_compounds


def main():
    print("reading parquet...", file=sys.stderr)
    df = pd.read_parquet(PARQUET_PATH)
    eng = df[df["lang"] == "English"]
    print(f"  {len(eng)} English-source rows, {eng['term_id'].nunique()} unique terms", file=sys.stderr)

    words = {}
    n_terms = 0
    for term_id, group in eng.groupby("term_id", sort=False):
        n_terms += 1
        term = group["term"].iloc[0]
        res = resolve_term(list(group.itertuples()))
        if res is not None:
            words[term] = res

    print(f"  {n_terms} terms processed, {len(words)} resolved", file=sys.stderr)

    # Apply corrections.py BEFORE the inheritance patches below, added
    # 2026-07-24 alongside widening those patches to no-entry terms. A
    # corrected hub word (e.g. "tag") needs to already be right by the time
    # _patch_root_stubs runs, so a derived word pointing at it (e.g. "detag")
    # inherits the CORRECTED story, not the raw (possibly collision-shaped)
    # one -- previously WORD_CORRECTIONS was only applied later, at resolver.py
    # runtime, which is too late for this bulk inheritance to see it. Also
    # still applied at runtime as before (harmless, idempotent) so a direct
    # lookup of a corrected word is never silently dependent on convert_wikt.py
    # having been re-run most recently.
    words.update(WORD_CORRECTIONS)

    _patch_root_stubs(words, eng)
    _patch_foreign_root_stubs(words, eng)
    auto_compounds = _extract_auto_compounds(words, eng)

    buckets = dict(NAME_TO_BUCKET)
    out = {"buckets": buckets, "words": words, "order": BUCKET_ORDER,
           "auto_compounds": auto_compounds}
    with open("wikt_words.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"  processed {n_terms} terms, wrote {len(words)} resolved English words", file=sys.stderr)


if __name__ == "__main__":
    main()
