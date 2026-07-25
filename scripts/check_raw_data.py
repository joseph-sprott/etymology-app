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

import pandas as pd

PARQUET_PATH = r"C:\Users\Josep\Desktop\Etymology Project\etymology.parquet"


def main():
    if len(sys.argv) != 2:
        print("usage: python scripts/check_raw_data.py WORD", file=sys.stderr)
        sys.exit(2)
    word = sys.argv[1]
    df = pd.read_parquet(PARQUET_PATH)
    eng = df[df["lang"] == "English"]
    rows = eng[eng["term"] == word]
    if len(rows) == 0:
        print(f'"{word}" is NOT present as an English term_id in the raw data at all.')
        return
    cols = ["reltype", "related_lang", "related_term", "group_tag", "parent_tag", "parent_position"]
    print(rows[cols].to_string())


if __name__ == "__main__":
    main()
