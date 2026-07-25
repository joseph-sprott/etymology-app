"""
wiktextract language-code -> bucket mapping.

Wiktextract's `etymology_templates` args use WIKTIONARY'S OWN internal
language codes (Module:languages), not the ISO 639-3 codes buckets.py was
built for (the `ety` package's convention) -- confirmed empirically 2026-07-24:
e.g. Dutch is "nl" here vs. "nld" in buckets.py, Italian is "it" vs. "ita",
and proto-languages use a "-pro" suffix ("gem-pro", "ine-pro") that mostly
(not entirely) coincides with buckets.py's own extra entries for those exact
codes. Rather than inventing a THIRD parallel bucket vocabulary, this module
only maps wiktextract's codes to the LANGUAGE NAME Wiktionary itself would
show, then hands that name to buckets_wikt.py's existing `bucket_for_name()`
-- reusing the same bucket taxonomy already shared by convert_wikt.py, not
duplicating it (composability -- see the 2026-07-24 skill-audit dimensions
this project holds itself to).

CODE_TO_NAME below covers the codes that actually appear with real frequency
in the donor templates (inh/der/bor and their uncertain/"u"-prefixed and "+"
variants) across the full English wiktextract extract, found empirically via
scripts/scan wiktextract lang codes (not guessed) -- see the commit that
introduced this file for the exact frequency counts. A code missing from this
map still resolves (falls through to buckets_wikt.py's "Other" bucket, same
"found but not yet classified" semantics already used for arbitrary Wiktionary
language names), it just isn't broken out into its own family bucket yet.
"""

from buckets_wikt import bucket_for_name

CODE_TO_NAME = {
    # English's own stages
    "en": "English", "enm": "Middle English", "ang": "Old English",
    "sco": "Scots",

    # West/continental Germanic
    "de": "German", "nds": "Low German", "nl": "Dutch", "dum": "Middle Dutch",
    "odt": "Old Dutch", "gml": "Middle Low German", "goh": "Old High German",
    "gmh": "Middle High German", "osx": "Old Saxon",
    "gem-pro": "Proto-Germanic", "gmw-pro": "Proto-West Germanic",
    "frk": "Frankish", "got": "Gothic", "gem": "Proto-Germanic",
    "fy": "West Frisian", "stq": "Saterland Frisian", "frr": "North Frisian",
    "ofs": "Old Frisian", "yi": "Yiddish", "af": "Afrikaans",

    # North Germanic / Norse
    "non": "Old Norse", "is": "Icelandic", "sv": "Swedish", "da": "Danish",
    "no": "Norwegian", "nb": "Norwegian Bokmål", "nn": "Norwegian Nynorsk",
    "fo": "Faroese", "gmq-pro": "Norse", "gmq": "Old Norse",

    # French
    "fr": "French", "fro": "Old French", "frm": "Middle French",
    "xno": "Anglo-Norman", "nrf": "Norman", "fro-nor": "Old Northern French",

    # Latin (plus sub-variant codes -- found with real frequency in the
    # empirical scan: la-lat/la-med/la-new/la-vul/la-ecc/la-cla)
    "la": "Latin", "itc-pro": "Proto-Italic", "la-lat": "Late Latin",
    "la-med": "Medieval Latin", "la-new": "New Latin", "la-vul": "Vulgar Latin",
    "la-ecc": "Ecclesiastical Latin", "la-cla": "Latin",

    # Greek
    "grc": "Ancient Greek", "el": "Greek", "gkm": "Byzantine Greek",
    "gmy": "Mycenaean Greek", "grc-koi": "Koine Greek",

    # Other Romance
    "it": "Italian", "es": "Spanish", "pt": "Portuguese", "ro": "Romanian",
    "ca": "Catalan", "oc": "Occitan", "gl": "Galician", "scn": "Sicilian",
    "sc": "Sardinian", "roa-opt": "Old Portuguese", "osp": "Old Spanish",
    "roa-tara": "Tarantino", "pro": "Old Occitan", "pt-BR": "Portuguese",

    # Celtic
    "ga": "Irish", "sga": "Old Irish", "gd": "Scottish Gaelic", "cy": "Welsh",
    "br": "Breton", "kw": "Cornish", "cel-pro": "Proto-Celtic",
    "xtg": "Gaulish", "gv": "Manx", "mga": "Middle Irish",
    "xbm": "Middle Breton", "cel-gau": "Gaulish", "cel": "Proto-Celtic",
    "cel-bry-pro": "Proto-Brythonic",

    # Slavic
    "ru": "Russian", "pl": "Polish", "cs": "Czech", "uk": "Ukrainian",
    "sla-pro": "Proto-Slavic", "sh": "Serbo-Croatian", "sk": "Slovak",
    "sl": "Slovene", "bg": "Bulgarian", "cu": "Old Church Slavonic",
    "hr": "Croatian", "sr": "Serbian", "be": "Belarusian", "sla": "Proto-Slavic",

    # Indo-Iranian
    "sa": "Sanskrit", "hi": "Hindi", "ur": "Urdu", "fa": "Persian",
    "bn": "Bengali", "pa": "Punjabi", "ae": "Avestan", "pal": "Pahlavi",
    "peo": "Old Persian", "ira-pro": "Proto-Iranian",
    "inc-pro": "Proto-Indo-Iranian", "rom": "Romani", "mr": "Marathi",
    "ne": "Nepali", "gu": "Gujarati", "si": "Sinhalese", "te": "Telugu",
    "ml": "Malayalam", "ta": "Tamil", "pra": "Prakrit",
    "fa-cls": "Classical Persian", "fa-ira": "Persian", "inc-hnd": "Hindi",

    # Semitic
    "ar": "Arabic", "he": "Hebrew", "hbo": "Biblical Hebrew",
    "arc": "Aramaic", "akk": "Akkadian", "syc": "Classical Syriac",
    "am": "Amharic", "ota": "Ottoman Turkish", "arz": "Arabic",
    "afa": "Egyptian", "afa-pro": "Egyptian", "iir-pro": "Proto-Indo-Iranian",

    # Turkic / Central Asian
    "tr": "Turkish", "ug": "Uyghur", "mn": "Mongolian",

    # East Asian (incl. romanization-variant codes for the same language,
    # e.g. cmn-pinyin/cmn-wadegiles/cmn-tongyong are all still Mandarin --
    # found with real frequency in the empirical code scan)
    "ja": "Japanese", "zh": "Chinese", "cmn": "Mandarin", "yue": "Cantonese",
    "ko": "Korean", "ltc": "Middle Chinese", "och": "Old Chinese",
    "vi": "Vietnamese", "th": "Thai", "my": "Burmese", "km": "Khmer",
    "bo": "Tibetan", "nan": "Min Nan", "hnj": "Hmong Njua",
    "cmn-pinyin": "Mandarin", "cmn-wadegiles": "Mandarin",
    "cmn-tongyong": "Mandarin", "nan-hbl": "Hokkien", "zh-postal": "Chinese",

    # Southeast Asian / Pacific
    "ms": "Malay", "tl": "Tagalog", "haw": "Hawaiian", "mi": "Maori",
    "ceb": "Cebuano", "id": "Indonesian", "jv": "Javanese",

    # Other notable donors
    "nci": "Nahuatl", "nci-cla": "Classical Nahuatl", "nah": "Nahuatl", "oj": "Ojibwe",
    "qu": "Quechua", "tup-old": "Old Tupi", "cr": "Cree",
    "egy": "Egyptian", "sw": "Swahili", "yo": "Yoruba", "zu": "Zulu",

    # Caribbean
    "tnq": "Taino", "acf": "Saint Lucian Creole French",
    "jam": "Jamaican Creole", "ht": "Haitian Creole", "lou": "Louisiana Creole",
    "pap": "Papiamento", "gyn": "Guyanese Creole",

    # Deep proto-root
    "ine-pro": "Proto-Indo-European",
}

# "mul"/"mul-tax" are Wiktionary's "Translingual" meta-codes (taxonomic
# binomials, symbols, etc.) -- NOT a real single donor language, so a
# donor-template citing one isn't real chain evidence at all (unlike an
# unmapped-but-real code, which still falls through to bucket "Other").
# Found with real frequency (958 + 183 occurrences) in the empirical code
# scan -- excluded outright rather than left to silently produce a bogus
# "Other" bucket entry.
EXCLUDED_CODES = {"mul", "mul-tax"}


def bucket_for_wikt_code(code: str) -> str:
    name = CODE_TO_NAME.get(code)
    if name is None:
        return "Other"
    return bucket_for_name(name)


def name_for_wikt_code(code: str):
    """
    The Wiktionary display name for a wiktextract language code, or None if
    this code isn't in the map. Deliberately returns None rather than the
    raw code itself -- caught 2026-07-24 via the sample-conversion smoke
    test ("cat"'s root showed root_lang "afa", a raw wiktextract code for
    Proto-Afro-Asiatic that had leaked through as if it were a real display
    name, because an earlier version of this function fell back to
    returning the code unchanged). An unmapped code should never masquerade
    as a real name; callers skip the step entirely when this returns None
    rather than fabricate one.
    """
    return CODE_TO_NAME.get(code)
