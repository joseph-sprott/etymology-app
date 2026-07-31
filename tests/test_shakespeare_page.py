"""
Both features must show the annotation, or they disagree about a word.

The paragraph analyzer shows it on the hover card. The Word Search renders a
different template and would silently omit it -- the same one-feature-knows-
more split that issue #16 exists to prevent, just in the display layer.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app


def _get(path):
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        return client.get(path).get_data(as_text=True)


def test_word_search_shows_the_annotation():
    html = _get("/?word=assassination")
    # The exact phrase, not just the name: an earlier version of this test
    # asserted "Shakespeare" in html and passed against a page that never
    # rendered the annotation at all.
    assert "popularized by Shakespeare" in html


def test_word_search_does_not_show_it_for_an_ordinary_word():
    html = _get("/?word=table")
    assert "popularized by Shakespeare" not in html
