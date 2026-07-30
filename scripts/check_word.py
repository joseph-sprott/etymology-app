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
import sys
from typing import Any

import scriptlib

scriptlib.bootstrap()

from resolver import default_resolver

MODES = ("direct", "influence", "root")


def format_split(view: Any) -> str:
    """A compound shown as its component parts."""
    return "split: " + " + ".join(f"{p.word}={p.bucket}" for p in view.parts)


def format_answer(view: Any) -> str:
    """
    One mode's answer, as the UI renders it.

    Prints `depth_lang` and adds `specific_lang` only when it differs. Fixed
    2026-07-25: this used to print `specific_lang or depth_lang`, so
    specific_lang always won and Deepest Root's whole point (the "Latin (from
    PIE)" label built from root_lang/root_pie) was invisible -- precisely the
    field you check when investigating a wrong root. It reported
    "Proto-Indo-European" for `mile` both before AND after a fix that genuinely
    changed the answer.
    """
    label = view.depth_lang or view.specific_lang or "-"
    extra = ""
    if view.specific_lang and view.specific_lang != view.depth_lang:
        extra = f"   (donor: {view.specific_lang})"
    return f"{view.bucket:14s} | {label}{extra}"


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python scripts/check_word.py WORD", file=sys.stderr)
        raise SystemExit(2)
    resolution = default_resolver().resolve(sys.argv[1])
    for mode in MODES:
        view = resolution.view(mode)
        body = format_split(view) if view.parts else format_answer(view)
        print(f"{mode:10s} -> {body}")


if __name__ == "__main__":
    main()
