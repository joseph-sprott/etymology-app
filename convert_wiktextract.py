"""
Convert kaikki.org's English wiktextract JSONL extract into the resolver's
word->chain JSON -- same output shape convert_wikt.py produces (resolver.py's
WiktextractResolver reads it the same way WiktionaryResolver reads
wikt_words.json), built from a much richer source. See
FUTURE_FEATURES_AND_RESOURCES.md / GITHUB_RESOURCES.md for the source
research, and the prototype-phase coverage numbers (CLAUDE.md) that justified
building this.

Parses each English-language entry's STRUCTURED `etymology_templates` list
(not the human-rendered `etymology_text` prose, and not the special `etymon`/
`ety` multi-part-phrase templates -- those encode things like "goodbye" =
"God be with you" + "good"[influence] as a nested tree structure, complex
enough to warrant their own follow-up pass, not phase 1) into an ordered
ancestry sequence, then hands that to the SAME etymology_chain.build_chain()
convert_wikt.py uses -- both pipelines share one already-debugged
implementation of the subtle chain-assembly rules (PIE-terminal invariant,
root_lang/root_term/root_pie derivation) instead of two copies drifting
apart, per this project's composability rule.

Template vocabulary (Wiktionary's Module:etymology/templates convention,
confirmed against real entries 2026-07-24):
  - inh/uinh      -- inherited (unbroken line of descent), "u" = uncertain
  - der/uder      -- derived (related, not unbroken inheritance)
  - bor/ubor/bor+ -- borrowed
  - root          -- deepest reconstructed/attested root pointer ONLY, not
                      itself a chain step -- same "bare stub" shape
                      convert_wikt.py already handles via prox_kind == "root"
  - cog/ucog/noncog/doublet -- NOT ancestry (a cognate is a sibling, not an
    ancestor -- same hedge-relation exclusion as etymology-db's
    etymologically_related_to/cognate_of, known issue #14's shape). Ignored
    entirely, not parsed.
  - suffix/prefix/confix/af/affix/blend/clipping/compound/univ -- word-
    FORMATION templates (cite an English base word/pieces, not a foreign
    donor). Phase 1 does NOT follow these to inherit a cited base word's
    story (unlike convert_wikt.py's _patch_root_stubs for has_affix/
    has_confix). Left as documented future work -- NOT silently equivalent
    to doing nothing, though: the EXISTING resolver-layer stemmer
    (resolver.py's _stem_candidates, already strips "-er"/"-tion"/etc.)
    recovers many of these for free once the cited base word resolves via
    this same data (e.g. "teenager" -> suffix template citing "teenage" ->
    already reached by the ordinary "-er" stemming retry with zero new code).

A headword can have multiple JSONL lines (one per part-of-speech and/or
Wiktionary's own etymology_number -- distinct numbered "Etymology N"
sections for different senses). This first pass does NOT attempt
sense-splitting (same documented limitation as convert_wikt.py, known issue
#14): the FIRST entry encountered with real ancestry evidence wins; file
order follows Wiktionary's own page order, first sense first, generally the
primary/most-common sense.

    python convert_wiktextract.py [--limit N]
"""
import argparse
import json
import sys

sys.path.insert(0, ".")
from etymology_chain import build_chain
from wiktextract_langs import name_for_wikt_code, bucket_for_wikt_code, EXCLUDED_CODES
from buckets_wikt import family_for_name
# Reused, not reinvented (composability): the shared depth-hint table, tuned
# to break ties between untied donor languages by real chronological tier
# (modern/Middle/Old/Classical/proto, per family).
#
# Imported from `linguistics`, its actual home, rather than through
# `convert_wikt` -- that indirection meant this build script loaded the OTHER
# build script (and pandas) for one dict. Same table, same values.
import linguistics
from linguistics import DEPTH_HINT as _DEPTH_HINT
from wiktextract_dump import stream_english_entries

JSONL_PATH = r"C:\Users\Josep\Desktop\Etymology Project\wiktextract_data\kaikki.org-dictionary-English.jsonl"
OUT_PATH = "wiktextract_words.json"

_INHERIT_TEMPLATES = {"inh", "uinh"}
_DERIVE_TEMPLATES = {"der", "uder"}
_BORROW_TEMPLATES = {"bor", "ubor", "bor+"}
# Compound multi-donor templates (e.g. inh+bor, naming two donor languages in
# one template call) exist but weren't seen with meaningful frequency in the
# empirical language-code scan -- phase 1 treats them as a single edge using
# their first lang/term pair (args "2"/"3"), the conservative approximation:
# undercounting a rare multi-hop is safer than mis-parsing one.
_COMPOUND_DONOR_TEMPLATES = {"inh+bor", "der+bor"}
_ROOT_TEMPLATE = "root"

# Owned by `linguistics`, which documents WHY Scots is in this set here but
# not in `ENGLISH_STAGE_NAMES` -- a real, preserved inconsistency rather
# than an accident. Identical values; this just stops them drifting.
_ENGLISH_STAGE_CODES = linguistics.ENGLISH_STAGE_WIKT_CODES


def _kind_for_template(name: str):
    if name in _INHERIT_TEMPLATES:
        return "inherited"
    if name in _DERIVE_TEMPLATES:
        return "derived"
    if name in _BORROW_TEMPLATES or name in _COMPOUND_DONOR_TEMPLATES:
        return "borrowed"
    return None


def parse_entry(entry: dict):
    """
    One wiktextract JSONL entry (already filtered to lang == "English") ->
    the resolve_term()-shaped dict (see etymology_chain.build_chain), or
    None if this entry has no usable ancestry evidence at all.
    """
    templates = entry.get("etymology_templates") or []
    foreign = []            # (prox_kind, lang_name, term), proximate -> deep
    roots = []               # (lang_name, term)
    has_english_stage = False
    english_stage_seq = []
    seen_stage_names = set()

    for t in templates:
        name = t.get("name")
        args = t.get("args") or {}
        code = args.get("2")
        term = args.get("3")
        if not code or code in EXCLUDED_CODES:
            continue
        # A bare "-" term is Wiktionary's own placeholder for "uncertain,
        # no specific form recorded" -- found 2026-07-24 via test_regression.py
        # ("table" showed Germanic instead of French): its raw data has
        # `{{uder|en|gem|-}}` (an uncertain, term-less Proto-Germanic
        # citation) sitting BEFORE the real `{{der|en|la|tabula}}`/
        # `{{der|en|fro|table}}` citations, and file order is otherwise
        # trusted as depth order (see module docstring) -- so this
        # placeholder was winning the "first real donor" slot over the
        # genuine, specific citations that follow it. Not informative
        # evidence of anything; skipped outright rather than trusted.
        if term == "-":
            continue
        kind = _kind_for_template(name)
        if kind is not None:
            if code in _ENGLISH_STAGE_CODES:
                has_english_stage = True
                lang_name = name_for_wikt_code(code) or "English"
                if lang_name not in seen_stage_names:
                    seen_stage_names.add(lang_name)
                    english_stage_seq.append([lang_name, term])
                continue
            # A donor template (inh/der/bor) citing PIE DIRECTLY -- found
            # 2026-07-24 via test_regression.py ("trust" showed PIE for
            # Direct Source, which should be impossible, same shape as the
            # pre-existing "computer"/"vitamin" bare-root-stub bug this
            # project has fixed before -- see resolver.py's
            # Resolution.view() prox_kind=="root" handling). Wiktionary's
            # own template usage sometimes reaches PIE through an ordinary
            # der/inh template (e.g. "trust"'s `{{der|en|ine-pro|*deru-}}`)
            # rather than the dedicated `root` template idiom -- same
            # meaning either way (PIE can never be a genuine immediate
            # donor to modern English), so route it to `roots` regardless
            # of which template name introduced it.
            if bucket_for_wikt_code(code) == "PIE":
                lang_name = name_for_wikt_code(code)
                if lang_name is not None:
                    roots.append((lang_name, term))
                continue
            lang_name = name_for_wikt_code(code)
            if lang_name is not None:
                # An unmapped code is skipped entirely here, not just
                # bucketed "Other" -- see name_for_wikt_code's docstring
                # (2026-07-24): fabricating a chain step with no real name
                # is worse than omitting it, and the code-frequency scan
                # already covers the codes that matter in practice.
                foreign.append((kind, lang_name, term))
        elif name == _ROOT_TEMPLATE and code not in _ENGLISH_STAGE_CODES:
            lang_name = name_for_wikt_code(code)
            if lang_name is not None:
                roots.append((lang_name, term))

    # File order is USUALLY shallow->deep (verified against "coffee"/
    # "government"/"checkmate"), but not always -- found 2026-07-24 via
    # test_regression.py: "table"'s raw data lists `{{der|en|la|tabula}}`
    # BEFORE `{{der|en|fro|table}}`, even though French is the real, more
    # recent direct donor and Latin the deeper one. A stable sort by
    # convert_wikt.py's own depth-hint tiers fixes that -- but only under
    # TWO conditions, each learned by breaking something:
    #
    # 1. Every language must have a known tier. `_depth_hint` defaults an
    #    UNLISTED language to 10 ("modern"), which silently outranked "Old
    #    French"'s real tier-12 entry once Arabic/Classical Persian (both
    #    unlisted) were treated as shallower than French -- breaking
    #    "checkmate", whose file order was already correct.
    #
    # 2. Every language must be in the SAME FAMILY. Added 2026-07-25 after
    #    Joe asked why "mile" claimed a PIE root: those tiers describe depth
    #    WITHIN a lineage ("Old" stage = 12, Classical = 14, proto = 15+), so
    #    comparing Latin (14) against Proto-West Germanic (15) is meaningless
    #    -- they're different branches, not different depths. Wiktionary's own
    #    order for "mile" is Middle English -> Old English -> Proto-West
    #    Germanic -> Latin, i.e. correct; this sort was REVERSING the last two
    #    and making Proto-West Germanic look like the deepest step. That in
    #    turn made `build_chain` credit "Proto-West Germanic (from PIE)" when
    #    PWG *miliju is, per Wiktionary, "a borrowing of Latin milia" -- it
    #    doesn't inherit from PIE at all. Same damage in street/Friday/
    #    Saturday/Sunday/Monday. Restricting the sort to single-family chains
    #    fixes those while KEEPING the "table" fix (Latin and Old French are
    #    both Italic, so their tiers really are comparable).
    families = {family_for_name(lang) for _, lang, _ in foreign}
    families.discard(None)
    if len(families) <= 1 and all(lang in _DEPTH_HINT for _, lang, _ in foreign):
        foreign.sort(key=lambda item: _DEPTH_HINT[item[1]])

    return build_chain(foreign, roots, has_english_stage, english_stage_seq)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                     help="stop after this many English entries (for a quick partial-run sanity check)")
    ap.add_argument("--jsonl", default=JSONL_PATH)
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    words = {}
    total_english_entries = 0
    # `--limit` is honoured by the reader itself, which counts YIELDED English
    # entries -- the same thing the old inline `break` counted.
    for line_no, entry, word in stream_english_entries(args.jsonl, limit=args.limit):
        total_english_entries += 1
        if word not in words:
            result = parse_entry(entry)
            if result is not None:
                words[word] = result
        if line_no % 1_000_000 == 0:
            print(f"...{line_no:,} lines scanned, {len(words):,} words resolved", file=sys.stderr)

    print(f"{total_english_entries:,} English entries scanned, "
          f"{len(words):,} distinct headwords with a resolvable chain.", file=sys.stderr)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"words": words}, f, ensure_ascii=False)
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
