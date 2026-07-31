"""
Read access to etymology.db. THE ONLY MODULE THAT OPENS THE DATABASE.

WHY THAT RULE MATTERS (2026-07-25): the previous data layer let each feature
do its own lookup. The paragraph analyzer and the Word Search each had their
own case policy, their own inflection retry and their own tree fetch, and
they disagreed in eleven measurable ways -- `intrude` showed a Latin donor in
one and not the other, ~75 hand-corrected words were corrected in one place
only. Those were not bugs in the lookups; they were bugs in there BEING two
lookups.

So the contract here is deliberately narrow:

    entry = etymology_db.get().entry("mile")

`entry.etymologies` is what the tree renders. `Etymology.spine()` is what the
percentage bars count. They are the SAME OBJECT read two ways, which is why
the two features cannot drift apart again -- not because a test watches them,
but because there is nothing left to drift.

Nothing in here decides anything. Every fallback -- case folding, inflected
forms, derivational stemming -- was resolved at BUILD time and stored in
surface_form, so lookup is one indexed query with no branching.
"""
import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import language_codes
import linguistics

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "etymology.db")

# Edge certainty that chain/percentage code is allowed to walk. 'related' is
# the dotted edge: it says "these two are connected somehow" without claiming
# descent, which is what lets the tree show a node instead of floating it.
# Counting a dotted edge as ancestry would fabricate lineage -- the exact
# failure that got branch-merging reverted twice before.
DIRECT = "direct"

# Relation kinds that are word-to-word, never ancestry. Ancestry code must
# never read word_relation at all; this list exists for the UI's benefit.
RELATION_KINDS = ("cognate", "doublet", "derived_term", "related", "synonym",
                  "antonym", "descendant", "hyponym", "hypernym", "meronym",
                  "holonym", "coordinate", "false_friend", "root_family")

# Stages where "the trail ended inside English" -- the signal that a formation
# part still needs following. Was a local copy of buckets_wikt's set, kept
# separate to avoid an import cycle; `linguistics` is a leaf module below both,
# so the copy is gone and the cycle is still impossible.
ENGLISH_STAGES = linguistics.ENGLISH_STAGE_NAMES

# Which edges actually TRANSMIT material, and so may answer "where is this word
# from". Stated as an allowlist rather than a list of exclusions because the
# question is what counts as evidence, and a new relation kind should have to
# argue its way IN rather than silently become a donor the day it is added.
#
# The two that are left out are left out for different reasons:
#
#   `root`   -- real, and cited by Wiktionary itself, but a root is not a donor.
#               `trust` runs English -> Middle English -> Old English -> PIE
#               *deru-; the honest direct source is native Germanic, not PIE.
#               This exclusion already existed at both call sites.
#   `calque` -- a calque transmits NO material. `blackshirt` is English black +
#               shirt, modelled on Italian *camicia nera*; not one morpheme
#               crossed over. Treating it as a donor is how `peacemaker` came
#               to read Greek: its only recorded edge is a calque of Koine
#               Greek εἰρηνοποιοί, i.e. the phrase English was TRANSLATING.
#               2,437 edges over ~2,200 words were affected.
#
# `formed_from` IS included, deliberately. When its part is foreign the material
# genuinely did cross over -- `sthenolagnia` really is built out of Greek -- so
# excluding it would lose true ancestry rather than reject a false claim.
DONOR_RELS = frozenset({"inherited", "borrowed", "derived", "formed_from"})


# `-ize`, `pre-`, `-graphy`: grammatical, not where the etymology lives.
_is_affix = linguistics.is_affix


def _is_bound(node: "Node") -> bool:
    """
    Is this formation part a morpheme rather than a word?

    ONE definition, used by every consumer. The database column is the real
    answer (Wiktionary's own `suffix`/`prefix`/`confix` template, recorded at
    build time); the spelling test still runs so a database built before the
    column existed keeps behaving as it did. Two call sites independently
    re-deriving this is the shape of issue #16 -- every feature must read from
    one shared source.
    """
    return bool(node.is_affix) or _is_affix(node.term)


@dataclass(frozen=True)
class Node:
    """One step in a word's history. `children` are its ANCESTORS."""
    lang: str
    term: Optional[str]
    rel: str                      # head|inherited|borrowed|derived|calque|root|formed_from
    certainty: str                # direct | related
    is_root: bool
    # A bound morpheme (`-ness`, `un-`) rather than a word, recorded from
    # Wiktionary's own template at BUILD time. Governs weight splitting and
    # component display only -- never ancestry, since `geology`'s Greek
    # genuinely arrives through `geo-`/`-logy` (issue #22's lesson).
    is_affix: bool = False
    children: Tuple["Node", ...] = ()

    @property
    def is_direct(self) -> bool:
        return self.certainty == DIRECT

    def walk(self):
        """Every node in this subtree, parents before children."""
        yield self
        for child in self.children:
            yield from child.walk()

    def depth(self) -> int:
        """Longest run of DIRECT edges below this node. Drives fork choice."""
        best = 0
        for child in self.children:
            if child.is_direct:
                best = max(best, 1 + child.depth())
        return best


@dataclass(frozen=True)
class Etymology:
    ordinal: int                  # this word's own 1..n slot
    label: Optional[str]          # Wiktionary's etymology number, for display
    shape: str                    # chain|fork|mixed|rendered|stub
    head: Node

    def spine(self) -> List[Node]:
        """
        The main line of descent, head first, following DIRECT edges only.

        At a fork (telephone = tele- + -phone) both parts are real ancestry,
        but a single chain has to pick one; it takes the deepest branch, and
        ties break on source order. Callers that need the whole picture read
        `head` instead -- this is the linear reading, not the truth.
        """
        line = [self.head]
        node = self.head
        while True:
            options = [c for c in node.children if c.is_direct]
            if not options:
                return line
            node = max(options, key=lambda c: c.depth())
            line.append(node)

    def nodes(self) -> List[Node]:
        return list(self.head.walk())

    def root(self) -> Optional[Node]:
        """Deepest node on the spine -- what 'Deepest Root' should show."""
        spine = self.spine()
        return spine[-1] if len(spine) > 1 else None


@dataclass(frozen=True)
class Entry:
    word_id: int
    headword: str
    status: str                   # resolved | stub | none
    etymologies: Tuple[Etymology, ...]
    match_kind: str               # how the typed form reached this word
    match_note: Optional[str]
    primary_index: int = 0

    @property
    def resolved(self) -> bool:
        return self.status == "resolved"

    @property
    def primary(self) -> Optional[Etymology]:
        """
        The history the percentage bars count.

        NOT simply the first one. `table` genuinely entered English twice --
        early through Old English from Latin, and later straight from Old
        French -- and Wiktionary happens to number the early route first, so
        taking slot 1 made the bars say Germanic where the word is normally
        thought of as French. Wiktionary's numbering is entry order, not
        significance, so it cannot carry that decision.

        The rule (Joe, 2026-07-26) is to prefer a route whose immediate
        source is an ATTESTED language over one that goes straight into a
        reconstruction: Old French is a language with surviving records,
        Proto-Germanic is scholarly inference. Where no route is attested,
        or several are, order decides and slot 1 wins as before.
        """
        if not self.etymologies:
            return None
        return self.etymologies[self.primary_index]

    @property
    def is_exact(self) -> bool:
        """False when the answer came from an inflection or a stem."""
        return self.match_kind in ("verbatim", "exact", "case", "correction")


def _node(raw: dict) -> Node:
    # `language_codes.resolve` upgrades a raw Wiktionary code to a real
    # language name. The builder wrote codes into the language table's `name`
    # column for 1,250 of 1,530 rows, so `muskrat` displayed its donor as
    # "alg" and bucketed it "Other" (Joe, 2026-07-27). Doing it HERE means
    # every consumer -- the bars, the hover card, the tree, the descendants
    # view -- gets the real name from one place, because they all build their
    # nodes through this function.
    #
    # This is a LOOKUP-layer repair of a BUILD-time defect, the same shape as
    # known issue #19. `build_etymology_db.py` now resolves the name too, so a
    # future rebuild stores it correctly and this call becomes a no-op rather
    # than load-bearing. Keeping both costs nothing and means neither the
    # current database nor a rebuilt one is wrong.
    return Node(
        lang=language_codes.resolve(raw["lang"]),
        term=raw.get("term"),
        rel=raw.get("rel", "head"),
        certainty=raw.get("certainty", DIRECT),
        is_root=bool(raw.get("is_root")),
        is_affix=bool(raw.get("is_affix")),
        children=tuple(_node(c) for c in raw.get("children", ())),
    )


class Db:
    def __init__(self, path: str = DB_PATH):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{path} not found -- run `python build_etymology_db.py` "
                "(or --sample 20000 for a quick dev copy).")
        self.path = path
        self._db = sqlite3.connect(f"file:{path}?mode=ro", uri=True,
                                    check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._proto = None        # lazily loaded, see _proto_names()

    # ------------------------------------------------------------ lookup
    def entry(self, form: str) -> Optional[Entry]:
        """
        Typed string -> Entry, or None if nothing in the database knows it.

        One query. Both the string as typed and its lowercase form go in, so
        `March` can reach the month while `march` reaches the verb, without a
        second pass or a case rule living out here.
        """
        if not form:
            return None
        form = form.strip()
        row = self._db.execute(
            "SELECT w.word_id, w.headword, w.status, w.tree_json,"
            "       s.kind, s.note"
            "  FROM surface_form s JOIN word w ON w.word_id = s.word_id"
            " WHERE s.form IN (?, ?)"
            # Tie-break: a headword spelled exactly like its lookup key beats
            # a capitalised homograph. Someone typing `wolves` means the
            # animal, not the surname Wolf -- and ety_count alone got that
            # backwards, because the proper noun happened to carry more
            # numbered etymologies.
            " ORDER BY s.rank, (w.headword = w.key_lower) DESC,"
            "          w.ety_count DESC, w.headword"
            " LIMIT 1", (form, form.lower())).fetchone()
        if row is None:
            return None
        etys = tuple(
            Etymology(ordinal=e["ordinal"], label=e.get("label"),
                      shape=e["shape"], head=_node(e["head"]))
            for e in json.loads(row["tree_json"] or "[]"))
        return Entry(
            word_id=row["word_id"],
            headword=row["headword"],
            status=row["status"],
            etymologies=etys,
            match_kind=row["kind"],
            match_note=row["note"],
            primary_index=self._pick_primary(etys),
        )

    def _pick_primary(self, etys) -> int:
        """
        Index of the etymology whose immediate source is attested.

        Only ever replaces a BORROWED route with a better-attested borrowed
        route. A word whose first etymology is NATIVE -- no foreign donor at
        all, just English stages back into Proto-Germanic -- keeps it, always.

        That guard is the whole safety of this rule. Without it, `go` lost its
        native history to the unrelated Japanese loanword ç¢ (the board game),
        because a native word legitimately has no attested foreign donor to
        compete with, so any homograph borrowed from anywhere outranked it.
        `went` came out East Asian, `seen` Semitic, `and` and `with` Norse.
        A second numbered etymology is usually a DIFFERENT WORD that happens
        to be spelled the same, not a rival account of this one.
        """
        if len(etys) < 2:
            return 0

        proto = self._proto_names()

        def donors_of(ety):
            return [n.lang for n in ety.spine()[1:]
                    if n.lang not in ENGLISH_STAGES and n.rel != "root"]

        first = donors_of(etys[0])
        if not first or first[0] not in proto:
            return 0          # native, or already an attested source

        # The first route reaches a reconstruction before anything attested.
        # Only prefer a sibling if this route DOES eventually name a real
        # language -- that is what marks it as a borrowing whose donor is
        # merely buried, rather than a native descent.
        #
        #   table  Proto-Germanic -> LATIN      borrowed long ago, and a
        #                                       sibling names Old French
        #                                       directly -> prefer it
        #   go     Proto-Germanic (ends there)  native descent -> keep it,
        #                                       even though a Japanese
        #                                       homograph (the board game)
        #                                       offers an attested donor
        #
        # Without this, `go` lost its history to ç¢, and `went` -- an inflection
        # of `go` -- came out East Asian.
        if all(lang in proto for lang in first):
            return 0
        for i, ety in enumerate(etys):
            donors = donors_of(ety)
            if donors and donors[0] not in proto:
                return i
        return 0

    def _proto_names(self):
        """Reconstructed languages -- no surviving records, inferred forms."""
        if self._proto is None:
            self._proto = {r[0] for r in self._db.execute(
                "SELECT name FROM language WHERE is_proto = 1")}
        return self._proto

    def entries(self, forms: Sequence[str]) -> Dict[str, Optional[Entry]]:
        """Bulk lookup for the paragraph analyzer. Same answers, one call."""
        return {f: self.entry(f) for f in forms}

    def lineage(self, entry: Optional[Entry], max_depth: int = 4) -> List[Node]:
        """
        Full line of descent, FOLLOWING formation parts into their own words.

        Why this can't live on Etymology: a formed_from part is a pointer to
        another word, and that word's history is a different row. `Etymology`
        only ever sees one row, so its `spine()` stops dead at the part.

        That matters more than it sounds. `nationalize` is `national` + `-ize`
        -- an English formation, correctly recorded as a fork. Reading only
        this row, the deepest ancestor is the English word `national`, so the
        word scores as GERMANIC. Follow the part and the real story appears:
        national -> nation -> Old French -> Latin. Measured against the old
        stack, not following parts moved 20,776 words into the wrong bucket
        (12,674 of them French -> Germanic), which would visibly skew the
        percentage bars the whole app is built around.

        Affixes are skipped when choosing which part to follow: `-ize` is
        grammatical, `national` carries the etymology. Among real parts the
        deepest lineage wins, so the choice is decided by evidence rather
        than by argument order.
        """
        return self._lineage(entry, max_depth, set())

    def _lineage(self, entry, depth, seen) -> List[Node]:
        if entry is None or not entry.primary or depth <= 0:
            return []
        if entry.word_id in seen:
            return []            # `x` formed from `x` -- real, and a cycle
        seen = seen | {entry.word_id}

        line = entry.primary.spine()
        # A foreign DONOR anywhere means this word's own row already answers
        # the question. A root does not count: `computer` is compute + -er
        # with a PIE root hanging off `compute`, and treating that root as an
        # answer stopped the walk before it ever reached `compute`'s own
        # French/Latin history -- so the tree showed French while the bars
        # said PIE. Roots are citations, not donors, here as everywhere else.
        # `DONOR_RELS`, not "anything but a root": a calque is a foreign node
        # that answers nothing, and stopping here on one meant the walk never
        # reached the parts that DO carry the etymology. `peacemaker` returned
        # its Koine Greek calque and never looked at peace + maker.
        if any(n.lang not in ENGLISH_STAGES and n.rel in DONOR_RELS
               for n in line):
            return line

        best_line = self._deepest_part_line(entry, depth, seen)
        if not best_line:
            return line

        # Return the head followed by the COMPONENT'S line -- not the word's
        # own dead-end English tail followed by it. Concatenating those two
        # asserts an adjacency nothing recorded: it read `Aberdeen -> Middle
        # English schire` (Aberdeen does not come from schire) and
        # `Middle English professhennalle -> English profession`. Every pair
        # this returns is now an edge the data actually states -- the head IS
        # formed from the component, and the rest is the component's own
        # descent. The dropped English tail is still drawn in the tree; this
        # view answers "how far back can we follow it", which is a different
        # question off the same rows.
        return [line[0]] + best_line

    def _deepest_part_line(self, entry, depth: int, seen) -> List[Node]:
        """
        The component whose own history reaches furthest back, or [].

        A formed word's etymology lives on its PARTS. Whichever part travels
        through the most foreign languages is the one that answers "where is
        this word from" -- `bagpipe` follows `pipe` to Latin, not `bag`.

        A part with NO foreign step still answers, though. Ranking on foreign
        count alone scored a purely native component at zero and rejected it,
        so `chuckled` (-> chuck, Middle English), `fondling` (-> fond) and
        `hikers` (-> hike) lost their evidence and reported a miss -- while
        each base resolves Germanic on its own. The longest line wins among
        equals, so native descent propagates instead of being discarded.

        Bound affixes are skipped, but `or parts` keeps them as a last resort:
        a word made ONLY of affixes still has to answer, and `geology` is
        geo- + -logy, so falling back to them is what lets it reach Greek
        instead of going Unknown.
        """
        parts = [c for c in entry.primary.head.children
                 if c.rel == "formed_from" and c.term]
        candidates = [p for p in parts if not _is_bound(p)] or parts
        best_line: List[Node] = []
        best_rank = (0, 0)
        for part in candidates:
            sub = self._lineage(self.entry(part.term), depth - 1, seen)
            foreign = sum(1 for n in sub if n.lang not in ENGLISH_STAGES)
            rank = (foreign, len(sub))
            if rank > best_rank:
                best_line, best_rank = sub, rank
        return best_line

    # ------------------------------------------------------------- facts
    def senses(self, word_id: int, limit: int = 8) -> List[sqlite3.Row]:
        return self._db.execute(
            "SELECT pos, gloss, ety_ordinal FROM sense WHERE word_id=?"
            " ORDER BY ordinal LIMIT ?", (word_id, limit)).fetchall()

    def relations(self, word_id: int, kind: Optional[str] = None,
                  limit: int = 200) -> List[sqlite3.Row]:
        """
        Word-to-word relations: cognates, doublets, derived terms, synonyms...

        HARD RULE, enforced by not being reachable from Etymology: ancestry
        code never calls this. A cognate is a sibling, not an ancestor.
        """
        sql = ("SELECT r.kind, r.term, r.gloss, r.note, r.other_word_id,"
               "       l.name AS lang"
               "  FROM word_relation r"
               "  LEFT JOIN language l ON l.lang_id = r.lang_id"
               " WHERE r.word_id = ?")
        args: list = [word_id]
        if kind:
            sql += " AND r.kind = ?"
            args.append(kind)
        sql += " ORDER BY r.kind, r.ordinal LIMIT ?"
        args.append(limit)
        return self._db.execute(sql, args).fetchall()

    def relation_counts(self, word_id: int) -> Dict[str, int]:
        return {r["kind"]: r["n"] for r in self._db.execute(
            "SELECT kind, COUNT(*) n FROM word_relation WHERE word_id=?"
            " GROUP BY kind", (word_id,))}

    def language(self, name: str) -> Optional[sqlite3.Row]:
        return self._db.execute(
            "SELECT l.* FROM language l JOIN language_alias a"
            " ON a.lang_id = l.lang_id WHERE a.alias = ?", (name,)).fetchone()

    def languages(self) -> Dict[str, sqlite3.Row]:
        return {r["name"]: r for r in self._db.execute("SELECT * FROM language")}

    # ------------------------------------------------------- descendants
    # The one part of this module that runs DOWNWARD. Everything above answers
    # "where did this word come from"; this answers "what came from this form",
    # which is a different dataset living on the ancestor's Wiktionary page.
    # Loaded by build_descendants.py -- see that module for why it needs its
    # own extracts. Absent tables are a normal state (nothing built yet), so
    # every method here degrades to empty rather than raising.

    def _has_descendants(self) -> bool:
        if self.__dict__.get("_desc_ok") is None:
            row = self._db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
                " AND name='descendant_tree'").fetchone()
            self.__dict__["_desc_ok"] = row is not None
        return self.__dict__["_desc_ok"]

    def descendant_tree(self, tree_id: int) -> Optional[dict]:
        """One stored tree, nested. Children keep their recorded sibling order."""
        if not self._has_descendants():
            return None
        head = self._db.execute(
            "SELECT * FROM descendant_tree WHERE tree_id=?", (tree_id,)).fetchone()
        if head is None:
            return None
        by_parent: Dict[Optional[int], list] = {}
        for row in self._db.execute(
                "SELECT * FROM descendant_node WHERE tree_id=? ORDER BY depth, ordinal",
                (tree_id,)):
            by_parent.setdefault(row["parent_id"], []).append(row)

        def build(parent_id):
            out = []
            for row in by_parent.get(parent_id, ()):
                out.append({"lang": row["lang"], "lang_code": row["lang_code"],
                            "term": row["term"], "raw_term": row["raw_term"],
                            "children": build(row["node_id"])})
            return out

        return {"lang": head["lang"], "term": head["term"],
                "raw_term": head["raw_term"], "root": True,
                "children": build(None)}

    def tree_for_form(self, lang: str, term: str) -> Optional[int]:
        """The stored tree whose ROOT is this form -- the splice target."""
        if not self._has_descendants() or not term:
            return None
        row = self._db.execute(
            "SELECT tree_id FROM descendant_tree WHERE lang=? AND term=?"
            " ORDER BY node_count DESC LIMIT 1", (lang, term)).fetchone()
        return row["tree_id"] if row else None

    def trees_containing(self, term: str, lang: str = "English",
                          limit: int = 4) -> List[sqlite3.Row]:
        """
        Trees with this word somewhere inside them -- the entry point for an
        ordinary search. Biggest tree first: for a common word the largest is
        reliably the real lineage rather than a passing mention.
        """
        if not self._has_descendants() or not term:
            return []
        return list(self._db.execute(
            "SELECT DISTINCT t.tree_id, t.lang, t.term, t.raw_term, t.node_count"
            " FROM descendant_node n JOIN descendant_tree t ON t.tree_id = n.tree_id"
            " WHERE n.term = ? AND n.lang = ?"
            " ORDER BY t.node_count DESC LIMIT ?", (term, lang, limit)))

    def parent_tree_of(self, lang: str, term: str) -> Optional[sqlite3.Row]:
        """
        The tree one level UP: whoever lists this form as a descendant.

        This is what turns two extracts into one diagram. Wiktionary ends the
        PIE page's Germanic row at `*brōþēr` and says "see there for further
        descendants"; the continuation is a separate tree. Joining them here
        rather than at build time means adding an extract later enriches
        existing trees with no rebuild.
        """
        if not self._has_descendants() or not term:
            return None
        return self._db.execute(
            "SELECT t.tree_id, t.lang, t.term, t.raw_term FROM descendant_node n"
            " JOIN descendant_tree t ON t.tree_id = n.tree_id"
            " WHERE n.term = ? AND n.lang = ? AND t.term != ?"
            " ORDER BY t.node_count DESC LIMIT 1", (term, lang, term)).fetchone()

    # -------------------------------------------------------------- meta
    def stats(self) -> Dict[str, int]:
        out = {}
        for table in ("word", "etymology", "ety_node", "ety_edge",
                      "surface_form", "sense", "word_relation", "language"):
            out[table] = self._db.execute(
                f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for status, n in self._db.execute(
                "SELECT status, COUNT(*) FROM word GROUP BY status"):
            out[f"word.{status}"] = n
        return out

    def close(self):
        self._db.close()


_DB: Optional[Db] = None


def get(path: Optional[str] = None) -> Db:
    """
    Process-wide handle. Read-only, so sharing it across threads is safe.

    `get()` with no argument means "the shared handle" -- it does NOT re-point
    an already-open database back to the default. That matters because callers
    disagree about who configures the path: a test or a build check opens a
    specific file, then app code calls get() expecting to reuse it. Treating
    the bare call as "reset to DB_PATH" silently gave those two callers
    different databases, and the symptom was every word reading as native
    English while the tree beside it showed a Latin chain.
    """
    global _DB
    if path is None:
        if _DB is None:
            _DB = Db(DB_PATH)
        return _DB
    if _DB is None or _DB.path != path:
        _DB = Db(path)
    return _DB
