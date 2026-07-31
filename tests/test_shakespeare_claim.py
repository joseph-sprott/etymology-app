"""
Not every Wiktionary etymology that says "Shakespeare" is a Shakespeare word.

203 dump entries mention him. Some genuinely attribute the word to him
(`weird` -- "reintroduced by Shakespeare"); others mention him incidentally
(`bowdlerize` is named after the man who CENSORED Shakespeare, and
`Shakespearean` is merely built from his name). Flagging those would put a
false claim on the page, so the phrasing has to be read, not just matched.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_shakespeare_words import asserts_shakespeare


def test_accepts_a_real_attribution():
    assert asserts_shakespeare(
        "Obsolete by the 16th century, it was reintroduced by Shakespeare.")
    assert asserts_shakespeare("Coined by William Shakespeare in Hamlet.")
    assert asserts_shakespeare("First attested in Shakespeare's As You Like It.")
    assert asserts_shakespeare("From Hamlet by William Shakespeare.")


def test_rejects_an_incidental_mention():
    # `bowdlerize`: Bowdler censored Shakespeare. Not a Shakespeare coinage.
    assert not asserts_shakespeare(
        "In 1818, he published a censored version of William Shakespeare.")
    # `Shakespearean`: built FROM the name, not coined BY the man.
    assert not asserts_shakespeare("From Shakespeare + -ean.")
    assert not asserts_shakespeare(
        "Named after English playwright William Shakespeare (1564-1616).")
    # No mention at all.
    assert not asserts_shakespeare("From Old English wyrd.")
