"""
Word -> renderable etymology tree: lookup, fallback, glosses, links, layout.

Lifted out of `app.py` in the 2026-07-27 audit, unchanged. It was ~490 lines
of the 1,700-line web module, and it is not web code: nothing here touches a
request, a response or a template. It is the answer to "show me where this
word came from", which is a question the Flask view merely asks.

THE PUBLIC SURFACE IS SIX FUNCTIONS:

    resolve_tree(word)      the tree, with every fallback applied
    build_diagram(tree)     that tree laid out as positioned SVG boxes
    node_slug(node)         palette slot for one node
    root_gloss(term)        what a reconstructed root MEANS, when known
    is_reconstructed(term)  is this a starred proto-form
    wiktionary_url(term)    where a reader can go and check us

Everything else is private. That boundary is the point of the move: a future
feature wanting a tree imports these six and cannot accidentally depend on a
detail of how the fallback chain happens to be wired today.

ON THE RESOLVER: this module uses `resolver.shared_resolver()`, the one
process-wide instance, rather than building its own. Building its own is how
a feature ends up disagreeing with the analyzer about a word -- known issue
#16, which this project has already paid for once.
"""
import json
import os
from urllib.parse import quote

import etymology_db
import linguistics
from buckets_wikt import bucket_for_name
from palette import PROTO_SLUGS, bucket_slug
from linguistics import depth_hint as _depth_hint
from corrections import WORD_CORRECTIONS
from resolver import shared_resolver
from tree_model import TreeNode
import sys

# The shared word database, when it has been built. The TREE and the ANALYZER
# read the same rows: `shared_resolver()`'s DbResolver backend and
# `_tree_from_db()` below both go through `etymology_db`, the only module that
# opens the file. None means "not built yet" and every path degrades to the
# older per-feature stores.
# ETYMOLOGY_DB=0 disables it for BOTH paths, which is what
# scripts/compare_db.py relies on to measure the legacy stack honestly.
if os.environ.get("ETYMOLOGY_DB") == "0":
    _DB = None
else:
    try:
        _DB = etymology_db.get()
    except Exception as _db_exc:      # not built, or mid-rebuild
        print(f"etymology.db unavailable ({_db_exc}); using legacy stores",
              file=sys.stderr)
        _DB = None

# Etymology-tree feature, 2026-07-23 (Joe: "I really like the etymology tree
# that Wiktionary provides"). Loaded from etymology_trees.json
# (build_etymology_trees.py) -- a separate file from wikt_words.json because
# the bucket/chain pipeline deliberately FLATTENS a word's graph into one
# answer, while a real tree needs every branch preserved. See that build
# script's docstring for the full design (and the two things tried and
# reverted: naive has_root placement, and merging top-level branches -- both
# produced actively wrong trees, not just untidy ones, so this shows the raw
# recorded structure rather than guessing which fragments belong together).
def _load_trees():
    try:
        with open("etymology_trees.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


TREES = _load_trees()


def _lookup_tree_direct(word):
    """Exact-case only: lowercase first (the common case), then as-typed.

    Deliberately does NOT also try word.capitalize() here, unlike the rest
    of this file's other case-fallback lookups -- found 2026-07-24 (Joe:
    "ran" showed an unrelated Japanese loanword in the tree, even though the
    analyzer correctly showed Norse). Root cause: this function used to try
    capitalize() unconditionally, landing on "Ran"'s real-but-unrelated tree
    before resolve_tree() below ever got a chance to check whether the
    resolver would actually trust that match -- the EXACT same coincidental-
    homograph risk `Resolution.case_fallback` now protects against in
    resolver.py (issue #12's "went"/"Went" bug, widened today for "ran"), but
    this second, independent case-fallback implementation didn't know about
    that protection at all. Rather than re-teach this function the same
    fragile judgment call, resolve_tree() now defers capitalize() to its own
    final fallback, AFTER checking what the resolver itself actually trusts
    (inherited_from/compound_parts) -- the same "one real source of truth,
    not two implementations that can quietly drift" principle as the rest of
    today's fix.
    """
    return TREES.get(word.lower()) or TREES.get(word)


# A stored tree whose every branch is a bare, childless `has_root` pointer
# isn't really a lineage -- it's the tree-side equivalent of the resolver's
# `prox_kind == "root"` stub (see Resolution.prox_kind), and the same rule
# applies: never let a stub outrank a real answer.
_ROOT_ONLY_RELS = {"has_root"}


def _is_bare_root_tree(tree):
    """
    Does this tree actually say anything, or is it a stub wearing branches?

    The rule lives on `TreeNode.is_stub`; this wrapper keeps the name the rest
    of this module already uses. See that method for why a childless bound
    affix counts for no more than a bare root pointer (`movie`).
    """
    node = TreeNode.from_dict(tree)
    return node is None or node.is_stub()


# etymology_db's relation names -> the reltype vocabulary this module and the
# stored trees already speak, so the renderer and _is_bare_root_tree need no
# changes to accept a database-backed tree.
_DB_RELTYPE = {"inherited": "inherited_from", "borrowed": "borrowed_from",
               "derived": "derived_from", "calque": "calqued_from",
               "root": "has_root", "formed_from": "compound_of"}

# The exact key set `_tree_from_db` has always emitted. Pinned so `TreeNode`
# reproduces it byte-for-byte -- the cached `tree_json` column and the golden
# master were both written against this shape.
_DB_NODE_KEYS = frozenset({"lang", "term", "reltype", "is_affix",
                           "certainty", "children"})


def _wants_expanding(n, depth, seen):
    """
    Is this node a COMPONENT whose own history lives on another row?

    Expanding it is what keeps the tree and the analyzer telling the same
    story: `lineage()` already follows `pipe` to Latin for `bagpipe`, so a tree
    stopping at "English pipe" would show a Germanic-looking word beside a bar
    chart saying Latin -- the split-brain the database rework removed.

    "Already expanded" means having a DONOR child; a bare root pointer does
    not count. `computer`'s `compute` carries a PIE root, which made it look
    expanded and hid its French ancestry.
    """
    if n.rel != "formed_from" or not n.term:
        return False
    if depth >= 4 or n.term.lower() in seen:
        return False
    return not any(c.rel != "root" for c in n.children)


def _is_redundant_orphan(drawn, placed):
    """
    A childless branch whose node is already drawn elsewhere in the diagram.

    `sandal` keeps a bare `Arabic صَنْدَل` etymology alongside a fuller account
    containing the same term mid-chain; drawing both puts a redundant orphan
    box beside the real lineage. A branch WITH children is never skipped --
    that would drop a whole competing account.
    """
    return not drawn.children and (drawn.lang, drawn.term) in placed


def _tree_from_db(word):
    """
    The word's tree straight from etymology.db, or None.

    THIS is what closes the gap the rework exists for. Every other path in
    resolve_tree() derives the tree from a DIFFERENT store than the analyzer
    reads, which is how `intrude` came to show a Latin donor in one feature
    and not the other. Here the tree and the analyzer's chain are two readings
    of ONE `Etymology` object: the analyzer walks it with spine()/lineage(),
    the renderer walks the same nodes. They cannot disagree, because there is
    no second derivation left to disagree with.
    """
    if _DB is None:
        return None
    entry = _DB.entry(word)
    if entry is None or not entry.primary:
        return None

    def node(n, depth, seen):
        children = [node(c, depth, seen) for c in n.children]
        if _wants_expanding(n, depth, seen):
            sub = _DB.entry(n.term)
            if sub is not None and sub.primary:
                expanded = [node(c, depth + 1, seen | {n.term.lower()})
                            for c in sub.primary.head.children]
                if expanded:
                    # Keep the root alongside the newly-found ancestry.
                    children = expanded + [c for c in children
                                            if c.reltype == "has_root"]
        return TreeNode(
            lang=n.lang, term=n.term,
            reltype=_DB_RELTYPE.get(n.rel, n.rel),
            # Wiktionary's own affix marking, so `is_stub` can tell a real
            # component from a word ending (issue #19).
            is_affix=bool(getattr(n, "is_affix", False)),
            # Carried through for the timeline work: 'related' renders as a
            # dotted edge and is never counted as descent.
            certainty=n.certainty,
            children=children,
            # This builder always emits the same key set, and the stored
            # `tree_json` cache was written with it.
            _source_keys=_DB_NODE_KEYS)

    # EVERY etymology, not just the primary one. `bow` the weapon and `bow` the
    # bend are different histories, and `sandal` has three competing accounts;
    # rendering only slot 1 silently hid the rest, which the regression suite
    # caught as "sandal: all multi-node branches preserved (3 expected)".
    # Separate etymologies appearing as separate top-level branches is the
    # existing contract of this shape -- the no-floating-nodes rule is about
    # nodes WITHIN one etymology, and each of these is connected to the head.
    head = entry.primary.head
    seen = {(head.term or word).lower()}
    branches = []
    placed = set()          # (lang, term) already drawn somewhere

    def record(n):
        for descendant in n.walk():
            placed.add((descendant.lang, descendant.term))

    for ety in entry.etymologies:
        for child in ety.head.children:
            drawn = node(child, 0, seen)
            if _is_redundant_orphan(drawn, placed):
                continue
            record(drawn)
            branches.append(drawn)
    if not branches:
        return None
    return TreeNode(lang=head.lang, term=head.term or word, is_root=True,
                    children=branches).to_dict()


def _tree_from_chain(word, res, stub=None):
    """
    Build a nested lineage tree from the resolver's OWN chain.

    Added 2026-07-25 (Joe: "intrude doesn't show that it's from Latin when
    using word search. Why are the two tools not agreeing?"). Root cause: the
    2026-07-24 wiktextract migration added a new top-priority resolver backend
    for the ANALYZER, but etymology_trees.json is still built by
    build_etymology_trees.py from the etymology-db parquet alone. So for any
    word wiktextract knows better -- 1,736 of them, measured, including
    computer/growth/investment/species -- the analyzer had a real chain while
    Word Search showed only whatever bare PIE root pointer the older data had.
    Two features, two databases: exactly what this project's standing "every
    feature must pool from the same database" rule forbids, and the same
    failure shape as known issue #16.

    Rather than teach the tree builder about wiktextract (a second, parallel
    tree pipeline that could drift from the resolver all over again), this
    reads the answer the shared RESOLVER already computed -- the same
    principle resolve_tree() already applies for inherited_from/compound_parts.

    Terms per step are recovered where available: the discarded stub's own
    nodes supply the deepest reconstructed form (e.g. PIE *trewd-), and
    root_lang/root_term supply the attested one (Latin intrudere). Steps with
    no recorded spelling render as language-only nodes rather than inventing
    a form.
    """
    if not res.chain:
        return None
    terms = {}
    for b in (stub or {}).get("branches") or []:
        if b.get("term") and b.get("lang"):
            terms.setdefault(b["lang"], b["term"])
    if res.root_lang and res.root_term:
        terms.setdefault(res.root_lang, res.root_term)

    langs = []
    for link in res.chain:
        lang = link.specific_lang or link.lang
        if lang and lang not in langs:
            langs.append(lang)
    if not langs:
        return None

    node = None
    for lang in reversed(langs):  # deepest first, nesting outward
        node = {"lang": lang, "term": terms.get(lang), "reltype": "derived_from",
                "children": [node] if node else []}
    return {"lang": "English", "term": word, "branches": [node]}


def resolve_tree(word, _depth=0):
    """
    Word -> tree dict (same {"lang", "term", "branches"} shape TREES itself
    uses), falling back to real resolver data when the word has no raw-data
    tree of its own. Added 2026-07-24 (Joe, all-caps: every feature must
    pool from the SAME database -- there should be no way one feature has
    word info another doesn't). etymology_trees.json is built straight from
    raw ancestry rows with no awareness of compounds.py/auto_compounds, of
    convert_wikt.py's has_prefix_with_root inheritance (issue #15), or of
    resolver.py's own runtime irregular-form/stemming fallback -- so a word
    fixed through ANY of those (mindset, professional, consistency, ...)
    used to show "no recorded etymology data" here despite the analyzer
    having a real answer.

    Rather than re-implementing each of those mechanisms a second time (risking
    a second copy that quietly drifts from what the analyzer actually does),
    this asks RESOLVER -- the exact same instance analyze() uses below -- what
    it actually did, via two general fields on Resolution that exist for
    exactly this purpose:
      - `inherited_from`: the OTHER word whose data actually produced the
        answer, whenever it isn't a direct hit (covers data-layer inheritance
        AND the resolver's own irregular/stemming retry -- see
        Resolution.inherited_from's docstring). Recurses through this
        function again for that word, so a multi-hop chain (a word inherited
        from a word that was itself found via stemming) still resolves.
      - `compound_parts`: unchanged from the original version of this
        function -- builds one synthetic branch per part (a wrapper node
        labeled with the part's own word, children = that part's own real
        branches, found the same recursive way).
      - Last resort: if the resolver has SOME real answer (a chain) but
        neither of the above applies and still no tree was found anywhere
        (e.g. convert_wikt.py's _patch_foreign_root_stubs, a direct foreign-
        root citation with no English intermediate to recurse through),
        synthesize a single-node tree from root_lang/root_term rather than
        showing nothing for a word the analyzer really does have data for.
    Any word the resolver can't really answer (a bare has_root stub, or a
    genuine total miss) correctly still returns None here too -- same honest
    "no data" the analyzer shows for those, not a fabricated tree.

    `_depth` guards against runaway recursion on a pathological cycle (not
    expected in practice, but defensive, matching build_etymology_trees.py's
    own `seen_groups` guard for the same class of risk).
    """
    # The database first: it is the only store the analyzer also reads, so a
    # word it can answer is answered identically in both features. Everything
    # below is the legacy cascade, kept as a gap-filler for words the dump
    # doesn't cover -- it can add coverage, never override.
    from_db = _tree_from_db(word)
    if from_db is not None and not _is_bare_root_tree(from_db):
        return _honour_correction(word, from_db, _depth)

    # A real stored tree still wins outright. A bare-root STUB no longer
    # short-circuits the resolver-backed paths below -- 2026-07-25, the
    # "intrude" bug, where the tree showed PIE while the analyzer said Latin.
    direct = _lookup_tree_direct(word)
    if direct is not None and not _is_bare_root_tree(direct):
        return _honour_correction(word, direct, _depth)
    if _depth > 5:
        return direct

    res = shared_resolver().resolve(word)
    for build in (_tree_via_inherited, _tree_via_parts):
        built = build(word, res, _depth)
        if built is not None:
            return built
    built = _tree_via_resolver_chain(word, res, direct)
    if built is not None:
        return built
    # Nothing better found. Return the thin stored stub if we had one -- it's
    # real (if incomplete) recorded data, and better than claiming no data.
    return direct


def _honour_correction(word, tree, depth):
    """
    Replace a stored tree ONLY when it contradicts a hand-verified correction.

    Issue #16's standing residual, closed 2026-07-31. `resolve_tree` consults
    stored trees before the resolver, so a word fixed in `corrections.py` kept
    rendering the uncorrected tree unless someone ALSO hand-wrote a matching
    entry in the parallel `tree_corrections.py`. Two tables, kept in step by
    hand -- and they HAD drifted: six corrected words rendered a tree
    contradicting their own correction, `photograph` showing Germanic/PIE
    while the analyzer said Greek.

    Contradiction only, never wholesale replacement. A correction's chain is
    bucket names, so substituting it everywhere would flatten the rich nested
    trees `tree_corrections.py` supplies for `die`, `bull`, `and` and `low` --
    real attested spellings replaced by one word like "Germanic". Where the
    stored tree already reaches the corrected bucket, it stays.
    """
    fix = WORD_CORRECTIONS.get(word.lower())
    if fix is None or depth > 5:
        return tree
    wanted = fix.get("p")
    # A correction's chain holds BUCKET names, a tree node holds a LANGUAGE
    # name, so both readings count -- `bucket_for_name("Norse")` does not
    # recognise a bucket as a language.
    for lang in TreeNode.from_dict(tree).languages():
        if lang == wanted or bucket_for_name(lang) == wanted:
            return tree
    # `_synthesized_tree`, NOT `_tree_via_resolver_chain`: that one first tries
    # the word's CAPITALIZED entry, which for `calypso` is Calypso the Greek
    # nymph -- the exact unrelated-homograph collision this correction exists
    # to overrule.
    corrected = _synthesized_tree(word, shared_resolver().resolve(word))
    return corrected if corrected is not None else tree


def _rooted(word, branches):
    """An English-headed tree over these branches, in the wire shape."""
    return TreeNode(lang="English", term=word, is_root=True,
                    children=branches).to_dict()


def _branches_of(tree):
    """The branches of a built tree as TreeNodes, or []."""
    node = TreeNode.from_dict(tree)
    return node.children if node else []


def _tree_via_inherited(word, res, depth):
    """The tree of the OTHER word whose data actually produced this answer."""
    if not res.inherited_from or res.inherited_from == word:
        return None
    inherited = resolve_tree(res.inherited_from, depth + 1)
    if not inherited:
        return None
    return _rooted(word, _branches_of(inherited))


def _tree_via_parts(word, res, depth):
    """One synthetic branch per component, each carrying its own real tree."""
    if not res.compound_parts:
        return None
    branches = [
        TreeNode(lang="English", term=part.word, reltype="compound_of",
                 children=_branches_of(resolve_tree(part.word, depth + 1)))
        for part in res.compound_parts
    ]
    return _rooted(word, branches)


def _tree_via_resolver_chain(word, res, direct):
    """
    Build a tree from the resolver's own chain, for a word with no stored one.

    Three shapes, narrowest first:
      * a word that genuinely only exists CAPITALIZED (`Paris` typed
        lowercase) -- use that entry's full tree. Reached only after `res`
        confirms the resolver itself would trust an answer here, NOT tried
        unconditionally the way `_lookup_tree_direct` once did, which is what
        made `ran` render the Japanese `Ran`.
      * a real non-stub chain -- render the whole thing. This is what fixes
        the "intrude shows PIE but not Latin" class.
      * a bare root stub -- a single flattened node, which is all it has.
    """
    if not res.chain:
        return None
    cap_tree = TREES.get(word.capitalize())
    if cap_tree is not None:
        return cap_tree
    if res.prox_kind != "root":
        built = _tree_from_chain(word, res, direct)
        if built is not None:
            return built
    return _synthesized_tree(word, res)


def _synthesized_tree(word, res):
    """
    A one-node tree naming the deepest form the resolver reached.

    `root_lang` names a specific form where the data has one. A hand-verified
    correction often does not carry one -- its chain is bucket names -- so the
    deepest chain entry is used instead, rather than drawing nothing, which is
    what left `calypso` and `duppy` rendering their uncorrected trees.
    """
    if not res.chain:
        return None
    # The WHOLE chain, nested, not just its deepest step. `obeah` is
    # Caribbean <- African, and drawing only the African end contradicted its
    # own correction, which names Caribbean as the direct donor. A one-step
    # chain renders exactly as it did before.
    steps = [link.specific_lang or link.lang for link in res.chain]
    if res.root_lang and res.root_lang not in steps:
        steps.append(res.root_lang)
    node = None
    for lang in reversed(steps):
        term = res.root_term if (node is None and lang == res.root_lang) else None
        node = TreeNode(lang=lang, term=term, reltype="derived_from",
                        children=[node] if node else [])
    return _rooted(word, [node])


def node_slug(node):
    """Color slot for one tree node, reusing the same bucket->hue mapping
    as the rest of the app (English stages already map to Germanic via
    buckets_wikt.py, no special-casing needed here)."""
    return bucket_slug(bucket_for_name(node["lang"]))


# What a reconstructed root MEANS, for the hover tooltip Joe asked for
# 2026-07-26 ("hover over a PIE root and see what that root means -- gidʰ-
# means kid/goatling/little goat"). Built by build_root_glosses.py from
# Wiktionary's own template arguments; see that module for why the meaning
# can't come from the database (`ety_node.gloss` is empty for all 12,996 root
# nodes) and why it is never inferred from the descendant word.
#
# Missing file is a normal state, not an error: the app runs fine without it
# and simply shows no tooltip, exactly like a word with no definition.
_ROOT_GLOSSES = None
_ROOT_GLOSS_FOLD = None


def _load_root_glosses():
    global _ROOT_GLOSSES, _ROOT_GLOSS_FOLD
    if _ROOT_GLOSSES is not None:
        return
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "root_glosses.json")
    try:
        with open(path, encoding="utf-8") as fh:
            _ROOT_GLOSSES = json.load(fh)
    except Exception as exc:
        print(f"root_glosses.json unavailable ({exc}); root tooltips off",
              file=sys.stderr)
        _ROOT_GLOSSES = {}
    # Citation styles differ over the TRAILING hyphen that marks a bound root
    # (`*gʰaid-` vs `*gʰaid`), so fold that -- and only where the result is
    # unambiguous, since two roots collapsing to one spelling would show a
    # meaning belonging to the other.
    #
    # The LEADING hyphen is never folded. It marks a suffix, which is a
    # different lexical item, not a different way of writing the same one:
    # folding both ends matched Proto-West-Germanic `*frī` ("free") to the
    # suffix `-frī` and captioned the root of `free` as "-free".
    folded = {}
    for key in _ROOT_GLOSSES:
        folded.setdefault(key.rstrip("-").casefold(), []).append(key)
    _ROOT_GLOSS_FOLD = {k: v[0] for k, v in folded.items() if len(v) == 1}


def root_gloss(term):
    """
    The recorded meaning of a reconstructed form, or None.

    Returns the most frequently attested wording plus any alternative wordings
    Wiktionary's own entries use, so the card can show that a reconstruction's
    meaning is a range rather than a single settled definition.
    """
    if not term:
        return None
    _load_root_glosses()
    # Shared with the BUILD side (`build_root_glosses.key_for`) so the two
    # cannot compute different keys -- they used to each hold their own copy
    # of this expression, with the strip order wrong in both.
    key = linguistics.root_key(term)
    rec = _ROOT_GLOSSES.get(key)
    if rec is None:
        alt = _ROOT_GLOSS_FOLD.get(key.rstrip("-").casefold())
        rec = _ROOT_GLOSSES.get(alt) if alt else None
    return rec


def is_reconstructed(term):
    """Wiktionary's own convention: a leading asterisk marks a form that is
    reconstructed rather than attested, and those live under a different
    namespace on the site."""
    return bool(term) and term.startswith("*")


def wiktionary_url(term, lang=None):
    """
    Link to the Wiktionary page for a term (Joe, 2026-07-26 -- "a link to the
    Wiktionary page whenever you look up a word", for spot-checking answers
    against the source).

    Reconstructed forms are not ordinary entries: `*gʰaidos` lives at
    `Reconstruction:Proto-Indo-European/gʰaidos`. Without the language name
    that page cannot be addressed at all, so those link to the site's search
    instead of to a URL that would 404.
    """
    if not term:
        return None
    term = term.strip()
    if is_reconstructed(term):
        form = term.lstrip("*")
        if not lang:
            return ("https://en.wiktionary.org/w/index.php?search="
                    + quote(form))
        return ("https://en.wiktionary.org/wiki/Reconstruction:"
                + quote(lang.replace(" ", "_")) + "/" + quote(form))
    return "https://en.wiktionary.org/wiki/" + quote(term)


# Free-floating tree diagram (task 2026-07-23): Joe wants a "free floating"
# layout like Wiktionary's own tree diagram or the old Google etymology
# panel, not a spreadsheet grid -- but with one specific structural rule he
# clarified: forms from the SAME generation (e.g. every "Old English" stage
# node, across whatever branch they belong to) share one horizontal axis,
# while parent->child depth within a single branch runs vertically. That's
# exactly a "row = generation, column = branch" layout, so that's what this
# computes -- generation is the same _depth_hint tiering already used to
# order branches shallowest-first (see convert_wikt.py), so alignment is
# automatic: two branches that both pass through "Old English" land on the
# same row without any special-casing. Static/auto-computed only (Joe chose
# this over an interactive draggable canvas) -- rendered as plain SVG,
# no JS or charting library needed.
_TIER_ROW_H = 54
_COL_W = 210
_NODE_W = 176
_NODE_H = 40
_PAD = 24


def _diagram_color(lang):
    return "var(--c-%s)" % bucket_slug(bucket_for_name(lang))


def build_diagram(tree):
    """
    Lays out one word's tree (see etymology_trees.json's shape) as a flat
    list of positioned nodes + connecting edges for SVG rendering.

    Cosmetic merge (closes the "two adjacent PIE boxes" look flagged for
    "what" -- diagnosed as legitimate data, not a bug: a reconstructed
    form's OWN has_root citation, e.g. PIE *kʷód's root *kʷ-, both being
    "Proto-Indo-European"): when a node's only child shares its exact `lang`
    and the child is a has_root edge, they're drawn as ONE box with both
    terms stacked, instead of two boxes that look like an accidental repeat.
    """
    if not tree or not tree.get("branches"):
        return None

    raw = []  # (branch_index, raw_depth_hint_tier, lang, term, term2)
    for col, branch in enumerate(tree["branches"]):
        node = branch
        while node is not None:
            children = node.get("children") or []
            merged_term2 = None
            if (len(children) == 1 and children[0]["lang"] == node["lang"]
                    and children[0].get("reltype") == "has_root"):
                merged_term2 = children[0].get("term")
                children = children[0].get("children") or []
            raw.append((col, _depth_hint(node["lang"]), node["lang"], node.get("term"), merged_term2))
            node = children[0] if children else None

    # Compress the (sparse, 0-18) depth-hint tiers actually used in THIS tree
    # down to compact consecutive rows -- a word rarely touches more than
    # 3-5 distinct tiers, so using the raw scale directly would waste most
    # of the diagram's height on empty rows. Order (not spacing) is what
    # carries meaning, so this loses nothing.
    used_tiers = sorted({t for _, t, *_ in raw})
    row_of = {t: i for i, t in enumerate(used_tiers)}
    rows = [(col, row_of[t], lang, term, term2) for col, t, lang, term, term2 in raw]
    max_tier = len(used_tiers) - 1 if used_tiers else 0

    n_cols = len(tree["branches"])
    width = _PAD * 2 + n_cols * _COL_W
    height = _PAD * 2 + (max_tier + 1) * _TIER_ROW_H

    def cx(col):
        return _PAD + col * _COL_W

    def cy(tier):
        return _PAD + tier * _TIER_ROW_H

    nodes = [
        {"x": cx(col), "y": cy(tier), "w": _NODE_W, "h": _NODE_H,
         "lang": lang, "term": term, "term2": term2,
         "color": _diagram_color(lang)}
        for col, tier, lang, term, term2 in rows
    ]
    # Edges: consecutive rows within the same column (branch).
    by_col = {}
    for col, tier, *_ in rows:
        by_col.setdefault(col, []).append(tier)
    edges = []
    for col, tiers in by_col.items():
        tiers = sorted(tiers)
        for a, b in zip(tiers, tiers[1:]):
            x = cx(col) + _NODE_W / 2
            edges.append({"x1": x, "y1": cy(a) + _NODE_H, "x2": x, "y2": cy(b)})

    return {"width": width, "height": height, "nodes": nodes, "edges": edges}



