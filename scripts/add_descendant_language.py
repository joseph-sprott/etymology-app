r"""
Add one language branch to the descendant trees.

Extracted from the etymology-descendants skill 2026-07-26. Widening coverage is
the most common request against that feature and every step of it is fixed:
derive the kaikki URL, download, register the source, rebuild the two tables.
The only judgment involved is WHICH language, which is the argument.

The URL derivation is the part worth having in code rather than in prose: the
filename strips hyphens and spaces from the language name while the directory
keeps them, so Proto-Indo-European lives at
`/dictionary/Proto-Indo-European/kaikki.org-dictionary-ProtoIndoEuropean.jsonl`.
Getting that wrong yields a 404 that looks like "the language isn't available".

    python scripts\add_descendant_language.py "Proto-Italic"
    python scripts\add_descendant_language.py "Proto-Italic" --check   # URL only

Registers the file in build_descendants.py's SOURCES list if it isn't already
there, then runs the build. Only the two descendant tables are touched -- this
never rebuilds etymology.db.
"""

import argparse
import io
import os
import subprocess
import sys
import urllib.error
import urllib.request

import scriptlib

scriptlib.bootstrap()

ROOT = scriptlib.PROJECT_ROOT
BUILDER = os.path.join(ROOT, "build_descendants.py")

# The URL/filename derivation lives in scriptlib because it is pure, easily got
# wrong, and therefore worth a test -- see test_units.py.
kaikki_url = scriptlib.kaikki_url
local_name = scriptlib.local_name


def register(filename: str, language: str) -> bool:
    """Add the file to SOURCES. Returns False when it was already listed."""
    src = io.open(BUILDER, encoding="utf-8").read()
    if filename in src:
        return False
    marker = '    ("proto-germanic.jsonl", "kaikki:Proto-Germanic"),\n'
    if marker not in src:
        raise SystemExit("could not find the SOURCES anchor in build_descendants.py")
    src = src.replace(
        marker, marker + f'    ("{filename}", "kaikki:{language}"),\n')
    io.open(BUILDER, "w", encoding="utf-8").write(src)
    return True


def probe(url: str, language: str) -> bool:
    """Is the extract actually published? A 404 here reads as 'no such language'."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            size = int(response.headers.get("Content-Length") or 0)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"available: NO ({exc})")
        print("  -> check the language's page at "
              f"https://kaikki.org/dictionary/{language}/index.html")
        return False
    print(f"available: yes ({size / 1e6:.1f} MB)")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("language", help='e.g. "Proto-Italic"')
    ap.add_argument("--check", action="store_true",
                    help="resolve and probe the URL, download nothing")
    ap.add_argument("--data", default=scriptlib.WIKTEXTRACT_DIR)
    args = ap.parse_args()

    url = kaikki_url(args.language)
    dest = os.path.join(args.data, local_name(args.language))
    print(f"language : {args.language}")
    print(f"url      : {url}")

    if not probe(url, args.language):
        return
    if args.check:
        return

    if os.path.exists(dest):
        print(f"already downloaded: {dest}")
    else:
        print(f"downloading -> {dest}")
        urllib.request.urlretrieve(url, dest)
        print(f"  {os.path.getsize(dest) / 1e6:.1f} MB")

    added = register(local_name(args.language), args.language)
    print("registered in SOURCES" if added else "already in SOURCES")

    print("\nrebuilding descendant tables...")
    subprocess.run([sys.executable, BUILDER], cwd=ROOT, check=True)
    print("\nnow run: python scripts\\verify.py")


if __name__ == "__main__":
    main()
