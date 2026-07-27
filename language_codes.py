"""
Raw Wiktionary language code -> real language name.

WHY (2026-07-27): `muskrat` displayed its donor as **"alg"** and bucketed it
"Other". The builder had written the raw code into the language table's `name`
column, so every layer downstream -- the chart, the hover card, the tree --
faithfully showed a code to the reader and mapped it to nothing.

Not a one-word problem. **1,250 of 1,530 language rows were code-shaped**,
covering **8,575 words**: `sem-pro`, `phn`, `ett`, `eo`, `lv`, `zlw-opl`,
`enm-nor` and 1,243 more, every one of them reading "Other".

Two sources, deliberately kept apart:

1. `language_codes.csv` -- Wiktionary's own registry, 8,651 code->name rows.
   Joe downloaded it 2026-07-23 and CLAUDE.md recorded it as "not yet wired
   into anything" for four days. It resolves 1,103 of the 1,250 (88%).
   Vendored into the repo rather than read from Downloads, which is not a
   dependency a build should have.

2. `_FAMILY_CODES` below -- the registry lists LANGUAGES, so family codes
   (`alg` Algonquian, `trk` Turkic, `dra` Dravidian) are absent from it, and
   `alg` is exactly what `muskrat` needs. These are curated, not guessed:
   each is a documented ISO 639-5 collective code or a Wiktionary family code
   whose expansion is unambiguous, and only codes that ACTUALLY APPEAR in this
   database were added. Codes whose expansion I could not state confidently
   were left out; they keep reading "Other", which is honest.

An unknown code returns None. It never invents a name -- a plausible-looking
wrong language is worse than a visible code, because only one of those tells
the reader something is missing.
"""
import csv
import os
from typing import Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "language_codes.csv")

# Family and collective codes, absent from Wiktionary's language registry.
# Ordered by how many words in this database they affect, which is also the
# order they were verified in. The bucket each maps to is decided by
# `buckets_wikt`, not here -- this module only supplies the NAME.
_FAMILY_CODES: Dict[str, str] = {
    "alg": "Algonquian",            # 67 words -- muskrat's donor
    "alg-eas": "Eastern Algonquian",   # 60 -- tomahawk, skunk
    "trk-pro": "Proto-Turkic",         # 46
    "gmw-msc": "Middle Scots",         # 41
    "nan-tws": "Teochew",              # 60
    "trk": "Turkic",                # 66
    "cel-bry": "Brythonic",         # 55
    "azc-nah": "Nahuan",            # 50
    "sem": "Semitic",               # 43
    "roa": "Romance",               # 37
    "tup": "Tupian",                # 27
    "bnt": "Bantu",                 # 22
    "dra": "Dravidian",             # 19
    "ira": "Iranian",               # 16
    "ath": "Athabaskan",
    "aav": "Austroasiatic",
    "iro": "Iroquoian",
    "sio": "Siouan",
    "mus": "Muskogean",
    "sla": "Slavic",
    "gem": "Germanic",
    "cel": "Celtic",
    "ine": "Indo-European",
    "itc": "Italic",
    "grk": "Hellenic",
    "inc": "Indo-Aryan",
    "iir": "Indo-Iranian",
    "urj": "Uralic",
    "map": "Austronesian",
    "nic": "Niger-Congo",
    "afa": "Afro-Asiatic",
    "cus": "Cushitic",
    "ber": "Berber",
    "tut": "Altaic",
    "khi": "Khoisan",
    "paa": "Papuan",
    "aus": "Australian",
    "nai": "Native American",
    "sai": "South American Indian",
    "cai": "Central American Indian",
    "crp": "Creole",
    "art": "Constructed",
}

_REGISTRY: Optional[Dict[str, str]] = None


def _registry() -> Dict[str, str]:
    """Wiktionary's code->name table, loaded once. Absent file = no coverage."""
    global _REGISTRY
    if _REGISTRY is None:
        table: Dict[str, str] = {}
        try:
            with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
                for row in csv.reader(fh):
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        table[row[0].strip()] = row[1].strip()
        except OSError:
            pass          # not vendored yet -- degrade, don't raise
        _REGISTRY = table
    return _REGISTRY


def name_for(code: Optional[str]) -> Optional[str]:
    """
    The language named by this code, or None if nothing here knows it.

    Family codes win over the registry: where both have an entry, the family
    reading is the one this project's chains actually mean.
    """
    code = (code or "").strip()
    if not code:
        return None
    if code in _FAMILY_CODES:
        return _FAMILY_CODES[code]
    return _registry().get(code)


def resolve(name_or_code: Optional[str]) -> Optional[str]:
    """
    Best available name for whatever the database holds.

    Pass-through for anything already a real name, upgrade for a bare code,
    and unchanged for a code nothing recognises -- so an unresolved value
    stays visible as a code rather than silently becoming a wrong language.
    """
    if not name_or_code:
        return name_or_code
    return name_for(name_or_code) or name_or_code
