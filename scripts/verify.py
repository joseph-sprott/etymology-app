"""
One command that answers "is the database good?" -- compactly.

WHY THIS EXISTS (2026-07-26, Joe): during the etymology.db rework this exact
sequence -- invariants, regression suite, spot-check a panel of words, check
the two features agree -- was re-typed by hand after all ten builds, each time
dumping several screens of output. That is both slow and expensive: every
stats block stays in context forever. This runs the whole loop and prints ONE
summary, with detail ONLY for what failed.

    python scripts/verify.py                    # the live database
    python scripts/verify.py --db etymology.db.new   # before swapping it in
    python scripts/verify.py --verbose          # show passing checks too
    python scripts/verify.py --words mile father # add words to the panel

Exit code is non-zero if any invariant fails or a panel word regresses, so it
can gate a build.
"""
import argparse
import io
import os
import subprocess
import sys
from contextlib import redirect_stdout

import scriptlib

scriptlib.bootstrap()

ROOT = scriptlib.PROJECT_ROOT

# Words with a KNOWN correct answer, each earning its place by having been
# wrong at some point. The comment is the bug it guards against -- keep it,
# it is the difference between a panel and a pile of words.
PANEL = {
    "mile":      "Latin",        # false Middle-English -> PIE edge
    "intrude":   "Latin",        # tree and analyzer disagreed
    "father":    "Proto-West Germanic",   # chain lived only in rendered text
    "beef":      "Anglo-Norman",
    "knife":     "Old Norse",    # Norse layer lost to the era guard
    "law":       "Old Norse",
    "trust":     None,           # native: PIE is a root, not a donor
    "wolves":    "Proto-West Germanic",   # resolved to the surname Wolf
    "ran":       "Old Norse",    # resolved to the Hebrew given name Ran
    # Native Germanic descent. Proto-West Germanic counts as a "donor" here
    # only because it isn't an English stage -- the point of the check is that
    # `went` must reach GERMANIC ancestry via `go`, not the unrelated Japanese
    # homograph ç¢ (the board game) it briefly resolved to.
    "went":      "Proto-West Germanic",
    "table":     "Old French",   # picked the wrong one of two etymologies
    "telephone": "Ancient Greek",
    "October":   "Old French",
    # "*" = must reach SOME foreign donor. `bagpipe` has no etymology of its
    # own; the bug it guards is a compound failing to follow its components
    # at all, and any donor proves it did. Naming a specific language here
    # would just re-assert whatever the code currently produces.
    "bagpipe":   "*",
    # compute + -er, with a PIE root on `compute`. That root made the walk
    # look finished, so the bars said PIE while the tree showed French.
    "computer":  "French",
    # Split into stem + suffix, so half the word's weight went to the affix:
    # `beautiful` lost half to `ful` (resolves to nothing -> Unknown) and
    # `darkness` half to `ness` (a real word, a headland). The donor below was
    # right the whole time -- test_regression.py guards the half that wasn't.
    "beautiful": "Old French",
    # Native descent; "Proto-West Germanic" counts as the donor here for the
    # same reason `went` does -- it is simply the deepest non-English stage.
    "darkness":  "Proto-West Germanic",
}


def run_module(path, args=()):
    """Run a check script, return (ok, last summary line, full text)."""
    proc = subprocess.run([sys.executable, path, *args], cwd=ROOT,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    text = (proc.stdout or "") + (proc.stderr or "")
    summary = next((l.strip() for l in reversed(text.splitlines())
                    if "checks passed" in l), "(no summary)")
    return proc.returncode == 0, summary, text


def check_panel(db_path, extra_words):
    """Each panel word must still name its known donor language."""
    import etymology_db
    db = etymology_db.get(db_path) if db_path else etymology_db.get()
    english = etymology_db.ENGLISH_STAGES

    failures = []
    for word, expect in list(PANEL.items()) + [(w, None) for w in extra_words]:
        entry = db.entry(word)
        if entry is None:
            failures.append(f"{word}: not found at all")
            continue
        line = db.lineage(entry)
        donors = [n.lang for n in line[1:]
                  if n.lang not in english and n.rel != "root"]
        if expect is None:
            # Expected NATIVE: any foreign donor means a homograph crept in.
            if donors:
                failures.append(f"{word}: expected native, got {donors[0]}"
                                f" (resolved to {entry.headword!r})")
        elif expect == "*":
            if not donors:
                failures.append(f"{word}: expected some foreign donor, got none"
                                f" (resolved to {entry.headword!r})")
        elif expect not in donors:
            failures.append(f"{word}: expected {expect}, got "
                            f"{donors[0] if donors else 'nothing'}"
                            f" (resolved to {entry.headword!r})")
    return failures


def check_agreement(db_path):
    """
    Goal 1: every language the analyzer reports must appear in the tree.

    Containment, not string equality -- Deepest Root names the deepest
    non-PIE language while the tree also draws PIE, so comparing the two
    labels measures a design decision rather than agreement.
    """
    os.environ.pop("ETYMOLOGY_DB", None)
    import etymology_db
    if db_path:
        etymology_db.get(db_path)
    # word_trees, not app: this needs `resolve_tree` and a resolver, neither
    # of which is web code. Importing `app` dragged Flask and the page
    # templates in just to draw a tree (2026-07-27 audit).
    import word_trees
    resolver = word_trees.shared_resolver()

    failures = []
    for word in PANEL:
        tree = word_trees.resolve_tree(word)
        langs = set()
        if tree:
            langs.add(tree["lang"])

            def collect(n):
                langs.add(n["lang"])
                for c in n.get("children", ()):
                    collect(c)
            for b in tree["branches"]:
                collect(b)
        res = resolver.resolve(word)
        reported = {l.specific_lang or l.lang for l in res.chain}
        root = (res.view("root").depth_lang or "").replace(" (from PIE)", "")
        if root:
            reported.add(root)
        reported = {r for r in reported if r and r != "English (native core)"}
        missing = reported - langs
        if missing:
            failures.append(f"{word}: analyzer says {sorted(missing)},"
                            f" tree doesn't show it")
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--words", nargs="*", default=[])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--skip-regression", action="store_true",
                    help="skip the slow legacy suite")
    args = ap.parse_args()

    rows = []
    detail = {}

    ok, summary, text = run_module(os.path.join(ROOT, "test_etymology_db.py"),
                                   [args.db] if args.db else [])
    rows.append(("invariants", summary, ok))
    detail["invariants"] = [l for l in text.splitlines() if "FAIL" in l]

    # The fast unit suite (2026-07-27 audit). Runs first-ish and takes about a
    # second, so a broken predicate is reported before the slow suite spends
    # minutes loading the world to tell you the same thing.
    ok, summary, text = run_module(os.path.join(ROOT, "test_units.py"))
    rows.append(("units (fast)", summary, ok))
    detail["units (fast)"] = [l.strip() for l in text.splitlines()
                              if l.strip().startswith("FAIL")]

    if not args.skip_regression:
        ok, summary, text = run_module(os.path.join(ROOT, "test_regression.py"))
        rows.append(("regression (legacy)", summary, ok))
        detail["regression (legacy)"] = [l.strip() for l in text.splitlines()
                                          if l.strip().startswith("FAIL")]

    buf = io.StringIO()
    with redirect_stdout(buf):
        panel_fail = check_panel(args.db, args.words)
    rows.append(("known words", f"{len(PANEL) + len(args.words) - len(panel_fail)}"
                 f"/{len(PANEL) + len(args.words)} correct", not panel_fail))
    detail["known words"] = panel_fail

    buf = io.StringIO()
    with redirect_stdout(buf):
        agree_fail = check_agreement(args.db)
    rows.append(("tree/analyzer agree",
                 f"{len(PANEL) - len(agree_fail)}/{len(PANEL)} contained",
                 not agree_fail))
    detail["tree/analyzer agree"] = agree_fail

    print()
    for name, summary, ok in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:22} {summary}")
    for name, lines in detail.items():
        if lines and (not args.verbose or True):
            print(f"\n  --- {name} ---")
            for line in lines[:25]:
                print(f"    {line}")
            if len(lines) > 25:
                print(f"    ... and {len(lines) - 25} more")

    # The legacy suite is expected to fail where the rework deliberately
    # changed behaviour, so it reports but does not gate.
    blocking = [n for n, _, ok in rows if not ok and n != "regression (legacy)"]
    print()
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
