"""
Shared chain-assembly logic: turn a normalized ancestry sequence into the
resolver's {"p","d","chain","prox_kind","root_lang","root_pie",...} shape.

Extracted 2026-07-24 from convert_wikt.py's `resolve_term()` while building
convert_wiktextract.py (the wiktextract/kaikki.org prototype -- see
FUTURE_FEATURES_AND_RESOURCES.md / GITHUB_RESOURCES.md), so both build
pipelines share this one, already-debugged implementation of some genuinely
subtle rules (the PIE-terminal invariant, root_lang/root_term/root_pie
derivation, the native-stage-vs-foreign-branch distinction) instead of two
copies quietly drifting apart -- per this project's standing composability
rule (see .claude/skills/etymology-skill-audit).

Deliberately source-agnostic: callers do their OWN source-specific parsing
(etymology-db's group_tag/parent_tag graph walk for convert_wikt.py,
wiktextract's etymology_templates list for convert_wiktextract.py) and hand
this function an already-normalized ancestry sequence. See `build_chain`'s
docstring for the exact input shape.
"""
from typing import List, Optional, Tuple

from buckets_wikt import bucket_for_name


def build_chain(
    foreign: List[Tuple[str, str, Optional[str]]],
    roots: List[Tuple[str, Optional[str]]],
    has_english_stage: bool,
    english_stage_seq: List[List[Optional[str]]],
) -> Optional[dict]:
    """
    foreign: ordered list of (prox_kind, lang_name, term) for every non-
        English-stage ancestry edge, proximate -> deep. `prox_kind` is
        ALREADY normalized by the caller to one of "borrowed"/"derived"/
        "inherited" (convert_wikt.py maps its raw reltype strings via
        `_prox_kind_for`; convert_wiktextract.py maps its template names
        directly) -- this function has no source-specific vocabulary.
    roots: ordered list of (lang_name, term) for root-only citations (no
        prox_kind of their own -- e.g. a bare `has_root`/wiktextract `root`
        pointer with no real derived/borrowed/inherited edge backing it).
    has_english_stage: whether the word's own ancestry touches a Middle/Old
        English (or Scots) stage at all.
    english_stage_seq: ordered [lang_name, term] pairs for those English-
        stage citations specifically (may be empty even if
        has_english_stage is True, when a stage was detected but no
        specific term was recorded).

    Returns the same dict shape resolve_term() has always produced, or None
    if there's no ancestry evidence at all (word has no chain, no root, and
    never touched an English stage either).
    """
    if not foreign and not roots:
        if has_english_stage:
            out = {"p": "Germanic", "d": "Germanic", "chain": [], "prox_kind": "core"}
            if english_stage_seq:
                out["native_stages"] = english_stage_seq
            return out
        return None

    chain: List[str] = []
    chain_langs: List[str] = []
    chain_terms: List[Optional[str]] = []
    prox_kind: Optional[str] = None

    if has_english_stage and (not foreign or foreign[0][0] == "inherited"):
        chain.append("Germanic")
        if english_stage_seq:
            chain_langs.append(english_stage_seq[0][0])
            chain_terms.append(english_stage_seq[0][1])
        else:
            chain_langs.append("Germanic")
            chain_terms.append(None)
        prox_kind = "inherited"
    for kind, lang, term in foreign:
        b = bucket_for_name(lang)
        if prox_kind is None:
            prox_kind = kind
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

    # PIE-terminal invariant (see convert_wikt.py's original comment for the
    # full "with"/"low" bug history this fixes): PIE, the deepest
    # reconstructable ancestor, can never be shallower than an attested
    # language -- if it appears anywhere but last, move it to the true end.
    if "PIE" in chain and chain[-1] != "PIE":
        triples = list(zip(chain, chain_langs, chain_terms))
        non_pie = [t for t in triples if t[0] != "PIE"]
        pie = [t for t in triples if t[0] == "PIE"]
        chain = [t[0] for t in non_pie] + [t[0] for t in pie]
        chain_langs = [t[1] for t in non_pie] + [t[1] for t in pie]
        chain_terms = [t[2] for t in non_pie] + [t[2] for t in pie]

    if chain[-1] == "PIE":
        if len(chain_langs) >= 2:
            root_lang, root_term = chain_langs[-2], chain_terms[-2]
            root_pie = True
        else:
            root_lang, root_term = chain_langs[-1], chain_terms[-1]
            root_pie = False
    else:
        root_lang, root_term = chain_langs[-1], chain_terms[-1]
        root_pie = False

    out = {"p": chain[0], "d": chain[-1], "chain": chain, "prox_kind": prox_kind,
           "root_lang": root_lang, "root_pie": root_pie}
    if root_term:
        out["root_term"] = root_term
    if any(cl != b for cl, b in zip(chain_langs, chain)):
        out["chain_langs"] = chain_langs
    if english_stage_seq:
        out["native_stages"] = english_stage_seq
    return out
