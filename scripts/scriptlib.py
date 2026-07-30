"""
The plumbing every script in this folder used to hand-roll.

WHY THIS EXISTS (2026-07-30). The scripts/ folder had grown four spellings of
the same sys.path bootstrap, the 60-character dump path pasted verbatim into
two files, a UTF-8 console fix in two of nine scripts, and three separate
implementations of "climb to the topmost ancestor". None of that is script
plumbing anyone chose -- it is what happens when each new script starts by
copying the top of the last one.

That is known issue #16 (every feature must read from one shared source, never
its own copy) in the tooling layer, so it gets issue #16's answer: one leaf
module that everything imports, rather than a convention everyone is expected
to retype correctly. It imports nothing project-local, so it cannot create a
cycle and is safe to import before `bootstrap()` has even run.

Two of those copies were latent bugs, not just noise:

  * `sys.path.insert(0, ".")` (in two scripts) resolves against the CURRENT
    DIRECTORY, so those scripts only worked when launched from the project
    root and failed confusingly anywhere else.
  * This machine's console is cp1252 (see CLAUDE.md's environment facts), so
    any script printing a proto-form -- `*bʰréh₂tēr`, `*erþō` -- dies with
    UnicodeEncodeError after the real work has already succeeded. Seven of the
    nine printed such forms; two set the encoding.

Both are fixed once, here, for every caller.

    import scriptlib
    scriptlib.bootstrap()          # project imports work; console is UTF-8
"""
from __future__ import annotations

import os
import re
import sys
from typing import Optional

HERE: str = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT: str = os.path.dirname(HERE)

#: Where the multi-GB source data sits, one level above the code. Derived
#: rather than hardcoded so the absolute path exists in exactly one place --
#: and overridable, which is what makes these scripts runnable on any machine.
DATA_ROOT: str = os.environ.get("ETYMOLOGY_DATA_ROOT") or os.path.dirname(PROJECT_ROOT)

WIKTEXTRACT_DIR: str = os.path.join(DATA_ROOT, "wiktextract_data")
ENGLISH_DUMP: str = os.path.join(WIKTEXTRACT_DIR,
                                 "kaikki.org-dictionary-English.jsonl")
PARQUET_PATH: str = os.path.join(DATA_ROOT, "etymology.parquet")

def enable_utf8_console() -> None:
    """Stop cp1252 from killing a script that has already done its work."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass            # A redirected or closed stream is not worth dying for.


def bootstrap() -> None:
    """Make project modules importable and the console UTF-8 safe."""
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    enable_utf8_console()


def require_file(path: str, hint: str) -> str:
    """Fail with the reason and the fix, not with a bare stack trace."""
    if os.path.exists(path):
        return path
    raise SystemExit(f"missing: {path}\n  -> {hint}")


def kaikki_url(language: str) -> str:
    """
    The download URL for one language's extract.

    The directory keeps the hyphens and spaces; the filename strips them, so
    Proto-Indo-European lives under `/Proto-Indo-European/` as
    `kaikki.org-dictionary-ProtoIndoEuropean.jsonl`. Getting this wrong yields
    a 404 that reads as "that language isn't available".
    """
    flat = re.sub(r"[^A-Za-z0-9]", "", language)
    return (f"https://kaikki.org/dictionary/{language}/"
            f"kaikki.org-dictionary-{flat}.jsonl")


def local_name(language: str) -> str:
    """The on-disk filename for a language's extract."""
    return re.sub(r"[^a-z0-9]+", "-", language.lower()).strip("-") + ".jsonl"


# NOTE: "climb to the topmost ancestor" deliberately does NOT live here, even
# though two scripts need it. It is domain logic owned by `descendants.py`, and
# a core module must never import from scripts/. Call
# `descendants.climb_to_root` after `bootstrap()`.
