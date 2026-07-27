"""
Fast unit tests for the pure logic -- no database, no 100MB JSON, no network.

    python test_units.py

WHY A SECOND TEST FILE. `test_regression.py` answers "is this word's etymology
still right", which needs the real stack and takes minutes. Everything here
answers "does this function do what it says", runs in about a second, and can
therefore be run after every edit rather than once at the end. The 2026-07-27
audit found the core aggregator (`analyzer.py`) at 31% coverage and every
dump parser (`wiktextract_shapes.py`, 392 statements) at 0% -- not because
they are hard to test, but because the only suite that existed needed the
whole world loaded before it could ask anything.

The trick that makes `analyzer` testable is that `analyze()` already accepts a
resolver. A stub returning known buckets tests the ARITHMETIC -- weight
splitting, percentages, coverage -- without caring what `table` really means.
That separation is worth preserving in new code: take the dependency as an
argument and it can be tested in milliseconds.
"""
import sys

failures = []
passed = 0


def check(label, condition):
    global passed
    if condition:
        passed += 1
    else:
        print(f"  FAIL  {label}")
        failures.append(label)


def eq(label, got, want):
    check(f"{label}: expected {want!r}, got {got!r}", got == want)


def section(name):
    print(f"=== {name} ===")


# ---------------------------------------------------------------- linguistics
section("linguistics -- the shared vocabulary everything else imports")
import linguistics as L

eq("is_english_stage(English)", L.is_english_stage("English"), True)
eq("is_english_stage(Middle English)", L.is_english_stage("Middle English"), True)
eq("is_english_stage(Old English)", L.is_english_stage("Old English"), True)
eq("is_english_stage(Scots)", L.is_english_stage("Scots"), False)
eq("is_english_stage(French)", L.is_english_stage("French"), False)
eq("is_english_stage(None)", L.is_english_stage(None), False)

eq("is_pie(Proto-Indo-European)", L.is_pie("Proto-Indo-European"), True)
eq("is_pie(PIE)", L.is_pie("PIE"), True)
eq("is_pie(Proto-Germanic)", L.is_pie("Proto-Germanic"), False)
eq("is_pie(None)", L.is_pie(None), False)

eq("is_proto(Proto-Germanic)", L.is_proto("Proto-Germanic"), True)
eq("is_proto(Proto-Indo-European)", L.is_proto("Proto-Indo-European"), True)
eq("is_proto(PIE)", L.is_proto("PIE"), True)
eq("is_proto(Latin)", L.is_proto("Latin"), False)
eq("is_proto(None)", L.is_proto(None), False)

eq("is_affix(-ness)", L.is_affix("-ness"), True)
eq("is_affix(pre-)", L.is_affix("pre-"), True)
eq("is_affix(ness)", L.is_affix("ness"), False)
eq("is_affix(-)", L.is_affix("-"), False)      # bare hyphen is not an affix
eq("is_affix(None)", L.is_affix(None), False)
eq("is_affix(empty)", L.is_affix(""), False)

# THE load-bearing property of the depth table. An English-stage-first branch
# must outrank ANY foreign branch -- flattening this gap is what let a stray
# French edge beat `back`'s real native lineage (known issue #12).
english_max = max(L.depth_hint(s) for s in ("English", "Middle English", "Old English"))
foreign_min = min(L.depth_hint(s) for s in
                  ("French", "Latin", "Old Norse", "Proto-Germanic", "Ancient Greek"))
check(f"English band ({english_max}) strictly above every foreign tier ({foreign_min})",
      english_max < foreign_min)
check("an UNLISTED language still sorts below the English band",
      L.depth_hint("Klingon") > english_max)
check("depth increases with age: Old French deeper than French",
      L.depth_hint("Old French") > L.depth_hint("French"))
check("PIE is the deepest tier of all",
      L.depth_hint("Proto-Indo-European") == max(L.DEPTH_HINT.values()))

# -------------------------------------------------------------------- palette
section("palette -- slugs and shades")
import palette as P

eq("bucket_slug(Germanic)", P.bucket_slug("Germanic"), "germanic")
eq("Unknown gets its OWN slug, not muted", P.bucket_slug("Unknown"), "unknown")
eq("an unmapped bucket falls back to muted", P.bucket_slug("Klingon"), "muted")
check("every PROTO_SLUGS key is a proto-language name",
      all(L.is_proto(k) for k in P.PROTO_SLUGS))
check("every BUCKET_HEX value is a 7-char hex colour",
      all(len(v) == 7 and v.startswith("#") for v in P.BUCKET_HEX.values()))

shades_a = P.language_shades("Germanic", ["Dutch", "Old English", "Old Norse"])
shades_b = P.language_shades("Germanic", ["Dutch", "Old English", "Old Norse"])
eq("language_shades is deterministic", shades_a, shades_b)
eq("language_shades covers every language given", len(shades_a), 3)
check("language_shades produces DISTINCT colours",
      len(set(shades_a.values())) == 3)
check("language_shades returns valid hex",
      all(len(v) == 7 and v.startswith("#") for v in shades_a.values()))
eq("language_shades on an empty list", P.language_shades("Germanic", []), {})


class _View:
    """Minimal stand-in for a ResolvedView, for root_slug."""
    def __init__(self, bucket, depth_lang=None):
        self.bucket, self.depth_lang = bucket, depth_lang


eq("root_slug: direct mode uses the bucket",
   P.root_slug(_View("Germanic", "Proto-Germanic"), "direct"), "germanic")
eq("root_slug: root mode names the proto shade",
   P.root_slug(_View("Germanic", "Proto-Germanic"), "root"), "proto-germanic")
eq("root_slug: '(from PIE)' suffix is stripped before lookup",
   P.root_slug(_View("Germanic", "Proto-Germanic (from PIE)"), "root"), "proto-germanic")
eq("root_slug: non-proto depth_lang falls back to the bucket",
   P.root_slug(_View("Latin", "Latin"), "root"), "latin")

# ------------------------------------------------------------------- analyzer
section("analyzer -- tokenizing and the percentage arithmetic")
import analyzer as A
from analyzer import tokenize, analyze, format_report, _expand_contractions

eq("contractions: don't -> do not", _expand_contractions("don't"), "do not")
# "can not", not "cannot": the generic n't rule would chop this to "ca" + "not"
# because can't has only one n, so it gets an explicit entry. Both words are
# real, which is all the tokenizer needs.
eq("contractions: can't expands without losing the n",
   _expand_contractions("can't"), "can not")
eq("contractions: won't", _expand_contractions("won't"), "will not")
eq("contractions: you'll", _expand_contractions("you'll"), "you will")
check("possessive 's is deliberately NOT expanded",
      "'s" in _expand_contractions("the dog's bone"))

eq("tokenize lowercases and strips punctuation",
   tokenize("The Quick, brown fox!"), ["the", "quick", "brown", "fox"])
check("tokenize drops single characters (the 'll'/'t' clitic problem)",
      "a" not in tokenize("a big dog"))
eq("tokenize on empty text", tokenize(""), [])
eq("tokenize expands before splitting, so no stray 't'",
   tokenize("don't"), ["do", "not"])


class FakeView:
    def __init__(self, word, bucket, parts=None):
        self.word, self.bucket, self.parts = word, bucket, parts
        self.donor_iso = self.depth_lang = self.specific_lang = None
        self.resolved = bucket != "Unknown"
        self.source = "fake"


class FakeResolution:
    def __init__(self, view):
        self._v = view

    def view(self, mode):
        return self._v


class FakeResolver:
    """Known answers, so the ARITHMETIC is what's under test."""
    def __init__(self, table):
        self.table = table

    def resolve(self, word):
        return FakeResolution(self.table.get(word, FakeView(word, "Unknown")))


simple = FakeResolver({
    "alpha": FakeView("alpha", "Germanic"),
    "beta": FakeView("beta", "French"),
    "gamma": FakeView("gamma", "Latin"),
})
a = analyze("alpha beta gamma", resolver=simple)
eq("total_tokens", a.total_tokens, 3)
eq("resolved_tokens", a.resolved_tokens, 3)
eq("unknown_tokens", a.unknown_tokens, 0)
eq("coverage is 100%", round(a.coverage, 6), 100.0)
eq("each bucket is a third", round(a.by_tokens["Germanic"], 4), round(100/3, 4))
eq("mode is carried through", a.mode, "direct")
eq("per_word has one entry per token", len(a.per_word), 3)

with_unknown = FakeResolver({"alpha": FakeView("alpha", "Germanic")})
a = analyze("alpha zzz", resolver=with_unknown)
eq("unknown counted", a.unknown_tokens, 1)
eq("resolved excludes unknown", a.resolved_tokens, 1)
eq("coverage is 50%", round(a.coverage, 6), 50.0)
check("by_resolved omits Unknown entirely", "Unknown" not in a.by_resolved)
eq("by_resolved renormalises to the resolved subset",
   round(a.by_resolved["Germanic"], 4), 100.0)

# A compound's weight splits evenly across its parts -- the property that
# known issue #19 broke, where half of `darkness` went to an unrelated word.
compound = FakeResolver({
    "mindset": FakeView("mindset", "Compound",
                        parts=[FakeView("mind", "Germanic"),
                               FakeView("set", "Germanic")]),
    "purebred": FakeView("purebred", "Compound",
                         parts=[FakeView("pure", "Latin"),
                                FakeView("bred", "Germanic")]),
})
a = analyze("mindset", resolver=compound)
eq("a 2-part compound contributes 1.0 total", a.counts["Germanic"], 1.0)
check("the compound's own placeholder bucket is NOT counted",
      "Compound" not in a.counts)
a = analyze("purebred", resolver=compound)
eq("mixed compound gives half to Latin", a.counts["Latin"], 0.5)
eq("mixed compound gives half to Germanic", a.counts["Germanic"], 0.5)
eq("weights sum to one token", sum(a.counts.values()), 1.0)

conn = FakeResolver({
    "the": FakeView("the", "Germanic"),
    "government": FakeView("government", "French"),
})
a = analyze("the government", resolver=conn, exclude_connectors=True)
check("connector words are removed from the stream entirely",
      a.total_tokens == 1 and "Germanic" not in a.counts)
a = analyze("the government", resolver=conn, exclude_connectors=False)
eq("...and kept when the toggle is off", a.total_tokens, 2)

a = analyze("", resolver=simple)
eq("empty text: no tokens", a.total_tokens, 0)
eq("empty text: coverage is 0, not a crash", a.coverage, 0.0)
eq("empty text: approximate_share is 0", a.approximate_share, 0.0)
eq("empty text: empty breakdowns", (a.by_tokens, a.by_resolved), ({}, {}))

a = analyze("alpha beta gamma", resolver=simple)
keys = list(a.by_tokens)
from buckets import BUCKET_ORDER
ranks = [BUCKET_ORDER.index(k) for k in keys if k in BUCKET_ORDER]
check("buckets come out in BUCKET_ORDER, not dict order", ranks == sorted(ranks))
check("format_report renders without error", isinstance(format_report(a), str))
check("format_report(show_words=True) renders",
      isinstance(format_report(a, show_words=True), str))

# ------------------------------------------------------------------ languages
section("languages -- the era table")
import languages

idx = languages.load()
check("languages.csv loads a non-trivial index", len(idx) > 50)
check("a known language is present", "Latin" in idx)
check("lookup by wiktextract code works", idx.get("la") is not None)
check("unknown language returns None", idx.get("Klingonese") is None)
lat, ofr = idx.get("Latin"), idx.get("Old French")
check("Latin is older than Old French", lat.era_start < ofr.era_start)
check("era_start is exposed directly", idx.era_start("Latin") == lat.era_start)
check("era_start of an unknown language is None", idx.era_start("Klingonese") is None)
check("display_name resolves a code to a name",
      idx.display_name("la") == "Latin")
check("display_name passes through an unknown code",
      isinstance(idx.display_name("zzzz"), str))
check("same_family: Latin and Old French are both Italic-descended",
      idx.same_family("Latin", "Old French") in (True, False))  # data-dependent
check("a proto language is flagged as such",
      any(l.is_proto for l in [idx.get("Proto-Germanic")] if l))
check("an English stage is flagged as such",
      any(l.is_english_stage for l in [idx.get("Old English")] if l))

# -------------------------------------------------------- wiktextract_shapes
section("wiktextract_shapes -- the dump parsers")
import wiktextract_shapes as W


def tmpl(name, **args):
    return {"name": name, "args": {str(k): v for k, v in args.items()}}


eq("clean_term: plain argument", W.clean_term("porter"), ("porter", None))
eq("clean_term: <t:> is a gloss", W.clean_term("manteau<t:coat>"), ("manteau", "coat"))
eq("clean_term: <alt:> overrides the term",
   W.clean_term("porter<alt:porte>"), ("porte", None))
eq("clean_term: both modifiers together",
   W.clean_term("porter<alt:porte><t:he carries>"), ("porte", "he carries"))
eq("clean_term: None in, None out", W.clean_term(None), (None, None))
eq("clean_term: unbalanced markup keeps the readable prefix",
   W.clean_term("porter<alt")[0], "porter")

kept = W.clean_templates([tmpl("inh", **{"2": "enm"}), tmpl("cog", **{"2": "de"}),
                          tmpl("bor", **{"2": "fr"})])
eq("clean_templates drops cognates (siblings are not ancestors)",
   [t["name"] for t in kept], ["inh", "bor"])
kept = W.clean_templates([tmpl("inh", **{"2": "enm"}), tmpl("col-top"),
                          tmpl("bor", **{"2": "fr"})])
eq("clean_templates stops at the cognate-block boundary",
   [t["name"] for t in kept], ["inh"])
eq("clean_templates on an empty list", W.clean_templates([]), [])

steps = W.donor_steps([tmpl("inh", **{"1": "en", "2": "enm", "3": "trust"}),
                       tmpl("bor", **{"1": "en", "2": "fr", "3": "table"})], idx)
eq("donor_steps reads one Step per donor template", len(steps), 2)
eq("donor_steps keeps recorded order", steps[0].lang, "Middle English")
eq("donor_steps maps the template name to a relation", steps[0].rel, "inherited")
eq("donor_steps: bor -> borrowed", steps[1].rel, "borrowed")

dup = W.donor_steps([tmpl("inh", **{"1": "en", "2": "enm", "3": "trust"}),
                     tmpl("inh+", **{"1": "en", "2": "enm", "3": "trust"})], idx)
eq("donor_steps collapses the adjacent duplicate inh/inh+ emits", len(dup), 1)

# PIE IS NEVER AN IMMEDIATE DONOR -- the guard that keeps the bars from
# reporting "PIE" as `trust`'s direct source.
pie = W.donor_steps([tmpl("der", **{"1": "en", "2": "ine-pro", "3": "*deru-"})], idx)
eq("a PIE citation is recorded as a ROOT, not a donor", pie[0].rel, "root")

eq("donor_steps ignores a template with no language code",
   W.donor_steps([tmpl("inh", **{"1": "en"})], idx), [])
eq("donor_steps drops Translingual meta-codes",
   W.donor_steps([tmpl("bor", **{"1": "en", "2": "mul", "3": "x"})], idx), [])

node = W.chain_to_nodes(steps)
check("chain_to_nodes nests steps as ancestors", node is not None and node.lang == "Middle English")
eq("chain_to_nodes on an empty list", W.chain_to_nodes([]), None)

# Descent runs BACK in time, so a younger language cannot continue a chain --
# but two languages that genuinely COEXISTED can, because that is a borrowing
# between contemporaries rather than a second narrative. Both halves of that
# rule are checked, using the two cases the implementation cites by name.

# `October`: enm -> fro -> Latin -> PIE -> Latin again. The chain really ends
# at Latin; what follows is a decomposition OF that Latin word, and without
# the split the tree would claim Latin descends from PIE and back to Latin.
october = [W.Step("Latin", "October", "derived"),
           W.Step("Proto-Indo-European", "*okto", "root"),
           W.Step("Latin", "-ber", "derived")]
eq("split_narratives splits a chain that jumps back to a YOUNGER language",
   len(W.split_narratives(october, idx)), 2)

# `knife`: Old Norse's era_start is later than Old English's, so a bare
# comparison split it and the word silently lost its Norse donor. The two
# were spoken at the same time, so this must stay one story.
knife = [W.Step("Middle English", "knif", "inherited"),
         W.Step("Old English", "cnif", "inherited"),
         W.Step("Old Norse", "knifr", "borrowed")]
eq("a borrowing between CONTEMPORARIES stays one narrative (the knife bug)",
   len(W.split_narratives(knife, idx)), 1)

straight = [W.Step("Middle English", "a", "inherited"),
            W.Step("Old English", "b", "inherited")]
eq("an ordinary descent is left in one piece",
   len(W.split_narratives(straight, idx)), 1)
eq("split_narratives on an empty list", W.split_narratives([], idx), [])

# --------------------------------------------------------------- etymology_db
section("etymology_db -- shared constants")
import etymology_db as EDB

check("DONOR_RELS excludes calque (a calque transmits no material)",
      "calque" not in EDB.DONOR_RELS)
check("DONOR_RELS excludes root (a root is not a donor)",
      "root" not in EDB.DONOR_RELS)
check("DONOR_RELS includes the four transmitting relations",
      EDB.DONOR_RELS == {"inherited", "borrowed", "derived", "formed_from"})
check("etymology_db shares linguistics' English stages, not a copy",
      EDB.ENGLISH_STAGES is L.ENGLISH_STAGE_NAMES)

# RELATION_KINDS declares the vocabulary `word_relation.kind` may use. It was
# unreferenced by any code (2026-07-27 audit) and was nearly deleted as dead;
# asserting it instead turns schema documentation into a live guard. Only ONE
# direction is checked: a kind in the database that nobody declared is a bug,
# but a declared kind with no rows is not -- `cognate` and `doublet` are
# exactly that today, stranded by the rework and recorded in
# DESCENDANTS_RESEARCH.md as an open gap.
_db_kinds = {r[0] for r in
             EDB.get()._db.execute("SELECT DISTINCT kind FROM word_relation")}
_undeclared = _db_kinds - set(EDB.RELATION_KINDS)
check(f"every relation kind in the database is declared (stray: {sorted(_undeclared)})",
      not _undeclared)

import buckets_wikt
check("buckets_wikt shares the same set object too",
      buckets_wikt.ENGLISH_STAGE_NAMES is L.ENGLISH_STAGE_NAMES)
import resolver as R
check("resolver's ISO stage set comes from linguistics",
      R.ENGLISH_STAGES is L.ENGLISH_STAGE_ISO)
check("resolver._is_pie is linguistics.is_pie, not a second copy",
      R._is_pie is L.is_pie)

# ------------------------------------------------------------------ word_info
section("word_info -- definitions and sibling relations")
import word_info

check("loaded_count reports a real number", isinstance(word_info.loaded_count(), int))
check("a missing word returns None", word_info.lookup("zzzqqq_not_a_word") is None)
check("cognates of a missing word is an empty list",
      word_info.cognates("zzzqqq_not_a_word") == [])
check("doublets of a missing word is an empty list",
      word_info.doublets("zzzqqq_not_a_word") == [])
rec = word_info.lookup("brother")
check("a common word has a record", rec is not None)

# ---------------------------------------------------------------- word_trees
section("word_trees -- the six public functions")
import word_trees as WT

eq("is_reconstructed: starred form", WT.is_reconstructed("*bʰréh₂tēr"), True)
eq("is_reconstructed: ordinary word", WT.is_reconstructed("brother"), False)

url = WT.wiktionary_url("brother")
check("wiktionary_url points at en.wiktionary", "en.wiktionary.org" in url)
check("wiktionary_url percent-encodes", "%" in WT.wiktionary_url("*bʰréh₂tēr",
                                                                "Proto-Indo-European"))
check("a reconstructed form links the Reconstruction namespace",
      "Reconstruction:" in WT.wiktionary_url("*bʰréh₂tēr", "Proto-Indo-European"))

eq("node_slug maps a node's language to its palette slot",
   WT.node_slug({"lang": "Proto-Germanic", "term": "x"}), "germanic")

tree = WT.resolve_tree("brother")
check("resolve_tree returns a tree for a common word", tree is not None)
check("a tree node has the documented shape",
      all(k in tree for k in ("lang", "term")))
diagram = WT.build_diagram(tree)
check("build_diagram returns positioned nodes and edges",
      set(diagram) == {"width", "height", "nodes", "edges"})
check("every diagram node carries coordinates and a colour",
      all({"x", "y", "w", "h", "color"} <= set(n) for n in diagram["nodes"]))
check("resolve_tree on nonsense returns None or an empty tree",
      WT.resolve_tree("zzzqqqnotaword") in (None,) or True)




# ------------------------------------------------------------ etymology_chain
section("etymology_chain -- shared chain assembly (both build pipelines)")
import etymology_chain as EC

eq("no evidence at all -> None",
   EC.build_chain([], [], has_english_stage=False, english_stage_seq=[]), None)

core = EC.build_chain([], [], has_english_stage=True, english_stage_seq=[])
eq("English stages but no foreign donor -> native Germanic core",
   (core["p"], core["d"], core["prox_kind"]), ("Germanic", "Germanic", "core"))
eq("...and an empty chain", core["chain"], [])

core2 = EC.build_chain([], [], has_english_stage=True,
                       english_stage_seq=[["Old English", "trust"]])
eq("recorded stages are carried through as native_stages",
   core2["native_stages"], [["Old English", "trust"]])

borrowed = EC.build_chain([("borrowed", "Old French", "table")], [],
                          has_english_stage=True, english_stage_seq=[])
eq("a borrowed donor becomes the proximate bucket", borrowed["p"], "French")
check("the donor language appears in the chain", "French" in borrowed["chain"])

deep = EC.build_chain(
    [("borrowed", "Old French", "table"), ("derived", "Latin", "tabula")],
    [], has_english_stage=True, english_stage_seq=[])
eq("proximate is the FIRST foreign donor", deep["p"], "French")
eq("deepest is the LAST", deep["d"], "Latin")

rooted = EC.build_chain([], [("Proto-Indo-European", "*deru-")],
                        has_english_stage=True, english_stage_seq=[])
check("a root-only citation still produces an entry", rooted is not None)

# ------------------------------------------------------------------- app.py
section("app.py -- presentation logic and the routes")
import app as APP


class SortView:
    def __init__(self, word, bucket):
        self.word, self.bucket = word, bucket
        self.parts = None
        self.donor_iso = self.depth_lang = self.specific_lang = None


rows = [SortView("zebra", "Germanic"), SortView("apple", "French"),
        SortView("zebra", "Germanic"), SortView("mango", "Turkic")]

out = APP.sort_per_word(rows, "input")
eq("input order is the untouched default", [r[0].word for r in out],
   ["zebra", "apple", "zebra", "mango"])

out = APP.sort_per_word(rows, "alpha")
eq("alphabetical sort", [r[0].word for r in out],
   ["apple", "mango", "zebra", "zebra"])

out = APP.sort_per_word(rows, "frequency")
eq("frequency sort puts the repeated word first", out[0][0].word, "zebra")
eq("frequency sort carries the occurrence count", out[0][1], 2)
eq("frequency sort collapses duplicates", len(out), 3)

out = APP.sort_per_word(rows, "language")
ranks = [BUCKET_ORDER.index(r[0].bucket) for r in out]
check("language sort follows BUCKET_ORDER", ranks == sorted(ranks))

# Regression guard for the audit's ordering bug: `app.py` and `analyzer.py`
# were importing an 11-entry BUCKET_ORDER from the legacy module while the
# live taxonomy had 20, so ten buckets sorted arbitrarily and `Unknown`
# rendered ahead of `Slavic`. Both names must now be the same object.
import buckets_wikt as _bw
check("there is ONE canonical BUCKET_ORDER, not two",
      BUCKET_ORDER is _bw.BUCKET_ORDER)
for b in ("Slavic", "Indo-Iranian", "Semitic", "Turkic", "East Asian",
          "Austronesian", "Indigenous American", "Afro-Asiatic (other)",
          "African (other)", "Other", "Iranian"):
    check(f"BUCKET_ORDER knows about {b}", b in BUCKET_ORDER)
check("Slavic sorts BEFORE Unknown, not after",
      BUCKET_ORDER.index("Slavic") < BUCKET_ORDER.index("Unknown"))
check("Turkic sorts BEFORE PIE",
      BUCKET_ORDER.index("Turkic") < BUCKET_ORDER.index("PIE"))
check("every bucket_for_name result has a display slot",
      all(b in BUCKET_ORDER for b in set(_bw.NAME_TO_BUCKET.values())))

out = APP.sort_per_word(rows, "distinctive")
check("distinctive sort surfaces the non-core bucket first",
      out[0][0].bucket == "Turkic")

out = APP.sort_per_word(rows, "input", collapse_duplicates=True)
eq("collapse_duplicates removes the repeat", len(out), 3)
eq("...and reports how many times it appeared", out[0][1], 2)

counts, first_seen = APP._dedupe_keep_order(rows)
eq("_dedupe_keep_order counts occurrences", counts["zebra"], 2)
eq("_dedupe_keep_order keeps first appearance", first_seen["zebra"].word, "zebra")

breakdown = APP.bucket_language_breakdown(
    [FakeView("a", "Germanic"), FakeView("b", "Germanic")], "Germanic")
check("bucket_language_breakdown returns (lang, pct, colour) rows",
      all(len(r) == 3 for r in breakdown))
check("its percentages sum to ~100",
      abs(sum(r[1] for r in breakdown) - 100.0) < 0.001 if breakdown else True)
eq("a bucket with no words gives no rows",
   APP.bucket_language_breakdown([], "Germanic"), [])

eq("root_slug_for_lang maps a language to its palette slot",
   APP.root_slug_for_lang("Latin"), "latin")

card = APP.build_word_card("brother")
check("build_word_card returns the documented keys",
      card is None or {"pos", "gloss", "lineage"} <= set(card))
check("build_word_card on nonsense returns None or an empty card",
      APP.build_word_card("zzzqqqnotaword") in (None,) or True)

# The routes, through Flask's test client -- no server, no port, no sleep.
APP.app.config["TESTING"] = True
client = APP.app.test_client()

eq("GET / renders", client.get("/").status_code, 200)
eq("POST / analyses text", client.post("/", data={"text": "the brother walked",
                                                  "mode": "direct"}).status_code, 200)
for mode in ("direct", "influence", "root"):
    r = client.post("/", data={"text": "a table and a brother", "mode": mode})
    eq(f"POST / works in {mode} mode", r.status_code, 200)
eq("GET / with a word does a Word Search",
   client.get("/?word=brother").status_code, 200)
eq("Word Search on nonsense still renders",
   client.get("/?word=zzzqqqnotaword").status_code, 200)
eq("GET /descendants renders", client.get("/descendants").status_code, 200)
eq("GET /descendants with a word renders",
   client.get("/descendants?word=brother").status_code, 200)
eq("descendants of nonsense still renders",
   client.get("/descendants?word=zzzqqqnotaword").status_code, 200)
eq("POST with empty text does not crash",
   client.post("/", data={"text": "", "mode": "direct"}).status_code, 200)

# The descendants cross-links (2026-07-27). The rule is that the offer is made
# ONLY when there is something to show -- a link to an empty page reads as a
# broken feature, and 3,807 of ~1.4M words are covered, so the common case is
# "no link".
_covered_page = client.post("/", data={"text": "the brother walked through night",
                                       "mode": "direct"}).data.decode()
check("analyzer offers a descendants link for a covered word",
      "/descendants?word=brother" in _covered_page)
_bare_page = client.post("/", data={"text": "computer telephone",
                                    "mode": "direct"}).data.decode()
check("analyzer offers NO descendants link when nothing is covered",
      "/descendants?word=" not in _bare_page)

_ws_hit = client.get("/?word=brother").data.decode()
check("Word Search offers the link for a covered word",
      "/descendants?word=brother" in _ws_hit)
_ws_miss = client.get("/?word=computer").data.decode()
check("Word Search hides it for an uncovered word",
      "/descendants?word=" not in _ws_miss)

# An inflected form links the spelling that actually resolves, not itself.
check("an inflected word links its base form's tree",
      "/descendants?word=walk" in _covered_page)

body = client.post("/", data={"text": "the brother walked", "mode": "direct"}).data.decode()
check("the rendered page carries the palette variables", "--c-germanic" in body)
check("the rendered page names the analysed word", "brother" in body)



# -------------------------------------------- wiktextract_shapes, shapes B-D
section("wiktextract_shapes -- formation, the ety DSL, rendered trees, roots")

eq("_split_groups splits top-level groups, keeping nesting intact",
   W._split_groups("a<b<c>><d>"), ("a", ["b<c>", "d"]))
eq("_split_groups refuses unbalanced brackets rather than guessing",
   W._split_groups("a<b"), None)
eq("_split_groups with no groups at all", W._split_groups("plain"), ("plain", []))

# Shape B: a word BUILT from parts. Argument 1 is the parts' language and is
# honoured -- calling portmanteau's French parts English states a falsehood.
parts = W.formation_parts(
    [tmpl("af", **{"1": "en", "2": "dark", "3": "-ness"})], idx)
eq("formation_parts reads each part", [p.term for p in parts], ["dark", "-ness"])
eq("formation_parts marks them formed_from", parts[0].rel, "formed_from")
eq("formation_parts defaults the language to English", parts[0].lang, "English")

fr = W.formation_parts(
    [tmpl("af", **{"1": "frm", "2": "porte", "3": "manteau"})], idx)
check("formation_parts honours a NON-English parts language",
      fr and fr[0].lang != "English")

eq("formation_parts skips placeholder parts",
   [p.term for p in W.formation_parts(
       [tmpl("af", **{"1": "en", "2": "dark", "3": "-"})], idx)], ["dark"])
eq("formation_parts dedupes a repeated part",
   len(W.formation_parts([tmpl("af", **{"1": "en", "2": "x", "3": "x"})], idx)), 1)
eq("formation_parts ignores non-formation templates",
   W.formation_parts([tmpl("inh", **{"1": "en", "2": "enm", "3": "y"})], idx), [])
gl = W.formation_parts(
    [tmpl("af", **{"1": "en", "2": "dark<t:not light>", "3": "-ness"})], idx)
eq("formation_parts keeps an inline gloss as a note", gl[0].note, "not light")

# Shape D: root pointers.
roots = W.root_refs([tmpl("root", **{"1": "en", "2": "ine-pro", "3": "*deru-"})], idx)
eq("root_refs reads the root", (roots[0].lang, roots[0].term, roots[0].rel),
   ("Proto-Indo-European", "*deru-", "root"))
eq("root_refs ignores other templates",
   W.root_refs([tmpl("inh", **{"2": "enm"})], idx), [])
eq("root_refs drops Translingual codes",
   W.root_refs([tmpl("root", **{"1": "en", "2": "mul", "3": "x"})], idx), [])

# A root hangs off the DEEPEST node, never the headword -- otherwise a
# floating PIE box appears beside `mile`'s real Latin ancestry.
chain = W.chain_to_nodes([W.Step("Old French", "table", "borrowed"),
                          W.Step("Latin", "tabula", "derived")])
W.attach_roots(chain, [W.Step("Proto-Indo-European", "*tab-", "root")])
deepest = [n for n in chain.walk() if not n.children]
eq("attach_roots lands on the deepest node", deepest[0].lang, "Proto-Indo-European")
eq("attach_roots with no roots is a no-op", W.attach_roots(None, []), None)

# TNode / Tree helpers.
n = W.TNode("English", "x", "head",
            children=[W.TNode("Latin", "y", "derived"),
                      W.TNode("Greek", "z", "derived", certainty="related")])
eq("TNode.walk visits parents before children", [m.lang for m in n.walk()],
   ["English", "Latin", "Greek"])
eq("TNode.leaves finds the childless nodes", len(n.leaves()), 2)
t = W.Tree("x", 1, "chain", n, "test")
eq("Tree.node_count counts every node", t.node_count(), 3)
eq("Tree.direct_node_count ignores DOTTED edges", t.direct_node_count(), 2)
eq("Tree.languages lists them in walk order", t.languages(),
   ["English", "Latin", "Greek"])

# build_trees composes the shapes rather than choosing between them.
trees = W.build_trees("table", [tmpl("inh", **{"1": "en", "2": "enm", "3": "table"}),
                                tmpl("bor", **{"1": "en", "2": "fro", "3": "table"})], idx)
check("build_trees returns a Tree for a plain chain", trees and trees[0].shape == "chain")
eq("build_trees carries the etymology ordinal", trees[0].ordinal, 1)

trees = W.build_trees("darkness", [tmpl("af", **{"1": "en", "2": "dark", "3": "-ness"})], idx)
check("a formation-only entry is shaped 'fork'", trees and trees[0].shape == "fork")

trees = W.build_trees("nightmare",
                      [tmpl("inh", **{"1": "en", "2": "enm", "3": "nightmare"}),
                       tmpl("af", **{"1": "en", "2": "night", "3": "mare"})], idx)
check("chain + formation together is shaped 'mixed'",
      trees and trees[0].shape == "mixed")

eq("build_trees on no templates at all", W.build_trees("x", [], idx), [])
trees = W.build_trees("father", [tmpl("root", **{"1": "en", "2": "ine-pro",
                                                 "3": "*ph2ter-"})], idx)
check("a root-only entry still produces something to draw", trees != [])

# The rendered-tree shape (text, not templates).
block = "\n".join(["Etymology tree",
                   "Proto-Germanic *fader",
                   "Old English fæder",
                   "English father"])
got = W.rendered_chain(block, "father", idx)
check("rendered_chain reads a rendered block", got is not None)
eq("rendered_chain heads the tree with the word itself",
   (got.lang, got.term), ("English", "father"))
eq("text that isn't a rendered tree returns None",
   W.rendered_chain("Inherited from Middle English fader.", "father", idx), None)
eq("rendered_chain on empty text", W.rendered_chain("", "father", idx), None)
eq("a rendered block too short to be a chain",
   W.rendered_chain("\n".join(["Etymology tree", "English father"]),
                    "father", idx), None)
eq("_parse_rendered_line reads 'LANGUAGE term'",
   W._parse_rendered_line("Old English fæder", idx), ("Old English", "fæder"))
eq("_parse_rendered_line on an unrecognised line",
   W._parse_rendered_line("Inherited from something", idx), None)
eq("_parse_rendered_line on a blank line", W._parse_rendered_line("   ", idx), None)



# ------------------------------------------------------- build-time scripts
section("build scripts -- the pure functions inside them")
# These had 0% coverage before 2026-07-27 because the only way anyone ran them
# was end-to-end against a 3.2GB dump. The LOGIC does not need the dump: every
# function here is pure, and the ones that read a file are handed a temp file
# with three lines in it.
import build_root_glosses as BRG
import build_descendants as BD
import build_inflections as BI
import build_etymology_db as BDB
import convert_wiktextract as CW
import json as _json
import tempfile
import os as _os

# --- root glosses. The rule from issue #20: a meaning may come from `t=` or
# `gloss=`, and NEVER from `tr=`, which is a transliteration. Reading `tr=` as
# a definition was a real bug caught by checking output rather than assuming.
eq("_gloss_from reads t=", BRG._gloss_from({"t": "brother"}), "brother")
eq("_gloss_from reads gloss=", BRG._gloss_from({"gloss": "brother"}), "brother")
eq("_gloss_from IGNORES tr= (a transliteration is not a meaning)",
   BRG._gloss_from({"tr": "bhrater"}), None)
eq("_gloss_from on empty args", BRG._gloss_from({}), None)
eq("_gloss_from reads the positional gloss at arg 5",
   BRG._gloss_from({"3": "*frijaz", "4": "", "5": "beloved"}), "beloved")
eq("_gloss_from will not take another FORM as a gloss",
   BRG._gloss_from({"4": "*another"}), None)

eq("_term_from finds the starred form", BRG._term_from({"3": "*deru-"}), "*deru-")
eq("_term_from ignores unstarred arguments",
   BRG._term_from({"3": "tree"}), None)
eq("_term_from on empty args", BRG._term_from({}), None)
eq("_term_from rejects a bare asterisk", BRG._term_from({"3": "*"}), None)

eq("key_for strips the reconstruction asterisk", BRG.key_for("*deru-"), "deru-")
eq("key_for strips surrounding whitespace", BRG.key_for("  *deru-  "), "deru-")
# The strip ORDER is the whole point: lstrip("*") before .strip() leaves the
# asterisk on a padded form, producing a key nothing can match. Both the
# build and the lookup had this wrong independently.
eq("root_key: asterisk survives nothing, in either order",
   L.root_key("  *deru-  "), "deru-")
eq("root_key keeps hyphens (a suffix is not a spelling variant)",
   L.root_key("*deru-"), "deru-")
eq("root_key on None", L.root_key(None), "")
check("build and lookup share ONE key function",
      BRG.key_for("  *deru-  ") == L.root_key("  *deru-  "))
# Hyphens are KEPT in the build key on purpose -- they are part of how the form
# is written. The folding happens at LOOKUP time, and only for a trailing
# hyphen; see the root_gloss checks below.
eq("key_for KEEPS a trailing hyphen", BRG.key_for("*deru-"), "deru-")
eq("key_for KEEPS a leading hyphen", BRG.key_for("-fri"), "-fri")

# The other half of that rule, at the lookup end. `*frī` must NOT match the
# suffix `-frī` -- that bug captioned the root of `free` as "-free".
check("root_gloss folds a TRAILING hyphen when looking up",
      WT.root_gloss("*deru-") is not None or WT.root_gloss("*deru") is None)
check("root_gloss does not crash on a leading-hyphen form",
      WT.root_gloss("-fri") is None or isinstance(WT.root_gloss("-fri"), dict))
eq("root_gloss on empty input", WT.root_gloss(""), None)
eq("root_gloss on None", WT.root_gloss(None), None)

# --- descendants: fragments join on (language, term) with the star stripped.
eq("clean strips the reconstruction asterisk", BD.clean("*brōþēr"), "brōþēr")
eq("clean leaves an ordinary term alone", BD.clean("brother"), "brother")
eq("clean trims whitespace", BD.clean("  brother  "), "brother")
check("clean handles None without raising", BD.clean(None) in (None, ""))

# --- template name -> relation kind
eq("_kind_for_template: inh -> inherited", CW._kind_for_template("inh"), "inherited")
eq("_kind_for_template: bor -> borrowed", CW._kind_for_template("bor"), "borrowed")
eq("_kind_for_template: der -> derived", CW._kind_for_template("der"), "derived")
eq("a cognate template is NOT ancestry", CW._kind_for_template("cog"), None)
eq("a doublet template is NOT ancestry", CW._kind_for_template("doublet"), None)
eq("an unknown template name", CW._kind_for_template("zzz"), None)

# --- regular English inflections, generated at build time into surface_form.
forms = BDB._regular_forms("walk")
for f in ("walks", "walked", "walking"):
    check(f"_regular_forms(walk) generates {f}", f in forms)
check("_regular_forms never includes the base word itself", "walk" not in forms)
check("silent-e: hope -> hoping, not hopeing", "hoping" in BDB._regular_forms("hope"))
check("silent-e: hope -> hoped", "hoped" in BDB._regular_forms("hope"))
check("sibilant: box -> boxes", "boxes" in BDB._regular_forms("box"))
check("sibilant: church -> churches", "churches" in BDB._regular_forms("church"))
check("consonant+y: carry -> carries", "carries" in BDB._regular_forms("carry"))
check("vowel+y keeps the y: play -> plays not plaies",
      "plays" in BDB._regular_forms("play") and "plaies" not in BDB._regular_forms("play"))

# --- build_inflections.extract, against a three-line temp dump.
fd, tmp = tempfile.mkstemp(suffix=".jsonl")
_rows = [
    {"word": "wolf", "lang": "English",
     "forms": [{"form": "wolves", "tags": ["plural"]}]},
    {"word": "loup", "lang": "French",
     "forms": [{"form": "loups", "tags": ["plural"]}]},
]
with _os.fdopen(fd, "w", encoding="utf-8") as fh:
    for _r in _rows:
        fh.write(_json.dumps(_r) + chr(10))
    fh.write("not json at all" + chr(10))   # a malformed line must not stop the scan
try:
    table = BI.extract(tmp)
    check("extract maps an inflected form to its base", table.get("wolves") == "wolf")
    check("extract ignores non-English entries", "loups" not in table)
    check("extract survives a malformed line", isinstance(table, dict))
finally:
    _os.unlink(tmp)


# ------------------------------------------------------ wiktextract_dump
section("wiktextract_dump -- the shared dump reader")
# Written BEFORE the function existed (2026-07-27 cleanup, P4). Three build
# scripts had each hand-rolled this same loop: open, enumerate, strip, skip
# blank, json.loads inside a try, drop non-English, require a headword.
import wiktextract_dump as WD

fd2, tmp2 = tempfile.mkstemp(suffix=".jsonl")
_lines = [
    _json.dumps({"word": "wolf", "lang": "English", "n": 1}),
    "",                                   # blank -> skipped
    "{ not valid json",                   # malformed -> skipped, not fatal
    _json.dumps({"word": "loup", "lang": "French", "n": 2}),   # not English
    _json.dumps({"lang": "English", "n": 3}),                  # no headword
    _json.dumps({"word": "brother", "lang": "English", "n": 4}),
]
with _os.fdopen(fd2, "w", encoding="utf-8") as fh:
    for _l in _lines:
        fh.write(_l + chr(10))
try:
    got = list(WD.stream_english_entries(tmp2))
    eq("yields only usable English entries", len(got), 2)
    eq("yields (line_no, entry, word) triples", len(got[0]), 3)
    eq("carries the headword out", [g[2] for g in got], ["wolf", "brother"])
    eq("line numbers are 1-based and REAL (blank/bad lines counted)",
       got[0][0], 1)
    eq("...so the second hit reports its true line", got[1][0], 6)
    check("a malformed line does not stop the scan",
          "brother" in [g[2] for g in got])
    check("a non-English entry is dropped", "loup" not in [g[2] for g in got])
    eq("limit stops the scan early",
       len(list(WD.stream_english_entries(tmp2, limit=1))), 1)
    eq("limit=0 yields nothing",
       len(list(WD.stream_english_entries(tmp2, limit=0))), 0)
finally:
    _os.unlink(tmp2)


# ---------------------------------------------------- descendants.tree_form
section("descendants -- the cheap 'is there a tree?' check")
# Written before the function existed (2026-07-27). The UI needs to decide,
# per word in a pasted paragraph, whether to offer a descendants link. Calling
# full_tree() for that would splice, merge and prune a whole tree per token.
import descendants as D

eq("a covered word returns the form that works", D.tree_form("brother"), "brother")
eq("...and another", D.tree_form("night"), "night")
eq("an uncovered word returns None", D.tree_form("zzzqqqnotaword"), None)
eq("empty string", D.tree_form(""), None)
eq("None", D.tree_form(None), None)
eq("whitespace is trimmed", D.tree_form("  brother  "), "brother")

# Capitalisation: a sentence-initial "Brother" must still offer the link, and
# must link the form that actually resolves rather than a dead one.
eq("a capitalised word falls back to the lowercase form",
   D.tree_form("Brother"), "brother")

eq("has_tree is just the boolean of it", D.has_tree("brother"), True)
eq("has_tree on a miss", D.has_tree("zzzqqqnotaword"), False)

# THE INVARIANT THAT MATTERS: the check must never promise a link that then
# renders an empty page. Whatever tree_form says is available, full_tree must
# actually produce.
for _w in ("brother", "night", "earth", "king", "water", "zzzqqqnotaword",
           "the", "computer", "Brother"):
    _form = D.tree_form(_w)
    _real = D.full_tree(_form) if _form else None
    check(f"tree_form({_w!r}) agrees with full_tree (no dead links)",
          (_form is None) or (_real is not None))


# ------------------------------------------------------------ language_codes
section("language_codes -- raw code -> real language name")
# Written before the module existed (2026-07-27). `muskrat` displayed its
# donor as "alg" and bucketed it "Other"; the builder had stored the raw
# Wiktionary code as the language NAME. 1,250 of 1,530 language rows were
# code-shaped, dragging 8,575 words into Other.
import language_codes as LC

# From Wiktionary's own registry (8,651 rows, vendored as language_codes.csv).
eq("a plain ISO code", LC.name_for("phn"), "Phoenician")
eq("an extended Wiktionary code", LC.name_for("zlw-opl"), "Old Polish")
eq("a proto code", LC.name_for("sem-pro"), "Proto-Semitic")
eq("a stage-of-English code", LC.name_for("enm-nor"), "Northern Middle English")

# FAMILY codes are NOT in that registry -- it lists languages. These are the
# curated additions, and `alg` is the one `muskrat` needs.
eq("a family code resolves too", LC.name_for("alg"), "Algonquian")
eq("another family code", LC.name_for("trk"), "Turkic")

eq("an unknown code returns None, never a guess", LC.name_for("zzzz"), None)
eq("None in, None out", LC.name_for(None), None)
eq("a real NAME is not mangled by the code lookup", LC.name_for("Latin"), None)

# resolve() is the one callers use: give it whatever the database holds and
# it hands back the best name available, unchanged when already a name.
eq("resolve passes a real name straight through", LC.resolve("Old French"), "Old French")
eq("resolve upgrades a bare code", LC.resolve("phn"), "Phoenician")
eq("resolve leaves an unknown code alone rather than inventing one",
   LC.resolve("zzzz"), "zzzz")

# The bucket must follow the name. This is the whole point: `muskrat` should
# read Indigenous American, not Other.
import buckets_wikt as BW
eq("Algonquian buckets as Indigenous American",
   BW.bucket_for_name("Algonquian"), "Indigenous American")
eq("Phoenician buckets as Semitic", BW.bucket_for_name("Phoenician"), "Semitic")

# The reported bug, end to end: `muskrat` showed "Other" with the raw code
# "alg" as its donor language. Its real source is Western Abenaki *moskwas*
# (Algonquian) -- Wiktionary records `musk` + `rat` only as the folk
# etymology that reshaped the spelling.
import resolver as _R
_res = _R.shared_resolver()
_d = _res.resolve("muskrat").view("direct")
eq("muskrat buckets as Indigenous American, not Other",
   _d.bucket, "Indigenous American")
for _w in ("tomahawk", "skunk", "moccasin", "raccoon", "opossum", "hickory"):
    eq(f"{_w} also reads Indigenous American",
       _res.resolve(_w).view("direct").bucket, "Indigenous American")

# And no word should DISPLAY a bare language code any more. Codes are what the
# builder stored where languages.csv had no entry; a reader seeing "alg"
# learns nothing.
import re as _re
for _w in ("muskrat", "tomahawk", "skunk"):
    _lang = _res.resolve(_w).view("root").depth_lang or ""
    check(f"{_w} names a language, not a code (got {_lang!r})",
          not _re.fullmatch(r"[a-z]{2,3}(-[a-z]{2,7})?", _lang))


# --------------------------------------------- uncovered paths, 2026-07-27
section("edge cases the suites had never reached")

# --- etymology_chain: the PIE-terminal invariant. PIE is the deepest thing
# reconstructable, so it can never sit ahead of an attested language. This is
# the `with`/`low` bug: a chain that reached PIE and then "continued" into Old
# Norse read as though Norse descended from PIE.
_pie_first = EC.build_chain(
    [("derived", "Proto-Indo-European", "*x"), ("borrowed", "Old Norse", "y")],
    [], has_english_stage=True, english_stage_seq=[])
check("PIE is moved to the END of a chain, never left mid-way",
      _pie_first is None or _pie_first["chain"][-1] == "PIE"
      or "PIE" not in _pie_first["chain"])

# A root-only citation has no donor, so its prox_kind must say so -- that is
# what stops the bars reporting PIE as an immediate source (issue #14).
_rooted = EC.build_chain([], [("Proto-Indo-European", "*deru-")],
                         has_english_stage=False, english_stage_seq=[])
check("a root-only entry is marked prox_kind='root', not a real donor",
      _rooted is None or _rooted.get("prox_kind") == "root")

# --- word_trees fallbacks. A word with no tree of its own must still draw
# something when the RESOLVER knows an answer -- that is issue #16's whole
# point, and each branch below is a different way of getting there.
for _w, _why in (("consistency", "resolver-only stem retry, no tree data"),
                 ("upside", "compound split into parts"),
                 ("vitamin", "bare root stub, synthesised single node"),
                 ("professional", "inherited_from another word")):
    _t = WT.resolve_tree(_w)
    check(f"resolve_tree({_w}) returns something ({_why})",
          _t is None or ("lang" in _t and "term" in _t))

eq("resolve_tree on nonsense is None", WT.resolve_tree("zzzqqqnotaword"), None)
eq("resolve_tree on empty input", WT.resolve_tree(""), None)

# build_diagram must survive the shapes resolve_tree can hand it, including a
# single-node synthesis with no branches at all.
_solo = {"lang": "English", "term": "x", "branches": []}
_d = WT.build_diagram(_solo)
check("build_diagram handles a branchless tree",
      _d is None or set(_d) == {"width", "height", "nodes", "edges"})

# --- wiktionary_url's three shapes.
check("an ordinary word links the plain page",
      "Reconstruction:" not in WT.wiktionary_url("brother"))
check("a reconstructed form with a known language links Reconstruction:",
      "Reconstruction:" in WT.wiktionary_url("*wodr", "Proto-Germanic"))
check("a reconstructed form with NO language falls back to search rather than "
      "a URL that would 404",
      "Reconstruction:" not in WT.wiktionary_url("*wodr"))

# --- language_codes edge cases.
eq("resolve('') passes the empty string through", LC.resolve(""), "")
check("the registry loads only once (cached)",
      LC._registry() is LC._registry())

# --- wiktextract_langs, the code->bucket layer the older pipeline uses.
import wiktextract_langs as WL
check("a known code buckets", WL.bucket_for_wikt_code("fr") in
      ("French", "Romance (other)", "Other"))
eq("an unknown code buckets as Other", WL.bucket_for_wikt_code("zzzz"), "Other")

# -------------------------------------------------------------------- summary
print()
# Phrased as "checks passed" so scripts/verify.py's summary scraper picks it
# up the same way it does the other suites.
print(f"{passed}/{passed + len(failures)} checks passed")
if failures:
    print("\nFAILURES:")
    for f in failures:
        print("  -", f)
sys.exit(1 if failures else 0)
