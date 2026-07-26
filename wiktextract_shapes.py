"""
Turn one wiktextract entry into a CONNECTED etymology tree.

The whole point: a word's history is ONE rooted tree -- the modern word at
the head, its ancestors as children, recursively. Every node has a parent, so
a floating node is structurally impossible. That is the fix for `mile`, whose
current tree draws Middle English -> PIE as an edge while Latin (the language
the root actually came through) hangs off to the side unconnected.

FOUR INPUT SHAPES, measured across all 1,481,704 English entries:

  A. DONOR CHAIN (9.1%) -- ordered inh/der/bor templates. 99.92% state no
     nesting at all, so the chain exists ONLY as list order, and 93.19% of
     multi-donor entries are in true descent order. The other 6.81% are two
     narratives concatenated; `_split_narratives` catches those.
  B. FORMATION FORK (~51%, the majority) -- suffix/prefix/compound/blend.
     `telephone` = tele- + -phone. Reading these as a chain produces nonsense
     (grc -> ine-pro -> grc -> ine-pro -> fr), which is what happens today.
  C. `ety` TEMPLATE TREE -- Wiktionary migrated many words to an `ety`
     template, leaving 62,076 entries with NO donor templates at all
     (`father`, `cat`, `free`, `computer`). This dump truncates that
     template's rendered `expansion` mid-JSON, and its `etymology_text` is a
     FLATTENED pre-order listing whose parent/child structure is genuinely
     unrecoverable -- which is why this shape was repeatedly deferred as the
     risky one. But the template's own ARGS survive intact, and they carry a
     compact nested DSL that says exactly what the flattened text can't:

         book         enm:booken<ety:inh<ang:bocian>>
         portmanteau  frm:portemanteau<ety:af<porter<alt:porte>>...>

     So this shape parses the ARGS, never the prose. Structured input, so it
     can be strict: anything malformed returns None rather than guessing.
  D. ROOT POINTER (12,332 entries) -- a `root` template naming the ultimate
     PIE etymon. 76% appear FIRST in the list and 37% duplicate the chain's
     terminal node. It attaches to the TAIL of the chain, never to the
     headword. Attaching it to the headword is exactly the `mile` bug.

Shapes compose: a word can have a chain AND a fork AND a root (`nightmare`,
`government`). They are not alternatives to choose between.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from languages import LangIndex

# --- template vocabularies -------------------------------------------------

_INHERIT = {"inh", "uinh", "inh+"}
_DERIVE = {"der", "uder", "der+"}
_BORROW = {"bor", "ubor", "bor+", "lbor", "slbor", "obor"}
_CALQUE = {"cal", "calque", "clq"}
DONOR_TEMPLATES = _INHERIT | _DERIVE | _BORROW | _CALQUE

FORMATION_TEMPLATES = {"suffix", "suf", "prefix", "pre", "confix", "af",
                       "affix", "compound", "com", "blend", "clipping",
                       "surf", "univ", "back-form"}

ROOT_TEMPLATE = "root"

# Sibling relations -- NOT ancestry. Dropped even when they appear mid-chain
# (`bank`, `sky`, `dog` all interleave them). A cognate is not an ancestor and
# letting one into a lineage fabricates descent.
SIBLING_TEMPLATES = {"cog", "ucog", "ncog", "noncog", "doublet", "dbt"}

# Marks the start of a cognate/notes block; donor templates appearing after it
# are usually stray annotations rather than chain continuations (`bear`,
# `house` both have these).
BOUNDARY_TEMPLATE = "col-top"

# Wiktionary's "no specific form recorded" placeholder.
_PLACEHOLDER_TERMS = {"-", ""}

# Not a real donor language -- Wiktionary's Translingual meta-codes.
EXCLUDED_CODES = {"mul", "mul-tax"}


def _rel_for(name: str) -> str:
    if name in _INHERIT:
        return "inherited"
    if name in _BORROW:
        return "borrowed"
    if name in _CALQUE:
        return "calque"
    return "derived"


# --- tree ------------------------------------------------------------------

@dataclass
class TNode:
    """One step in a lineage. `children` are ANCESTORS of this node."""
    lang: str
    term: Optional[str]
    rel: str                      # inherited|borrowed|derived|calque|root|formed_from
    certainty: str = "direct"     # direct -> solid edge, related -> dotted
    note: Optional[str] = None
    children: List["TNode"] = field(default_factory=list)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def leaves(self) -> List["TNode"]:
        return [n for n in self.walk() if not n.children]


@dataclass
class Tree:
    word: str
    ordinal: int                  # 1-based -> "Etymology 1"
    shape: str                    # chain|fork|rendered|stub|mixed
    head: TNode
    source: str

    def node_count(self) -> int:
        return sum(1 for _ in self.head.walk())

    def direct_node_count(self) -> int:
        """
        Nodes reachable from the head through SOLID edges only.

        This is what "we know where this word came from" actually means. A
        word whose only ancestor is a dotted root pointer (`father`, whose
        entry has nothing but `{{root|en|ine-pro|*pehâ‚‚-}}`) has a node to
        draw but no lineage to walk, and calling that 'resolved' would let
        the percentage bars count a link the tree itself marks unproven.
        """
        n = 1
        stack = [self.head]
        while stack:
            for child in stack.pop().children:
                if child.certainty == "direct":
                    n += 1
                    stack.append(child)
        return n

    def languages(self) -> List[str]:
        return [n.lang for n in self.head.walk()]


@dataclass
class Step:
    """A cleaned donor template, before it becomes a node."""
    lang: str
    term: Optional[str]
    rel: str


# --- shape A: donor chain --------------------------------------------------

def clean_templates(templates: List[dict]) -> List[dict]:
    """Drop everything that isn't usable ancestry evidence, in order."""
    out = []
    for t in templates:
        name = t.get("name", "")
        if name == BOUNDARY_TEMPLATE:
            break  # trailing strays after a cognate/notes block
        if name in SIBLING_TEMPLATES:
            continue
        out.append(t)
    return out


def clean_term(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Strip inline modifiers off a template argument. Returns (term, gloss).

    Wiktionary's newer templates accept modifiers inline in the argument
    itself -- `{{af|frm|porter<alt:porte><t:he carries>|manteau<t:coat>}}` --
    using the same bracket syntax as the `ety` DSL. Without this, the whole
    string is stored as the term and the app renders a node captioned
    `porter<alt:porte><t:he carries>`. Affects shape B, which is ~51% of all
    entries, so it is worth doing on every argument rather than on the ones
    that happen to have been noticed.
    """
    if not raw:
        return None, None
    if "<" not in raw:
        return raw.strip() or None, None
    split = _split_groups(raw)
    if split is None:
        # Unbalanced: keep the text before the first bracket rather than
        # storing markup, but don't pretend to have understood it.
        return raw.split("<", 1)[0].strip() or None, None
    base, mods = split
    term = base.strip() or None
    gloss = None
    for mod in mods:
        key, sep, value = mod.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if key == "alt" and value:
            term = value
        elif key == "t" and value:
            gloss = value
    return term, gloss


def donor_steps(templates: List[dict], langs: LangIndex) -> List[Step]:
    """Ordered donor steps, deduped. List order IS the claimed descent order."""
    steps: List[Step] = []
    for t in templates:
        name = t.get("name", "")
        if name not in DONOR_TEMPLATES:
            continue
        args = t.get("args") or {}
        code = args.get("2")
        term, _gloss = clean_term(args.get("3"))
        if not code or code in EXCLUDED_CODES:
            continue
        if term in _PLACEHOLDER_TERMS:
            term = None
        lang_name = langs.display_name(code)
        rel = _rel_for(name)
        # PIE IS NEVER AN IMMEDIATE DONOR. No language borrows from a
        # reconstructed proto-language thousands of years dead -- a template
        # citing it is making a ROOT claim, whatever its name. `trust`'s entry
        # uses `der|en|ine-pro|*deru-`, and read as a donor that makes PIE the
        # word's direct source, so the bars reported "PIE" where the honest
        # answer is native Germanic. Recording it as a root instead keeps the
        # citation (it is real) while denying it donor status.
        lang = langs.get(code)
        if lang is not None and lang.bucket == "PIE":
            rel = "root"
        # `inh` and `inh+` (and bor/bor+) routinely emit the SAME step twice
        # -- `bank`, `dog`, `table` all do. Collapse adjacent duplicates.
        if steps and steps[-1].lang == lang_name and steps[-1].term == term:
            continue
        steps.append(Step(lang_name, term, rel))
    return steps


def split_narratives(steps: List[Step], langs: LangIndex) -> List[List[Step]]:
    """
    Split an ordered step list wherever it stops being a valid descent.

    Descent goes BACK in time, so `era_start` must not increase. A step whose
    language is YOUNGER than one already reached cannot be a continuation --
    it's a second narrative that got concatenated into the same list.

    `October` is the canonical case: enm -> fro -> la(OctÅber) -> la(octÅ) ->
    ine-pro -> la(-ber). The chain legitimately ends at Latin OctÅber; what
    follows is a morphological decomposition OF that Latin word. Without this
    guard the tree claims Latin descends from PIE and then back to Latin.
    `close` and `sound` restart at Middle English after reaching Old English.

    Languages with no era data never trigger a split (we can't judge them) but
    also never move the floor, so they can't mask a later real violation.
    """
    if not steps:
        return []
    groups: List[List[Step]] = [[]]
    floor: Optional[int] = None
    floor_lang: Optional[str] = None
    for step in steps:
        era = langs.era_start(step.lang)
        if era is not None and floor is not None and era > floor:
            # Younger than something already reached. Normally that means a
            # second narrative -- EXCEPT when the two languages actually
            # coexisted, in which case this is a BORROWING BETWEEN
            # CONTEMPORARIES and still the same story.
            #
            # `knife` is the case that exposed this: Middle English -> Old
            # English -> OLD NORSE -> Proto-Germanic -> PIE is one chain, but
            # Old Norse's era_start is later than Old English's, so the bare
            # comparison split it in two and the word lost its Norse donor
            # entirely (it read Germanic). Same for `law` and `bull` -- the
            # whole Viking-era borrowing layer, which is a big and very
            # visible part of English.
            #
            # This does NOT reopen `October`: PIE stopped being spoken
            # thousands of years before Latin began, so those two are not
            # contemporaries and that split still happens.
            if not langs.contemporaries(step.lang, floor_lang):
                groups.append([])
                floor, floor_lang = era, step.lang
                groups[-1].append(step)
                continue
            # A contemporary borrowing does not move the floor: the story
            # continues from the OLDER language reached so far, so a genuinely
            # unrelated younger step later on can still be caught.
        elif era is not None and (floor is None or era < floor):
            floor, floor_lang = era, step.lang
        groups[-1].append(step)
    return [g for g in groups if g]


def chain_to_nodes(steps: List[Step]) -> Optional[TNode]:
    """Link an ordered step list head-first into a connected path."""
    if not steps:
        return None
    nodes = [TNode(s.lang, s.term, s.rel) for s in steps]
    for parent, child in zip(nodes, nodes[1:]):
        parent.children.append(child)
    return nodes[0]


# --- shape B: formation fork ----------------------------------------------

def formation_parts(templates: List[dict], langs: LangIndex) -> List[TNode]:
    """
    Component words/morphemes a word was BUILT from, as sibling parents.

    Fork-shaped entries outnumber chain-shaped ones roughly 2:1. Argument 1 is
    the language the parts are in; args 2,3,4... are the parts themselves.

    That language argument is honoured rather than assumed to be English: the
    parts of `portmanteau` are Middle French `porte` + `manteau`, and calling
    them English states something false about both.
    """
    parts: List[TNode] = []
    for t in templates:
        if t.get("name") not in FORMATION_TEMPLATES:
            continue
        args = t.get("args") or {}
        code = (args.get("1") or "en").strip()
        lang = langs.get(code)
        lang_name = lang.name if lang else "English"
        for key in sorted((k for k in args if k.isdigit()), key=int):
            if key == "1":
                continue
            term, gloss = clean_term(args.get(key))
            if not term or term in _PLACEHOLDER_TERMS:
                continue
            if any(p.term == term for p in parts):
                continue
            parts.append(TNode(lang_name, term, "formed_from", note=gloss))
    return parts


# --- shape C: `ety` template tree ------------------------------------------
#
# The DSL, by example:
#
#   args {"1": "en", "2": ":inh", "3": "enm:booken<ety:inh<ang:bocian>>"}
#
#   arg 1     the entry's own language
#   arg 2     ":KEYWORD" -- how the headword relates to args 3+
#   args 3+   TERMSPEC, one per ancestor (or per part, for affix/compound)
#
#   TERMSPEC  [LANG ":"] TERM MODIFIER*
#   MODIFIER  "<" KEY ":" VALUE ">"          -- alt, t (gloss), id, unc, pos
#   the `ety` MODIFIER  "<ety:" KEYWORD TERMSPEC_GROUP* ">"   -- recurses
#
# Two different bracket meanings share one syntax: groups hanging off a
# TERMSPEC are modifiers, groups inside an `ety` value are TERMSPECs. Which
# one applies is fixed by position, so each is parsed by its own function
# rather than by sniffing the contents.

# Two names, one DSL. `father` uses `etymon` and `book` uses `ety` with
# byte-identical argument structure, so matching only one of them silently
# skipped a large slice of exactly the words this shape exists to rescue.
ETY_TEMPLATES = {"ety", "etymon"}

# Inside an `ety`, these keywords introduce PARTS of a word rather than
# ancestors of it -- same distinction as shape B, so they get the same
# `formed_from` relation and the same fork shape.
_ETY_FORMATION = {"af", "affix", "com", "compound", "suf", "suffix", "pre",
                  "prefix", "confix", "blend", "clipping", "univ", "surf",
                  "back-form", "back-formation"}

# Sibling pointers can appear inside an `ety` too. Dropped for the same
# reason they're dropped everywhere else: a cognate is not an ancestor.
_ETY_SIBLING = {"cog", "ucog", "ncog", "noncog", "dbt", "doublet", "see",
                "desc", "descendant"}

_LANG_CODE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

# Depth limit is a safety net against a malformed arg, not a real constraint:
# the deepest genuine tree observed is 8.
_ETY_MAX_DEPTH = 16


def _split_groups(spec: str) -> Optional[Tuple[str, List[str]]]:
    """
    'a<b<c>><d>' -> ('a', ['b<c>', 'd']). Top-level groups only; nesting is
    preserved inside each group for the recursive call to deal with.

    Returns None on unbalanced brackets. Refusing beats guessing here: a
    half-parsed etymology is a wrong etymology, and it would be indis-
    tinguishable from a real one downstream.
    """
    base: List[str] = []
    groups: List[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(spec):
        if ch == "<":
            depth += 1
            if depth == 1:
                start = i + 1
                continue
        elif ch == ">":
            depth -= 1
            if depth < 0:
                return None
            if depth == 0:
                groups.append(spec[start:i])
                continue
        if depth == 0:
            base.append(ch)
    if depth != 0:
        return None
    return "".join(base).strip(), groups


def _split_lang(base: str, default_lang: str, langs: LangIndex) -> Tuple[str, Optional[str]]:
    """
    'frm:portemanteau' -> ('Middle French', 'portemanteau').

    A bare term ('multicultural', '-ism') inherits the surrounding language,
    which is how the DSL writes same-language parts.
    """
    code, sep, rest = base.partition(":")
    if sep and _LANG_CODE.match(code) and len(code) <= 15:
        return langs.display_name(code), (rest.strip() or None)
    return default_lang, (base.strip() or None)


def _parse_termspec(spec: str, default_lang: str, langs: LangIndex,
                    rel: str, depth: int = 0) -> Optional[TNode]:
    """One TERMSPEC -> a TNode with its own ancestry already attached."""
    if depth > _ETY_MAX_DEPTH or not spec.strip():
        return None
    split = _split_groups(spec)
    if split is None:
        return None
    base, mods = split
    lang, term = _split_lang(base, default_lang, langs)
    if not lang or lang in EXCLUDED_CODES or term in _PLACEHOLDER_TERMS:
        return None

    node = TNode(lang, term, rel)
    for mod in mods:
        key, sep, value = mod.partition(":")
        key = key.strip()
        if not sep:
            continue
        if key == "alt":
            # The attested spelling. Wiktionary shows it in preference to the
            # lemma, and so do we -- `month` cites Middle English mon(e)th,
            # not the lemma `moneth`.
            if value.strip():
                node.term = value.strip()
        elif key == "t":
            node.note = value.strip() or None
        elif key == "unc":
            # Uncertain: real enough to draw, not solid enough to count.
            node.certainty = "related"
        elif key == "ety":
            node.children.extend(
                _parse_ety_value(value, lang, langs, depth + 1))
    return node


def _parse_ety_value(value: str, parent_lang: str, langs: LangIndex,
                     depth: int) -> List[TNode]:
    """'inh<ang:bocian>' -> [TNode(Old English, bocian, inherited)]."""
    split = _split_groups(value)
    if split is None:
        return []
    keyword, groups = split
    keyword = keyword.strip().lstrip(":").split(":")[0].strip()
    if keyword in _ETY_SIBLING:
        return []
    formation = keyword in _ETY_FORMATION
    rel = "formed_from" if formation else _rel_for(keyword)
    # Parts of a compound default to the language of the word they compose;
    # ancestors default to it too, but nearly always name their own.
    out = []
    for g in groups:
        node = _parse_termspec(g, parent_lang, langs, rel, depth)
        if node is not None:
            out.append(node)
    return out


def ety_tree(word: str, templates: List[dict], langs: LangIndex) -> Optional[TNode]:
    """
    Build a head TNode from the first usable `ety` template, or None.

    None means "this shape has nothing to say", not "this word has no
    etymology" -- callers fall through to the other shapes.
    """
    for t in templates:
        if t.get("name") not in ETY_TEMPLATES:
            continue
        args = t.get("args") or {}
        keyword = (args.get("2") or "").strip().lstrip(":").split(":")[0].strip()
        if not keyword or keyword in _ETY_SIBLING:
            continue
        default_lang = "English"
        term_keys = sorted((k for k in args if k.isdigit() and int(k) >= 3),
                           key=int)
        if not term_keys:
            continue
        formation = keyword in _ETY_FORMATION
        rel = "formed_from" if formation else _rel_for(keyword)
        head = TNode("English", word, "head")
        for k in term_keys:
            node = _parse_termspec(args[k] or "", default_lang, langs, rel)
            if node is not None:
                head.children.append(node)
        if head.children:
            return head
    return None


# --- shape C2: the rendered "Etymology tree" block -------------------------
#
# `father`'s templates name exactly one step (Middle English fader). The rest
# of its history exists only in the rendered block:
#
#     Etymology tree
#     Proto-Indo-European *pehâ‚‚-?      <- an affix branch, NOT the main line
#     Proto-Indo-European *-tḗr         <-
#     Proto-Indo-European *phâ‚‚tḗr
#     Proto-Germanic *fadēr
#     Proto-West Germanic *fader
#     Old English fæder
#     Middle English fader
#     English father
#
# It is a FLATTENED pre-order listing: parent/child is not marked, and for the
# forked part at the top it is genuinely unrecoverable. That ambiguity is why
# this was deferred -- and it is real, so this does not try to solve it.
#
# What IS recoverable is the tail. Read from the headword backwards and keep
# going only while each preceding line is STRICTLY OLDER. Descent goes back in
# time, so a strictly-decreasing era run is a chain by definition; the first
# non-decrease is where a sibling branch begins, and that is where it stops.
# The rule discards the ambiguous part rather than guessing at it:
#
#   father             keeps all 6 steps back to PIE *phâ‚‚tḗr, stops before
#                      the same-era affix pair above it            -> correct
#   month              keeps 6 steps, stops at the second PIE line -> correct
#   gratis             English <- Latin gratis, stops at the
#                      same-era Latin grātiīs                      -> correct
#   multiculturalism   stops immediately (English after English)   -> nothing
#                      claimed, which is right: those are PARTS
#
# So it either recovers a true chain or returns nothing. It never invents one.

# Relation abbreviations the renderer glues onto the end of a line, with no
# separator: "Latin gratisbor.", "Proto-Indo-European *mḗhâ‚n̥sder."
_RENDER_SUFFIX = re.compile(
    r"(?:bor|der|inh|cal|clq|lbor|obor|slbor|ubor|uder|uinh|influ|surf|"
    r"abbrev|clip|blend)\.$")


def _parse_rendered_line(line: str, langs: LangIndex):
    """'Old English fæder' -> ('Old English', 'fæder'), or None."""
    line = line.strip().rstrip("?").strip()
    if not line:
        return None
    line = _RENDER_SUFFIX.sub("", line).strip()
    # Longest language name that prefixes the line wins, so "Proto-West
    # Germanic" is never mistaken for "Proto-West Germanic"'s shorter cousins.
    best = None
    for name in langs.by_name:
        if line.lower().startswith(name) and (
                len(line) == len(name) or line[len(name)] == " "):
            if best is None or len(name) > len(best):
                best = name
    if best is None:
        return None
    lang = langs.get(best)
    return lang.name, (line[len(best):].strip() or None)


def rendered_chain(text: str, word: str, langs: LangIndex) -> Optional[TNode]:
    """Main line of descent from a rendered tree block, or None."""
    if not text or not text.startswith("Etymology tree"):
        return None
    # The block is a contiguous run of "LANGUAGE term" lines directly after
    # the header, and real entries append a PROSE paragraph after it ("
    # Inherited from Middle English fader, from Old English ..."). So the
    # first line that doesn't parse ends the block -- it does not invalidate
    # what came before, which is what discarded every real tree at first.
    parsed = []
    for line in text.split("\n")[1:]:
        if not line.strip():
            continue
        got = _parse_rendered_line(line, langs)
        if got is None:
            break
        parsed.append(got)
    if len(parsed) < 2:
        return None

    # The headword's own line must be last, or this isn't the block we think.
    if parsed[-1][1] and parsed[-1][1].lower() != word.lower():
        return None

    chain = [parsed[-1]]
    floor = langs.era_start(parsed[-1][0])
    for lang_name, term in reversed(parsed[:-1]):
        era = langs.era_start(lang_name)
        if era is None or floor is None or era >= floor:
            break                # not strictly older -> sibling branch, stop
        chain.append((lang_name, term))
        floor = era
    if len(chain) < 2:
        return None

    head = TNode("English", word, "head")
    node = head
    for lang_name, term in chain[1:]:
        child = TNode(lang_name, term, "inherited")
        node.children.append(child)
        node = child
    return head


# --- shape D: root pointer -------------------------------------------------

def root_refs(templates: List[dict], langs: LangIndex) -> List[Step]:
    out: List[Step] = []
    for t in templates:
        if t.get("name") != ROOT_TEMPLATE:
            continue
        args = t.get("args") or {}
        code = args.get("2")
        term, _gloss = clean_term(args.get("3"))
        if not code or code in EXCLUDED_CODES:
            continue
        out.append(Step(langs.display_name(code), term, "root"))
    return out


def attach_roots(head: Optional[TNode], roots: List[Step]) -> Optional[TNode]:
    """
    Hang root pointers off the DEEPEST node, never off the headword.

    76% of root templates appear first in the source list and 37% duplicate
    the chain's terminal node. Trusting that position is what puts a floating
    PIE box next to `mile`'s real Latin ancestry instead of at the end of it.
    """
    if not roots:
        return head
    if head is None:
        first = roots[0]
        return TNode(first.lang, first.term, "root", certainty="related")
    # Hanging a root directly off the WORD (rather than off the end of a real
    # chain) claims English descends straight from PIE, skipping every stage
    # in between -- `father` would draw English -> *pehâ‚‚- as one solid step.
    # The pointer itself is true; only its directness is not. So it renders
    # dotted and the spine won't walk it, which is the whole reason the
    # 'related' certainty exists.
    onto_word = head.rel == "head"
    for r in roots:
        deepest = head.leaves()[-1]
        if deepest.lang == r.lang and deepest.term == r.term:
            continue  # already the chain terminal -- adding it would duplicate
        deepest.children.append(TNode(
            r.lang, r.term, "root",
            certainty="related" if onto_word else "direct"))
    return head


# --- assembly --------------------------------------------------------------

def _graft_or_separate(head: TNode, group: List[Step]) -> bool:
    """
    Try to attach a broken-off narrative as a FORK inside the existing tree.

    When the monotonicity guard breaks a list, the tail is one of two things:

      - a DECOMPOSITION of a word already in the tree -- `October`'s trailing
        `Latin -ber` is the second half of Latin `OctÅber` (octÅ + -ber), not
        a separate history of the English word. Signal: its language already
        appears in the tree. Attach it there as an additional parent, which
        is what makes the fork.
      - a genuinely INDEPENDENT account -- `sandal`'s Arabic/Sanskrit theory
        shares nothing with its Latin/Greek one. Signal: its language appears
        nowhere in the tree. Those must stay separate; fusing them is exactly
        the false merge that was tried and reverted twice.

    Returns True if grafted. The discriminator is a fact about the data, not
    a heuristic, which is why this is safe where the earlier attempts weren't.
    """
    if not group:
        return False
    target_lang = group[0].lang
    match = next((n for n in head.walk()
                  if n.lang == target_lang and n.rel != "head"), None)
    if match is None:
        return False
    chain = chain_to_nodes(group)
    if chain is None:
        return False
    chain.rel = "formed_from"
    match.children.append(chain)
    return True


def build_trees(word: str, templates: List[dict], langs: LangIndex,
                 ordinal: int = 1, text: Optional[str] = None) -> List[Tree]:
    """
    Connected trees for ONE (word, etymology_number) group.

    `ordinal` is the word's etymology_number, so labels read "Etymology 2"
    because Wiktionary says so -- not because of how many pieces this
    function happened to split the list into.

    Composes the shapes rather than choosing between them: a word can have a
    chain, a fork, and a root at once (`nightmare` = night+mare with a PIE
    root; `government` = a French chain plus a govern+-ment analysis).
    """
    templates = clean_templates(templates)
    steps = donor_steps(templates, langs)
    roots = root_refs(templates, langs)
    parts = formation_parts(templates, langs)

    narratives = split_narratives(steps, langs)
    trees: List[Tree] = []

    if narratives:
        head = TNode("English", word, "head")
        chain = chain_to_nodes(narratives[0])
        if chain:
            head.children.append(chain)
        attach_roots(chain, roots)
        for p in parts:
            head.children.append(p)

        # Every later narrative either grafts into this tree as a fork, or
        # becomes its own labeled etymology. Never silently dropped, never
        # force-joined.
        #
        # EXCEPT when the word has formation parts: then a second donor
        # narrative is almost certainly the ancestry of a DIFFERENT part, not
        # a decomposition of the first one. `telephone` (tele- + -phone) cites
        # Ancient Greek twice -- τῆλε for one part, φωνή for the other -- and
        # grafting the second under the first claims φωνή descends from τῆλε,
        # which is false. Nothing in the data says which part each donor
        # belongs to, so they hang off the word itself: connected, and
        # asserting only what's actually recorded.
        if parts:
            for g in narratives[1:]:
                extra_chain = chain_to_nodes(g)
                if extra_chain:
                    head.children.append(extra_chain)
            leftovers = []
        else:
            leftovers = [g for g in narratives[1:] if not _graft_or_separate(head, g)]

        # Immediate donor first: the youngest language is the one English
        # actually took the word from. Source order doesn't guarantee this --
        # `telephone` lists Ancient Greek before French even though French is
        # the immediate donor and Greek is two steps behind it.
        head.children.sort(
            key=lambda n: -(langs.era_start(n.lang) or -9999)
            if n.rel != "formed_from" else 10**6)

        shape = "mixed" if parts and chain else ("chain" if chain else "fork")
        trees.append(Tree(word, ordinal, shape, head, "wiktextract.templates"))

        for extra in leftovers:
            alt_head = TNode("English", word, "head")
            alt_chain = chain_to_nodes(extra)
            if alt_chain:
                alt_head.children.append(alt_chain)
            trees.append(Tree(word, ordinal + len(trees), "chain",
                               alt_head, "wiktextract.templates"))
        return trees

    if parts:
        head = TNode("English", word, "head")
        for p in parts:
            head.children.append(p)
        # (ordinal flows through so a fork-only Etymology 2 is still labeled 2)
        # A root alongside a formation fork describes the WHOLE word, not any
        # one component, so it hangs off the word itself. Picking a component
        # to attach it to would be a guess (`nightmare`'s *mer- belongs to
        # "mare", but nothing in the data says so).
        for r in roots:
            head.children.append(TNode(r.lang, r.term, "root",
                                        certainty="related"))
        return [Tree(word, ordinal, "fork", head, "wiktextract.templates")]

    # Shape C runs only where A and B found nothing, so it can only ADD
    # coverage -- it never overrides a donor chain. It is tried BEFORE the
    # bare-root stub below because that stub is the worse answer for the same
    # word: `father` has a root pointer and an `ety`, and the stub alone draws
    # English -> PIE *pehâ‚‚- as a single direct edge, asserting a descent that
    # skipped Proto-Germanic and Old English. Same false-edge class as `mile`.
    ety_head = ety_tree(word, templates, langs)
    text_head = rendered_chain(text, word, langs) if text else None
    # Both are conservative and both refuse rather than guess, so the richer
    # answer wins. `father`'s template names one step (Middle English fader)
    # while its rendered block recovers all six back to PIE.
    best = max((h for h in (ety_head, text_head) if h is not None),
               key=lambda h: sum(1 for _ in h.walk()), default=None)
    if best is not None:
        deepest_line = max(best.children, key=lambda n: len(list(n.walk())),
                           default=None)
        attach_roots(deepest_line, roots)
        return [Tree(word, ordinal, "rendered", best,
                      "wiktextract.templates")]

    if roots:
        head = TNode("English", word, "head")
        attach_roots(head, roots)
        return [Tree(word, ordinal, "stub", head, "wiktextract.templates")]

    return []
