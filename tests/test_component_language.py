"""
A part that names its own language is parsed into that language.

`{{af|en|la:obvius|-ous}}` is Latin `obvius` + the English suffix `-ous`.
The builder stored `la:obvius` verbatim as an English term, so it resolved to
nothing and `obvious` fell through to the legacy backends.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import languages
import wiktextract_shapes as WS

LANGS = languages.load()


def _parts(name, *args):
    numbered = {str(i): a for i, a in enumerate(args, start=1)}
    return [(p.lang, p.term)
            for p in WS.formation_parts([{"name": name, "args": numbered}], LANGS)]


def test_a_prefixed_part_takes_its_own_language():
    assert _parts("af", "en", "la:obvius", "-ous") == [
        ("Latin", "obvius"), ("English", "-ous")]


def test_an_unprefixed_part_keeps_the_templates_language():
    assert _parts("compound", "en", "black", "bird") == [
        ("English", "black"), ("English", "bird")]


def test_the_templates_language_still_applies_to_all_parts():
    # `portmanteau` is Middle French porte + manteau; calling those English
    # would state something false about both. Unchanged by this fix.
    langs = {lang for lang, _term in _parts("af", "frm", "porte", "manteau")}
    assert langs == {"Middle French"}
