"""
Print every raw etymology-db relation row for one English term.

    python scripts/check_raw_data.py WORD

Deterministic, no AI judgment involved -- extracted 2026-07-24 from what had
been a hand-retyped pandas snippet in the etymology-fix-word skill (used
identically five-plus times this session for tag/auto/generate/meltdown/ran).

Run from the project root (C:\\Users\\Josep\\Desktop\\Etymology Project\\etymology-app).
Takes a few seconds -- reads the raw parquet fresh each run.
"""
import sys

import scriptlib

scriptlib.bootstrap()

COLUMNS = ["reltype", "related_lang", "related_term",
           "group_tag", "parent_tag", "parent_position"]


def relation_rows(word: str):
    """Every raw English relation row for one term, or an empty frame."""
    import pandas as pd

    try:
        frame = pd.read_parquet(scriptlib.PARQUET_PATH)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"could not read {scriptlib.PARQUET_PATH}: {exc}\n"
                         "  -> this is the legacy gap-filler; see CLAUDE.md's "
                         "environment facts for where it lives")
    english = frame[frame["lang"] == "English"]
    return english[english["term"] == word]


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python scripts/check_raw_data.py WORD", file=sys.stderr)
        raise SystemExit(2)
    word = sys.argv[1]
    scriptlib.require_file(scriptlib.PARQUET_PATH,
                           "the raw etymology-db parquet is not on this machine")
    rows = relation_rows(word)
    if rows.empty:
        print(f'"{word}" is NOT present as an English term_id in the raw data at all.')
        return
    print(rows[COLUMNS].to_string())


if __name__ == "__main__":
    main()
