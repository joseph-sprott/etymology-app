r"""
Build `coinages.json` -- English words attributed to a named coiner.

    python build_coinages.py
    python build_coinages.py --add "Terry Pratchett"

Generalises the Shakespeare feature Joe asked for on 2026-07-30. Wiktionary
maintains a `Category:English terms coined by X` for several hundred people
under CC BY-SA; this fetches a curated subset of them.

WHY A CURATED SUBSET AND NOT ALL OF THEM. The full list is dominated by
academics and internet figures with one or two technical coinages each
(`Category:English terms coined by ISO/IEC JTC 1/SC 22`). Those fire almost
never and would make the feature feel like noise. The names below are people a
reader recognises, so a note that appears is a note worth reading. Adding one
is a single line -- that is the point of the `--add` flag.

The claim made is "coined by", which is stronger than the Shakespeare
feature's "popularized by" -- and deliberately so, because these categories
are Wiktionary's own explicit attribution rather than an inference from an
OED first-attestation date. See `shakespeare.py` for why the softer wording
is right there.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "coinages.json")

API = "https://en.wiktionary.org/w/api.php"

#: Recognisable coiners. Extend with `--add "Name"`, which rewrites this file
#: is NOT done automatically -- pass the name and it is fetched for this run;
#: add it here to keep it.
COINERS: List[str] = [
    "William Shakespeare",
    "Lewis Carroll",
    "Douglas Adams",
    "Isaac Asimov",
    "Charles Dickens",
    "John Milton",
    "Geoffrey Chaucer",
    "Thomas Carlyle",
    "Samuel Taylor Coleridge",
    "Jeremy Bentham",
    "Benjamin Franklin",
    "Michael Faraday",
    "Charles Darwin",
    "Richard Dawkins",
    "William Gibson",
    "Buckminster Fuller",
    "Murray Gell-Mann",
    "J. R. R. Tolkien",
    "George Orwell",
    "Jonathan Swift",
    "Roald Dahl",
    "Dr. Seuss",
    "Stephen Colbert",
    "Anthony Burgess",
]


def _fetch(params: Dict[str, str], attempts: int = 4) -> Optional[dict]:
    """
    One API call, retried with backoff. None rather than raising.

    Wiktionary returns 429 readily when a run makes a few dozen calls in
    sequence, and a swallowed 429 is indistinguishable from an empty
    category -- which is how the first run reported 0 words for Darwin,
    Dawkins and Orwell when all three have populated categories.
    """
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "etymology-app/1.0 (local research tool)"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                print(f"    fetch failed: {exc}", file=sys.stderr)
                return None
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"    fetch failed: {exc}", file=sys.stderr)
            return None
    return None


def members(coiner: str) -> List[str]:
    """Every page in this coiner's Wiktionary category, following pagination."""
    titles: List[str] = []
    params = {"action": "query", "list": "categorymembers", "format": "json",
              "cmtitle": f"Category:English terms coined by {coiner}",
              "cmlimit": "500"}
    while True:
        data = _fetch(params)
        if data is None:
            break
        titles += [m["title"] for m in
                   data.get("query", {}).get("categorymembers", [])]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont
    return [t for t in titles if ":" not in t]


def collect(coiners: List[str]) -> Dict[str, dict]:
    """word -> {coiner}. First coiner wins on the rare overlap."""
    words: Dict[str, dict] = {}
    for coiner in coiners:
        found = members(coiner)
        print(f"  {len(found):5}  {coiner}")
        for title in found:
            key = title.strip().lower()
            if key and key not in words:
                words[key] = {"coiner": coiner}
        time.sleep(1.0)          # be polite; 429s are easy to provoke here
    return words


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", action="append", default=[],
                    help="fetch an extra coiner for this run")
    args = ap.parse_args()

    words = collect(COINERS + args.add)
    payload = {"source": "en.wiktionary.org Category:English coinages (CC BY-SA)",
               "coiners": sorted({v["coiner"] for v in words.values()}),
               "count": len(words), "words": words}
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"\n{len(words):,} words from {len(payload['coiners'])} coiners "
          f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
