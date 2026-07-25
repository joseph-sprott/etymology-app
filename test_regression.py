"""
Standalone regression check for the Etymology Analyzer -- no test framework
dependency (pytest isn't installed and this project has never used one), just
plain assertions with a PASS/FAIL summary. Run directly:

    python test_regression.py

Exits 0 if everything passes, 1 if anything fails -- usable as a real CI gate
later even without adding pytest. Covers:
  - the historical verified-word suite (CLAUDE.md "Current state")
  - known multi-sense-collision corrections (die/bull/and/low/... /tag/auto)
  - the compound-display feature (upside/purebred/.../mindset/meltdown)
  - the case-fallback guard (found/went/ran -- issue #12 and its 2026-07-24
    widening)
  - the bare-root-stub guard (issue #14 -- vitamin/critical)
  - the three-mode README example (checkmate)
  - tree/analyzer consistency (issue #16 -- a word fixed via inheritance or
    stemming, not raw tree data, must still produce a real tree)

Run this after ANY regeneration (see the etymology-regen skill) before
trusting the result, and after ANY corrections.py/compounds.py/
tree_corrections.py edit even without a full regen (corrections/compounds
apply immediately at resolver load time).
"""
import sys

from resolver import default_resolver

RESOLVER = default_resolver()

failures = []
passed = 0


def check(label, condition):
    global passed
    if condition:
        print(f"  PASS  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}")
        failures.append(label)


def bucket(word, mode="direct"):
    return RESOLVER.resolve(word).view(mode).bucket


print("=== Historical verified-word suite (Direct Source) ===")
HISTORICAL = {
    "skill": "Norse", "table": "French", "sky": "Norse", "egg": "Norse",
    "trust": "Norse", "anger": "Norse", "knife": "Norse", "they": "Norse",
    "them": "Norse", "law": "Norse", "beef": "French", "government": "French",
    "justice": "French", "army": "French", "the": "Germanic",
}
for word, expected in HISTORICAL.items():
    got = bucket(word)
    check(f"{word} -> {expected} (got {got})", got == expected)

print()
print("=== Multi-sense-collision corrections (must still hold) ===")
COLLISIONS = {
    "die": "Norse", "bull": "Norse", "and": "Germanic", "low": "Norse",
    "with": "Germanic", "back": "Germanic", "seen": "Germanic",
    "tag": "Germanic", "auto": "Greek",
}
for word, expected in COLLISIONS.items():
    got = bucket(word)
    check(f"{word} -> {expected} (got {got})", got == expected)

print()
print("=== Case-fallback guard (issue #12, widened 2026-07-24) ===")
CASE_FALLBACK = {"found": "French", "went": "Germanic", "ran": "Norse"}
for word, expected in CASE_FALLBACK.items():
    got = bucket(word)
    check(f"{word} -> {expected}, not a coincidental capitalized homograph (got {got})",
          got == expected)

print()
print("=== Bare-root-stub guard (issue #14) ===")
# "vitamin" has no sibling word the resolver's stem-retry can reach, so it
# stays honestly Unknown for Direct Source (the guard doing its job).
# "critical" is DIFFERENT despite the same root-stub shape in the data: the
# resolver's own "-al" suffix rule (added for "professional") independently
# retries "critic", which has a real, non-stub entry -- so "critical"
# legitimately resolving to French is a correct side effect, not a
# regression of the guard. Keeping both cases here, with different
# expectations, so a future change can't quietly break either shape.
d = RESOLVER.resolve("vitamin").view("direct")
r = RESOLVER.resolve("vitamin").view("root")
check("vitamin: Direct Source stays Unknown (no fabricated immediate donor)",
      d.bucket == "Unknown")
check(f"vitamin: Deepest Root still shows real PIE citation (got {r.bucket})",
      r.bucket != "Unknown")

d = RESOLVER.resolve("critical").view("direct")
r = RESOLVER.resolve("critical").view("root")
check(f"critical: Direct Source resolves via the 'critic' stem retry, not the bare stub (got {d.bucket})",
      d.bucket == "French")
check(f"critical: Deepest Root still shows PIE (got {r.bucket})",
      r.bucket != "Unknown")

print()
print("=== Compound-display feature (must still split) ===")
COMPOUNDS = ["upside", "purebred", "outdoorsman", "mindset", "meltdown"]
for word in COMPOUNDS:
    view = RESOLVER.resolve(word).view("direct")
    check(f"{word} splits into parts", bool(view.parts))

print()
print("=== Three-mode README example (checkmate) ===")
res = RESOLVER.resolve("checkmate")
MODE_EXPECT = {"direct": "French", "influence": "Semitic", "root": "Indo-Iranian"}
for mode, expected in MODE_EXPECT.items():
    got = res.view(mode).bucket
    check(f"checkmate {mode} -> {expected} (got {got})", got == expected)

print()
print("=== Tree/analyzer consistency (issue #16) ===")
try:
    import app as app_module
    app_module.RESOLVER = RESOLVER  # use the same resolver instance as above
    TREE_WORDS = ["professional", "consistency", "mindset", "ran"]
    for word in TREE_WORDS:
        tree = app_module.resolve_tree(word)
        check(f"{word} has a real tree (not 'no recorded etymology data')", tree is not None)
except ImportError as e:
    check(f"could not import app.py to check tree consistency ({e})", False)

print()
total = passed + len(failures)
print(f"{passed}/{total} checks passed")
if failures:
    print("\nFAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
sys.exit(0)
