"""
Analyzer: text  ->  origin-percentage breakdown.

Tokenizes input, resolves every word through the resolver layer, and aggregates.
Reports two views so results stay honest about Path-A limitations:

  by_tokens    : every analyzable word counted (Unknown included)
  by_resolved  : only words we actually placed in a real origin bucket

It also surfaces `coverage` (how much of the text we could classify) and
`approximate_share` (how much of the classification leans on the OE/ME->Germanic
approximation), so you can watch both numbers improve as Path B fills in.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict
import re

from resolver import Resolver, default_resolver, ResolvedView
from buckets import BUCKET_ORDER, APPROXIMATE_BUCKETS

# Connector/function words -- added 2026-07-23 (Joe: "toggle off connector
# words like to, a, of, but, for, the"). Standard closed-class categories:
# articles, prepositions, conjunctions, pronouns, and common auxiliary/modal
# verbs -- words that carry grammatical structure rather than lexical
# content, and (not coincidentally) are almost always the native-Germanic
# core that dominates the Direct Source chart. Deliberately conservative:
# only genuinely closed-class function words, no ordinary content words
# (verbs like "go"/"make", nouns, adjectives stay -- even common ones).
CONNECTOR_WORDS = frozenset({
    # articles / determiners
    "a", "an", "the", "this", "that", "these", "those", "some", "any",
    "no", "every", "each", "either", "neither",
    # prepositions
    "of", "to", "in", "on", "at", "by", "for", "with", "from", "into",
    "onto", "upon", "over", "under", "about", "against", "between",
    "among", "through", "during", "before", "after", "above", "below",
    "off", "out", "up", "down", "as", "than", "like", "near", "within",
    "without", "along", "across", "behind", "beyond", "despite", "since",
    "until", "till", "towards", "toward", "per", "via",
    # conjunctions
    "and", "but", "or", "nor", "so", "yet", "if", "because", "although",
    "though", "while", "unless", "whether", "either", "neither",
    # pronouns
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "who", "whom", "which", "what", "whose", "myself",
    "yourself", "himself", "herself", "itself", "ourselves",
    "yourselves", "themselves", "my", "your", "his", "its", "our",
    "their", "mine", "yours", "hers", "ours", "theirs",
    # auxiliary / modal verbs
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
})


# Words -> lowercase alphabetic tokens. Internal apostrophes/hyphens are still
# kept out (v1) -- but contractions are expanded to their real component
# words FIRST (you'll -> you will), so both halves resolve as real words
# instead of leaving a stray, unresolvable clitic (or worse, a clitic that
# happens to collide with an unrelated real word, e.g. "don't" naively
# splitting to "don" + "t" would silently resolve "don" as the real verb
# "don" (to put on clothing) instead of recognizing it as "do").
_TOKEN_RE = re.compile(r"[a-z]+")

# Contractions that don't fit the regular "stem + n't" shape and need an
# explicit expansion (the "n" in "can't"/"shan't" is part of the base word
# itself, not an added negation marker, so the generic rule below would
# wrongly truncate "can" to "ca").
_IRREGULAR_CONTRACTIONS = {
    "won't": "will not",
    "can't": "can not",
    "shan't": "shall not",
    "ain't": "am not",
}


# Apostrophes that are not the ASCII one. Word, Google Docs, iOS and most of
# the web emit U+2019, so this is what a real paste actually contains -- and
# every contraction rule below is written against "'". Found 2026-07-30 by a
# corpus scan, where 6 of 35 remaining gaps were contraction fragments.
#
# Silent WRONG answers, not just Unknown -- the same shape as known issue #9
# (`don't` splitting to `don`): the leftover fragment can be a real but
# unrelated word, so `don’t` read as the verb "to don clothing", `won’t` as
# the past tense of `win`, and `can’t` as the container.
_APOSTROPHES = {
    "’": "'",   # right single quotation mark -- the standard smart quote
    "ʼ": "'",   # modifier letter apostrophe
    "＇": "'",   # fullwidth apostrophe
    "‘": "'",   # left single quote, used as an apostrophe in sloppy text
}
_APOSTROPHE_RE = re.compile("[" + "".join(_APOSTROPHES) + "]")


def _expand_contractions(text: str) -> str:
    text = _APOSTROPHE_RE.sub("'", text)
    for full, expansion in _IRREGULAR_CONTRACTIONS.items():
        text = re.sub(r"\b" + re.escape(full) + r"\b", expansion, text)
    # Regular "n't" negations: isn't -> is not, doesn't -> does not, etc.
    text = re.sub(r"(\w+)n't\b", r"\1 not", text)
    # Unambiguous clitics.
    text = re.sub(r"'ll\b", " will", text)
    text = re.sub(r"'ve\b", " have", text)
    text = re.sub(r"'re\b", " are", text)
    text = re.sub(r"'m\b", " am", text)
    # 's and 'd are left alone -- genuinely ambiguous (is/has/possessive,
    # would/had) and guessing wrong would misclassify possessives more often
    # than it correctly expands a contraction. They degrade to a dropped
    # length-1 token ("s"/"d") via the existing filter below, not a wrong word.
    return text


def tokenize(text: str) -> List[str]:
    tokens = _TOKEN_RE.findall(_expand_contractions(text.lower()))
    return [t for t in tokens if len(t) > 1]


@dataclass
class Analysis:
    total_tokens: int
    resolved_tokens: float
    unknown_tokens: float
    approximate_tokens: float
    by_tokens: Dict[str, float]      # bucket -> % of all analyzable tokens
    by_resolved: Dict[str, float]    # bucket -> % of resolved tokens only
    counts: Dict[str, float]         # bucket -> raw count (fractional for split compounds)
    mode: str = "direct"              # which reading produced this analysis
    per_word: List[ResolvedView] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        return 100.0 * self.resolved_tokens / self.total_tokens

    @property
    def approximate_share(self) -> float:
        """% of resolved words that rely on the OE/ME->Germanic approximation."""
        if self.resolved_tokens == 0:
            return 0.0
        return 100.0 * self.approximate_tokens / self.resolved_tokens


def _ordered(d: Dict[str, float]) -> Dict[str, float]:
    keys = [b for b in BUCKET_ORDER if b in d]
    keys += [k for k in d if k not in BUCKET_ORDER]
    return {k: d[k] for k in keys}


def analyze(text: str, resolver: Resolver = None, mode: str = "direct",
            exclude_connectors: bool = False) -> Analysis:
    resolver = resolver or default_resolver()
    tokens = tokenize(text)
    if exclude_connectors:
        # A standalone toggle, independent of mode (see CONNECTOR_WORDS) --
        # removed from the token stream entirely, same as if they were never
        # typed, so they don't count toward total_tokens/coverage either.
        tokens = [t for t in tokens if t not in CONNECTOR_WORDS]

    counts = Counter()
    approximate = 0
    per_word = []

    for tok in tokens:
        view = resolver.resolve(tok).view(mode)
        per_word.append(view)
        if view.parts:
            # Compound split (see compounds.py): this one token's weight is
            # divided evenly across its component words' own buckets rather
            # than counted once under a single answer -- e.g. "upside" (Unknown
            # on its own) contributes 0.5 Germanic ("up") + 0.5 Germanic
            # ("side"), and a mixed-origin compound splits across two buckets.
            share = 1.0 / len(view.parts)
            for part in view.parts:
                counts[part.bucket] += share
                if part.bucket in APPROXIMATE_BUCKETS:
                    approximate += share
        else:
            counts[view.bucket] += 1
            if view.bucket in APPROXIMATE_BUCKETS:
                approximate += 1

    total = len(tokens)
    unknown = counts.get("Unknown", 0)
    resolved = total - unknown

    by_tokens = {b: 100.0 * c / total for b, c in counts.items()} if total else {}
    by_resolved = (
        {b: 100.0 * c / resolved for b, c in counts.items() if b != "Unknown"}
        if resolved else {}
    )

    return Analysis(
        total_tokens=total,
        resolved_tokens=resolved,
        unknown_tokens=unknown,
        approximate_tokens=approximate,
        by_tokens=_ordered(by_tokens),
        by_resolved=_ordered(by_resolved),
        counts=dict(counts),
        mode=mode,
        per_word=per_word,
    )


def format_report(a: Analysis, show_words: bool = False) -> str:
    lines = []
    lines.append(f"Tokens analyzed : {a.total_tokens}")
    lines.append(f"Classified      : {a.resolved_tokens}  (coverage {a.coverage:.1f}%)")
    lines.append(f"Unknown         : {a.unknown_tokens}")
    lines.append(f"Approx. (OE/ME) : {a.approximate_tokens}  "
                 f"({a.approximate_share:.1f}% of classified lean on the Germanic approximation)")
    lines.append("")
    lines.append("Origin breakdown (of classified words):")
    for bucket, pct in a.by_resolved.items():
        bar = "#" * int(round(pct / 2))
        lines.append(f"  {bucket:16s} {pct:5.1f}%  {bar}")
    if show_words:
        lines.append("")
        lines.append("Per-word:")
        for r in a.per_word:
            if r.parts:
                detail = " + ".join(f"{p.word}={p.bucket}" for p in r.parts)
                lines.append(f"  {r.word:16s} -> split: {detail}")
            else:
                tag = r.depth_lang or "-"
                lines.append(f"  {r.word:16s} -> {r.bucket:14s} ({tag})")
    return "\n".join(lines)
