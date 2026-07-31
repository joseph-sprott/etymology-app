"""
Standalone regression check for the Etymology Analyzer -- no test framework
dependency (pytest isn't installed and this project has never used one), just
plain assertions with a PASS/FAIL summary. Run directly:

    python test_regression.py

Exits 0 if everything passes, 1 if anything fails -- usable as a real CI gate
later even without adding pytest. Covers:
  - the historical verified-word suite (CLAUDE.md "Current state")
  - known multi-sense-collision corrections (die/bull/and/low/... /tag/auto)
  - the compound-display feature (upside/purebred/.../mindset/meltdown)
  - the case-fallback guard (found/went/ran -- issue #12 and its 2026-07-24
    widening)
  - the bare-root-stub guard (issue #14 -- vitamin/critical)
  - the three-mode README example (checkmate)
  - tree/analyzer consistency (issue #16 -- a word fixed via inheritance or
    stemming, not raw tree data, must still produce a real tree)

Run this after ANY regeneration (see the etymology-regen skill) before
trusting the result, and after ANY corrections.py/compounds.py/
tree_corrections.py edit even without a full regen (corrections/compounds
apply immediately at resolver load time).
"""
import sys

from resolver import shared_resolver

# The SAME instance app.py and word_trees.py use, so the tree checks
# below compare like with like instead of poking a module global.
RESOLVER = shared_resolver()

failures = []
passed = 0


def check(label, condition):
    global passed
    if condition:
        print(f"  PASS  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}")
        failures.append(label)


def bucket(word, mode="direct"):
    return RESOLVER.resolve(word).view(mode).bucket


print("=== Historical verified-word suite (Direct Source) ===")
# "trust" changed from "Norse" to "Germanic" 2026-07-24 (the wiktextract
# migration): the old etymology-db snapshot recorded trust as borrowed from
# Old Norse "traust", but live Wiktionary confirms that theory has since
# been revised -- the root vocalism is incompatible, so "trust" is now
# considered a native reflex of an unattested Old English "*trust", with Old
# Norse only a cognate (a related sibling word, not the source). A genuine
# scholarly correction the migration surfaced, not a regression.
HISTORICAL = {
    "skill": "Norse", "table": "French", "sky": "Norse", "egg": "Norse",
    "trust": "Germanic", "anger": "Norse", "knife": "Norse", "they": "Norse",
    "them": "Norse", "law": "Norse", "beef": "French", "government": "French",
    "justice": "French", "army": "French", "the": "Germanic",
}
for word, expected in HISTORICAL.items():
    got = bucket(word)
    check(f"{word} -> {expected} (got {got})", got == expected)

print()
print("=== Multi-sense-collision corrections (must still hold) ===")
COLLISIONS = {
    "die": "Norse", "bull": "Norse", "and": "Germanic", "low": "Norse",
    "with": "Germanic", "back": "Germanic", "seen": "Germanic",
    "tag": "Germanic", "auto": "Greek",
}
for word, expected in COLLISIONS.items():
    got = bucket(word)
    check(f"{word} -> {expected} (got {got})", got == expected)

print()
print("=== Case-fallback guard (issue #12, widened 2026-07-24) ===")
CASE_FALLBACK = {"found": "French", "went": "Germanic", "ran": "Norse"}
for word, expected in CASE_FALLBACK.items():
    got = bucket(word)
    check(f"{word} -> {expected}, not a coincidental capitalized homograph (got {got})",
          got == expected)

print()
print("=== Bare-root-stub guard (issue #14) ===")
# "vitamin" USED to demonstrate this (no sibling word the resolver's stem-
# retry could reach) but no longer does: wiktextract's own data (added
# 2026-07-24) has a real, if uncertain, Latin "vita" derivation for it
# (`{{uder|en|la|vīta}}`) that etymology-db simply lacked -- Direct Source
# now correctly shows Latin, a genuine coverage improvement, not a
# regression of this guard. "movie" replaces it as the pure-stub example:
# its only chain-relevant template is a bare `root` (PIE) pointer, no real
# inh/der/bor edge of its own, and no suffix/stem retry reaches a sibling
# word either -- confirmed still Unknown for Direct Source after the
# wiktextract migration.
# "critical" is DIFFERENT despite the same root-stub shape in the data: the
# resolver's own "-al" suffix rule (added for "professional") independently
# retries "critic", which has a real, non-stub entry -- so "critical"
# legitimately resolving to French is a correct side effect, not a
# regression of the guard. Keeping both cases here, with different
# expectations, so a future change can't quietly break either shape.
d = RESOLVER.resolve("movie").view("direct")
r = RESOLVER.resolve("movie").view("root")
check("movie: Direct Source stays Unknown (no fabricated immediate donor)",
      d.bucket == "Unknown")
check(f"movie: Deepest Root still shows real PIE citation (got {r.bucket})",
      r.bucket != "Unknown")

d = RESOLVER.resolve("critical").view("direct")
r = RESOLVER.resolve("critical").view("root")
check(f"critical: Direct Source resolves via the 'critic' stem retry, not the bare stub (got {d.bucket})",
      d.bucket == "French")
check(f"critical: Deepest Root still shows PIE (got {r.bucket})",
      r.bucket != "Unknown")

print()
print("=== Donor evidence: only transmitting edges may answer (2026-07-27) ===")
# Two bugs with one cause: the resolver decided a donor by "any foreign node
# that isn't a root", and claimed native descent whenever that found nothing.
# So a CALQUE became a donor (`peacemaker` read Greek -- it is peace + maker,
# merely modelled on Koine Greek), and ABSENCE of evidence became a positive
# Germanic claim (`movie`, whose recorded formation is only the suffix `ie`,
# and `zoophysiologist`, which is Greek). Both directions are checked here,
# plus the controls that must NOT move -- the danger of the fix is over-reach.

# A calque transmits no material and must never be the answer.
d = RESOLVER.resolve("peacemaker").view("direct")
check(f"peacemaker: not the Koine Greek phrase it calques (got {d.bucket})",
      d.bucket != "Greek")
check("peacemaker: shows its peace + maker split instead", bool(d.parts))
d = RESOLVER.resolve("blackshirt").view("direct")
check(f"blackshirt: not the Italian phrase it calques (got {d.bucket})",
      d.bucket != "Romance (other)" and d.bucket != "Latin")

# A native-core claim needs an `inherited` edge, not merely the absence of a
# foreign one. `zoophysiologist`'s parts are absent from the database, so the
# walk dead-ends in English -- which is not evidence that it IS English.
d = RESOLVER.resolve("zoophysiologist").view("direct")
check(f"zoophysiologist: no fabricated Germanic claim (got {d.bucket})",
      d.bucket != "Germanic")

# Controls. Real native descent must survive untouched -- these carry genuine
# inherited edges through the English stages.
for word in ("trust", "free", "brother", "the", "walk", "back"):
    d = RESOLVER.resolve(word).view("direct")
    check(f"{word}: real native inheritance still reads Germanic (got {d.bucket})",
          d.bucket == "Germanic")

# And `formed_from` pointing at a FOREIGN part is real transmission, not a
# calque: `sthenolagnia` genuinely is built out of Greek. Excluding it along
# with calques would have lost true ancestry.
d = RESOLVER.resolve("sthenolagnia").view("direct")
check(f"sthenolagnia: foreign formation still counts as ancestry (got {d.bucket})",
      d.bucket == "Greek")

print()
print("=== Compound-display feature (must still split) ===")
COMPOUNDS = ["upside", "purebred", "outdoorsman", "mindset", "meltdown"]
for word in COMPOUNDS:
    view = RESOLVER.resolve(word).view("direct")
    check(f"{word} splits into parts", bool(view.parts))

print()
print("=== Three-mode README example (checkmate) ===")
res = RESOLVER.resolve("checkmate")
MODE_EXPECT = {"direct": "French", "influence": "Semitic", "root": "Indo-Iranian"}
for mode, expected in MODE_EXPECT.items():
    got = res.view(mode).bucket
    check(f"checkmate {mode} -> {expected} (got {got})", got == expected)

print()
print("=== Tree/analyzer consistency (issue #16) ===")
try:
    import word_trees as app_module
    TREE_WORDS = ["professional", "consistency", "mindset", "ran"]
    for word in TREE_WORDS:
        tree = app_module.resolve_tree(word)
        check(f"{word} has a real tree (not 'no recorded etymology data')", tree is not None)
except ImportError as e:
    check(f"could not import word_trees.py to check tree consistency ({e})", False)

print()
print("=== Issue #17: 347-paragraph coverage scan fixes (2026-07-24) ===")
IRREGULAR_FORMS_FIXED = ["hidden", "meant", "got", "gotten", "woke", "swung",
                         "spun", "stung", "sped", "snuck", "laid", "heard"]
for word in IRREGULAR_FORMS_FIXED:
    got = bucket(word)
    check(f"{word} -> resolved, not Unknown (got {got})", got != "Unknown")

FV_PLURALS = {"wolves": "wolf", "knives": "knife", "shelves": "shelf"}
for plural, singular in FV_PLURALS.items():
    pb, sb = bucket(plural), bucket(singular)
    check(f"{plural} -> matches {singular}'s bucket (got {pb} vs {sb})",
          pb == sb and pb != "Unknown")

UN_PREFIX_BRIDGE = {"unheard": "hear", "unexplained": "explain", "unusual": "usual",
                    "unfamiliar": "familiar"}
for word, root in UN_PREFIX_BRIDGE.items():
    wb, rb = bucket(word), bucket(root)
    check(f"{word} -> matches {root}'s bucket via inheritance bridge (got {wb} vs {rb})",
          wb == rb and wb != "Unknown")
# Note: "unusual matching usual's bucket" above already proves it isn't
# wrongly inheriting from the bound morpheme "un-" (which resolves to a
# totally different, unrelated chain -- see convert_wikt.py's bound-
# morpheme filter, issue #17) -- a separate assertion here would be redundant.

HAND_VERIFIED = {
    "previous": "Latin", "mom": "Germanic", "package": "Germanic",
    "incident": "French", "expert": "French", "metaphor": "French",
    "adult": "French", "puppy": "French", "presence": "French",
    "familiar": "Latin", "unless": "Germanic",
}
for word, expected in HAND_VERIFIED.items():
    got = bucket(word)
    check(f"{word} -> {expected} (got {got})", got == expected)

print()
print("=== Hand-verified compounds.py must never be silently bypassed ===")
# Found 2026-07-24 auditing ALL 743 compounds.py entries after widening
# convert_wikt.py's inheritance patches: 147 entries started resolving via
# an auto-inherited chain instead of their hand-verified split (worse,
# less-complete answers, e.g. "mountainside" losing "side" entirely), and 3
# (bathrobe/bathtub/bluebird) regressed all the way to Unknown via an
# unrelated pre-existing bug (EtyResolver citing an ISO code with no bucket
# mapping, chain=["Unknown"], which used to block the compound fallback
# from ever being reached). Both fixed generally in resolver.py -- this
# checks the ENTIRE compounds.py table, not just a sample, since the whole
# point is that this must hold for all 743, not just the ones spot-checked
# today.
# "threadbare" is a deliberate, known exception as of 2026-07-24 (the
# wiktextract migration), not a bug: wiktextract's own combined etymology
# section for the compound documents BOTH "thread" and "bare"'s real native
# Germanic/PIE ancestry directly (prox_kind == "inherited", not a stub or an
# inherited_from patch) -- genuinely resolving on its own with correct data,
# which is exactly the case compounds.py's own docstring says should win
# over the hand-verified split ("never override a word that resolves on its
# own"). Both parts land in the same Germanic bucket anyway, so the split
# would add little here. Excluded from this check by name, not by loosening
# the check itself -- a NEW word landing in this set unexpectedly should
# still fail loudly and get investigated, not silently pass.
_KNOWN_OWN_DATA_EXCEPTIONS = {"threadbare"}
from compounds import COMPOUND_SPLITS
bypassed = [w for w in COMPOUND_SPLITS
            if w not in _KNOWN_OWN_DATA_EXCEPTIONS and not RESOLVER.resolve(w).view("direct").parts]
check(f"all {len(COMPOUND_SPLITS) - len(_KNOWN_OWN_DATA_EXCEPTIONS)} non-exception compounds.py entries "
      f"still show their split (0 bypassed, got {len(bypassed)}: {bypassed[:10]})",
      len(bypassed) == 0)

NEW_COMPOUNDS = ["mountainside", "faraway", "foothill", "foothills",
                  "downside", "downsides", "earlobe", "earlobes"]
for word in NEW_COMPOUNDS:
    view = RESOLVER.resolve(word).view("direct")
    check(f"{word} splits into parts", bool(view.parts))

print()
print("=== A derivational suffix is not a component word (2026-07-26) ===")
# Found by testing localhost after the etymology.db rework: the dump's
# formation templates list affixes alongside real components, so `beautiful`
# split into `beauty` + `ful` and `darkness` into `dark` + `ness`. Each half
# carries half the word's weight in the bar chart, so `ful` (which resolves to
# nothing) pushed weight into Unknown, and `ness` -- a real word, a headland --
# pushed it into an unrelated word's bucket. 36% of the derived words sampled
# carried an explicitly hyphenated affix part.
#
# The guard is "no parts", not a bucket, because the bucket was never wrong:
# every one of these words resolved to the right family the whole time, which
# is exactly why nothing caught it.
for word in ["beautiful", "darkness", "government", "quickly", "happiness",
             "careful", "abacination"]:
    view = RESOLVER.resolve(word).view("direct")
    parts = [p.word for p in (view.parts or [])]
    check(f"{word} is one word, not stem + affix (got {parts})", not view.parts)

# The other half of the same rule: a real two-word compound must KEEP its
# split. `craftsman` is recorded `crafts` + `-man` -- hyphenated, but `man` is
# a word, and two earlier versions of the affix rule broke 263 and then 134 of
# these before this one held.
for word in ["craftsman", "businesswoman", "basketball", "mountainside"]:
    view = RESOLVER.resolve(word).view("direct")
    check(f"{word} still splits into component words", bool(view.parts))

print()
print("=== Prefixes are affixes too (issue #19 closed at build time, 2026-07-30) ===")
# `_BOUND_SUFFIXES` only ever covered FINAL-position endings, so ~92,000
# {{prefix}} templates were never handled: `rewrite` was counted half Latin
# through `re` and `disagree` half Norse through `dis`. `ety_node.is_affix`
# now carries Wiktionary's own positional statement, so these stop splitting.
for word in ["unhappy", "undo", "rewrite", "disagree", "preview"]:
    view = RESOLVER.resolve(word).view("direct")
    parts = [p.word for p in (view.parts or [])]
    check(f"{word} is one word, not prefix + stem (got {parts})", not view.parts)

# A `+` in a template's first argument is a DIRECTIVE, not a language code
# (`{{surf|+deverbal|en|let}}`), and reading it positionally made the language
# code itself a component: `late` displayed as "en + let" (Joe, 2026-07-30).
# Word Search was right while the analyzer was wrong, because the two derive
# components separately -- issue #16 (one shared source) in miniature.
for word in ["late", "biology"]:
    view = RESOLVER.resolve(word).view("direct")
    parts = [p.word for p in (view.parts or [])]
    check(f"{word}: no part is a bare language code (got {parts})",
          not any(p in ("en", "grc", "la", "enm", "ang") for p in parts))

# A hand-verified split may override the affix filter ONLY where the word
# genuinely has a formation. `muskrat` does not: it is borrowed from Algonquian
# and "musk + rat" is folk etymology, so the table must not beat a real donor.
check("muskrat stays Algonquian rather than being split by compounds.py",
      RESOLVER.resolve("muskrat").view("direct").bucket == "Indigenous American")
check("overactive DOES take its hand-verified split (a real formation)",
      bool(RESOLVER.resolve("overactive").view("direct").parts))

print()
print("=== Deepest Root must not credit a borrower with PIE descent (2026-07-25) ===")
# Joe: "mile results as having a PIE root when I can't find one on wiktionary."
# The PIE root turned out to be real (Wiktionary tags it via a root template,
# not prose: Latin mille <- PIE *sem- "one"). The actual bug was WHICH language
# got credited. convert_wiktextract.py sorted chain steps by convert_wikt.py's
# _DEPTH_HINT tiers, but those describe depth WITHIN one lineage ("Old" stage
# = 12, Classical = 14, proto = 15+) -- so comparing Latin (14) against
# Proto-West Germanic (15) is meaningless, they're different branches. That
# sort REVERSED Wiktionary's own correct order (mile: ME -> OE -> PWG ->
# Latin), making PWG look deepest, so build_chain rendered "Proto-West
# Germanic (from PIE)" -- false, since Wiktionary states *miliju is "a
# borrowing of Latin milia" and so inherits nothing from PIE. Fixed by
# restricting the sort to single-family chains (buckets_wikt.family_for_name).
BORROWED_ROOTS = {"mile": "Latin", "street": "Latin", "Friday": "Latin"}
for word, expect in BORROWED_ROOTS.items():
    v = RESOLVER.resolve(word).view("root")
    check(f"{word}: Deepest Root credits {expect}, not the Germanic borrower "
          f"(got {v.depth_lang!r})",
          bool(v.depth_lang) and v.depth_lang.startswith(expect))

# Control: genuinely-inherited chains must KEEP their attribution. These are
# single-family, so the depth sort still applies and is still correct.
INHERITED_ROOTS = {"sky": "Proto-Germanic", "free": "Middle English"}
for word, expect in INHERITED_ROOTS.items():
    v = RESOLVER.resolve(word).view("root")
    check(f"{word}: still credits {expect} (got {v.depth_lang!r})",
          bool(v.depth_lang) and v.depth_lang.startswith(expect))

# Control: cross-family chains whose recorded order was ALREADY correct must
# be left alone -- the earlier version of this sort broke "checkmate" exactly
# this way, and "table" is the case the sort was originally added for.
check("table: direct source still French (single-family sort still applies)",
      RESOLVER.resolve("table").view("direct").bucket == "French")
check("checkmate: root still Indo-Iranian (cross-family order untouched)",
      RESOLVER.resolve("checkmate").view("root").bucket == "Indo-Iranian")

print()
print("=== Tree and analyzer must agree (2026-07-25, the 'intrude' bug) ===")
# Joe: "intrude doesn't show that it's from Latin when using word search. Why
# are the two tools not agreeing?" The 2026-07-24 wiktextract migration gave
# the ANALYZER a new top-priority backend, but etymology_trees.json is still
# built from the etymology-db parquet alone -- so 1,736 words had a real
# analyzer chain while Word Search showed only a bare PIE root pointer. Fixed
# in app.resolve_tree by refusing to let a bare-root-stub tree short-circuit
# the resolver-backed paths. This guards the whole class, not just "intrude":
# if the analyzer names a specific donor language, the tree must mention it.
try:
    import word_trees as app_module

    def _langs_in(tree):
        out = set()
        def walk(n):
            out.add(n["lang"])
            for c in n["children"]:
                walk(c)
        for b in (tree or {}).get("branches") or []:
            walk(b)
        return out

    AGREEMENT_WORDS = ["intrude", "species", "computer", "growth", "investment"]
    for word in AGREEMENT_WORDS:
        res = RESOLVER.resolve(word)
        tree = app_module.resolve_tree(word)
        donor = (res.chain[0].specific_lang or res.chain[0].lang) if res.chain else None
        langs = _langs_in(tree)
        check(f"{word}: tree mentions the analyzer's donor {donor!r} (tree has {sorted(langs)[:4]})",
              bool(donor) and donor in langs)

    # The stub must not win over a genuinely richer stored tree either --
    # guard the opposite direction so the fix can't over-apply.
    #
    # UPDATED 2026-07-26: this used to require `served == stored`, byte for
    # byte. Since the rework the tree is built from etymology.db rather than
    # replayed from etymology_trees.json, so identity is the wrong test -- it
    # asserts WHICH FILE the answer came from, not that the answer is good.
    # The intent was "don't serve something poorer than what we had", so that
    # is what it now checks: every language the stored tree showed must still
    # appear. Losing one is a real regression; adding some is the point.
    for word in ["sky", "coffee", "sandal"]:
        stored = app_module._lookup_tree_direct(word)
        served = app_module.resolve_tree(word)
        lost = _langs_in(stored) - _langs_in(served) if stored else set()
        check(f"{word}: served tree keeps every language the stored one had"
              f"{(' -- lost ' + str(sorted(lost))) if lost else ''}",
              stored is not None and served is not None and not lost)
except ImportError as e:
    check(f"could not import word_trees.py to check tree/analyzer agreement ({e})", False)

print()
print("=== Tree: no duplicate orphan branches (2026-07-24) ===")
# Joe: "sometimes there's a random PIE path that doesn't link to the main
# link to the modern word... just feels incomplete." Root cause (verified
# against the live data, not guessed): etymology-db records some ancestor
# citations as EXTRA parentless rows duplicating a term the tree already
# shows, and build_tree() -- correctly, per its own no-merging policy --
# turns every parentless row into its own top-level branch. dedupe_branches
# (build_etymology_trees.py) now drops a branch ONLY when it's a single
# childless node exactly restating a (lang, term) already displayed.
#
# Both directions are checked below, because the FAILURE MODE OF THE FIX
# would be over-deletion: a genuinely-new-but-stranded citation must
# survive, since dropping it would silently lose real information.
try:
    import word_trees as app_module

    def _pairs_in(node, out):
        out.append((node["lang"], node["term"]))
        for c in node["children"]:
            _pairs_in(c, out)

    def _size(node):
        return 1 + sum(_size(c) for c in node["children"])

    # (a) No tree may show a bare orphan restating something already shown.
    DEDUP_WORDS = ["sky", "sandal", "fruit"]
    for word in DEDUP_WORDS:
        tree = app_module.resolve_tree(word)
        if tree is None:
            check(f"{word}: tree exists to check for duplicate orphans", False)
            continue
        branches = tree["branches"]
        elsewhere = []
        for b in branches:
            if _size(b) > 1:
                _pairs_in(b, elsewhere)
        orphans = [(b["lang"], b["term"]) for b in branches if _size(b) == 1]
        dupes = [p for p in orphans if p in elsewhere or orphans.count(p) > 1]
        check(f"{word}: no duplicate orphan branch (got {dupes})", not dupes)

    # (b) Genuinely-new stranded citations must NOT have been deleted --
    # these are deeper/different terms than anything their main chain
    # reaches (religion's PIE *h₂leg-, coffee's Arabic triliteral root
    # ق ه ي vs. the surface form قَهْوَة already in its chain).
    #
    # UPDATED 2026-07-26: this used to require the citation appear as a
    # single-node TOP-LEVEL branch, because that is the only shape the old
    # builder could give a parentless row. Connecting those to the word is
    # precisely what the rework does, so the old assertion now fails for the
    # best possible reason. What must still hold -- and what the check was
    # really for -- is that the citation is not DELETED. So: it must appear
    # somewhere in the tree, stranded or connected.
    PRESERVED = {"religion": "Proto-Indo-European", "coffee": "Arabic"}
    for word, expect_lang in PRESERVED.items():
        tree = app_module.resolve_tree(word)
        if tree is None:
            check(f"{word}: tree exists to check preservation", False)
            continue
        langs = _langs_in(tree)
        check(f"{word}: {expect_lang} citation still present somewhere "
              f"(tree has {sorted(langs)[:5]})", expect_lang in langs)

    # (c) The real, substantive chains must be untouched by the dedup.
    # Counting BRANCHES is a shape assertion the rework deliberately changed
    # (accounts that used to hang side by side are now connected where the
    # data supports it). `sandal`'s three competing origin stories must still
    # be distinguishable, so count the distinct deep sources instead.
    sandal = app_module.resolve_tree("sandal")
    sandal_langs = _langs_in(sandal) if sandal else set()
    check(f"sandal: all three origin accounts still represented "
          f"(has {sorted(sandal_langs)[:6]})",
          {"Ancient Greek", "Arabic"} <= sandal_langs
          and any(l.endswith("Latin") for l in sandal_langs))
except ImportError as e:
    check(f"could not import word_trees.py to check tree dedup ({e})", False)

print()
print("=== Descendant trees (2026-07-26) ===")
# The downward view: what came FROM a root, rather than where a word came from.
# Skipped rather than failed when the tables aren't built -- build_descendants.py
# needs its own extracts and a fresh clone won't have them.
try:
    import descendants as _desc
    _bro = _desc.full_tree("brother")
    if _bro is None:
        print("  SKIP  descendant tables not built (run build_descendants.py)")
    else:
        check("brother's descendant tree climbs to the PIE root",
              _bro["root_lang"] == "Proto-Indo-European"
              and _bro["root_term"].startswith("b"))

        def _flat(node, out):
            out.append((node.get("lang"), node.get("raw_term") or node.get("term")))
            for kid in node.get("children") or ():
                _flat(kid, out)
            return out

        rows = _flat(_bro["tree"], [])
        langs = {l for l, _ in rows}
        # The splice: PIE lists Proto-Germanic and stops ("see there for further
        # descendants"). If the join breaks, the tree ends at the branch heads
        # and everything below Proto-Germanic silently vanishes.
        check("splice reaches modern English through Proto-Germanic",
              {"Proto-Germanic", "Proto-West Germanic", "Old English",
               "Middle English", "English"} <= langs)
        def _any_match(node):
            return bool(node.get("match")) or any(
                _any_match(k) for k in node.get("children") or ())
        # The view opens on the searched word by following `match`/`on_path`.
        # Without the mark it opens on a folded root and the user sees nothing.
        check("the searched word is marked in the tree", _any_match(_bro["tree"]))

        # Variant merging. `night`'s raw tree is 3,402 nodes but only 97
        # distinct forms -- the same leaves repeated under 180 spelling
        # variants of their ancestors. If merging regresses, this explodes.
        _night = _desc.full_tree("night")
        check(f"night's tree stays deduplicated "
              f"(got {_night['total_nodes']} nodes, raw is 3,402)",
              _night["total_nodes"] < 300)

        # A merge must never invent a parent-child link: every merged group
        # had structurally identical subtrees, so no (lang, term) pair should
        # appear twice at the same depth under one parent.
        def _dupe_children(node):
            kids = node.get("children") or []
            seen = [(k.get("lang"), k.get("raw_term")) for k in kids]
            if len(seen) != len(set(seen)):
                return True
            return any(_dupe_children(k) for k in kids)
        check("no duplicate siblings survive the merge",
              not _dupe_children(_bro["tree"]))
except ImportError as e:
    check(f"could not import descendants.py ({e})", False)

print()
total = passed + len(failures)
print(f"{passed}/{total} checks passed")
if failures:
    print("\nFAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
sys.exit(0)
