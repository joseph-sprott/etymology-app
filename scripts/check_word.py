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
            # Print `depth_lang` -- what the UI actually renders -- and add
            # `specific_lang` only when it says something different. Fixed
            # 2026-07-25: this used to print `specific_lang or depth_lang`,
            # so specific_lang always won and Deepest Root's whole point (the
            # "Latin (from PIE)" style label built from root_lang/root_pie)
            # was invisible. That's precisely the field you're checking when
            # investigating a wrong root, so the script was hiding the
            # evidence -- it reported "Proto-Indo-European" for `mile` both
            # before AND after a fix that genuinely changed the answer to
            # "Latin (from PIE)".
            label = v.depth_lang or v.specific_lang or "-"
            extra = ""
            if v.specific_lang and v.specific_lang != v.depth_lang:
                extra = f"   (donor: {v.specific_lang})"
            print(f"{mode:10s} -> {v.bucket:14s} | {label}{extra}")


if __name__ == "__main__":
    main()
