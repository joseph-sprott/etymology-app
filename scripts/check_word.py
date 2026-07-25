"""
Print how the resolver currently answers a word, across all three modes.

    python scripts/check_word.py WORD

Deterministic, no AI judgment involved -- extracted 2026-07-24 from what had
been a hand-retyped inline snippet in the etymology-fix-word skill (and would
otherwise have been re-invented, slightly differently, by etymology-regen's
own verification needs too). Shared at the project level, not nested inside
either skill's own scripts/ folder, so both point at the same file instead
of maintaining two copies that can drift.

Run from the project root (C:\\Users\\Josep\\Desktop\\Etymology Project\\etymology-app).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resolver import default_resolver


def main():
    if len(sys.argv) != 2:
        print("usage: python scripts/check_word.py WORD", file=sys.stderr)
        sys.exit(2)
    word = sys.argv[1]
    r = default_resolver()
    res = r.resolve(word)
    for mode in ("direct", "influence", "root"):
        v = res.view(mode)
        if v.parts:
            detail = " + ".join(f"{p.word}={p.bucket}" for p in v.parts)
            print(f"{mode:10s} -> split: {detail}")
        else:
            print(f"{mode:10s} -> {v.bucket:14s} | {v.specific_lang or v.depth_lang}")


if __name__ == "__main__":
    main()
