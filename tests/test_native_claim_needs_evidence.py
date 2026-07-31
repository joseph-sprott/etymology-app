"""
Native descent is a CLAIM. Claiming it without evidence is worse than a gap.

Issue #22 established this for `etymology.db`: a word only counts as native
core when the data shows an `inherited` edge through the English stages.
The legacy `ety` backend never got the same rule, so it still answers "English
native core" for any word it has no chain for -- which the analyzer renders as
Germanic. That is a confident WRONG answer where Unknown was the honest one,
and it hides because nothing looks broken.

`lithology` is the specimen: live Wiktionary gives "From litho- + -ology",
both from Ancient Greek (λίθος "stone", -λογία "study of"). It is reported as
Germanic. Found by scanning 4,000 database headwords for the signature
(answer came from `ety`, claims an English stage, carries no chain) -- 11 hits
in that sample, so this is a class, not one word.
"""
from resolver import shared_resolver


def test_a_greek_formation_is_not_claimed_as_native_germanic():
    view = shared_resolver().resolve("lithology").view("direct")
    assert view.bucket != "Germanic"
