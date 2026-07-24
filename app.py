"""
Minimal local web UI for testing the analyzer. Not the planned Java/Spring
backend -- a throwaway Flask wrapper around analyze() so results can be viewed
in a browser instead of a terminal.

Run: python app.py
Then open http://localhost:5000
"""
import json
from collections import Counter

from flask import Flask, render_template_string, request

from analyzer import analyze, format_report
from buckets import BUCKET_ORDER
from buckets_wikt import bucket_for_name
from convert_wikt import _depth_hint

app = Flask(__name__)

# "Core" families for the Most Distinctive sort -- same set resolver.py's
# _pick_influence uses to decide what counts as an unremarkable, expected
# donor vs. a notable/rare one.
_CORE_FAMILIES = {"Germanic", "Norse", "French", "Latin", "Greek",
                   "Romance (other)", "Celtic", "PIE"}


def sort_per_word(per_word, word_sort):
    """
    Returns a list of (ResolvedView, count_or_None) pairs for the "Per word"
    section, added 2026-07-23 (Joe: filter the per-word results by language
    group, input order, "and a couple other interesting filters"). Display-
    only -- doesn't touch Analysis/per_word itself (input order stays the
    source of truth for the percentage breakdown).
    """
    if word_sort == "language":
        order = {b: i for i, b in enumerate(BUCKET_ORDER)}
        rows = sorted(per_word, key=lambda w: (order.get(w.bucket, 999), w.word))
        return [(w, None) for w in rows]
    if word_sort == "alpha":
        return [(w, None) for w in sorted(per_word, key=lambda w: w.word)]
    if word_sort == "distinctive":
        # Rarest/most unexpected origins first -- surfaces the interesting
        # loanwords in a text instead of burying them under the Germanic/
        # French/Latin majority.
        rows = sorted(per_word, key=lambda w: (w.bucket in _CORE_FAMILIES, w.word))
        return [(w, None) for w in rows]
    if word_sort == "frequency":
        # Dedupe repeated words, most-repeated first -- most useful on long
        # texts/whole books where the same word appears many times.
        counts = Counter(w.word for w in per_word)
        first_seen = {}
        for w in per_word:
            first_seen.setdefault(w.word, w)
        return [(first_seen[word], count) for word, count in counts.most_common()]
    return [(w, None) for w in per_word]  # "input" (default): unchanged order

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


def node_slug(node):
    """Color slot for one tree node, reusing the same bucket->hue mapping
    as the rest of the app (English stages already map to Germanic via
    buckets_wikt.py, no special-casing needed here)."""
    return bucket_slug(bucket_for_name(node["lang"]))


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

# Bucket -> color slot.
#
# The dataviz skill's categorical palette is a hard 8-hue ceiling ("a 9th
# series is never a generated hue" -- CVD-safe adjacent-pair distinguishability
# genuinely doesn't scale past 8 fixed hues; the skill's own validator has no
# passing 9-hue ordering). These 8 stay exactly as originally validated
# (validate_palette.py confirms this exact order clears CVD/contrast checks
# for adjacent pairs in both modes -- re-ordering to chase hue<->bucket
# associations was tried and FAILED the same validator).
#
# 2026-07-23: Joe asked for every bucket to look different, not just these 8.
# Added a second, lower-chroma "extended tier" (one new hue family, hue~205 --
# the largest open gap between the 8 core hues -- differentiated by an ORDINAL
# lightness ramp, not 5 more competing categorical hues) for the 5 buckets
# most likely to actually appear in real English prose per this project's own
# scan history (Slavic, Indo-Iranian, Semitic, Turkic, East Asian). Verified
# against a Python port of the skill's validator (same OKLab/CVD math,
# cross-checked against the documented default's published numbers before
# trusting it) -- passes validate_ordinal (monotone L, gaps >=0.06, light-end
# contrast, single hue) in both modes. The remaining 7 rare buckets
# (Austronesian, Indigenous American, Caribbean, Afro-Asiatic (other),
# African (other), Other, Unknown) still share the flat muted tone -- adding
# a 3rd tier for buckets this rare wasn't judged worth the added visual noise.
BUCKET_SLUGS = {
    "Germanic": "germanic",
    "Norse": "norse",
    "French": "french",
    "Latin": "latin",
    "Greek": "greek",
    "Romance (other)": "romance-other",
    "Celtic": "celtic",
    "PIE": "pie",
    "Slavic": "slavic",
    "Indo-Iranian": "indo-iranian",
    "Semitic": "semitic",
    "Turkic": "turkic",
    "East Asian": "east-asian",
}


def bucket_slug(name):
    # "Unknown" (a true lookup failure) gets its own slug -- deliberately
    # distinct from "muted" (the shared tone for real-but-rare buckets like
    # "Other"/Caribbean/Austronesian). Found 2026-07-23 (Joe: "persona" reads
    # as Unknown) -- the word actually resolves fine (Etruscan<-Latin<-Greek,
    # bucket "Other"), but "Other" and "Unknown" rendered in the EXACT same
    # muted gray with no distinction, so a real-but-rare answer was
    # indistinguishable from a genuine failure. Same root cause would affect
    # every "Other"-bucket word, not just this one -- fixed generally, not
    # per-word, by giving Unknown its own visually-recessive treatment (see
    # --c-unknown in the page CSS) instead of sharing muted's tone.
    if name == "Unknown":
        return "unknown"
    return BUCKET_SLUGS.get(name, "muted")


# Deepest Root mode names the specific reconstructed form (see resolver.py's
# root_lang/root_pie) -- coordinate each proto-language with its parent
# bucket's hue via a validated lightness step (lighter = deeper reconstructed
# stage), so "Proto-Germanic (from PIE)" reads as a shade of Germanic-blue,
# not an unrelated color. Slots not tied to one of the 8 core hues (Slavic,
# Indo-Iranian) get a lighter step of their own extended-tier hue instead.
PROTO_SLUGS = {
    "Proto-Germanic": "proto-germanic",
    "Proto-West Germanic": "proto-west-germanic",
    "Proto-Italic": "proto-italic",
    "Proto-Celtic": "proto-celtic",
    "Proto-Slavic": "proto-slavic",
    "Proto-Indo-Iranian": "proto-indo-iranian",
}


# Base hex per bucket (light-mode values from the CSS custom properties
# below) -- kept here too so Python can generate shades from them. Used only
# for the bar-drill-down sub-language shading (task 2026-07-23): a lighter-
# weight scope than the validated CVD-checked palette above -- Joe's own
# framing ("sky blue, dark blue, neon blue... or a nice visualization to
# distinguish the subgroups") was satisfied with simple lightness/saturation
# variation around the bucket hue, not another full ordinal-ramp validation
# pass (which the original 8-hue palette and the proto-language shades DID
# get -- this reuses that same visual language without re-deriving it for
# what could be dozens of specific donor languages per bucket).
BUCKET_HEX = {
    "Germanic": "#2a78d6", "Norse": "#eb6834", "French": "#1baf7a",
    "Latin": "#eda100", "Greek": "#e87ba4", "Romance (other)": "#008300",
    "Celtic": "#4a3aa7", "PIE": "#e34948",
    "Slavic": "#156068", "Indo-Iranian": "#30767e", "Semitic": "#488c94",
    "Turkic": "#5fa4ab", "East Asian": "#77bbc3",
}
_MUTED_HEX = "#898781"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def language_shades(bucket, languages):
    """
    Maps each specific language name (within one bucket) to its own shade of
    that bucket's base hue -- deterministic (same language always gets the
    same shade), spread across a moderate lightness/saturation range chosen
    to stay legible on both light and dark surfaces without needing a
    separate light/dark variant (a lighter-weight approach than the main
    palette's per-mode CSS variables -- see BUCKET_HEX comment).
    """
    import colorsys
    base = BUCKET_HEX.get(bucket, _MUTED_HEX)
    r, g, b = (c / 255.0 for c in _hex_to_rgb(base))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    n = max(len(languages), 1)
    shades = {}
    for i, lang in enumerate(sorted(languages)):
        # Spread lightness across a legible band; nudge saturation opposite
        # to lightness so the darkest shade doesn't also look washed out.
        t = i / n if n > 1 else 0.5
        lt = 0.35 + t * 0.35          # 0.35 -> 0.70
        st = min(1.0, s * (0.85 + 0.3 * (1 - t)))
        rr, gg, bb = colorsys.hls_to_rgb(h, lt, st)
        shades[lang] = _rgb_to_hex((rr * 255, gg * 255, bb * 255))
    return shades


def bucket_language_breakdown(per_word, bucket):
    """
    For the bar-drill-down (task 2026-07-23): the specific languages that
    make up `bucket` for this analysis, sized by their share WITHIN that
    bucket (not the whole text). Native-inherited words (no specific donor
    language recorded) group under their own `depth_lang` label (e.g.
    "English (native core)"). Compound-split words contribute their parts
    individually, same convention as the main aggregation in analyzer.py.
    Returns a list of (language, pct, hex_color) sorted by share descending.
    """
    from collections import Counter
    counts = Counter()

    def _is_proto(lang):
        return lang is not None and (lang == "Proto-Indo-European" or lang.startswith("Proto-"))

    def _tally(view):
        if view.bucket != bucket:
            return
        specific = view.specific_lang
        if _is_proto(specific):
            # A proto-language name this deep in a Direct Source/Influence
            # chain means "still native inheritance, no separate attested
            # donor was ever recorded" -- not a real donor language, so it
            # shouldn't read as one in this breakdown (Deepest Root mode is
            # where naming the proto-form is the point; here it would just
            # look like "Proto-West Germanic" is a borrowing source).
            specific = None
        if specific is None and view.donor_iso == "eng" and view.depth_lang:
            # Native-core words (no chain at all) carry their real nearest
            # recorded stage name (e.g. "Old English", "Middle English") in
            # depth_lang instead of specific_lang -- see
            # WiktionaryResolver.resolve()'s native-core branch, fixed
            # 2026-07-24 (Joe: wants Old English/Middle English/etc. visible
            # here instead of one flat native label). donor_iso == "eng" is
            # the reliable signal this came from that branch specifically --
            # a chain-based (foreign-donor) word's depth_lang just repeats
            # the bucket name for direct/influence mode, which wouldn't be a
            # useful label here, so this fallback is scoped to exclude it.
            specific = view.depth_lang
        # Generic label only when truly nothing else is known -- a bare
        # proto-name that got filtered above, or (rare) no stage recorded.
        label = specific or "Native (inherited)"
        counts[label] += 1

    for view in per_word:
        if view.parts:
            for p in view.parts:
                _tally(p)
        else:
            _tally(view)

    total = sum(counts.values())
    if not total:
        return []
    shades = language_shades(bucket, list(counts.keys()))
    rows = [(lang, 100.0 * c / total, shades[lang]) for lang, c in counts.items()]
    rows.sort(key=lambda row: -row[1])
    return rows


def root_slug(w, mode):
    """Per-word swatch slug for the current mode -- the proto-language slug
    in Deepest Root mode when one applies, else the plain bucket slug."""
    if mode == "root" and w.depth_lang:
        base = w.depth_lang.removesuffix(" (from PIE)")
        if base in PROTO_SLUGS:
            return PROTO_SLUGS[base]
    return bucket_slug(w.bucket)


PAGE = """
<!doctype html>
<html>
<head>
  <title>Etymology Analyzer</title>
  <style>
    :root {
      --surface: #fcfcfb;
      --surface-2: #f2f1ed;
      --text-primary: #0b0b0b;
      --text-secondary: #52514e;
      --track-bg: #e1e0d9;
      --c-germanic: #2a78d6;
      --c-norse: #eb6834;
      --c-french: #1baf7a;
      --c-latin: #eda100;
      --c-greek: #e87ba4;
      --c-romance-other: #008300;
      --c-celtic: #4a3aa7;
      --c-pie: #e34948;
      --c-muted: #898781;
      /* "Unknown" (a true lookup failure) -- deliberately lighter/more
         washed-out than --c-muted, so it visually recedes as "nothing
         found" rather than reading as a real (if rare) category the way
         --c-muted's "Other"/Caribbean/etc. do. See bucket_slug() comment. */
      --c-unknown: #d6d4cc;
      /* Extended tier (hue~205, lower chroma -- see BUCKET_SLUGS comment in app.py) */
      --c-slavic: #156068;
      --c-indo-iranian: #30767e;
      --c-semitic: #488c94;
      --c-turkic: #5fa4ab;
      --c-east-asian: #77bbc3;
      /* Proto-language shades: validated lighter step of the parent hue */
      --c-proto-germanic: #75a7e9;
      --c-proto-west-germanic: #5391e0;
      --c-proto-italic: #a37734;
      --c-proto-celtic: #7d7ad1;
      --c-proto-slavic: #4e939a;
      --c-proto-indo-iranian: #61a5ad;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --surface: #1a1a19;
        --surface-2: #242422;
        --text-primary: #ffffff;
        --text-secondary: #c3c2b7;
        --track-bg: #2c2c2a;
        --c-germanic: #3987e5;
        --c-norse: #d95926;
        --c-french: #199e70;
        --c-latin: #c98500;
        --c-greek: #d55181;
        --c-romance-other: #008300;
        --c-celtic: #9085e9;
        --c-pie: #e66767;
        --c-muted: #898781;
        --c-unknown: #3a3a37;
        --c-slavic: #156068;
        --c-indo-iranian: #30767e;
        --c-semitic: #488c94;
        --c-turkic: #5fa4ab;
        --c-east-asian: #77bbc3;
        --c-proto-germanic: #75a7e9;
        --c-proto-west-germanic: #5391e0;
        --c-proto-italic: #a37734;
        --c-proto-celtic: #7d7ad1;
        --c-proto-slavic: #4e939a;
        --c-proto-indo-iranian: #61a5ad;
      }
    }
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem;
           background: var(--surface); color: var(--text-primary); }
    textarea { width: 100%; height: 160px; font-family: inherit; font-size: 1rem;
               background: var(--surface-2); color: var(--text-primary); border: 1px solid var(--track-bg); }
    .mode-toggle { margin: 0.75rem 0; }
    button { padding: 0.5rem 1.25rem; font-size: 1rem; }
    .bar-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.3rem 0; }
    .bar-swatch { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
    .bar-label { width: 150px; color: var(--text-primary); }
    .bar-track { flex: 1; background: var(--track-bg); height: 1rem; border-radius: 3px; overflow: hidden; }
    .bar-fill { height: 100%; }
    .bar-pct { width: 55px; text-align: right; color: var(--text-secondary); }
    /* Expandable bucket drill-down (task 2026-07-23): each bucket bar is a
       <details> disclosure -- native, no JS needed. The bar-row itself
       becomes the <summary> (a custom marker replaces the default triangle
       so it lines up with the swatch), sub-language bars nest and indent
       underneath, "tabbed over" like the etymology tree's own nesting. */
    details.bucket-details { margin: 0.3rem 0; }
    details.bucket-details > summary { list-style: none; cursor: pointer; }
    details.bucket-details > summary::-webkit-details-marker { display: none; }
    details.bucket-details > summary .bar-row { margin: 0; }
    details.bucket-details .expand-arrow { width: 0.9rem; color: var(--text-secondary);
                flex-shrink: 0; transition: transform 0.15s ease; }
    details.bucket-details[open] .expand-arrow { transform: rotate(90deg); }
    .sub-bars { margin: 0.3rem 0 0.6rem 1.6rem; padding-left: 0.75rem;
                border-left: 1px dashed var(--track-bg); }
    .sub-bar-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.2rem 0; }
    .sub-bar-swatch { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
    .sub-bar-label { width: 170px; font-size: 0.85rem; color: var(--text-secondary); }
    .sub-bar-track { flex: 1; background: var(--track-bg); height: 0.7rem; border-radius: 3px; overflow: hidden; }
    .sub-bar-fill { height: 100%; }
    .sub-bar-pct { width: 48px; text-align: right; font-size: 0.8rem; color: var(--text-secondary); }
    .stats { color: var(--text-secondary); margin: 1rem 0; }
    .words { font-size: 0.9rem; color: var(--text-primary); line-height: 1.8; }
    .word-tag { display: inline-block; margin: 0.15rem; padding: 0.1rem 0.5rem;
                border-radius: 3px; background: var(--surface-2); border-left: 4px solid var(--c-muted); }
    /* Compound-split display (compounds.py): the whole tag drops the plain
       border-left swatch (there's no single answer to swatch) and instead
       underlines the original word to mark it as "shown split", with each
       component rendered as its own mini colored chip. */
    .word-tag.compound { border-left: none; padding-left: 0.3rem; }
    .compound-word { font-weight: 600; text-decoration: underline dotted var(--text-secondary);
                      text-underline-offset: 3px; }
    .compound-part { display: inline-block; margin-left: 0.3rem; padding: 0.05rem 0.4rem;
                      border-radius: 3px; background: var(--surface); border-left: 3px solid var(--c-muted);
                      font-size: 0.85rem; color: var(--text-secondary); }
    .compound-plus { margin: 0 0.15rem; color: var(--text-secondary); }
    .word-count { color: var(--text-secondary); font-size: 0.8rem; }
    /* Unknown words get a dashed border + reduced opacity, not just a
       lighter fill -- a texture/shape difference reads as "no answer"
       unmistakably, not just a subtle shade shift someone could miss. */
    .word-tag.unknown { border-left-style: dashed; opacity: 0.65; }
    .tree-lookup { margin: 1.5rem 0; padding-top: 1rem; border-top: 1px solid var(--track-bg); }
    .tree-lookup input[type=text] { font-size: 1rem; padding: 0.35rem 0.5rem;
                background: var(--surface-2); color: var(--text-primary); border: 1px solid var(--track-bg); }
    .tree-branches { list-style: none; margin: 0.5rem 0 0; padding: 0; }
    .tree-branches ul { list-style: none; margin: 0.15rem 0 0 1.1rem; padding: 0;
                         border-left: 1px dashed var(--track-bg); padding-left: 0.9rem; }
    .tree-branches li { margin: 0.15rem 0; }
    .tree-node { display: inline-block; padding: 0.05rem 0.5rem; border-radius: 3px;
                 background: var(--surface-2); border-left: 4px solid var(--c-muted); font-size: 0.9rem; }
    .tree-node .tree-lang { color: var(--text-secondary); }
    .tree-node .tree-term { font-style: italic; margin-left: 0.35rem; }
    .tree-error { color: var(--text-secondary); font-size: 0.9rem; }
    .tree-view-toggle { margin-left: 1rem; font-size: 0.9rem; color: var(--text-secondary); }
    .tree-view-toggle label { margin-right: 0.5rem; }
    .tree-diagram { max-width: 100%; height: auto; display: block; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>Etymology Analyzer</h1>
  <form method="post">
    <input type="hidden" name="form" value="analyze">
    <textarea name="text" placeholder="Paste a paragraph...">{{ text }}</textarea>
    <div class="mode-toggle">
      <label><input type="radio" name="mode" value="direct" {{ 'checked' if mode == 'direct' else '' }}> Direct Source</label>
      &nbsp;&nbsp;
      <label><input type="radio" name="mode" value="influence" {{ 'checked' if mode == 'influence' else '' }}> Notable Influence</label>
      &nbsp;&nbsp;
      <label><input type="radio" name="mode" value="root" {{ 'checked' if mode == 'root' else '' }}> Deepest Root</label>
    </div>
    <div class="mode-toggle">
      <label><input type="checkbox" name="exclude_connectors" {{ 'checked' if exclude_connectors else '' }}>
        Exclude connector words (a, the, to, of, and, ...)</label>
    </div>
    <div class="mode-toggle">
      <label>Per-word order:
        <select name="word_sort">
          <option value="input" {{ 'selected' if word_sort == 'input' else '' }}>Input order</option>
          <option value="language" {{ 'selected' if word_sort == 'language' else '' }}>Language group</option>
          <option value="alpha" {{ 'selected' if word_sort == 'alpha' else '' }}>Alphabetical</option>
          <option value="distinctive" {{ 'selected' if word_sort == 'distinctive' else '' }}>Most distinctive first</option>
          <option value="frequency" {{ 'selected' if word_sort == 'frequency' else '' }}>Most frequent</option>
        </select>
      </label>
    </div>
    <button type="submit">Analyze</button>
  </form>

  {% if analysis %}
  <div class="stats">
    Tokens: {{ analysis.total_tokens }} &middot;
    Classified: {{ "%g"|format(analysis.resolved_tokens) }} ({{ "%.1f"|format(analysis.coverage) }}% coverage) &middot;
    Unknown: {{ "%g"|format(analysis.unknown_tokens) }} &middot;
    {{ "%.1f"|format(analysis.approximate_share) }}% of classified lean on the Germanic approximation
  </div>

  {% for bucket, pct in analysis.by_resolved.items() %}
  {% set sub_rows = bucket_breakdown(analysis.per_word, bucket) %}
  <details class="bucket-details">
    <summary>
      <div class="bar-row">
        <span class="expand-arrow">&#9656;</span>
        <div class="bar-swatch" style="background: var(--c-{{ bucket_slug(bucket) }})"></div>
        <div class="bar-label">{{ bucket }}</div>
        <div class="bar-track"><div class="bar-fill" style="width: {{ pct }}%; background: var(--c-{{ bucket_slug(bucket) }})"></div></div>
        <div class="bar-pct">{{ "%.1f"|format(pct) }}%</div>
      </div>
    </summary>
    {% if sub_rows %}
    <div class="sub-bars">
      {% for lang, sub_pct, hex in sub_rows %}
      <div class="sub-bar-row">
        <div class="sub-bar-swatch" style="background: {{ hex }}"></div>
        <div class="sub-bar-label">{{ lang }}</div>
        <div class="sub-bar-track"><div class="sub-bar-fill" style="width: {{ sub_pct }}%; background: {{ hex }}"></div></div>
        <div class="sub-bar-pct">{{ "%.1f"|format(sub_pct) }}%</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </details>
  {% endfor %}

  <h3>Per word</h3>
  <div class="words">
    {% for w, count in word_rows %}
      {% if w.parts %}
      <span class="word-tag compound" title="not in our database on its own -- shown as its two component words">
        <span class="compound-word">{{ w.word }}</span>{% if count %} <span class="word-count">&times;{{ count }}</span>{% endif %} &rarr;
        {%- for p in w.parts %}
        <span class="compound-part" style="border-left-color: var(--c-{{ root_slug(p, analysis.mode) }})">{{ p.word }}
          {%- if analysis.mode == 'root' and p.depth_lang and p.depth_lang != p.bucket %} {{ p.depth_lang }}
          {%- else %} {{ p.bucket }}
          {%- endif %}</span>{% if not loop.last %}<span class="compound-plus">+</span>{% endif %}
        {%- endfor %}
      </span>
      {% else %}
      <span class="word-tag{{ ' unknown' if w.bucket == 'Unknown' else '' }}" style="border-left-color: var(--c-{{ root_slug(w, analysis.mode) }})">{{ w.word }}{% if count %} <span class="word-count">&times;{{ count }}</span>{% endif %} &rarr;
        {%- if analysis.mode == 'root' and w.depth_lang and w.depth_lang != w.bucket %} {{ w.depth_lang }}
        {%- else %} {{ w.bucket }}
        {%- endif %}</span>
      {% endif %}
    {% endfor %}
  </div>
  {% endif %}

  {% macro render_branch(node) %}
  <li>
    <span class="tree-node" style="border-left-color: var(--c-{{ node_slug(node) }})">
      <span class="tree-lang">{{ node.lang }}</span>{% if node.term %}<span class="tree-term">{{ node.term }}</span>{% endif %}
    </span>
    {% if node.children %}
    <ul>
      {% for child in node.children %}{{ render_branch(child) }}{% endfor %}
    </ul>
    {% endif %}
  </li>
  {% endmacro %}

  <div class="tree-lookup">
    <h3>Etymology tree</h3>
    <form method="post">
      <input type="hidden" name="form" value="tree">
      <input type="text" name="tree_word" placeholder="Look up a word..." value="{{ tree_word }}">
      <button type="submit">Show tree</button>
      <span class="tree-view-toggle">
        <label><input type="radio" name="tree_view" value="list" {{ 'checked' if tree_view == 'list' else '' }}> List</label>
        <label><input type="radio" name="tree_view" value="diagram" {{ 'checked' if tree_view == 'diagram' else '' }}> Diagram</label>
      </span>
    </form>
    {% if tree_word %}
      {% if tree %}
        {% if tree_view == 'diagram' %}
          {% set d = build_diagram(tree) %}
          {% if d %}
          <svg class="tree-diagram" width="{{ d.width }}" height="{{ d.height }}" viewBox="0 0 {{ d.width }} {{ d.height }}">
            {% for e in d.edges %}
            <line x1="{{ e.x1 }}" y1="{{ e.y1 }}" x2="{{ e.x2 }}" y2="{{ e.y2 }}" stroke="var(--track-bg)" stroke-width="2" />
            {% endfor %}
            {% for n in d.nodes %}
            <rect x="{{ n.x }}" y="{{ n.y }}" width="{{ n.w }}" height="{{ n.h }}" rx="6" fill="var(--surface-2)" stroke="{{ n.color }}" stroke-width="3" />
            <text x="{{ n.x + 10 }}" y="{{ n.y + 16 }}" font-size="11" fill="var(--text-secondary)">{{ n.lang }}</text>
            <text x="{{ n.x + 10 }}" y="{{ n.y + 31 }}" font-size="12" font-style="italic" fill="var(--text-primary)">{{ n.term or '' }}{% if n.term2 %} / {{ n.term2 }}{% endif %}</text>
            {% endfor %}
          </svg>
          {% endif %}
        {% else %}
        <ul class="tree-branches">
          {% for branch in tree.branches %}{{ render_branch(branch) }}{% endfor %}
        </ul>
        {% endif %}
      {% else %}
      <p class="tree-error">No recorded etymology data for "{{ tree_word }}".</p>
      {% endif %}
    {% endif %}
  </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    text = ""
    mode = "direct"
    exclude_connectors = False
    word_sort = "input"
    analysis = None
    word_rows = []
    tree_word = ""
    tree = None
    tree_view = "list"
    if request.method == "POST" and request.form.get("form") == "tree":
        tree_word = request.form.get("tree_word", "").strip()
        tree_view = request.form.get("tree_view", "list")
        if tree_word:
            # Same case-fallback convention as WiktionaryResolver.resolve():
            # lowercase first (the common case), then as-typed, then title
            # case (for a word that only exists capitalized).
            tree = (TREES.get(tree_word.lower())
                    or TREES.get(tree_word)
                    or TREES.get(tree_word.capitalize()))
    elif request.method == "POST":
        text = request.form.get("text", "")
        mode = request.form.get("mode", "direct")
        exclude_connectors = request.form.get("exclude_connectors") == "on"
        word_sort = request.form.get("word_sort", "input")
        if text.strip():
            analysis = analyze(text, mode=mode, exclude_connectors=exclude_connectors)
            word_rows = sort_per_word(analysis.per_word, word_sort)
    return render_template_string(PAGE, text=text, mode=mode, analysis=analysis,
                                   exclude_connectors=exclude_connectors,
                                   word_sort=word_sort, word_rows=word_rows,
                                   tree_word=tree_word, tree=tree, tree_view=tree_view,
                                   bucket_slug=bucket_slug, root_slug=root_slug,
                                   node_slug=node_slug, bucket_breakdown=bucket_language_breakdown,
                                   build_diagram=build_diagram)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
