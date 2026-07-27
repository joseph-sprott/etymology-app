"""
Run the test suites under coverage and print ONE honest table.

    python .claude/skills/etymology-test-first/scripts/coverage_report.py
    python .claude/skills/etymology-test-first/scripts/coverage_report.py --fast

Deterministic by design (skill-audit dimension 2): the omit list, the branch
flag and the suite order are decisions that should not be retyped -- and
retyping them is exactly how a coverage number quietly gains an omit and
becomes incomparable to the last one.

TWO NUMBERS ARE PRINTED, ALWAYS:

  * whole codebase, build scripts included -- the honest figure
  * runtime only, build scripts excluded  -- the one worth optimising

Reporting only the second inflates the result by ~30 points. Joe reads
"coverage" as JUnit/JaCoCo line coverage, so `--branch` is on: branch coverage
is closer to what he means and much harder to game.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

# Everything the suites can reach. Only the tests themselves are omitted --
# a test file counting toward its own coverage is meaningless.
OMIT_ALL = "*/__pycache__/*,test_*.py,scripts/verify.py"

# The runtime slice: what actually serves a request or answers a word.
OMIT_RUNTIME = OMIT_ALL + ",build_*.py,convert_*.py,fetch_*.py,export_*.py,scripts/*"

FAST_SUITES = ["test_units.py"]
FULL_SUITES = ["test_units.py", "test_regression.py", "test_etymology_db.py"]


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def measure(suites, omit, label):
    first = True
    for suite in suites:
        if not os.path.exists(os.path.join(ROOT, suite)):
            print(f"  (skipping {suite} -- not present)", file=sys.stderr)
            continue
        cmd = [sys.executable, "-m", "coverage", "run"]
        if not first:
            cmd.append("-a")
        cmd += ["--branch", f"--source=.", f"--omit={omit}", suite]
        proc = run(cmd)
        if proc.returncode != 0 and "test_regression" not in suite:
            # test_regression exits 1 on its known/accepted answer failures;
            # that is not a coverage problem. Anything else is worth showing.
            print(f"  ({suite} exited {proc.returncode})", file=sys.stderr)
        first = False
    rep = run([sys.executable, "-m", "coverage", "report", "--sort=cover"])
    total = next((l for l in reversed(rep.stdout.splitlines())
                  if l.startswith("TOTAL")), "")
    print(f"\n=== {label} ===")
    print(rep.stdout.rstrip())
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true",
                    help="unit suite only (~1s) instead of every suite")
    ap.add_argument("--quiet", action="store_true",
                    help="print only the two TOTAL lines")
    args = ap.parse_args()

    suites = FAST_SUITES if args.fast else FULL_SUITES
    out = sys.stdout
    if args.quiet:
        sys.stdout = open(os.devnull, "w")

    whole = measure(suites, OMIT_ALL, "WHOLE CODEBASE (build scripts included)")
    runtime = measure(suites, OMIT_RUNTIME, "RUNTIME ONLY (build scripts excluded)")

    sys.stdout = out
    print()
    print("  whole codebase :", whole.strip() or "(none)")
    print("  runtime only   :", runtime.strip() or "(none)")
    print()
    print("  Report the first number, or both. The second alone is an omit list,")
    print("  not an achievement.")


if __name__ == "__main__":
    main()
