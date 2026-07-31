"""
`photograph` is built from Greek pieces and must not read as native Germanic.

Wiktionary records it as photo- + -graph. The analyzer reports Germanic, which
is not a coverage gap but a WRONG answer -- the shape known issue #22 was meant
to end: a native-descent claim needs an `inherited` edge as evidence, and
`photograph` has none.
"""
from resolver import shared_resolver


def test_photograph_direct_source_is_greek():
    view = shared_resolver().resolve("photograph").view("direct")
    assert view.bucket == "Greek"
