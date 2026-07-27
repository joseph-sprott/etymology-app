"""
Build etymology.db -- the canonical word database.

Replaces convert_wikt.py, convert_wiktextract.py, build_etymology_trees.py,
build_word_info.py and build_inflections.py as the single place per-word data
is produced, and etymology_schema.sql documents why.

The load-bearing idea: EVERY fallback decision happens here, at build time,
and is stored as rows. Query time (etymology_db.py) is one indexed SELECT
with no branching -- which is what makes it impossible for the paragraph
analyzer and the Word Search to disagree.

    python build_etymology_db.py                    # full build
    python build_etymology_db.py --sample 20000     # fast dev database
    python build_etymology_db.py --words mile father # just these, for checking
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import languages
import language_codes
from buckets_wikt import bucket_for_name
from wiktextract_shapes import build_trees

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "etymology_schema.sql")
DB_PATH = os.path.join(HERE, "etymology.db")
JSONL = r"C:\Users\Josep\Desktop\Etymology Project\wiktextract_data\kaikki.org-dictionary-English.jsonl"

GLOSS_MAX = 200

# Wiktionary sections that are word-to-word relations rather than ancestry.
# ~700,000 rows sitting unread in the dump until now. Harvested during the
# same pass we already make for etymology, so they cost nothing extra.
RELATION_FIELDS = {
    "derived": "derived_term", "related": "related", "synonyms": "synonym",
    "antonyms": "antonym", "descendants": "descendant", "hyponyms": "hyponym",
    "hypernyms": "hypernym", "meronyms": "meronym", "holonyms": "holonym",
    "coordinate_terms": "coordinate",
}

SOURCES = [
    # name, kind, licence, additive_only, priority
    ("curated",                "curated", "project",       0,  0),
    ("wiktextract.templates",  "extract", "CC-BY-SA-3.0",  0, 10),
    ("wiktextract.relations",  "extract", "CC-BY-SA-3.0",  0, 20),
    ("builder.inference",      "derived", "project",       0, 90),
]

# surface_form rank bands -- lowest wins, and ties are impossible.
#
# `verbatim` exists so a capitalised headword is reachable AS capitalised.
# Every other band stores a LOWERCASED key, which on its own means `March`
# and `march` collapse into one bucket and the lowercase word always wins --
# the proper noun becomes unreachable (March, Polish, Turkey, August, May).
# One extra row per capitalised headword, matched by querying both the typed
# string and its lowercase form in a single IN (...), fixes that without
# reintroducing a branching case policy at query time.
RANK = {"verbatim": 5, "correction": 0, "exact": 10,
        # A REAL TAGGED INFLECTION OUTRANKS A CASE FOLD. Wiktionary stating
        # that `ran` is the past tense of `run` is strong evidence; finding a
        # capitalised homograph that happens to fold to the same letters is
        # weak. With case at 30 the weak evidence won, and `ran` resolved to
        # `Ran`, a Hebrew given name -- the went/Went and ran/Ran bug the old
        # stack fought for weeks, reintroduced purely by rank order.
        # `october` -> `October` still works: nothing else claims that form.
        "inflection": 40, "generated": 45, "case": 50, "derivation": 60}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path, fresh=False):
    if fresh and os.path.exists(path):
        # Swallowing a failed delete here silently REUSES the old database:
        # the schema is CREATE TABLE IF NOT EXISTS, so the build appends to
        # stale rows and dies on the first duplicate etymology -- with an
        # error that points at the insert rather than at the real cause.
        # A build that cannot start clean must say so.
        for suffix in ("", "-wal", "-shm"):
            target = path + suffix
            if not os.path.exists(target):
                continue
            try:
                os.remove(target)
            except OSError as exc:
                raise SystemExit(
                    f"cannot remove {target} to start a fresh build: {exc}\n"
                    "Something still holds it open (a previous crashed build, "
                    "or the running app). Close it and retry.") from exc
    db = sqlite3.connect(path)
    db.executescript(open(SCHEMA, encoding="utf-8").read())
    return db


def load_languages(db, langs):
    rows = {l.name: l for l in langs.by_name.values()}
    for name, l in rows.items():
        db.execute(
            "INSERT OR IGNORE INTO language (name, wikt_code, bucket, family,"
            " era_start, era_end, era_label, era_certain, is_proto,"
            " is_english_stage, source_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (l.name, l.wikt_code, l.bucket, l.family, l.era_start, l.era_end,
             l.era_label, int(l.era_certain), int(l.is_proto),
             int(l.is_english_stage), l.source))
    lang_ids = dict(db.execute("SELECT name, lang_id FROM language").fetchall())
    for name, l in rows.items():
        lid = lang_ids[name]
        for alias in filter(None, {l.name, l.wikt_code}):
            db.execute("INSERT OR IGNORE INTO language_alias (alias, lang_id)"
                       " VALUES (?,?)", (alias, lid))
    return lang_ids


def load_sources(db):
    for name, kind, licence, additive, priority in SOURCES:
        db.execute(
            "INSERT OR IGNORE INTO source (name, kind, licence, additive_only,"
            " ingested_at) VALUES (?,?,?,?,?)",
            (name, kind, licence, additive, now()))
        sid = db.execute("SELECT source_id FROM source WHERE name=?",
                         (name,)).fetchone()[0]
        db.execute("INSERT OR IGNORE INTO source_precedence (source_id, priority)"
                   " VALUES (?,?)", (sid, priority))
    return dict(db.execute("SELECT name, source_id FROM source").fetchall())


def scan_dump(path, limit=None, only=None):
    """
    Stream the dump into per-word records.

    Entries are per-PART-OF-SPEECH, so `bear` appears three times with
    byte-identical templates -- grouping is by (word, etymology_number), and
    identical template lists are deduped by signature. Getting this wrong
    builds the same tree three times.
    """
    want = {w.lower() for w in only} if only else None
    words = {}
    seen_sig = defaultdict(set)
    scanned = 0

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("lang") != "English":
                continue
            head = e.get("word")
            if not head:
                continue
            if want is not None and head.lower() not in want:
                continue

            rec = words.setdefault(head, {
                "etys": defaultdict(list), "pos": defaultdict(set),
                "senses": [], "relations": [], "text": {}})

            try:
                num = int(e.get("etymology_number") or 1)
            except (TypeError, ValueError):
                num = 1

            tmpl = e.get("etymology_templates") or []
            sig = tuple((t.get("name"),
                          tuple(sorted((t.get("args") or {}).items())))
                         for t in tmpl)
            if sig not in seen_sig[(head, num)]:
                seen_sig[(head, num)].add(sig)
                rec["etys"][num].extend(tmpl)
            if e.get("pos"):
                rec["pos"][num].add(e["pos"])
            # The rendered "Etymology tree" block, kept per etymology number:
            # shape C2 recovers the main line of descent from it for words
            # whose templates only name one step (`father`).
            text = e.get("etymology_text") or ""
            if text.startswith("Etymology tree") and num not in rec["text"]:
                rec["text"][num] = text

            if len(rec["senses"]) < 3:
                for s in e.get("senses") or []:
                    g = (s.get("glosses") or [None])[0]
                    if g:
                        rec["senses"].append(
                            (e.get("pos"), g[:GLOSS_MAX], len(rec["senses"])))
                        break

            for field, kind in RELATION_FIELDS.items():
                for row in (e.get(field) or []):
                    term = row.get("word")
                    if term:
                        rec["relations"].append(
                            (kind, term, row.get("lang"), row.get("sense")))

            scanned += 1
            if limit and len(words) >= limit:
                break
            if line_no % 500_000 == 0:
                print(f"  ...{line_no:,} lines, {len(words):,} words",
                      file=sys.stderr, flush=True)
    print(f"  scanned {scanned:,} English entries -> {len(words):,} words",
          file=sys.stderr)
    return words


def insert_tree(db, ety_id, head_node, lang_ids, src_id, unknown_langs):
    """Write a TNode tree as node+edge rows. Returns the head node_id."""
    def node_row(n):
        # Wiktionary hands us a CODE where languages.csv has no entry, and
        # this used to store that code as the language NAME -- so `muskrat`
        # displayed its donor as "alg" and bucketed it Other, along with 1,250
        # other rows covering ~9,400 words (found 2026-07-27). Resolve it to a
        # real name first, and let the bucket follow from that name instead of
        # defaulting everything to "Other".
        lang_name = language_codes.resolve(n.lang)
        lid = lang_ids.get(lang_name)
        if lid is None:
            # A language not in languages.csv used to be DROPPED, which silently
            # deleted real ancestry and left words marked "resolved" with no
            # ancestor at all (caught by the validator). Instead: create a
            # minimal row flagged era_certain=0 so nothing is lost, and report
            # it so the table gets topped up from evidence rather than guesses.
            unknown_langs[lang_name] += 1
            db.execute(
                "INSERT OR IGNORE INTO language (name, bucket, era_start,"
                " era_end, era_label, era_certain, source_url)"
                " VALUES (?,?,?,?,?,?,?)",
                (lang_name, bucket_for_name(lang_name), 0, 9999,
                 "era unknown", 0,
                 "auto-added at build time; needs curating in languages.csv"))
            lid = db.execute("SELECT lang_id FROM language WHERE name=?",
                              (lang_name,)).fetchone()[0]
            lang_ids[lang_name] = lid
        cur = db.execute(
            "INSERT INTO ety_node (ety_id, lang_id, term, is_head, is_root,"
            " source_id) VALUES (?,?,?,?,?,?)",
            (ety_id, lid, n.term, int(n.rel == "head"), int(n.rel == "root"),
             src_id))
        return cur.lastrowid

    head_id = node_row(head_node)
    if head_id is None:
        return None

    def walk(node, node_id):
        for i, child in enumerate(node.children):
            cid = node_row(child)
            if cid is None:
                continue
            db.execute(
                "INSERT OR IGNORE INTO ety_edge (ety_id, parent_id, child_id,"
                " rel, certainty, ordinal, source_id) VALUES (?,?,?,?,?,?,?)",
                (ety_id, cid, node_id, child.rel, child.certainty, i, src_id))
            walk(child, cid)
    walk(head_node, head_id)
    return head_id


def build(db, words, langs, lang_ids, src_ids):
    tmpl_src = src_ids["wiktextract.templates"]
    rel_src = src_ids["wiktextract.relations"]
    unknown_langs = defaultdict(int)
    stats = defaultdict(int)

    total = len(words)
    for done, (head, rec) in enumerate(words.items(), 1):
        if done % 100_000 == 0:
            print(f"  ...{done:,}/{total:,} words", file=sys.stderr, flush=True)
        trees_all = []
        for num in sorted(rec["etys"]):
            trees_all.extend(build_trees(head, rec["etys"][num], langs,
                                          ordinal=num,
                                          text=rec["text"].get(num)))

        # 'resolved' requires ancestry the spine can actually walk -- a tree
        # whose only ancestor is a dotted root pointer is a 'stub', because
        # the node is drawable but the descent is not attested here.
        status = "resolved" if any(t.direct_node_count() > 1 for t in trees_all) else (
            "stub" if trees_all else "none")
        # NEVER read cur.lastrowid after INSERT OR IGNORE without checking
        # rowcount first: on an ignored insert sqlite3 leaves lastrowid at the
        # last SUCCESSFUL insert on this connection -- which is usually a row
        # in a completely different table. That silently produced ety_ids
        # borrowed from word_relation and blew up on the FK.
        cur = db.execute(
            "INSERT OR IGNORE INTO word (headword, key_lower, status,"
            " ety_count, built_at) VALUES (?,?,?,?,?)",
            (head, head.lower(), status, len(trees_all), now()))
        # `== 1`, not truthiness: rowcount is -1 when sqlite can't determine
        # it, and -1 is truthy, which would take the stale-lastrowid branch.
        wid = cur.lastrowid if cur.rowcount == 1 else db.execute(
            "SELECT word_id FROM word WHERE headword=?", (head,)).fetchone()[0]
        stats[f"status_{status}"] += 1

        # `ordinal` is this word's own 1..n slot and is what UNIQUE protects;
        # `label` carries Wiktionary's etymology number. They are NOT the same
        # number: one Wiktionary etymology can split into several narratives
        # (march has 5 trees across 3 numbered etymologies), and keying on the
        # source number dropped every tree after the first in each group.
        for slot, t in enumerate(trees_all, 1):
            cur = db.execute(
                "INSERT INTO etymology (word_id, ordinal, label, shape,"
                " pos_list, source_id) VALUES (?,?,?,?,?,?)",
                (wid, slot, str(t.ordinal), t.shape,
                 ", ".join(sorted(rec["pos"].get(t.ordinal, ()))) or None,
                 tmpl_src))
            ety_id = cur.lastrowid
            head_id = insert_tree(db, ety_id, t.head, lang_ids, tmpl_src,
                                   unknown_langs)
            db.execute("UPDATE etymology SET head_node_id=? WHERE ety_id=?",
                       (head_id, ety_id))
            stats["etymologies"] += 1
            stats[f"shape_{t.shape}"] += 1

        for pos, gloss, ordinal in rec["senses"]:
            db.execute("INSERT INTO sense (word_id, pos, gloss, ordinal,"
                       " source_id) VALUES (?,?,?,?,?)",
                       (wid, pos, gloss, ordinal, rel_src))
            stats["senses"] += 1

        for i, (kind, term, lang, note) in enumerate(rec["relations"]):
            db.execute(
                "INSERT INTO word_relation (word_id, kind, lang_id, term,"
                " note, ordinal, source_id) VALUES (?,?,?,?,?,?,?)",
                (wid, kind, lang_ids.get(lang), term, note, i, rel_src))
            stats[f"rel_{kind}"] += 1

        # surface_form: the word itself. Only for words we actually have data
        # for -- a lookup row pointing at an empty word is a dead end that
        # would shadow a real match at a worse rank. Inflections/derivations
        # are added by a later stage, once every headword exists.
        if status != "none":
            lowered = head.lower()
            db.execute(
                "INSERT OR IGNORE INTO surface_form (form, word_id, kind, rank,"
                " source_id) VALUES (?,?,?,?,?)",
                (lowered, wid, "exact" if head == lowered else "case",
                 RANK["exact"] if head == lowered else RANK["case"], tmpl_src))
            if head != lowered:
                db.execute(
                    "INSERT OR IGNORE INTO surface_form (form, word_id, kind,"
                    " rank, note, source_id) VALUES (?,?,?,?,?,?)",
                    (head, wid, "verbatim", RANK["verbatim"],
                     "matched as typed, capitals included", tmpl_src))

    return stats, unknown_langs


def materialize_compounds(db, lang_ids, src_ids):
    """
    Give hand-verified compounds a real fork tree.

    `bagpipe`, `blowhard`, `upside` have no etymology templates of their own,
    so the templates alone leave them unresolved -- yet compounds.py records
    743 verified splits and the old stack used them. Rather than keeping that
    as a query-time fallback (which is what let the two features disagree in
    the first place), the split is materialized here as an ordinary fork:
    head, plus one `formed_from` child per part.

    That means nothing downstream needs to know compounds exist. The tree
    renders it like any other fork, and `lineage()` already follows parts into
    their own entries, so `bagpipe` reaches Old English through `bag`.
    """
    import compounds

    splits = dict(compounds.COMPOUND_SPLITS)
    # convert_wikt.py's auto-detected compound_of/blend_of splits, which the
    # old stack consulted alongside the hand-verified list -- `blindspot`,
    # `balljoint`, `boychild` came from here. Loaded from the legacy file
    # because that is where they were extracted to; they are evidence from
    # Wiktionary, not guesses. Hand-verified entries win on collision.
    try:
        with open(os.path.join(HERE, "wikt_words.json"), encoding="utf-8") as f:
            auto = json.load(f).get("auto_compounds") or {}
        for word, parts in auto.items():
            splits.setdefault(word, tuple(parts))
    except (OSError, ValueError):
        pass

    src = src_ids["curated"]
    english = lang_ids["English"]
    resolved = {w for (w,) in db.execute(
        "SELECT key_lower FROM word WHERE status != 'none'")}
    # `Bagpipe` and `bagpipe` share a key_lower, so a plain dict() keeps
    # whichever the scan happened to hit last and the split lands on the
    # capitalised row. COMPOUND_SPLITS keys are lowercase, so prefer the
    # headword spelled the same way.
    unresolved = {}
    for hw, kl, wid in db.execute(
            "SELECT headword, key_lower, word_id FROM word WHERE status='none'"):
        if kl not in unresolved or hw == kl:
            unresolved[kl] = wid

    added = 0
    # Two split keys can differ only by case ("Green Zone" / "green zone") and
    # fold to the same word row, so without this the second insert collides
    # with the first on UNIQUE(word_id, ordinal).
    done = set()
    for word, parts in sorted(splits.items()):
        wid = unresolved.get(word.lower())
        # Only fills gaps: a word the templates already explained is never
        # overwritten by a split.
        if wid is None or wid in done:
            continue
        if not all(p.lower() in resolved for p in parts):
            continue
        done.add(wid)
        cur = db.execute(
            "INSERT INTO etymology (word_id, ordinal, label, shape, source_id)"
            " VALUES (?,?,?,?,?)", (wid, 1, "1", "fork", src))
        ety_id = cur.lastrowid
        head = db.execute(
            "INSERT INTO ety_node (ety_id, lang_id, term, is_head, source_id)"
            " VALUES (?,?,?,1,?)",
            (ety_id, english, word, src)).lastrowid
        for i, part in enumerate(parts):
            nid = db.execute(
                "INSERT INTO ety_node (ety_id, lang_id, term, source_id)"
                " VALUES (?,?,?,?)", (ety_id, english, part, src)).lastrowid
            db.execute(
                "INSERT INTO ety_edge (ety_id, parent_id, child_id, rel,"
                " certainty, ordinal, source_id) VALUES (?,?,?,?,?,?,?)",
                (ety_id, nid, head, "formed_from", "direct", i, src))
        db.execute("UPDATE etymology SET head_node_id=? WHERE ety_id=?",
                   (head, ety_id))
        db.execute("UPDATE word SET status='resolved', ety_count=1"
                   " WHERE word_id=?", (wid,))
        db.execute(
            "INSERT OR IGNORE INTO surface_form (form, word_id, kind, rank,"
            " note, source_id) VALUES (?,?,?,?,?,?)",
            (word.lower(), wid, "exact", RANK["exact"],
             "verified compound split", src))
        added += 1
    return added


def materialize_surface_forms(db, src_ids):
    """
    Precompute every way a typed word can reach a headword.

    This is the whole cascade -- case fallback, inflections, derivational
    stemming -- resolved ONCE here instead of being re-derived at query time
    by four modules with three different case policies. `wolves` gets a row
    pointing at `wolf`; `professional` gets one pointing at `profession`.
    """
    import inflections
    from resolver import _stem_candidates

    src = src_ids["builder.inference"]
    # `wolf` and `Wolf` share a key_lower, so a plain dict() keeps whichever
    # row the scan hit last -- and it kept the SURNAME. Every inflection of
    # every word with a capitalised homograph then pointed at the proper noun:
    # `wolves` resolved to German `Wolf` and lost its Proto-Germanic ancestry
    # entirely. Same failure the old stack fought as the went/Went and ran/Ran
    # bugs. Inflection bases are common nouns, so prefer the headword spelled
    # exactly like its key.
    heads = {}
    spelled = set()          # headwords AS SPELLED, case included
    for kl, hw, wid in db.execute(
            "SELECT key_lower, headword, word_id FROM word"
            " WHERE status != 'none'"):
        if kl not in heads or hw == kl:
            heads[kl] = wid
        spelled.add(hw)
    added = defaultdict(int)

    # Inflections: real tagged data (wolves -> wolf), not a spelling guess.
    #
    # The skip test is against headwords AS SPELLED, not against folded keys.
    # Folded, the proper noun `Ran` occupies the key `ran` and suppressed the
    # `ran -> run` inflection row entirely, so `ran` resolved to a Hebrew
    # given name. A capitalised homograph must not veto a real inflection --
    # it has its own rank-50 `case` row and loses to rank 40 on merit.
    for form, base in inflections._load().items():
        wid = heads.get(base.lower())
        if wid and form not in spelled:
            db.execute("INSERT OR IGNORE INTO surface_form (form, word_id,"
                       " kind, rank, note, source_id) VALUES (?,?,?,?,?,?)",
                       (form, wid, "inflection", RANK["inflection"],
                        f"inflected form of {base}", src))
            added["inflection"] += 1

    # Derivational stemming: -ness/-ment/-tion/-al/-cy. Wiktionary's `forms`
    # field never covers these, so the hand-written rules stay -- but only
    # their OUTCOMES are stored, which is bounded.
    unresolved = [w for (w,) in db.execute(
        "SELECT headword FROM word WHERE status='none'")]
    for word in unresolved:
        for cand in _stem_candidates(word.lower()):
            wid = heads.get(cand)
            if wid:
                db.execute("INSERT OR IGNORE INTO surface_form (form, word_id,"
                           " kind, rank, note, source_id) VALUES (?,?,?,?,?,?)",
                           (word.lower(), wid, "derivation", RANK["derivation"],
                            f"stems to {cand}", src))
                added["derivation"] += 1
                break
    return added


def _regular_forms(word):
    """Regular inflected spellings of `word`, by the ordinary English rules."""
    out = {word + "s"}
    if word.endswith(("s", "x", "z", "ch", "sh")):
        out.add(word + "es")
    if len(word) > 2 and word.endswith("y") and word[-2] not in "aeiou":
        out.add(word[:-1] + "ies")
    if word.endswith("e"):
        out.update({word + "d", word[:-1] + "ing"})
    else:
        out.update({word + "ed", word + "ing"})
    return out - {word}


def materialize_generated_forms(db, src_ids):
    """
    Emit the regular inflections of every resolved word, FORWARD.

    materialize_surface_forms() only stems words that exist as headwords in
    the dump, because that is all it can see. The old resolver stemmed
    whatever was typed, at query time -- so it answered `Ryans`, `-athons`,
    `arhats` and 182 other plurals that simply have no Wiktionary page. That
    single difference was the largest cause of regression against the old
    stack (185 of 390 lost words).

    Reproducing it without putting branching back into the read path means
    going the other way: generate the forms from the words we DO have. Bounded
    at ~5 spellings per resolved word, and ranked below real tagged inflection
    data, so Wiktionary's own `forms` always wins and any collision with a
    genuine headword loses to that headword's rank-10 exact row.
    """
    src = src_ids["builder.inference"]
    rows = db.execute(
        "SELECT headword, key_lower, word_id FROM word WHERE status != 'none'"
    ).fetchall()
    taken = {f for (f,) in db.execute("SELECT DISTINCT form FROM surface_form")}
    added = 0
    for headword, key_lower, wid in rows:
        for form in _regular_forms(key_lower):
            if form in taken:
                continue
            db.execute(
                "INSERT OR IGNORE INTO surface_form (form, word_id, kind,"
                " rank, note, source_id) VALUES (?,?,?,?,?,?)",
                (form, wid, "generated", RANK["generated"],
                 f"regular inflection of {headword}", src))
            added += 1
    return added


def cache_trees(db):
    """
    Denormalise each word's etymologies into word.tree_json.

    Purely a read-path optimisation so lookup is a single row fetch; always
    rebuildable from ety_node/ety_edge, never the source of truth.
    """
    nodes_by_ety = defaultdict(dict)
    for ety_id, nid, lang, term, is_head, is_root in db.execute(
        "SELECT n.ety_id, n.node_id, l.name, n.term, n.is_head, n.is_root"
        " FROM ety_node n JOIN language l ON l.lang_id=n.lang_id"):
        nodes_by_ety[ety_id][nid] = {"lang": lang, "term": term,
                                      "is_head": is_head, "is_root": is_root,
                                      "children": []}
    edges_by_ety = defaultdict(list)
    for ety_id, parent, child, rel, certainty, ordinal in db.execute(
        "SELECT ety_id, parent_id, child_id, rel, certainty, ordinal"
        " FROM ety_edge ORDER BY ordinal"):
        edges_by_ety[ety_id].append((parent, child, rel, certainty))

    by_word = defaultdict(list)
    for ety_id, word_id, ordinal, label, shape in db.execute(
        "SELECT ety_id, word_id, ordinal, label, shape FROM etymology"
        " ORDER BY word_id, ordinal"):
        nodes = nodes_by_ety.get(ety_id, {})
        for parent, child, rel, certainty in edges_by_ety.get(ety_id, ()):
            if parent in nodes and child in nodes:
                node = dict(nodes[parent], rel=rel, certainty=certainty)
                nodes[parent] = node
                nodes[child]["children"].append(node)
        head = next((n for n in nodes.values() if n["is_head"]), None)
        if head:
            by_word[word_id].append({"ordinal": ordinal, "label": label,
                                      "shape": shape, "head": head})

    for wid, etys in by_word.items():
        db.execute("UPDATE word SET tree_json=? WHERE word_id=?",
                   (json.dumps(etys, ensure_ascii=False), wid))
    return len(by_word)


def validate(db):
    """
    Build-gating invariants. Goal 2 as an executable assertion rather than
    something to keep an eye on: if anything floats, the build fails.
    """
    problems = {}

    # 1. Every node reachable from its head. THE no-floating-nodes rule.
    floating = db.execute("""
        SELECT COUNT(*) FROM ety_node n
        WHERE n.is_head = 0
          AND NOT EXISTS (SELECT 1 FROM ety_edge e
                          WHERE e.ety_id = n.ety_id AND e.parent_id = n.node_id)
    """).fetchone()[0]
    if floating:
        problems["floating_nodes"] = floating

    # 2. Exactly one head per etymology.
    bad_heads = db.execute("""
        SELECT COUNT(*) FROM (
          SELECT ety_id, SUM(is_head) h FROM ety_node GROUP BY ety_id
          HAVING h != 1)
    """).fetchone()[0]
    if bad_heads:
        problems["etymologies_without_exactly_one_head"] = bad_heads

    # 3. A word marked resolved must have ancestry the spine can WALK -- a
    #    dotted-only tree is drawable but not traversable, so it is a stub.
    hollow = db.execute("""
        SELECT COUNT(*) FROM word w WHERE w.status='resolved'
          AND NOT EXISTS (SELECT 1 FROM etymology e
                          JOIN ety_edge g ON g.ety_id=e.ety_id
                          WHERE e.word_id=w.word_id AND g.certainty='direct')
    """).fetchone()[0]
    if hollow:
        problems["resolved_words_with_no_ancestor"] = hollow

    # 4. No surface_form may point at a word with no data.
    dangling = db.execute("""
        SELECT COUNT(*) FROM surface_form s JOIN word w ON w.word_id=s.word_id
        WHERE w.status='none'
    """).fetchone()[0]
    if dangling:
        problems["surface_forms_pointing_at_empty_words"] = dangling

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DB_PATH)
    ap.add_argument("--jsonl", default=JSONL)
    ap.add_argument("--sample", type=int, default=None,
                     help="stop after N distinct words (fast dev build)")
    ap.add_argument("--words", nargs="*", default=None,
                     help="build only these words")
    args = ap.parse_args()

    t0 = time.time()
    langs = languages.load()
    print(f"languages: {len(langs)}", file=sys.stderr)

    # Build to a scratch file and swap it in at the very end.
    #
    # Two reasons, both encountered for real. The app opens etymology.db
    # through DbResolver and holds it, and Windows refuses to delete an open
    # file -- so building in place either fails outright or (worse, before
    # connect() was made loud) silently appended to the previous database.
    # And a build takes ~10 minutes, during which a running app would
    # otherwise be reading a half-populated file.
    final = args.out
    work = final + ".new"
    db = connect(work, fresh=True)
    lang_ids = load_languages(db, langs)
    src_ids = load_sources(db)
    db.commit()

    print("scanning dump...", file=sys.stderr)
    words = scan_dump(args.jsonl, limit=args.sample, only=args.words)

    print("building...", file=sys.stderr)
    stats, unknown = build(db, words, langs, lang_ids, src_ids)
    db.commit()

    print("materializing compounds...", file=sys.stderr)
    stats["compound_splits"] = materialize_compounds(db, lang_ids, src_ids)
    db.commit()

    print("materializing surface forms...", file=sys.stderr)
    for kind, n in materialize_surface_forms(db, src_ids).items():
        stats[f"surface_{kind}"] = n
    db.commit()

    print("generating regular forms...", file=sys.stderr)
    stats["surface_generated"] = materialize_generated_forms(db, src_ids)
    db.commit()

    print("caching trees...", file=sys.stderr)
    stats["tree_json_cached"] = cache_trees(db)
    db.execute("INSERT OR REPLACE INTO build_meta (key, value) VALUES (?,?)",
               ("built_at", now()))
    db.commit()

    print(f"\nbuilt {work} in {time.time()-t0:.0f}s", file=sys.stderr)
    for k in sorted(stats):
        print(f"  {k:26s} {stats[k]:>9,}")
    if unknown:
        # These are AUTO-ADDED with era_certain=0, not dropped -- dropping
        # them is what previously deleted real ancestry and left words marked
        # resolved with no ancestor. The count is per distinct language (it
        # increments only on first sight, before the row exists), so it is a
        # to-curate list for languages.csv, not a volume measure.
        print(f"\n  languages auto-added, needing curation in languages.csv"
              f" ({len(unknown)} distinct):")
        for name in sorted(unknown)[:20]:
            print(f"    {name}")
        if len(unknown) > 20:
            print(f"    ... and {len(unknown) - 20} more")

    problems = validate(db)
    print("\n  === validators ===")
    if problems:
        for k, v in problems.items():
            print(f"    FAIL  {k}: {v:,}")
    else:
        print("    PASS  no floating nodes, one head per etymology,"
              " no hollow words, no dangling surface forms")

    # Fold the WAL back in so the swap moves ONE self-contained file.
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.close()
    if problems:
        print(f"\n  validators failed; leaving the build at {work}",
              file=sys.stderr)
        sys.exit(1)

    print(f"\n  swapping into place: {final}", file=sys.stderr)
    for suffix in ("-wal", "-shm"):
        try:
            os.remove(work + suffix)
        except OSError:
            pass
    try:
        os.replace(work, final)
    except OSError as exc:
        # The app holds the old file open; the new one is complete and valid,
        # so keep it rather than throwing away a ten-minute build.
        print(f"\n  could not replace {final}: {exc}\n"
              f"  The finished database is at {work} -- stop whatever has "
              f"{os.path.basename(final)} open (the running app.py) and "
              f"rename it, or just restart the app after renaming.",
              file=sys.stderr)
        sys.exit(2)
    print(f"  done in {time.time()-t0:.0f}s", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
