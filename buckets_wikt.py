"""
Language-NAME -> origin-bucket map for the etymology-db (Wiktionary) dataset.

Unlike buckets.py (which keys on ISO codes for the `ety` data), this dataset
labels languages by full English name. Same bucket philosophy:

  - Buckets reflect the DONOR/ORIGIN family English drew a word from.
  - English's own stages (Middle/Old English) are the inherited-Germanic core;
    when a word's only donor thread stays within them, it's Germanic.
  - Broad world coverage: this dataset reaches Arabic, Sanskrit, Japanese, etc.,
    so we add those buckets rather than dumping them in "Unknown".

Anything not in this map falls through to "Other" (not "Unknown" — the word WAS
found and traced; we just haven't assigned its donor a bucket yet). That keeps
"Unknown" meaning "no etymology data at all," consistent with the analyzer.
"""

NAME_TO_BUCKET = {
    # English stages -> inherited Germanic core
    "English": "Germanic",
    "Middle English": "Germanic",
    "Old English": "Germanic",
    "Scots": "Germanic",

    # West/continental Germanic
    "German": "Germanic", "Low German": "Germanic", "German Low German": "Germanic",
    "Dutch": "Germanic", "Middle Dutch": "Germanic", "Old Dutch": "Germanic",
    "Middle Low German": "Germanic", "Old High German": "Germanic",
    "Middle High German": "Germanic", "Old Saxon": "Germanic",
    "Proto-Germanic": "Germanic", "Proto-West Germanic": "Germanic",
    "Frankish": "Germanic", "Gothic": "Germanic",
    "West Frisian": "Germanic", "Saterland Frisian": "Germanic",
    "North Frisian": "Germanic", "Old Frisian": "Germanic", "Yiddish": "Germanic",
    "Afrikaans": "Germanic",
    # Family/collective names, 2026-07-27. "Germanic" (gem) is the family code
    # itself; Alemannic and Bavarian are High German varieties.
    "Germanic": "Germanic", "Alemannic German": "Germanic",
    "Bavarian": "Germanic", "Swiss German": "Germanic", "Old Swedish": "Norse",
    "Middle Scots": "Germanic",

    # North Germanic / Norse — broken out (core to the project)
    "Old Norse": "Norse", "Icelandic": "Norse", "Swedish": "Norse",
    "Danish": "Norse", "Norwegian": "Norse", "Norwegian Bokmål": "Norse",
    "Norwegian Nynorsk": "Norse", "Faroese": "Norse", "Old Swedish": "Norse",
    "Old Danish": "Norse",

    # French — broken out from Latin/Romance
    "French": "French", "Old French": "French", "Middle French": "French",
    "Anglo-Norman": "French", "Norman": "French", "Old Northern French": "French",

    # Latin (all stages)
    "Latin": "Latin", "Late Latin": "Latin", "Medieval Latin": "Latin",
    "New Latin": "Latin", "Vulgar Latin": "Latin", "Ecclesiastical Latin": "Latin",
    "Proto-Italic": "Latin", "Old Latin": "Latin",

    # Greek
    "Ancient Greek": "Greek", "Greek": "Greek", "Koine Greek": "Greek",
    "Byzantine Greek": "Greek", "Mycenaean Greek": "Greek",

    # Other Romance
    "Italian": "Romance (other)", "Spanish": "Romance (other)",
    "Portuguese": "Romance (other)", "Romanian": "Romance (other)",
    "Catalan": "Romance (other)", "Occitan": "Romance (other)",
    "Old Occitan": "Romance (other)", "Galician": "Romance (other)",
    "Sicilian": "Romance (other)", "Sardinian": "Romance (other)",
    "Old Italian": "Romance (other)", "Old Spanish": "Romance (other)",
    # Family/collective and regional names, 2026-07-27.
    "Romance": "Romance (other)", "Mexican Spanish": "Romance (other)",
    "Latin American Spanish": "Romance (other)", "Old Portuguese": "Romance (other)",
    "Venetian": "Romance (other)", "Neapolitan": "Romance (other)",

    # Celtic
    "Irish": "Celtic", "Old Irish": "Celtic", "Scottish Gaelic": "Celtic",
    "Welsh": "Celtic", "Breton": "Celtic", "Cornish": "Celtic",
    "Proto-Celtic": "Celtic", "Gaulish": "Celtic", "Manx": "Celtic",
    "Middle Irish": "Celtic", "Proto-Brythonic": "Celtic",
    # Family/collective names surfaced by language_codes.py, 2026-07-27.
    # Cumbric and Pictish are attested Brythonic-branch languages of northern
    # Britain; "Brythonic" (cel-bry) is the branch itself.
    "Brythonic": "Celtic", "Cumbric": "Celtic", "Pictish": "Celtic",
    "Celtic": "Celtic", "Goidelic": "Celtic",

    # Slavic
    "Russian": "Slavic", "Polish": "Slavic", "Czech": "Slavic",
    "Ukrainian": "Slavic", "Proto-Slavic": "Slavic", "Serbo-Croatian": "Slavic",
    "Slovak": "Slavic", "Slovene": "Slavic", "Bulgarian": "Slavic",
    "Old Church Slavonic": "Slavic", "Croatian": "Slavic", "Serbian": "Slavic",
    "Belarusian": "Slavic",
    "Slavic": "Slavic", "Macedonian": "Slavic", "Sorbian": "Slavic",
    "Old Polish": "Slavic", "Kashubian": "Slavic",

    # Indo-Iranian (also holds a few Dravidian/South-Asian donors grouped
    # loosely here for practical purposes, same tolerated stretch as the
    # existing Tamil entry -- these are geographic/donor-region groupings,
    # not a strict language-family claim)
    "Sanskrit": "Indo-Iranian", "Hindi": "Indo-Iranian", "Urdu": "Indo-Iranian",
    "Persian": "Indo-Iranian", "Bengali": "Indo-Iranian", "Punjabi": "Indo-Iranian",
    "Avestan": "Indo-Iranian", "Pahlavi": "Indo-Iranian", "Old Persian": "Indo-Iranian",
    "Tamil": "Indo-Iranian", "Prakrit": "Indo-Iranian",  # (Tamil is Dravidian; grouped loosely under South-Asian donors)
    "Middle Persian": "Indo-Iranian", "Classical Persian": "Indo-Iranian",
    "Proto-Indo-Iranian": "Indo-Iranian", "Romani": "Indo-Iranian",
    "Marathi": "Indo-Iranian", "Nepali": "Indo-Iranian", "Gujarati": "Indo-Iranian",
    "Sinhalese": "Indo-Iranian", "Telugu": "Indo-Iranian", "Malayalam": "Indo-Iranian",
    # Family/collective names, 2026-07-27 -- same loose South-Asian grouping
    # the Tamil entry above already documents.
    "Indo-Iranian": "Indo-Iranian", "Indo-Aryan": "Indo-Iranian",
    "Iranian": "Indo-Iranian", "Dravidian": "Indo-Iranian",
    "Kannada": "Indo-Iranian", "Pali": "Indo-Iranian", "Sauraseni Prakrit": "Indo-Iranian",

    # Semitic
    "Arabic": "Semitic", "Hebrew": "Semitic", "Biblical Hebrew": "Semitic",
    "Aramaic": "Semitic", "Akkadian": "Semitic", "Classical Syriac": "Semitic",
    "Amharic": "Semitic",
    # Family/collective names, 2026-07-27. Phoenician and Punic are attested
    # Semitic languages; "Semitic" (sem) is the family code itself.
    "Semitic": "Semitic", "Phoenician": "Semitic", "Punic": "Semitic",
    "Ugaritic": "Semitic", "Ge'ez": "Semitic",
    "Ottoman Turkish": "Turkic",  # (Ottoman Turkish borrowings — Turkic bucket)

    # Turkic / Central Asian
    "Turkish": "Turkic", "Uyghur": "Turkic", "Mongolian": "Turkic",
    # Family/collective names, 2026-07-27 (see the Indigenous American block).
    "Turkic": "Turkic", "Kazakh": "Turkic", "Kyrgyz": "Turkic",
    "Tatar": "Turkic", "Azerbaijani": "Turkic", "Uzbek": "Turkic",
    "Proto-Turkic": "Turkic", "Chagatai": "Turkic",

    # East Asian (also holds mainland-SE/Central-Asian donors grouped here
    # as a practical geographic bucket, not a language-family claim --
    # they're not Austronesian, and there's no dedicated bucket for them)
    "Japanese": "East Asian", "Chinese": "East Asian", "Mandarin": "East Asian",
    "Cantonese": "East Asian", "Korean": "East Asian", "Middle Chinese": "East Asian",
    # Same practical geographic grouping the existing entries use -- not a
    # language-family claim (see known issue #3).
    "Manipuri": "East Asian", "Dzongkha": "East Asian", "Tibeto-Burman": "East Asian",
    "Teochew": "East Asian",
    "Old Chinese": "East Asian", "Vietnamese": "East Asian", "Thai": "East Asian",
    "Burmese": "East Asian", "Khmer": "East Asian", "Tibetan": "East Asian",
    "Hokkien": "East Asian", "Min Nan": "East Asian",

    # Southeast Asian / Pacific
    "Malay": "Austronesian", "Tagalog": "Austronesian", "Hawaiian": "Austronesian",
    "Maori": "Austronesian", "Cebuano": "Austronesian", "Indonesian": "Austronesian",
    "Javanese": "Austronesian",
    "Austronesian": "Austronesian", "Malayo-Polynesian": "Austronesian",

    # Other notable donors
    "Nahuatl": "Indigenous American", "Classical Nahuatl": "Indigenous American",
    "Ojibwe": "Indigenous American", "Quechua": "Indigenous American",
    "Old Tupi": "Indigenous American", "Cree": "Indigenous American",

    # Added 2026-07-27, once `language_codes.py` started resolving raw codes
    # into real names -- these were previously invisible, showing as "alg",
    # "azc-nah", "iro" and bucketing to Other. `muskrat` is the reported case:
    # its donor is Algonquian (Western Abenaki *mòskwas*), not "Other".
    # Only families whose bucket is unambiguous under this project's existing
    # scheme were added; genuine isolates are still deliberately left out
    # (see known issue #3).
    "Algonquian": "Indigenous American", "Nahuan": "Indigenous American",
    "Iroquoian": "Indigenous American", "Siouan": "Indigenous American",
    "Muskogean": "Indigenous American", "Athabaskan": "Indigenous American",
    "Hopi": "Indigenous American", "Inuktitut": "Indigenous American",
    "Native American": "Indigenous American",
    "Central American Indian": "Indigenous American",
    "South American Indian": "Indigenous American",
    "Tupian": "Indigenous American",
    "Eastern Algonquian": "Indigenous American",
    "Powhatan": "Indigenous American", "Massachusett": "Indigenous American",
    "Narragansett": "Indigenous American", "Abenaki": "Indigenous American",
    "Western Abenaki": "Indigenous American", "Lenape": "Indigenous American",
    "Delaware": "Indigenous American", "Micmac": "Indigenous American",
    "Mi'kmaq": "Indigenous American", "Cherokee": "Indigenous American",
    "Choctaw": "Indigenous American", "Dakota": "Indigenous American",
    "Taos": "Indigenous American", "Chinook Jargon": "Indigenous American",
    "Egyptian": "Afro-Asiatic (other)", "Swahili": "African (other)",
    "Yoruba": "African (other)", "Zulu": "African (other)",

    # Caribbean -- added 2026-07-22 at Joe's request (was falling into the
    # vague "Other" catch-all). Taino is the indigenous pre-Columbian
    # Caribbean language (hurricane, barbecue, canoe, cay); the creoles are
    # each grouped here regardless of lexifier (English/French/Dutch/
    # Portuguese-Spanish base) since the geographic/cultural bucket is what
    # was asked for, not a split by which European language supplied most
    # of the vocabulary.
    "Taino": "Caribbean", "Taíno": "Caribbean", "Jamaican Creole": "Caribbean",
    "Haitian Creole": "Caribbean", "Louisiana Creole": "Caribbean",
    "Papiamento": "Caribbean", "Antigua and Barbuda Creole English": "Caribbean",
    "Bahamian Creole": "Caribbean", "Trinidadian Creole": "Caribbean",
    "Guyanese Creole": "Caribbean", "Belizean Creole": "Caribbean",
    "Saint Lucian Creole French": "Caribbean", "Garifuna": "Caribbean",

    # Deep proto-root
    "Proto-Indo-European": "PIE",
}

# English stage names (used to detect "never left English" chains).
# Re-exported from `linguistics`, which owns this definition -- importers that
# already say `from buckets_wikt import ENGLISH_STAGE_NAMES` keep working.
from linguistics import ENGLISH_STAGE_NAMES        # noqa: E402,F401

APPROXIMATE_BUCKETS = {"Germanic"}

# THE canonical display order for every bucket the app can show, in any
# chart, legend or sort. `buckets.py` re-exports this rather than keeping the
# shorter list it used to own -- see the note there for what that cost.
#
# "Iranian" is the legacy `ety`/ISO backend's name for what this taxonomy
# calls "Indo-Iranian" (`buckets.py` still maps fas/pal/peo to it), so it sits
# immediately after its modern equivalent. It is a display slot for a bucket
# that is still reachable, not a separate family.
BUCKET_ORDER = [
    "Germanic", "Norse", "French", "Latin", "Greek", "Romance (other)",
    "Celtic", "Slavic", "Indo-Iranian", "Iranian", "Semitic", "Turkic",
    "East Asian", "Austronesian", "Indigenous American", "Caribbean",
    "Afro-Asiatic (other)", "African (other)", "PIE", "Other", "Unknown",
]


# Which broad lineage each bucket belongs to. Added 2026-07-25 for chain
# ORDERING only -- not for display, and deliberately coarser than the buckets
# themselves. convert_wikt.py's `_DEPTH_HINT` assigns tiers like "Old-period
# stage = 12", "Classical = 14", "proto-language = 15+", but those tiers are
# only meaningful WITHIN one lineage: comparing Latin (14) against Proto-West
# Germanic (15) says nothing real, because they sit on different branches of
# the tree, not different depths of the same branch. Sorting across families
# on those numbers silently rewrites correct data -- it is exactly what broke
# `mile`/`street`/`Friday` (see convert_wiktextract.py's ordering guard).
BUCKET_FAMILY = {
    "Germanic": "germanic", "Norse": "germanic",
    "Latin": "italic", "French": "italic", "Romance (other)": "italic",
    "Greek": "hellenic",
    "Celtic": "celtic",
    "Slavic": "slavic",
    "Indo-Iranian": "indo-iranian", "Iranian": "indo-iranian",
    "Semitic": "semitic",
    "Turkic": "turkic",
    "East Asian": "east-asian",
    "Austronesian": "austronesian",
    "Indigenous American": "amerind",
    "Caribbean": "caribbean",
    "Afro-Asiatic (other)": "afro-asiatic",
    "African (other)": "african",
    "PIE": "pie",
}


def bucket_for_name(name: str) -> str:
    return NAME_TO_BUCKET.get(name, "Other")


def family_for_name(name: str):
    """Broad lineage for a language name, or None if unclassified."""
    return BUCKET_FAMILY.get(bucket_for_name(name))
