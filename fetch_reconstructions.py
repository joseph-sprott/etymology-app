"""
Piece 2 of issue #10: fill in the proto-language gap that etymology-db's raw
relation table can't -- it has ZERO source rows for any proto-language (see
CLAUDE.md issue #10), so a word whose chain bottoms out at e.g. Proto-Germanic
with `root_pie=False` has no further data available from the parquet no
matter how the graph is walked. Confirmed the data genuinely exists on live
Wiktionary instead (`Reconstruction:Proto-Germanic/fram` has a clean,
templated etymology reaching PIE) -- etymology-db's scraper just never
touched Wiktionary's `Reconstruction:` namespace, for any proto-language.

This script:
  1. Reads wikt_words.json, collects the unique (root_lang, root_term) pairs
     for every word stuck at a proto-language with root_pie=False.
  2. Fetches each Reconstruction page's raw wikitext from live Wiktionary
     (paced, not hammering the API -- see FETCH_DELAY).
  3. Parses its Etymology section for {{der}}/{{inh}}/{{bor}}/{{root}}
     templates (the same ancestry-relation philosophy as convert_wikt.py;
     {{cog}} is a cognate mention, not ancestry, and is skipped same as
     there) using wiktionary_codes.csv (Joe, 2026-07-23) to translate the
     template's language CODES (e.g. "gem-pro", "ine-pro") to the full names
     the rest of this project uses ("Proto-Germanic", "Proto-Indo-European").
  4. Patches wikt_words.json in place: any word whose root_term's
     Reconstruction page reaches Proto-Indo-European gets root_pie=True.

Run AFTER convert_wikt.py, as a separate enrichment pass -- it needs live
network access (convert_wikt.py deliberately doesn't: it only reads the
local parquet). Safe to re-run: results are cached in RECON_CACHE_PATH so a
second run doesn't re-fetch pages it already has.
"""
import json
import re
import sys
import time
import urllib.request
import urllib.parse

WIKT_WORDS_PATH = "wikt_words.json"
CODES_CSV_PATH = r"C:\Users\Josep\Downloads\wiktionary_codes.csv"
RECON_CACHE_PATH = "reconstruction_cache.json"
FETCH_DELAY = 0.7  # seconds between live requests -- paced, not hammering the API
USER_AGENT = "etymology-analyzer-project/1.0 (personal research tool; contact via GitHub)"

# Reconstruction pages are titled by the FULL language name, matching what's
# already in root_lang (verified: Reconstruction:Proto-Germanic/fram is the
# real page for Proto-Germanic *fram). No translation needed for the page
# prefix itself -- only the template language CODES inside the page need
# wiktionary_codes.csv.
PROTO_LANGUAGES = {
    "Proto-Germanic", "Proto-West Germanic", "Proto-Italic",
    "Proto-Celtic", "Proto-Slavic", "Proto-Indo-Iranian",
}

# Only {{root|...}} counts as a confirmed PIE connection -- NOT the general
# {{der}}/{{inh}}/{{bor}} templates. Found via a real test (Proto-Germanic
# *handuz): a bare {{der|gem-pro|ine-pro|*ḱómt}} on that page sits inside a
# prose sentence reading "It has been SUGGESTED to derive from..." -- one of
# FOUR competing theories on a page that opens with {{unc|gem-pro}} ("origin
# uncertain") and even raises a non-Indo-European origin as a serious
# alternative. A naive "any der/inh/bor template" match would have reported
# a genuinely disputed theory as settled fact -- overclaiming, exactly what
# rule 2/3 forbid. {{root|...}} is different: it's Wiktionary's own
# deliberate, curated "this word's accepted PIE root is X" tag -- the same
# mechanism that generates the etymology-tree diagram and correctly resolved
# `fram` (clean, unhedged {{root|gem-pro|ine-pro|*per-|id=before}}). Editors
# use it when the root is established, not merely floated as one of several
# guesses -- so restricting to it trades some recall for real precision.
ANCESTRY_TEMPLATES = {"root"}


def load_code_to_name():
    """wiktionary_codes.csv: `code,Name` per line, no header."""
    mapping = {}
    with open(CODES_CSV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or "," not in line:
                continue
            code, name = line.split(",", 1)
            mapping[code.strip()] = name.strip()
    return mapping


def target_list(words):
    """Unique (root_lang, root_term) pairs worth fetching."""
    seen = set()
    targets = []
    for w, e in words.items():
        if e.get("root_pie") or e.get("root_lang") not in PROTO_LANGUAGES:
            continue
        term = e.get("root_term")
        if not term:
            continue
        key = (e["root_lang"], term)
        if key not in seen:
            seen.add(key)
            targets.append(key)
    return targets


def page_title(root_lang, root_term):
    # URL path form drops the leading "*" (verified against the real
    # Reconstruction:Proto-Germanic/fram URL) but keeps everything else,
    # including a trailing "-" on bare roots.
    slug = root_term.lstrip("*").strip()
    return f"Reconstruction:{root_lang}/{slug}"


def fetch_wikitext(title):
    url = "https://en.wiktionary.org/w/index.php?" + urllib.parse.urlencode(
        {"title": title, "action": "raw"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                return None
            return resp.read().decode("utf-8", errors="replace")
    except Exception as ex:
        print(f"  fetch failed for {title}: {ex}", file=sys.stderr)
        return None


# Matches {{tmpl|arg1|arg2|...}} without trying to handle nested braces --
# etymology templates on Reconstruction pages are flat (verified against
# *fram's real wikitext), so this is sufficient.
_TEMPLATE_RE = re.compile(r"\{\{([a-zA-Z][\w-]*)\|([^{}]*)\}\}")


def parse_etymology_templates(wikitext):
    """
    Return a list of (template_name, args) for every {{...}} call in the
    page. Doesn't isolate the Etymology section specifically -- Reconstruction
    pages are typically etymology-only (no other prose sections competing for
    template calls), verified against *fram.
    """
    out = []
    for m in _TEMPLATE_RE.finditer(wikitext):
        name = m.group(1)
        args = m.group(2).split("|")
        out.append((name, args))
    return out


def find_deeper_ancestor(wikitext, code_to_name):
    """
    Look for a {{root|...}} template and return the destination language's
    full name if found, else None. Skips the whole page if its Etymology
    opens with {{unc|...}} ("origin uncertain") -- belt-and-braces on top of
    restricting to {{root}}: a page whose own headline verdict is "uncertain"
    shouldn't be reported as reaching PIE even if a root tag appears further
    down (e.g. as one of several noted alternatives).
    """
    templates = parse_etymology_templates(wikitext)
    if templates and templates[0][0] in ("unc", "unk"):
        return None
    for name, args in templates:
        if name not in ANCESTRY_TEMPLATES or len(args) < 2:
            continue
        dest_code = args[1].strip()
        if dest_code in code_to_name:
            return code_to_name[dest_code]
    return None


def main():
    with open(WIKT_WORDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    words = data["words"]

    try:
        with open(RECON_CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
    except FileNotFoundError:
        cache = {}

    code_to_name = load_code_to_name()
    targets = target_list(words)
    print(f"{len(targets)} unique proto-forms to check ({len(cache)} already cached)", file=sys.stderr)

    fetched_this_run = 0
    for root_lang, root_term in targets:
        key = f"{root_lang}:{root_term}"
        if key in cache:
            continue
        title = page_title(root_lang, root_term)
        wikitext = fetch_wikitext(title)
        fetched_this_run += 1
        if wikitext is None:
            cache[key] = {"found": False}
        else:
            deeper = find_deeper_ancestor(wikitext, code_to_name)
            cache[key] = {"found": True, "deeper_lang": deeper}
        if fetched_this_run % 25 == 0:
            print(f"  ...{fetched_this_run} fetched this run, saving checkpoint", file=sys.stderr)
            with open(RECON_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=1)
        time.sleep(FETCH_DELAY)

    with open(RECON_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    print(f"fetched {fetched_this_run} new pages this run, cache has {len(cache)} total", file=sys.stderr)

    # Patch wikt_words.json: any word whose root_term's Reconstruction page
    # reaches Proto-Indo-European gets root_pie=True.
    patched = 0
    for w, e in words.items():
        if e.get("root_pie") or e.get("root_lang") not in PROTO_LANGUAGES:
            continue
        term = e.get("root_term")
        if not term:
            continue
        entry = cache.get(f"{e['root_lang']}:{term}")
        if entry and entry.get("deeper_lang") == "Proto-Indo-European":
            e["root_pie"] = True
            patched += 1

    with open(WIKT_WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"patched {patched} words to root_pie=True", file=sys.stderr)


if __name__ == "__main__":
    main()
