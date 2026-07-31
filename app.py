"""
Minimal local web UI for testing the analyzer. Not the planned Java/Spring
backend -- a throwaway Flask wrapper around analyze() so results can be viewed
in a browser instead of a terminal.

Run: python app.py
Then open http://localhost:5000
"""
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass

from flask import Flask, render_template_string, request

from analyzer import analyze
from buckets import BUCKET_ORDER
from buckets_wikt import bucket_for_name
import linguistics
from palette import (PROTO_SLUGS, THEME_CSS,
                     bucket_slug, root_slug, language_shades)
from word_trees import (resolve_tree, build_diagram, node_slug,
                        root_gloss, is_reconstructed, wiktionary_url)
from resolver import shared_resolver
import descendants
import inflections
import shakespeare
import word_info

app = Flask(__name__)

# Single shared resolver instance, added 2026-07-24 (Joe, all-caps: every
# feature/function must use the SAME database -- no feature should have
# access to word data another doesn't). Previously each `analyze()` call
# built its own resolver from scratch (reloading wikt_words.json every
# request), and the etymology-tree feature read ONLY etymology_trees.json
# with no knowledge of compounds.py/auto_compounds at all -- so a compound
# word like "mindset" correctly split in the analyzer but showed "No
# recorded etymology data" in the tree. Both features now read through this
# one instance: `analyze()` below is passed `resolver=RESOLVER` explicitly,
# and `resolve_tree()` (now in word_trees.py) consults the same one.
#
# `shared_resolver()`, not `default_resolver()`: the tree code moved out of
# this module in the 2026-07-27 audit, and a second `default_resolver()` call
# there would have built a SECOND ~100MB stack -- and, worse, one that could
# answer differently. The shared accessor makes one instance the only thing
# either module can get.
RESOLVER = shared_resolver()

# "Core" families for the Most Distinctive sort -- same set resolver.py's
# _pick_influence uses to decide what counts as an unremarkable, expected
# donor vs. a notable/rare one.
_CORE_FAMILIES = {"Germanic", "Norse", "French", "Latin", "Greek",
                   "Romance (other)", "Celtic", "PIE"}


def _has_definition(rec):
    return bool(rec and (rec.get("gloss") or rec.get("pos")))


def _definition_for(word, rec, res):
    """
    (record, base_word) -- falling back to the base form's definition.

    An inflected form (`wolves`, `hidden`) has no dictionary entry of its own;
    Wiktionary defines the base word. The base is returned alongside so the
    card can SAY which word it defined, and never implies the definition
    belongs to the surface form.
    """
    if _has_definition(rec):
        return rec, None
    candidate = inflections.base_form(word) or res.inherited_from
    if not candidate or candidate.lower() == word.lower():
        return rec, None
    base_rec = word_info.lookup(candidate)
    if not _has_definition(base_rec):
        return rec, None
    return base_rec, candidate


def _lineage_steps(res):
    """The mini lineage for the hover card: each distinct language, once."""
    if not res.chain:
        if res.english_stage_lang:
            return [{"lang": res.english_stage_lang, "bucket": "Germanic"}]
        return []
    steps, seen = [], set()
    for link in res.chain:
        lang = link.specific_lang or link.lang
        if lang and lang not in seen:
            seen.add(lang)
            steps.append({"lang": lang, "bucket": link.bucket})
    return steps


def build_word_card(word):
    """
    Everything the hover card shows for one word: part of speech, definition,
    and its direct lineage. Added 2026-07-25 (Joe: hovering a word should give
    its definition/type, a mini lineage, and a way to search it).

    Lineage comes from the Resolution's OWN already-computed chain
    (`chain_langs` where available, else the bucket names), NOT from
    resolve_tree(). That's deliberate: resolve_tree costs a resolver hit per
    miss and returns the full multi-branch structure, which is far more than a
    tooltip needs and far too slow to do for every word in a pasted text.
    Reading the chain keeps the card in lockstep with the bar-graph answer the
    analyzer already gave for that same word -- one database, one answer, per
    this module's RESOLVER note above.

    Returns None when there's nothing worth showing, so the template can skip
    the card entirely rather than render an empty box.
    """
    rec = word_info.lookup(word)
    res = RESOLVER.resolve(word)
    rec, base = _definition_for(word, rec, res)
    lineage = _lineage_steps(res)

    pos = ", ".join(rec["pos"]) if rec and rec.get("pos") else None
    gloss = rec.get("gloss") if rec else None
    # An ANNOTATION, deliberately kept out of the origin answer (Joe,
    # 2026-07-30: "I dont want it to be in the language bucket or whatever,
    # just something on the side"). `shakespeare` is a leaf module that knows
    # nothing about buckets, so this cannot move a percentage.
    bard = shakespeare.is_shakespearean(word)
    if not (pos or gloss or lineage or bard):
        return None
    return {"pos": pos, "gloss": gloss, "lineage": lineage,
            "defined_by": base, "inherited_from": res.inherited_from,
            "shakespeare": bard, "shakespeare_note": shakespeare.note(word)}


def _dedupe_keep_order(per_word):
    """
    Collapse repeated words to one row each, carrying an occurrence count and
    keeping first-appearance order. Extracted 2026-07-25 from the "frequency"
    branch below so the new collapse-duplicates toggle reuses the exact same
    counting rather than growing a second, subtly-different implementation.
    """
    counts = Counter(w.word for w in per_word)
    first_seen = {}
    for w in per_word:
        first_seen.setdefault(w.word, w)
    return counts, first_seen


def sort_per_word(per_word, word_sort, collapse_duplicates=False):
    """
    Returns a list of (ResolvedView, count_or_None) pairs for the "Per word"
    section, added 2026-07-23 (Joe: filter the per-word results by language
    group, input order, "and a couple other interesting filters"). Display-
    only -- doesn't touch Analysis/per_word itself (input order stays the
    source of truth for the percentage breakdown).

    `collapse_duplicates` (2026-07-25, Joe: "toggle off duplicated words in
    the main search function") shows each unique word once with an occurrence
    count. Also display-only, and deliberately so: a word used 10 times really
    is 10 tokens of its language in that text, so deduping the STATS would
    silently change what the tool measures from "share of this text" to
    "share of this vocabulary". Those are both legitimate views, but the
    second is a different feature and shouldn't arrive disguised as a display
    toggle. "frequency" sort already implies collapsing, so it's unaffected.
    """
    if word_sort == "frequency":
        # Dedupe repeated words, most-repeated first -- most useful on long
        # texts/whole books where the same word appears many times. Already
        # collapsing by definition, so the toggle is a no-op here.
        counts, first_seen = _dedupe_keep_order(per_word)
        return [(first_seen[word], count) for word, count in counts.most_common()]

    counts = None
    if collapse_duplicates:
        counts, first_seen = _dedupe_keep_order(per_word)
        per_word = list(first_seen.values())

    if word_sort == "language":
        order = {b: i for i, b in enumerate(BUCKET_ORDER)}
        rows = sorted(per_word, key=lambda w: (order.get(w.bucket, 999), w.word))
    elif word_sort == "alpha":
        rows = sorted(per_word, key=lambda w: w.word)
    elif word_sort == "distinctive":
        # Rarest/most unexpected origins first -- surfaces the interesting
        # loanwords in a text instead of burying them under the Germanic/
        # French/Latin majority.
        rows = sorted(per_word, key=lambda w: (w.bucket in _CORE_FAMILIES, w.word))
    else:
        rows = per_word  # "input" (default): unchanged order

    return [(w, counts[w.word] if counts else None) for w in rows]

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

    _is_proto = linguistics.is_proto

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




PAGE = """
<!doctype html>
<html>
<head>
  <title>Etymology Analyzer</title>
  <style>
""" + THEME_CSS + """
    body { font-family: var(--serif); font-size: 1.02rem; line-height: 1.62;
           max-width: 860px; margin: 2.5rem auto 4rem; padding: 0 1.25rem;
           background: var(--surface); color: var(--text-primary);
           -webkit-font-smoothing: antialiased; }

    /* Masthead: a headword over a hairline, the way a dictionary entry opens.
       The rule does the work -- no banner, no box. */
    h1 { font-size: 1.95rem; font-weight: 600; letter-spacing: -0.01em;
         margin: 0 0 0.5rem; padding-bottom: 0.55rem;
         border-bottom: 2px solid var(--rule); }
    h2 { font-size: 1.3rem; font-weight: 600; margin: 2.2rem 0 0.7rem;
         padding-bottom: 0.3rem; border-bottom: 1px solid var(--rule); }
    h3 { font-size: 1.08rem; font-weight: 600; margin: 1.4rem 0 0.4rem; }
    a { color: var(--accent); text-underline-offset: 2px; }
    p { max-width: 64ch; }

    /* Instruments stay sans: a control that looks like prose invites being
       read as prose. Everything the user READS is serif; everything they
       OPERATE is not. */
    textarea, input, button, select,
    .stats, .hint, .bar-label, .bar-pct, .sub-bar-label, .sub-bar-pct,
    .word-count, .rel-more, .search-meta, .wc-cta, .tree-view-toggle {
      font-family: var(--sans);
    }
    textarea { width: 100%; height: 170px; font-size: 0.97rem; line-height: 1.5;
               padding: 0.7rem 0.8rem; border-radius: 3px;
               background: var(--surface-2); color: var(--text-primary);
               border: 1px solid var(--track-bg); }
    textarea:focus, input[type=text]:focus {
               outline: 2px solid var(--accent); outline-offset: 1px; }
    .mode-toggle { margin: 0.85rem 0; font-size: 0.9rem; }
    button { padding: 0.5rem 1.35rem; font-size: 0.95rem; border-radius: 3px;
             border: 1px solid var(--rule); background: var(--surface-2);
             color: var(--text-primary); cursor: pointer; }
    button:hover { border-color: var(--accent); color: var(--accent); }
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
    .tree-node { display: inline-block; padding: 0.08rem 0.5rem; border-radius: 3px;
                 background: var(--surface-2); border-left: 4px solid var(--c-muted); font-size: 0.94rem; }
    /* Reference-work conventions: the LANGUAGE is a label (small caps, muted,
       letterspaced) and the TERM is a cited foreign form (italic). Same
       distinction etymonline and print dictionaries draw, and it means a
       lineage reads as citation rather than as a list of tags. */
    .tree-node .tree-lang { color: var(--text-secondary); font-variant: small-caps;
                            letter-spacing: 0.03em; font-size: 0.92em; }
    .tree-node .tree-term { font-style: italic; margin-left: 0.35rem; }
    .tree-error { color: var(--text-secondary); font-size: 0.9rem; }
    .tree-view-toggle { margin-left: 1rem; font-size: 0.9rem; color: var(--text-secondary); }
    .tree-view-toggle label { margin-right: 0.5rem; }
    .tree-diagram { max-width: 100%; height: auto; display: block; margin-top: 0.5rem; }

    /* Hover cards (2026-07-25). Pure CSS -- this app has no JavaScript, by
       design (see the <details> drill-down and the server-computed SVG
       diagram). Card markup is pre-rendered inside each word tag and simply
       revealed on hover/focus-within, so it also works for keyboard users
       tabbing through the word links. */
    .hint { font-size: 0.85rem; color: var(--text-secondary); margin: 0.2rem 0 0.5rem; }
    .word-tag.has-card { position: relative; }
    .word-link { color: inherit; text-decoration: none; border-bottom: 1px dotted var(--text-secondary); }
    .word-link:hover { border-bottom-style: solid; }
    .word-card {
      display: none; position: absolute; left: 0; top: 100%; z-index: 40;
      min-width: 15rem; max-width: 22rem; margin-top: 0.3rem;
      padding: 0.5rem 0.65rem; border-radius: 5px;
      background: var(--surface); border: 1px solid var(--track-bg);
      box-shadow: 0 4px 14px rgba(0,0,0,0.16);
      font-size: 0.85rem; line-height: 1.35; white-space: normal; text-align: left;
      cursor: default;
    }
    .word-tag.has-card:hover .word-card,
    .word-tag.has-card:focus-within .word-card { display: block; }
    /* Flip to the right edge for tags near the end of a line, so the card
       doesn't run off-screen. Pure-CSS approximation of edge detection. */
    .words .word-tag.has-card:nth-child(n) .word-card { left: 0; right: auto; }
    .wc-head { display: block; font-weight: 600; }
    .wc-pos { margin-left: 0.4rem; font-weight: 400; font-style: italic; color: var(--text-secondary); }
    .wc-gloss { display: block; margin-top: 0.25rem; color: var(--text-secondary); }
    .wc-lineage { display: block; margin-top: 0.4rem; }
    .wc-step {
      display: inline-block; margin: 0.1rem 0; padding: 0.02rem 0.35rem;
      background: var(--surface-2); border-left: 3px solid var(--c-muted); border-radius: 3px;
    }
    .wc-arrow { color: var(--text-secondary); margin: 0 0.15rem; }
    .wc-note { display: block; margin-top: 0.35rem; font-style: italic; color: var(--text-secondary); }
    .wc-cta { display: block; margin-top: 0.4rem; font-size: 0.8rem; color: var(--text-secondary); }
    .wc-links { display: block; margin-top: 0.4rem; font-size: 0.8rem; }
    /* Shakespeare aside. Deliberately NOT a bucket colour -- it is an
       annotation, not an origin, and must not read as one. */
    .wc-bard { display: block; margin-top: 6px; padding: 5px 7px; font-size: 11px;
               line-height: 1.45; border-radius: 4px;
               background: color-mix(in srgb, var(--accent) 12%, transparent);
               color: var(--text-secondary); }
    .wc-bard-note { display: block; margin-top: 3px; font-style: italic; opacity: .85; }
    .word-bard { margin-left: 5px; font-size: 10px; opacity: .75; }
    .wc-wikt { color: var(--text-secondary); text-decoration: none; border-bottom: 1px dotted var(--text-secondary); }
    .wc-wikt:hover { border-bottom-style: solid; }
    /* Second link on the card, so it needs separating from the Wiktionary one
       and marking as the more interesting of the two -- it stays in-app. */
    .wc-desc { margin-left: 0.6rem; color: var(--accent); border-bottom-color: var(--accent); }

    /* Reconstructed-root meaning, shown on hover over a starred form in the
       tree (Joe 2026-07-26). Same pure-CSS pattern as .word-card above --
       pre-rendered server-side, revealed by :hover/:focus-within, no JS. */
    .tree-node.has-root-gloss { position: relative; }
    .tree-node.has-root-gloss .tree-term { border-bottom: 1px dashed var(--text-secondary); }
    .root-card {
      display: none; position: absolute; left: 0; top: 100%; z-index: 45;
      min-width: 14rem; max-width: 24rem; margin-top: 0.3rem;
      padding: 0.5rem 0.65rem; border-radius: 5px;
      background: var(--surface); border: 1px solid var(--track-bg);
      box-shadow: 0 4px 14px rgba(0,0,0,0.16);
      font-size: 0.85rem; line-height: 1.35; white-space: normal; text-align: left;
      font-style: normal; cursor: default;
    }
    .tree-node.has-root-gloss:hover .root-card,
    .tree-node.has-root-gloss:focus-within .root-card { display: block; }
    .rc-head { display: block; font-weight: 600; font-style: italic; }
    .rc-lang { margin-left: 0.4rem; font-weight: 400; font-style: normal;
               font-variant: small-caps; letter-spacing: 0.03em; color: var(--text-secondary); }
    .rc-gloss { display: block; margin-top: 0.25rem; }
    .rc-also { display: block; margin-top: 0.3rem; color: var(--text-secondary); }
    .rc-src { display: block; margin-top: 0.35rem; font-size: 0.78rem; font-style: italic;
              color: var(--text-secondary); }

    /* Word Search: cognates & doublets */
    .rel-section { margin-top: 1.1rem; }
    .rel-section h4 { margin: 0 0 0.15rem; font-size: 1rem; }
    .rel-explain { font-size: 0.85rem; color: var(--text-secondary); margin: 0 0 0.45rem; max-width: 46rem; }
    .rel-list { display: flex; flex-wrap: wrap; gap: 0.3rem; }
    .rel-item {
      display: inline-block; padding: 0.08rem 0.5rem; border-radius: 3px;
      background: var(--surface-2); border-left: 4px solid var(--c-muted); font-size: 0.9rem;
    }
    .rel-item { font-style: italic; }
    .rel-lang { color: var(--text-secondary); margin-right: 0.35rem; font-size: 0.85rem;
                font-style: normal; font-variant: small-caps; letter-spacing: 0.03em; }
    .rel-empty { font-size: 0.9rem; color: var(--text-secondary); font-style: italic; }
    .rel-more { font-size: 0.85rem; color: var(--text-secondary); }
    .search-meta { font-size: 0.9rem; color: var(--text-secondary); margin: 0.1rem 0 0.6rem; }
    .search-pos { font-style: italic; }
  </style>
</head>
<body>
  {# Hover card for one analyzed word: part of speech, definition, and its
     direct lineage. Content is pre-rendered server-side and revealed by a
     pure-CSS :hover rule -- no JavaScript anywhere, consistent with the
     <details> drill-down and the server-computed SVG diagram. #}
  {% macro word_card(word, note=None) %}
    {%- set card = word_cards.get(word) -%}
    {#- Resolved once here, because it also decides whether the card renders at
        all: ~12% of words WITH a descendant tree have no definition or lineage
        to show (obscure ones -- `dreigh`, `reke`), and gating the card on the
        definition alone hid the descendants link for exactly those. #}
    {%- set desc_form = descendant_form(card.defined_by if card and card.defined_by else word) -%}
    {%- if card or note or desc_form %}
    <span class="word-card">
      <span class="wc-head">{{ word }}{% if card and card.pos %}<span class="wc-pos">{{ card.pos }}</span>{% endif %}</span>
      {%- if card and card.defined_by %}<span class="wc-note">defined under &ldquo;{{ card.defined_by }}&rdquo;</span>{% endif %}
      {%- if card and card.gloss %}<span class="wc-gloss">{{ card.gloss }}</span>{% endif %}
      {%- if card and card.lineage %}
      <span class="wc-lineage">
        {%- for step in card.lineage %}
        <span class="wc-step" style="border-left-color: var(--c-{{ bucket_slug(step.bucket) }})">{{ step.lang }}</span>
        {%- if not loop.last %}<span class="wc-arrow">&larr;</span>{% endif %}
        {%- endfor %}
      </span>
      {%- endif %}
      {%- if card and card.inherited_from %}<span class="wc-note">via {{ card.inherited_from }}</span>{% endif %}
      {#- An ASIDE, never part of the origin answer: it sits below the lineage
          and carries its own colour, so it cannot be mistaken for a bucket. -#}
      {%- if card and card.shakespeare %}
      <span class="wc-bard">&#127917; popularized by Shakespeare
        {%- if card.shakespeare_note %}<span class="wc-bard-note">{{ card.shakespeare_note }}</span>{% endif %}
      </span>
      {%- endif %}
      {%- if note %}<span class="wc-note">{{ note }}</span>{% endif %}
      <span class="wc-cta">click to search &rarr;</span>
      {#- Straight to the source, for checking an answer against Wiktionary
          itself. Links the word the definition actually belongs to, so an
          inflected form points at the entry that has the content. #}
      {#- Descendants, when this word is actually in a stored tree (see the
          `desc_form` note at the top of this macro). Shown on the hover card
          rather than as a second clickable region on the chip itself: the
          chip's own click already means "search this word", and two competing
          click targets on one small chip is how you get people landing
          somewhere they didn't intend. #}
      <span class="wc-links"><a class="wc-wikt" href="{{ wiktionary_url((card.defined_by if card and card.defined_by else word)) }}" target="_blank" rel="noopener">Wiktionary &#8599;</a>
        {%- if desc_form %}
        <a class="wc-wikt wc-desc" href="/descendants?word={{ desc_form|urlencode }}">descendants &rarr;</a>
        {%- endif %}</span>
    </span>
    {%- endif %}
  {% endmacro %}

  <h1>Etymology Analyzer</h1>
  <p class="sub">Where English words come from &mdash; and, the other way round,
     <a class="feature-link" href="/descendants">what descended from one ancestor &rarr;</a></p>

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
      <label><input type="checkbox" name="collapse_duplicates" {{ 'checked' if collapse_duplicates else '' }}>
        Collapse duplicate words (show each word once, with a count)</label>
      <span class="hint">Affects the word list below only &mdash; percentages still count every occurrence.</span>
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
  <p class="hint">Hover any word for its definition and lineage &middot; click to open it in Word Search</p>
  <div class="words">
    {% for w, count in word_rows %}
      {% if w.parts %}
      <span class="word-tag compound has-card">
        <a class="word-link" href="/?word={{ w.word|urlencode }}" target="_blank" rel="noopener"><span class="compound-word">{{ w.word }}</span></a>{% if count %} <span class="word-count">&times;{{ count }}</span>{% endif %} &rarr;
        {%- for p in w.parts %}
        <span class="compound-part" style="border-left-color: var(--c-{{ root_slug(p, analysis.mode) }})">{{ p.word }}
          {%- if analysis.mode == 'root' and p.depth_lang and p.depth_lang != p.bucket %} {{ p.depth_lang }}
          {%- else %} {{ p.bucket }}
          {%- endif %}</span>{% if not loop.last %}<span class="compound-plus">+</span>{% endif %}
        {%- endfor %}
        {{ word_card(w.word, "shown with the component words it is built from") }}
      </span>
      {% else %}
      <span class="word-tag has-card{{ ' unknown' if w.bucket == 'Unknown' else '' }}" style="border-left-color: var(--c-{{ root_slug(w, analysis.mode) }})"><a class="word-link" href="/?word={{ w.word|urlencode }}" target="_blank" rel="noopener">{{ w.word }}</a>{% if count %} <span class="word-count">&times;{{ count }}</span>{% endif %} &rarr;
        {%- if analysis.mode == 'root' and w.depth_lang and w.depth_lang != w.bucket %} {{ w.depth_lang }}
        {%- else %} {{ w.bucket }}
        {%- endif %}{{ word_card(w.word) }}</span>
      {% endif %}
    {% endfor %}
  </div>
  {% endif %}

  {% macro render_branch(node) %}
  {%- set rg = root_gloss(node.term) if is_reconstructed(node.term) else None %}
  <li>
    <span class="tree-node{{ ' has-root-gloss' if rg else '' }}" style="border-left-color: var(--c-{{ node_slug(node) }})">
      <span class="tree-lang">{{ node.lang }}</span>{% if node.term %}<a class="tree-term" href="{{ wiktionary_url(node.term, node.lang) }}" target="_blank" rel="noopener">{{ node.term }}</a>{% endif %}
      {%- if rg %}
      <span class="root-card">
        <span class="rc-head">{{ node.term }}<span class="rc-lang">{{ node.lang }}</span></span>
        <span class="rc-gloss">&ldquo;{{ rg.gloss }}&rdquo;</span>
        {%- if rg.also %}<span class="rc-also">also glossed: {{ rg.also|join('; ') }}</span>{% endif %}
        <span class="rc-src">as glossed in {{ rg.count }} Wiktionary {{ 'entry' if rg.count == 1 else 'entries' }} citing this form</span>
      </span>
      {%- endif %}
    </span>
    {% if node.children %}
    <ul>
      {% for child in node.children %}{{ render_branch(child) }}{% endfor %}
    </ul>
    {% endif %}
  </li>
  {% endmacro %}

  <div class="tree-lookup">
    <h3>Word search</h3>
    <form method="post">
      <input type="hidden" name="form" value="tree">
      <input type="text" name="tree_word" placeholder="Search a word..." value="{{ tree_word }}">
      <button type="submit">Search</button>
      <span class="tree-view-toggle">
        <label><input type="radio" name="tree_view" value="list" {{ 'checked' if tree_view == 'list' else '' }}> List</label>
        <label><input type="radio" name="tree_view" value="diagram" {{ 'checked' if tree_view == 'diagram' else '' }}> Diagram</label>
      </span>
    </form>
    {% if tree_word %}
      {% if info and (info.pos or info.gloss) %}
      <p class="search-meta">
        {%- if info.pos %}<span class="search-pos">{{ info.pos|join(', ') }}</span>{% endif %}
        {%- if info.pos and info.gloss %} &middot; {% endif %}
        {%- if info.gloss %}{{ info.gloss }}{% endif %}
      </p>
      {% endif %}
      {# The source, one click away -- every answer on this page should be
         checkable against the page it was derived from. Alongside it, the
         same word read the OTHER way: this tree runs up to the ancestors,
         /descendants runs down from them. #}
      {#- The descendants link is CONDITIONAL: only ~3,800 English words sit in
          a stored tree, and offering it for the rest sent the reader to an
          empty page (Joe, 2026-07-27). `descendant_form` also returns the
          spelling that actually resolves, so a capitalised search still links
          a working one. #}
      {%- set desc_form = descendant_form(tree_word) %}
      <p class="search-meta"><a class="wc-wikt" href="{{ wiktionary_url(tree_word) }}" target="_blank" rel="noopener">&ldquo;{{ tree_word }}&rdquo; on Wiktionary &#8599;</a>
        {%- if desc_form %}
        &nbsp;&middot;&nbsp;
        <a class="feature-link" href="/descendants?word={{ desc_form|urlencode }}">what descended from its root &rarr;</a>
        {%- endif %}</p>
      {#- The same aside the analyzer's hover card shows. Both features read
          one leaf module, so they cannot disagree about a word (issue #16). -#}
      {%- if bard %}
      <p class="wc-bard">&#127917; popularized by Shakespeare
        {%- if bard_note %}<span class="wc-bard-note">{{ bard_note }}</span>{% endif %}
      </p>
      {%- endif %}
      {% if tree %}
        {% if tree_view == 'diagram' %}
          {% set d = build_diagram(tree) %}
          {% if d %}
          <svg class="tree-diagram" width="{{ d.width }}" height="{{ d.height }}" viewBox="0 0 {{ d.width }} {{ d.height }}">
            {% for e in d.edges %}
            <line x1="{{ e.x1 }}" y1="{{ e.y1 }}" x2="{{ e.x2 }}" y2="{{ e.y2 }}" stroke="var(--track-bg)" stroke-width="2" />
            {% endfor %}
            {% for n in d.nodes %}
            {#- The list view reveals a styled card on hover; inside SVG the
                equivalent is a <title> child, which browsers show as a native
                tooltip. Same data, same source, rendered the way each medium
                supports. #}
            {%- set rg = root_gloss(n.term) if is_reconstructed(n.term) else None %}
            <g>
              {%- if rg %}<title>{{ n.term }} &mdash; "{{ rg.gloss }}"</title>{% endif %}
              <rect x="{{ n.x }}" y="{{ n.y }}" width="{{ n.w }}" height="{{ n.h }}" rx="6" fill="var(--surface-2)" stroke="{{ n.color }}" stroke-width="3" />
              <text x="{{ n.x + 10 }}" y="{{ n.y + 16 }}" font-size="11" fill="var(--text-secondary)">{{ n.lang }}</text>
              <text x="{{ n.x + 10 }}" y="{{ n.y + 31 }}" font-size="12" font-style="italic" fill="var(--text-primary)">{{ n.term or '' }}{% if n.term2 %} / {{ n.term2 }}{% endif %}{% if rg %} <tspan font-size="10" font-style="normal" fill="var(--text-secondary)">&#9432;</tspan>{% endif %}</text>
            </g>
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

      {# Cognates and doublets. These are SIBLING relations, deliberately kept
         out of the lineage tree above (a cognate is not an ancestor) -- see
         build_word_info.py. Both sections always render when a word was
         searched, with an explicit empty state, so "we have nothing" is
         distinguishable from "this feature didn't load". #}
      <div class="rel-section">
        <h4>Cognates</h4>
        <p class="rel-explain">A <strong>cognate</strong> is a word in another language descended from the same ancestor &mdash; related by shared descent, not borrowed from one another. English <em>shirt</em> and German <em>Sch&uuml;rze</em> both come down from the same Germanic root.</p>
        {% if info and info.cognates %}
        <div class="rel-list">
          {% for lang, term in info.cognates[:40] %}
          <span class="rel-item" style="border-left-color: var(--c-{{ bucket_slug(bucket_for_name(lang)) }})"><span class="rel-lang">{{ lang }}</span>{{ term }}</span>
          {% endfor %}
        </div>
        {% if info.cognates|length > 40 %}
        <p class="rel-more">&hellip; and {{ info.cognates|length - 40 }} more.</p>
        {% endif %}
        {% else %}
        <p class="rel-empty">No cognates recorded for "{{ tree_word }}".</p>
        {% endif %}
      </div>

      <div class="rel-section">
        <h4>Doublets</h4>
        <p class="rel-explain">A <strong>doublet</strong> is another word in <em>the same</em> language that traces back to the same root, but arrived by a different route and drifted apart in meaning &mdash; like <em>travel</em> and <em>travail</em>, or <em>shirt</em> and <em>skirt</em>.</p>
        {% if info and info.doublets %}
        <div class="rel-list">
          {% for term in info.doublets[:40] %}
          <a class="rel-item" href="/?word={{ term|urlencode }}">{{ term }}</a>
          {% endfor %}
        </div>
        {% else %}
        <p class="rel-empty">No doublets recorded for "{{ tree_word }}".</p>
        {% endif %}
      </div>
    {% endif %}
  </div>
</body>
</html>
"""


DESC_PAGE = """
<!doctype html>
<html>
<head>
  <title>Descendants &mdash; Etymology Analyzer</title>
  <style>
""" + THEME_CSS + """
    body { font-family: var(--serif); font-size: 1.02rem; line-height: 1.62;
           max-width: 1400px; margin: 1.6rem auto 2rem; padding: 0 1.25rem;
           background: var(--surface); color: var(--text-primary);
           -webkit-font-smoothing: antialiased; }
    h1 { font-size: 1.95rem; font-weight: 600; letter-spacing: -0.01em;
         margin: 0 0 0.5rem; padding-bottom: 0.55rem;
         border-bottom: 2px solid var(--rule); }
    a { color: var(--accent); text-underline-offset: 2px; }
    form { margin: 0 0 0.9rem; font-family: var(--sans); }
    input[type=text] { font-family: var(--sans); font-size: 0.95rem;
      padding: 0.4rem 0.55rem; border: 1px solid var(--rule); border-radius: 4px;
      background: var(--surface-2); color: var(--text-primary); min-width: 15rem; }
    button { font-family: var(--sans); font-size: 0.92rem; padding: 0.42rem 0.9rem;
      border: 1px solid var(--rule); border-radius: 4px; cursor: pointer;
      background: var(--surface-2); color: var(--text-primary); }
    button:hover { border-color: var(--accent); }
    .meta { font-family: var(--sans); font-size: 0.85rem; color: var(--text-secondary);
            margin: 0 0 0.6rem; }
    .meta b { color: var(--text-primary); font-weight: 600; }
    .warn { color: var(--accent); }
    /* The canvas. Fixed height with the SVG panning inside it: a 3,000-node
       tree is far taller than any screen, and letting the page itself grow
       would put the controls off-screen. */
    #canvas { border: 1px solid var(--rule); border-radius: 6px;
              background: var(--surface-2); overflow: hidden; height: 74vh; }
    #canvas svg { display: block; width: 100%; height: 100%; cursor: grab; }
    #canvas svg:active { cursor: grabbing; }
    .link { fill: none; stroke: var(--track-bg); stroke-width: 1.4px; }
    .node circle { stroke-width: 2px; }
    .node text { font-family: var(--serif); font-size: 12px; fill: var(--text-primary);
                 paint-order: stroke; stroke: var(--surface-2); stroke-width: 3px; }
    .node .lang { font-family: var(--sans); font-size: 9.5px;
                  fill: var(--text-secondary); letter-spacing: 0.02em; }
    .node.collapsed circle { stroke-dasharray: 2 1.6; }
    .node.match text { font-weight: 700; }
    .node.match circle { stroke: var(--accent); stroke-width: 3.5px; }
    .legend { font-family: var(--sans); font-size: 0.8rem; color: var(--text-secondary);
              margin-top: 0.5rem; }
    .legend span { margin-right: 1rem; }
    .dot { display: inline-block; width: 0.62rem; height: 0.62rem; border-radius: 50%;
           margin-right: 0.3rem; vertical-align: -1px; }
    .empty { padding: 2rem 0; color: var(--text-secondary); }
  </style>
</head>
<body>
  <h1>Descendants</h1>
  <p class="sub">Everything Wiktionary records as descending from one ancestral form &mdash;
     the reverse of the etymology tree. <a href="/">&larr; analyzer</a></p>

  <form method="get">
    <input type="text" name="word" value="{{ word }}" placeholder="brother, water, night...">
    <button type="submit">Show descendants</button>
  </form>

  {% if result %}
  <p class="meta">
    <b>{{ result.root_lang }} *{{ result.root_raw }}</b> &rarr;
    <b>{{ "{:,}".format(result.total_nodes) }}</b> recorded descendants
    {%- if result.truncated %} <span class="warn">&middot; showing the first
      {{ "{:,}".format(result.shown_nodes) }}, breadth-first</span>{% endif %}
    &middot; click a node to fold or unfold it &middot; drag to pan, scroll to zoom
    &middot; <button type="button" id="refit" style="padding:0.1rem 0.5rem;font-size:0.8rem">fit to screen</button>
  </p>
  <div id="canvas"></div>
  <p class="legend" id="legend"></p>
  <script src="/static/d3.v7.min.js"></script>
  <script>
    const DATA = {{ tree_json|safe }};

    // Colour comes from the server as a palette slug per node, so this view
    // uses the SAME validated bucket hues as the bar chart and the etymology
    // tree rather than inventing a second colour system.
    const colorOf = d => getComputedStyle(document.documentElement)
      .getPropertyValue('--c-' + (d.data.slug || 'muted')).trim() || '#898781';

    const el = document.getElementById('canvas');
    const W = el.clientWidth, H = el.clientHeight;
    const svg = d3.select('#canvas').append('svg')
        .attr('viewBox', [0, 0, W, H]);
    const g = svg.append('g');

    const zoom = d3.zoom().scaleExtent([0.05, 3])
        .on('zoom', ev => g.attr('transform', ev.transform));
    svg.call(zoom);

    const root = d3.hierarchy(DATA);
    // Row height is per-NODE, not a fixed canvas size: these trees vary from
    // 12 nodes to 3,000, and a fixed size would squash the big ones into an
    // unreadable band. Horizontal layout because language names are wide.
    const layout = d3.tree().nodeSize([30, 258]);

    // Start folded. `on_path` marks the chain to the searched word, so the
    // view opens showing exactly that thread through an otherwise closed tree
    // -- the alternative, 3,000 nodes at once, is unreadable.
    root.descendants().forEach(d => {
      d.id = d.data.lang + '|' + (d.data.term || '') + '|' + d.depth;
      if (d.children && !d.data.on_path && d.depth >= 1) {
        d._children = d.children; d.children = null;
      }
    });

    function update(source) {
      layout(root);
      const nodes = root.descendants(), links = root.links();
      let x0 = Infinity, x1 = -Infinity;
      nodes.forEach(d => { if (d.x < x0) x0 = d.x; if (d.x > x1) x1 = d.x; });

      const t = svg.transition().duration(220);

      const link = g.selectAll('path.link').data(links, d => d.target.id);
      link.enter().append('path').attr('class', 'link')
        .merge(link).transition(t)
          .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x));
      link.exit().remove();

      const node = g.selectAll('g.node').data(nodes, d => d.id);
      const enter = node.enter().append('g')
          .attr('class', 'node')
          .attr('transform', d => `translate(${source.y0 || d.y},${source.x0 || d.x})`)
          .style('cursor', d => (d.children || d._children) ? 'pointer' : 'default')
          .on('click', (ev, d) => {
            if (d.children) { d._children = d.children; d.children = null; }
            else if (d._children) { d.children = d._children; d._children = null; }
            update(d);
          });
      enter.append('circle').attr('r', 4.5);
      enter.append('text').attr('class', 'lang')
          .attr('dy', '-0.55em').attr('x', 8).text(d => d.data.lang || '');
      // A merged variant node can carry a dozen spellings; printing them all
      // runs straight through the next column. Show three, keep the rest in
      // the tooltip -- hidden, not dropped.
      enter.append('text')
          .attr('dy', '0.72em').attr('x', 8)
          .text(d => {
            const term = d.data.raw_term || d.data.term || '';
            const parts = term.split(', ');
            let label = parts.length > 3
              ? parts.slice(0, 3).join(', ') + ` +${parts.length - 3}`
              : term;
            if (d.data.pruned) label += ` (+${d.data.pruned.toLocaleString()} more)`;
            return label;
          })
          .append('title').text(d => d.data.raw_term || d.data.term || '');

      const all = enter.merge(node);
      all.classed('collapsed', d => !!d._children)
         .classed('match', d => !!d.data.match);
      all.select('circle')
         .attr('fill', d => d._children ? colorOf(d) : 'var(--surface-2)')
         .attr('stroke', colorOf);
      all.transition(t).attr('transform', d => `translate(${d.y},${d.x})`);
      node.exit().remove();

      nodes.forEach(d => { d.x0 = d.x; d.y0 = d.y; });
    }

    root.x0 = 0; root.y0 = 0;
    update(root);

    // Fit whatever is open to the canvas on first paint. d3.tree() with
    // nodeSize puts the root at the origin, so without this a wide tree opens
    // with its modern-language end off the right edge -- which is exactly the
    // end the user searched for. Measured from the real bounding box rather
    // than a guessed scale, because tree width varies hugely by word.
    function fit(animate) {
      const b = g.node().getBBox();
      if (!b.width || !b.height) return;
      const scale = Math.min(1, 0.92 * Math.min(W / b.width, H / b.height));
      const tx = (W - b.width * scale) / 2 - b.x * scale;
      const ty = (H - b.height * scale) / 2 - b.y * scale;
      const target = d3.zoomIdentity.translate(tx, ty).scale(scale);
      (animate ? svg.transition().duration(280) : svg).call(zoom.transform, target);
    }
    fit(false);
    document.getElementById('refit').addEventListener('click', () => fit(true));

    // Legend from what is actually on screen, not a fixed list.
    const seen = new Map();
    root.descendants().forEach(d => {
      if (d.data.bucket && !seen.has(d.data.bucket)) seen.set(d.data.bucket, d.data.slug);
    });
    document.getElementById('legend').innerHTML =
      [...seen].slice(0, 12).map(([b, s]) =>
        `<span><i class="dot" style="background:var(--c-${s})"></i>${b}</span>`).join('');
  </script>
  {% elif word %}
  <p class="empty">No recorded descendants for &ldquo;{{ word }}&rdquo;.
     Coverage today is the Proto-Indo-European and Proto-Germanic branches
     &mdash; try <a href="/descendants?word=brother">brother</a>,
     <a href="/descendants?word=water">water</a> or
     <a href="/descendants?word=night">night</a>.</p>
  {% else %}
  <p class="empty">Try <a href="/descendants?word=brother">brother</a>,
     <a href="/descendants?word=water">water</a>,
     <a href="/descendants?word=king">king</a> or
     <a href="/descendants?word=night">night</a>.</p>
  {% endif %}
</body>
</html>
"""


def _decorate(node):
    """
    Tag every node with the palette slug its language maps to, server-side.

    Deliberately not done in JavaScript: `bucket_for_name` is the same taxonomy
    the bar chart and the etymology tree use, and reimplementing it in the
    browser would be a second copy free to drift -- the exact failure mode the
    2026-07-24 one-database rule exists to prevent.
    """
    lang = node.get("lang") or ""
    bucket = bucket_for_name(lang) if lang else "Other"
    node["bucket"] = bucket
    node["slug"] = root_slug_for_lang(lang)
    for kid in node.get("children") or ():
        _decorate(kid)
    return node


def root_slug_for_lang(lang):
    """Palette slug for a language name, preferring the proto-specific shade
    (Proto-Germanic has its own validated lighter hue) over the family bucket."""
    if lang in PROTO_SLUGS:
        return PROTO_SLUGS[lang]
    return bucket_slug(bucket_for_name(lang)) if lang else "muted"


@app.route("/descendants")
def descendants_view():
    word = (request.args.get("word") or "").strip()
    result = descendants.full_tree(word) if word else None
    tree_json = "null"
    if result:
        tree_json = json.dumps(_decorate(result["tree"]), ensure_ascii=False)
    return render_template_string(DESC_PAGE, word=word, result=result,
                                   tree_json=tree_json)



@dataclass
class _Request:
    """
    What the page was asked for -- one record instead of eleven locals.

    The route has three entry shapes (analyze a paragraph, search a word by
    POST, search a word by GET link) and every one of them had to initialise
    every variable the template reads. That is why a GET once rendered a blank
    page: it matched neither POST branch and left the defaults in place.
    """
    text: str = ""
    mode: str = "direct"
    exclude_connectors: bool = False
    collapse_duplicates: bool = False
    word_sort: str = "input"
    tree_word: str = ""
    tree_view: str = "list"


def _read_request(req) -> _Request:
    """Pull the form or query string into one record, per entry shape."""
    if req.method == "POST" and req.form.get("form") == "tree":
        return _Request(tree_word=req.form.get("tree_word", "").strip(),
                        tree_view=req.form.get("tree_view", "list"))
    if req.method == "POST":
        return _Request(
            text=req.form.get("text", ""),
            mode=req.form.get("mode", "direct"),
            exclude_connectors=req.form.get("exclude_connectors") == "on",
            collapse_duplicates=req.form.get("collapse_duplicates") == "on",
            word_sort=req.form.get("word_sort", "input"))
    # GET with ?word=... so an analyzed word can be a real clickable link into
    # Word Search. Before this existed a GET matched neither POST branch and
    # silently rendered an empty page.
    return _Request(tree_word=req.args.get("word", "").strip(),
                    tree_view=req.args.get("tree_view", "list"))


def _cards_for(analysis):
    """
    Hover-card data for each UNIQUE word, components included.

    Precomputed here rather than inside the Jinja loop: a long text repeats
    words many times and each card costs a real resolve.
    """
    if analysis is None:
        return {}
    cards = {}
    for view in analysis.per_word:
        for one in [view] + list(view.parts or []):
            if one.word not in cards:
                cards[one.word] = build_word_card(one.word)
    return cards


@app.route("/", methods=["GET", "POST"])
def index():
    asked = _read_request(request)
    text, mode = asked.text, asked.mode
    exclude_connectors = asked.exclude_connectors
    collapse_duplicates = asked.collapse_duplicates
    word_sort, tree_word, tree_view = asked.word_sort, asked.tree_word, asked.tree_view

    analysis, word_rows = None, []
    if text.strip():
        analysis = analyze(text, resolver=RESOLVER, mode=mode,
                           exclude_connectors=exclude_connectors)
        word_rows = sort_per_word(analysis.per_word, word_sort,
                                  collapse_duplicates=collapse_duplicates)

    tree = resolve_tree(tree_word) if tree_word else None
    info = word_info.lookup(tree_word) if tree_word else None
    word_cards = _cards_for(analysis)

    return render_template_string(PAGE, text=text, mode=mode, analysis=analysis,
                                   exclude_connectors=exclude_connectors,
                                   collapse_duplicates=collapse_duplicates,
                                   word_sort=word_sort, word_rows=word_rows,
                                   tree_word=tree_word, tree=tree, tree_view=tree_view,
                                   bard=shakespeare.is_shakespearean(tree_word),
                                   bard_note=shakespeare.note(tree_word),
                                   info=info, word_cards=word_cards,
                                   bucket_slug=bucket_slug, root_slug=root_slug,
                                   node_slug=node_slug, bucket_breakdown=bucket_language_breakdown,
                                   build_diagram=build_diagram, bucket_for_name=bucket_for_name,
                                   wiktionary_url=wiktionary_url, root_gloss=root_gloss,
                                   is_reconstructed=is_reconstructed,
                                   # Returns the spelling that HAS a descendant
                                   # tree, or None. The template links only when
                                   # it's a real form, so the offer is never made
                                   # for a word that would render an empty page.
                                   descendant_form=descendants.tree_form)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
