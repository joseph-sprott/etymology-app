"""
Phase 3: old data layer vs etymology.db, on every word, triaged.

The gate before switching over is not "the new one looks nicer" -- it is
"nothing got worse". So this classifies every single difference into one of a
fixed set of buckets and prints counts plus real examples, rather than
reporting an average that could hide a thousand regressions inside a bigger
number of improvements.

    python scripts/compare_db.py                    # every word
    python scripts/compare_db.py --sample 20000     # quick pass
    python scripts/compare_db.py --bucket lost_data --show 40

Buckets, worst first:
    lost_data        old resolved it, new doesn't             REGRESSION
    bucket_changed   the percentage bars move                 REVIEW
    root_changed     deepest root differs                     REVIEW
    gained_data      old had nothing, new resolves it         IMPROVEMENT
    unfloated        old drew >1 disconnected branch          IMPROVEMENT
    same             no material difference                   NEUTRAL

Only `lost_data` blocks the switch. The two REVIEW buckets are for reading
by hand -- `mile` dropping its false PIE edge shows up in root_changed, and
so would a fresh mistake of exactly the same kind, which is the point.
"""
import argparse
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import etymology_db
from buckets_wikt import ENGLISH_STAGE_NAMES as ENGLISH_STAGES

# Only losing an answer outright blocks the switch. A changed bucket or root
# is not automatically worse -- `mile` losing its false PIE edge shows up as
# a change -- so those are for reading, not for gating.
REGRESSION_BUCKETS = ("lost_data",)


def old_answer(app, word):
    """
    What the OLD stack reports, as the three things the UI shows.

    Deliberately NOT the raw chain: `Resolution.chain` omits English stages
    and falls back to BUCKET names ("Germanic") where the new spine carries
    real language names ("Old English"), so comparing the two lists directly
    would score nearly every word as changed and tell us nothing. These three
    fields are the same quantity on both sides.
    """
    try:
        res = app.RESOLVER.resolve(word)
    except Exception:
        return {"resolved": False, "bucket": None, "root": None, "branches": 0}
    direct = res.view("direct")
    root = res.view("root")
    try:
        tree = app.resolve_tree(word)
        branches = len((tree or {}).get("branches") or [])
    except Exception:
        branches = 0
    return {
        "resolved": bool(direct.resolved),
        "bucket": direct.bucket,
        # Strip the " (from PIE)" annotation -- it's presentation, and the new
        # side spells the same fact out as an edge instead.
        "root": (root.depth_lang or "").replace(" (from PIE)", "") or None,
        "branches": branches,
    }


def new_answer(entry, buckets, db):
    """The same three things, read off the new tree. One object, two readings."""
    if entry is None or not entry.resolved or not entry.primary:
        return {"resolved": False, "bucket": None, "root": None, "branches": 1,
                "shape": entry.primary.shape if (entry and entry.primary) else None,
                "match": entry.match_kind if entry else None}
    # lineage(), not spine(): a fork's parts are pointers to other words, and
    # stopping at the part is what scored `nationalize` as Germanic.
    spine = db.lineage(entry)[1:]               # drop the English head
    foreign = [n for n in spine if n.lang not in ENGLISH_STAGES]
    donor = foreign[0].lang if foreign else (spine[-1].lang if spine else None)
    return {
        "resolved": True,
        "bucket": buckets.bucket_for_name(donor) if donor else None,
        "root": spine[-1].lang if spine else None,
        # Structurally impossible for the new side to exceed 1: every node
        # hangs off the head. Kept so the comparison is symmetric.
        "branches": 1,
        "shape": entry.primary.shape,
        "match": entry.match_kind,
    }


def vocabulary(app, db):
    """
    Every word EITHER side knows -- the union, deliberately.

    Iterating only the new database's headwords would make `lost_data`
    structurally unreachable: a word the old layer resolves and the new one
    never heard of would simply not be looked at. That is the one bucket that
    blocks the switch, so the word list must be able to contain it.
    """
    words = {w for (w,) in db._db.execute("SELECT headword FROM word")}
    words |= set(getattr(app, "TREES", {}) or {})
    stack = list(getattr(app.RESOLVER, "backends", []) or []) + [app.RESOLVER]
    for backend in stack:
        words |= set(getattr(backend, "words", {}) or {})
        words |= set(getattr(backend, "auto_compounds", {}) or {})
    return words


def classify(old, new):
    """One word -> one bucket. Order matters: worst applicable wins."""
    if old["resolved"] and not new["resolved"]:
        return "lost_data"
    if new["resolved"] and not old["resolved"]:
        return "gained_data"
    if not old["resolved"] and not new["resolved"]:
        return "same"
    if old["bucket"] != new["bucket"]:
        return "bucket_changed"        # the percentage bars move
    if old["root"] != new["root"]:
        return "root_changed"          # `mile`'s fix lands here
    if old["branches"] > 1:
        return "unfloated"
    return "same"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=etymology_db.DB_PATH)
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--show", type=int, default=8,
                    help="examples to print per bucket")
    ap.add_argument("--bucket", default=None,
                    help="print only this bucket, with more examples")
    ap.add_argument("--seed", type=int, default=20260725)
    ap.add_argument("--dump", default=None,
                    help="TSV of every non-`same` word, for offline triage")
    args = ap.parse_args()

    print("loading new database...", file=sys.stderr)
    db = etymology_db.get(args.db)

    print("loading OLD data layer (this is the slow part)...", file=sys.stderr)
    # Force the LEGACY stack for the "old" side. app.default_resolver() now
    # puts DbResolver first, so without this the comparison silently measures
    # the new layer against itself -- which looks like a spectacular result
    # (0.04% changed) and proves nothing.
    os.environ["ETYMOLOGY_DB"] = "0"
    import app
    assert not any(type(b).__name__ == "DbResolver"
                   for b in getattr(app.RESOLVER, "backends", [])), \
        "old side is contaminated with DbResolver"

    words = sorted(vocabulary(app, db))
    if args.sample and args.sample < len(words):
        random.Random(args.seed).shuffle(words)
        words = sorted(words[:args.sample])

    print(f"comparing {len(words):,} words...", file=sys.stderr)
    counts = Counter()
    examples = defaultdict(list)

    import buckets_wikt

    dump = open(args.dump, "w", encoding="utf-8") if args.dump else None
    if dump:
        dump.write("bucket\tword\told_bucket\told_root\told_branches"
                   "\tnew_bucket\tnew_root\tnew_shape\tnew_match\n")

    for i, word in enumerate(words, 1):
        if i % 50_000 == 0:
            print(f"  ...{i:,}/{len(words):,}", file=sys.stderr, flush=True)
        old = old_answer(app, word)
        new = new_answer(db.entry(word), buckets_wikt, db)
        bucket = classify(old, new)
        counts[bucket] += 1
        if len(examples[bucket]) < 400:
            examples[bucket].append((word, old, new))
        if dump and bucket != "same":
            dump.write("\t".join(str(x) for x in (
                bucket, word, old["bucket"], old["root"], old["branches"],
                new["bucket"], new["root"], new.get("shape"),
                new.get("match"))) + "\n")
    if dump:
        dump.close()

    total = sum(counts.values())
    print("\n" + "=" * 72)
    print(f"  {total:,} words compared")
    print("=" * 72)
    order = ["lost_data", "bucket_changed", "root_changed", "gained_data",
             "unfloated", "same"]
    for bucket in order:
        n = counts.get(bucket, 0)
        flag = "  <-- BLOCKS SWITCH" if bucket in REGRESSION_BUCKETS and n else ""
        print(f"  {bucket:15} {n:9,}  {n / total * 100:5.2f}%{flag}")

    show_buckets = [args.bucket] if args.bucket else order
    limit = 40 if args.bucket else args.show
    for bucket in show_buckets:
        rows = examples.get(bucket) or []
        if not rows or bucket == "same":
            continue
        print(f"\n--- {bucket} ({counts[bucket]:,}) ---")
        for word, old, new in rows[:limit]:
            print(f"  {word}")
            print(f"      old: bucket={old['bucket']!r} root={old['root']!r}"
                  f" branches={old['branches']}")
            print(f"      new: bucket={new['bucket']!r} root={new['root']!r}")

    blocking = sum(counts.get(b, 0) for b in REGRESSION_BUCKETS)
    print("\n" + "=" * 72)
    if blocking:
        print(f"  {blocking:,} regressions -- DO NOT SWITCH OVER YET")
    else:
        print("  no regressions; the switch is safe on this measure")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
