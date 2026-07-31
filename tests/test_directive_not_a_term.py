"""
A DSL directive is not a component word.

`pathophysiologically` renders a component literally called `:af`. That string
is a directive in Wiktionary's `ety`/`etymon` mini-language -- the same family
as the `+af` / `+deverbal` prefixes that once made `late` display as "en +
let" -- and it reached the database as a TERM.

It resolves to nothing, so it takes half the word's weight into Unknown, and
it renders on the page as a component chip reading ":af".
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wiktextract_shapes import clean_term


def test_a_bare_directive_is_rejected():
    assert clean_term(":af")[0] is None
    assert clean_term(":inh")[0] is None
    assert clean_term(":afeq")[0] is None


def test_a_real_term_is_untouched():
    assert clean_term("beauty")[0] == "beauty"
    assert clean_term("-ful")[0] == "-ful"
    # A colon INSIDE a term is not a directive -- only a leading one is.
    assert clean_term("re:invent")[0] == "re:invent"
