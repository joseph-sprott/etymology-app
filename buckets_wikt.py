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

    # Celtic
    "Irish": "Celtic", "Old Irish": "Celtic", "Scottish Gaelic": "Celtic",
    "Welsh": "Celtic", "Breton": "Celtic", "Cornish": "Celtic",
    "Proto-Celtic": "Celtic", "Gaulish": "Celtic", "Manx": "Celtic",
    "Middle Irish": "Celtic", "Proto-Brythonic": "Celtic",

    # Slavic
    "Russian": "Slavic", "Polish": "Slavic", "Czech": "Slavic",
    "Ukrainian": "Slavic", "Proto-Slavic": "Slavic", "Serbo-Croatian": "Slavic",
    "Slovak": "Slavic", "Slovene": "Slavic", "Bulgarian": "Slavic",
    "Old Church Slavonic": "Slavic", "Croatian": "Slavic", "Serbian": "Slavic",
    "Belarusian": "Slavic",

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

    # Semitic
    "Arabic": "Semitic", "Hebrew": "Semitic", "Biblical Hebrew": "Semitic",
    "Aramaic": "Semitic", "Akkadian": "Semitic", "Classical Syriac": "Semitic",
    "Amharic": "Semitic",
    "Ottoman Turkish": "Turkic",  # (Ottoman Turkish borrowings — Turkic bucket)

    # Turkic / Central Asian
    "Turkish": "Turkic", "Uyghur": "Turkic", "Mongolian": "Turkic",

    # East Asian (also holds mainland-SE/Central-Asian donors grouped here
    # as a practical geographic bucket, not a language-family claim --
    # they're not Austronesian, and there's no dedicated bucket for them)
    "Japanese": "East Asian", "Chinese": "East Asian", "Mandarin": "East Asian",
    "Cantonese": "East Asian", "Korean": "East Asian", "Middle Chinese": "East Asian",
    "Old Chinese": "East Asian", "Vietnamese": "East Asian", "Thai": "East Asian",
    "Burmese": "East Asian", "Khmer": "East Asian", "Tibetan": "East Asian",
    "Hokkien": "East Asian", "Min Nan": "East Asian",

    # Southeast Asian / Pacific
    "Malay": "Austronesian", "Tagalog": "Austronesian", "Hawaiian": "Austronesian",
    "Maori": "Austronesian", "Cebuano": "Austronesian", "Indonesian": "Austronesian",
    "Javanese": "Austronesian",

    # Other notable donors
    "Nahuatl": "Indigenous American", "Classical Nahuatl": "Indigenous American",
    "Ojibwe": "Indigenous American", "Quechua": "Indigenous American",
    "Old Tupi": "Indigenous American", "Cree": "Indigenous American",
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
ENGLISH_STAGE_NAMES = {"English", "Middle English", "Old English"}

APPROXIMATE_BUCKETS = {"Germanic"}

BUCKET_ORDER = [
    "Germanic", "Norse", "French", "Latin", "Greek", "Romance (other)",
    "Celtic", "Slavic", "Indo-Iranian", "Semitic", "Turkic", "East Asian",
    "Austronesian", "Indigenous American", "Caribbean", "Afro-Asiatic (other)",
    "African (other)", "PIE", "Other", "Unknown",
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
