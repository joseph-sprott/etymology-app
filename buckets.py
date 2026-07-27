"""
Language-code -> origin-bucket mapping.

This is the *linguistic knowledge* layer, kept deliberately separate from the
resolver and analyzer code so it can grow without touching anything else.

Codes are ISO 639-3 (plus a few historical-stage codes) as emitted by the
etymology data source. When Wiktionary data is layered in (Path B), it uses the
same ISO codes, so this map keeps working unchanged.

Bucket philosophy for Path A:
  - We bucket by the DONOR/ORIGIN language family English drew the word from.
  - "Old English" and "Middle English" are stages of English itself, not donors.
    When a chain dead-ends there, we cannot prove a foreign donor, so we treat it
    as GERMANIC (inherited native core vocabulary is overwhelmingly Germanic).
    This is the deliberate Path-A approximation; Path B will reclassify the
    subset of these that were actually Norse/French borrowings.
"""

# Each ISO code maps to a bucket name.
CODE_TO_BUCKET = {
    # --- English's own stages: inherited Germanic core (Path A approximation) ---
    "ang": "Germanic",        # Old English
    "enm": "Germanic",        # Middle English
    "eng": "Germanic",        # (modern) English — only appears as a root in odd cases

    # --- Germanic proper ---
    "gem": "Germanic",        # Proto-Germanic
    "gem-pro": "Germanic",
    "p_gem": "Germanic",      # Proto-Germanic (dataset's code)
    "p_gmw": "Germanic",      # Proto-West-Germanic (dataset's code)
    "gmw-pro": "Germanic",
    "deu": "Germanic",        # German
    "goh": "Germanic",        # Old High German
    "gmh": "Germanic",        # Middle High German
    "nld": "Germanic",        # Dutch
    "dum": "Germanic",        # Middle Dutch
    "gml": "Germanic",        # Middle Low German
    "osx": "Germanic",        # Old Saxon
    "frk": "Germanic",        # Frankish
    "got": "Germanic",        # Gothic

    # --- Norse / North Germanic (broken out separately: this is the whole point) ---
    "non": "Norse",           # Old Norse
    "isl": "Norse",           # Icelandic
    "swe": "Norse",           # Swedish
    "dan": "Norse",           # Danish
    "nor": "Norse",           # Norwegian

    # --- Latin & Romance ---
    "lat": "Latin",           # Latin
    "la-vul": "Latin",        # Vulgar Latin
    "la-med": "Latin",        # Medieval Latin

    # --- French (broken out from Latin: distinct historical donor) ---
    "fra": "French",          # French
    "fro": "French",          # Old French
    "frm": "French",          # Middle French
    "xno": "French",          # Anglo-Norman

    # --- Other Romance ---
    "ita": "Romance (other)",
    "spa": "Romance (other)",
    "por": "Romance (other)",
    "ron": "Romance (other)",
    "cat": "Romance (other)",
    "oci": "Romance (other)",
    "roa-opt": "Romance (other)",

    # --- Greek ---
    "grc": "Greek",           # Ancient Greek
    "ell": "Greek",           # Modern Greek

    # --- Iranian ---
    "fas": "Iranian",         # Persian
    "pal": "Iranian",         # Pahlavi (Middle Persian)
    "peo": "Iranian",         # Old Persian

    # --- Celtic ---
    "cel": "Celtic",
    "gla": "Celtic",
    "gle": "Celtic",
    "cym": "Celtic",
    "bre": "Celtic",

    # --- Deep proto-root: only reached when nothing more specific exists ---
    "ine": "PIE",             # Proto-Indo-European
    "ine-pro": "PIE",
    "p_ine": "PIE",           # Proto-Indo-European (dataset's code)
}

# Buckets we consider "resolved to a real origin" vs. the fallback approximation.
# Used by the analyzer to report a confidence/coverage figure honestly.
APPROXIMATE_BUCKETS = {"Germanic"}   # because OE/ME dead-ends land here unproven

# Order for stable, readable reporting.
# DISPLAY ORDER LIVES IN `buckets_wikt`, NOT HERE (fixed in the 2026-07-27
# audit). This module's own list had 11 entries and the live taxonomy has 20,
# so the ten buckets it never heard of -- Slavic, Indo-Iranian, Semitic,
# Turkic, East Asian, Austronesian, Indigenous American, Afro-Asiatic,
# African, Other -- fell to the end of every chart and every "Language group"
# sort in arbitrary dict order. `Unknown` and `PIE` were rendering AHEAD of
# `Slavic` and `Turkic` as a result.
#
# Re-exported rather than deleted: `analyzer.py` and `app.py` both imported
# the name from here, and this keeps any other caller working while making it
# impossible for the two lists to disagree again.
from buckets_wikt import BUCKET_ORDER        # noqa: E402,F401


def bucket_for(iso_code: str) -> str:
    """Map an ISO language code to an origin bucket. Unknown codes -> 'Unknown'."""
    return CODE_TO_BUCKET.get(iso_code, "Unknown")
