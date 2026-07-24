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

    if not foreign and not roots:
        if has_english_stage:
            out = {"p": "Germanic", "d": "Germanic", "chain": [], "prox_kind": "core"}
            if english_stage_seq:
                out["native_stages"] = english_stage_seq
            return out
        return None

    chain = []
    chain_langs = []  # parallel to `chain`: the specific language name behind each bucket
    chain_terms = []  # parallel to `chain_langs`: the specific spelling recorded at that step
    prox_kind = None
    # Widened 2026-07-24 from the original `not foreign` condition. Found
    # while wiring native_stages through to the resolver: `foreign` is NOT
    # actually empty for most native words with a deep recorded lineage
    # (e.g. "the"/"walk"/"what") -- their Proto-West-Germanic/Proto-Germanic
    # steps are recorded as ordinary `inherited_from` edges in the SAME
    # native group as their Middle English/Old English citations, so they
    # land in `foreign` (only English-stage NAMES are filtered out, not
    # Proto-Germanic-family ones) and used to silently claim chain_langs[0]
    # ahead of the nearer, more relevant stage name. Checking foreign[0]'s
    # reltype distinguishes this (continuing the SAME native inheritance
    # thread) from a genuine foreign borrowing like "boss"'s Dutch/French
    # edges (reltype "borrowed_from", never inherited_from) -- only the
    # inherited-from case gets the native-stage prepend; a real borrowing
    # still correctly falls through to the `foreign` loop below untouched.
    if has_english_stage and (not foreign or foreign[0][0] in INHERIT_RELS):
        # Purely native inheritance (no foreign borrowing/derivation step at
        # all) but a deeper root is recorded beyond English (e.g. PIE) --
        # native core, just deepening past Germanic instead of stopping
        # there. Without this, a bare has_root pointer (e.g. "could"'s
        # PIE *gneh3-) would wipe out the native-Germanic base entirely and
        # report the word as if PIE were its *donor*, which it isn't.
        chain.append("Germanic")
        # Nearest recorded native stage name (e.g. "Middle English"), not
        # just the generic "Germanic" bucket repeated -- added 2026-07-24,
        # same fix as the native_stages field above. Falls back to the old
        # generic placeholder only if no stage was actually recorded (rare).
        if english_stage_seq:
            chain_langs.append(english_stage_seq[0][0])
            chain_terms.append(english_stage_seq[0][1])
        else:
            chain_langs.append("Germanic")
            chain_terms.append(None)
        prox_kind = "inherited"
    for rt, lang, term in foreign:
        b = bucket_for_name(lang)
        if prox_kind is None:
            prox_kind = _prox_kind_for(rt)
        if b not in chain:
            chain.append(b)
            chain_langs.append(lang)
            chain_terms.append(term)
    for lang, term in roots:
        b = bucket_for_name(lang)
        if b not in chain:
            chain.append(b)
            chain_langs.append(lang)
            chain_terms.append(term)
    if not chain:
        if has_english_stage:
            return {"p": "Germanic", "d": "Germanic", "chain": [], "prox_kind": "core"}
        return None
    if prox_kind is None:
        prox_kind = "root"

    # PIE-terminal invariant, added 2026-07-23 (Joe: "with"/"low" showed an
    # ATTESTED language -- Old Norse -- as the deepest point even though the
    # word's own recorded data ALSO cites PIE, which is chronologically
    # impossible: PIE, the deepest reconstructable ancestor in this entire
    # system, can never be shallower than an attested language. Root cause is
    # the same open problem as the "and" writeup (known issue #6) -- multiple
    # senses sharing one term_id sometimes sort incoherently across each
    # other -- and that's still not reliably fixable in general. But THIS
    # specific consequence always holds regardless of which branch/sense
    # produced the data, so it's enforced directly: if the "PIE" bucket
    # appears anywhere but last, move it to the true end.
    #
    # REGRESSION caught and fixed same day: a first version of this moved
    # EVERY proto-language-tagged bucket to the end, not just PIE. That broke
    # "back", whose real native chain legitimately STARTS at a Proto-West-
    # Germanic-tagged edge (Middle English -> Old English -> Proto-West
    # Germanic -> Proto-Germanic -> PIE, one coherent lineage) -- demoting
    # that whole bucket let an unrelated `borrowed_from French bac` edge
    # (a different, rarer sense sharing the same term_id) jump into the
    # Direct Source position instead. Scoping this to PIE specifically -- the
    # one bucket that should truly never be non-terminal -- fixes low/with
    # without touching legitimately-non-terminal proto-tagged buckets like
    # Proto-Germanic/Proto-West-Germanic.
    if "PIE" in chain and chain[-1] != "PIE":
        triples = list(zip(chain, chain_langs, chain_terms))
        non_pie = [t for t in triples if t[0] != "PIE"]
        pie = [t for t in triples if t[0] == "PIE"]
        chain = [t[0] for t in non_pie] + [t[0] for t in pie]
        chain_langs = [t[1] for t in non_pie] + [t[1] for t in pie]
        chain_terms = [t[2] for t in non_pie] + [t[2] for t in pie]

    # `root_lang`/`root_term`/`root_pie`: the specific deepest attested-or-
    # reconstructed name (and its exact recorded spelling) reached, plus
    # whether that name itself goes on to connect to PIE. Added 2026-07-23
    # for the "Deepest Root" mode redesign -- Joe wants level 3 to name the
    # actual reconstructed form reached, not just the family bucket, e.g.
    # "Proto-Germanic (from PIE)" instead of just "PIE". `root_term` (added
    # same day, for Piece 2) is the exact spelling at that step, e.g.
    # "*handuz" -- needed to look up the right Wiktionary Reconstruction
    # page (fetch_reconstructions.py) when `root_pie` is False and root_lang
    # is a proto-language, since the language name alone isn't enough to
    # find the specific page. This only surfaces names ALREADY explicitly
    # recorded in a word's own chain (e.g. `sky` cites "Proto-Germanic" and
    # "Proto-Indo-European" as separate real edges) -- it does not infer an
    # uncited intermediate step just because it's linguistically likely
    # (that would be guessing, not verifying). Words without an explicitly-
    # recorded proto-language step (e.g. "could", whose has_root PIE pointer
    # has no intermediate name in its own data) fall back to the generic
    # bucket name ("Germanic") with no root_term.
    if chain[-1] == "PIE":
        if len(chain_langs) >= 2:
            root_lang, root_term = chain_langs[-2], chain_terms[-2]
            root_pie = True
        else:
            root_lang, root_term = chain_langs[-1], chain_terms[-1]  # chain is PIE alone
            root_pie = False
    else:
        root_lang, root_term = chain_langs[-1], chain_terms[-1]
        root_pie = False

    out = {"p": chain[0], "d": chain[-1], "chain": chain, "prox_kind": prox_kind,
           "root_lang": root_lang, "root_pie": root_pie}
    if root_term:
        out["root_term"] = root_term
    # `chain_langs`: the specific language name behind EVERY step of `chain`,
    # not just the deepest (root_lang already covered that). Added 2026-07-23
    # for the bar-graph drill-down feature (Joe: clicking "Germanic" should
    # expand into per-language bars -- Dutch, German, native-inherited, etc.
    # -- not just repeat the bucket name). Only stored when at least one
    # entry differs from its own bucket name (i.e. carries real information);
    # a native-core word's synthetic "Germanic" placeholder entry isn't
    # worth persisting on its own.
    if any(cl != b for cl, b in zip(chain_langs, chain)):
        out["chain_langs"] = chain_langs
    if english_stage_seq:
        out["native_stages"] = english_stage_seq
    return out


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
    """
    root_rows = eng[eng["reltype"].isin(_ROOT_POINTER_RELS)]
    candidates = {}
    for row in root_rows.itertuples():
        if row.term not in words:
            continue
        if pd.isna(row.related_lang) or row.related_lang != "English" or pd.isna(row.related_term):
            continue
        candidates.setdefault(row.term, []).append(row.related_term)

    patched = 0
    changed = True
    while changed:
        changed = False
        for term, roots in candidates.items():
            entry = words.get(term)
            if entry is None or entry.get("prox_kind") != "root":
                continue  # not a stub (already patched, or never was one)
            for root_term in roots:
                root_key = root_term.split("#")[0].strip()
                root_entry = (words.get(root_key) or words.get(root_key.lower())
                              or words.get(root_key.capitalize()))
                if root_entry is None or root_entry.get("prox_kind") == "root":
                    continue  # root itself unresolved or still a stub
                words[term] = dict(root_entry)
                patched += 1
                changed = True
                break
    print(f"  patched {patched} bare-root stubs via has_prefix_with_root/has_confix/back-formation/clipping", file=sys.stderr)


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
    rel_priority = ["has_prefix_with_root", "has_confix", "has_affix", "has_prefix"]
    patched = 0
    for rel in rel_priority:
        rows = eng[eng["reltype"] == rel]
        for row in rows.itertuples():
            entry = words.get(row.term)
            if entry is None or entry.get("prox_kind") != "root":
                continue  # not a stub, or already patched by a higher-priority relation
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
        e = words.get(key) or words.get(key.lower()) or words.get(key.capitalize())
        return e is not None and e.get("prox_kind") != "root"

    auto_compounds = {}
    for term, group in rows.groupby("term"):
        entry = words.get(term)
        if entry is None or entry.get("prox_kind") != "root":
            continue
        parts = [rt.split("#")[0].strip() for rt in group["related_term"] if pd.notna(rt)]
        if len(parts) < 2 or not all(resolves(p) for p in parts):
            continue
        auto_compounds[term] = parts
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
