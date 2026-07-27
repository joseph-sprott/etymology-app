"""
The colour system: bucket -> palette slot, and the shades derived from it.

Lifted out of `app.py` in the 2026-07-27 audit. Nothing about the values
changed -- this is a move, not a restyle, and the values are load-bearing:
the 8 core hues and every proto-language step were validated against the
dataviz skill's CVD/contrast checks (see the comments below and known issue
#10's colour-scheme entry), so they are not free to "tidy".

It lives on its own now because three separate things need it -- the paragraph
analyzer, the Word Search tree, and the descendants view -- and because a
1,700-line `app.py` gave a new feature nowhere to import a colour from except
by growing the monolith further.

Imports nothing from this project except `linguistics`, so it cannot pull the
resolver stack (or a 60MB JSON) into anything that only wants a hex value.
"""
import colorsys

# Bucket -> color slot.
#
# The dataviz skill's categorical palette is a hard 8-hue ceiling ("a 9th
# series is never a generated hue" -- CVD-safe adjacent-pair distinguishability
# genuinely doesn't scale past 8 fixed hues; the skill's own validator has no
# passing 9-hue ordering). These 8 stay exactly as originally validated
# (validate_palette.py confirms this exact order clears CVD/contrast checks
# for adjacent pairs in both modes -- re-ordering to chase hue<->bucket
# associations was tried and FAILED the same validator).
#
# 2026-07-23: Joe asked for every bucket to look different, not just these 8.
# Added a second, lower-chroma "extended tier" (one new hue family, hue~205 --
# the largest open gap between the 8 core hues -- differentiated by an ORDINAL
# lightness ramp, not 5 more competing categorical hues) for the 5 buckets
# most likely to actually appear in real English prose per this project's own
# scan history (Slavic, Indo-Iranian, Semitic, Turkic, East Asian). Verified
# against a Python port of the skill's validator (same OKLab/CVD math,
# cross-checked against the documented default's published numbers before
# trusting it) -- passes validate_ordinal (monotone L, gaps >=0.06, light-end
# contrast, single hue) in both modes. The remaining 7 rare buckets
# (Austronesian, Indigenous American, Caribbean, Afro-Asiatic (other),
# African (other), Other, Unknown) still share the flat muted tone -- adding
# a 3rd tier for buckets this rare wasn't judged worth the added visual noise.
BUCKET_SLUGS = {
    "Germanic": "germanic",
    "Norse": "norse",
    "French": "french",
    "Latin": "latin",
    "Greek": "greek",
    "Romance (other)": "romance-other",
    "Celtic": "celtic",
    "PIE": "pie",
    "Slavic": "slavic",
    "Indo-Iranian": "indo-iranian",
    "Semitic": "semitic",
    "Turkic": "turkic",
    "East Asian": "east-asian",
}


def bucket_slug(name):
    # "Unknown" (a true lookup failure) gets its own slug -- deliberately
    # distinct from "muted" (the shared tone for real-but-rare buckets like
    # "Other"/Caribbean/Austronesian). Found 2026-07-23 (Joe: "persona" reads
    # as Unknown) -- the word actually resolves fine (Etruscan<-Latin<-Greek,
    # bucket "Other"), but "Other" and "Unknown" rendered in the EXACT same
    # muted gray with no distinction, so a real-but-rare answer was
    # indistinguishable from a genuine failure. Same root cause would affect
    # every "Other"-bucket word, not just this one -- fixed generally, not
    # per-word, by giving Unknown its own visually-recessive treatment (see
    # --c-unknown in the page CSS) instead of sharing muted's tone.
    if name == "Unknown":
        return "unknown"
    return BUCKET_SLUGS.get(name, "muted")


# Deepest Root mode names the specific reconstructed form (see resolver.py's
# root_lang/root_pie) -- coordinate each proto-language with its parent
# bucket's hue via a validated lightness step (lighter = deeper reconstructed
# stage), so "Proto-Germanic (from PIE)" reads as a shade of Germanic-blue,
# not an unrelated color. Slots not tied to one of the 8 core hues (Slavic,
# Indo-Iranian) get a lighter step of their own extended-tier hue instead.
PROTO_SLUGS = {
    "Proto-Germanic": "proto-germanic",
    "Proto-West Germanic": "proto-west-germanic",
    "Proto-Italic": "proto-italic",
    "Proto-Celtic": "proto-celtic",
    "Proto-Slavic": "proto-slavic",
    "Proto-Indo-Iranian": "proto-indo-iranian",
}


# Base hex per bucket (light-mode values from the CSS custom properties
# below) -- kept here too so Python can generate shades from them. Used only
# for the bar-drill-down sub-language shading (task 2026-07-23): a lighter-
# weight scope than the validated CVD-checked palette above -- Joe's own
# framing ("sky blue, dark blue, neon blue... or a nice visualization to
# distinguish the subgroups") was satisfied with simple lightness/saturation
# variation around the bucket hue, not another full ordinal-ramp validation
# pass (which the original 8-hue palette and the proto-language shades DID
# get -- this reuses that same visual language without re-deriving it for
# what could be dozens of specific donor languages per bucket).
BUCKET_HEX = {
    "Germanic": "#2a78d6", "Norse": "#eb6834", "French": "#1baf7a",
    "Latin": "#eda100", "Greek": "#e87ba4", "Romance (other)": "#008300",
    "Celtic": "#4a3aa7", "PIE": "#e34948",
    "Slavic": "#156068", "Indo-Iranian": "#30767e", "Semitic": "#488c94",
    "Turkic": "#5fa4ab", "East Asian": "#77bbc3",
}
_MUTED_HEX = "#898781"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def language_shades(bucket, languages):
    """
    Maps each specific language name (within one bucket) to its own shade of
    that bucket's base hue -- deterministic (same language always gets the
    same shade), spread across a moderate lightness/saturation range chosen
    to stay legible on both light and dark surfaces without needing a
    separate light/dark variant (a lighter-weight approach than the main
    palette's per-mode CSS variables -- see BUCKET_HEX comment).
    """
    base = BUCKET_HEX.get(bucket, _MUTED_HEX)
    r, g, b = (c / 255.0 for c in _hex_to_rgb(base))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    n = max(len(languages), 1)
    shades = {}
    for i, lang in enumerate(sorted(languages)):
        # Spread lightness across a legible band; nudge saturation opposite
        # to lightness so the darkest shade doesn't also look washed out.
        t = i / n if n > 1 else 0.5
        lt = 0.35 + t * 0.35          # 0.35 -> 0.70
        st = min(1.0, s * (0.85 + 0.3 * (1 - t)))
        rr, gg, bb = colorsys.hls_to_rgb(h, lt, st)
        shades[lang] = _rgb_to_hex((rr * 255, gg * 255, bb * 255))
    return shades

def root_slug(w, mode):
    """Per-word swatch slug for the current mode -- the proto-language slug
    in Deepest Root mode when one applies, else the plain bucket slug."""
    if mode == "root" and w.depth_lang:
        base = w.depth_lang.removesuffix(" (from PIE)")
        if base in PROTO_SLUGS:
            return PROTO_SLUGS[base]
    return bucket_slug(w.bucket)

# The colour system and typography, lifted out of PAGE so the descendant-tree
# view can share it rather than keep a second copy that drifts. Every --c-*
# value is load-bearing (validated hue/lightness steps -- see BUCKET_SLUGS and
# the 2026-07-23 palette work); this move is pure extraction, no value changed.
THEME_CSS = """
    :root {
      /* Dictionary/wiki typography (2026-07-26, Joe: "more in line with a
         dictionary look, etymonline is a good example ... nothing too
         crazy"). Serif for READING -- headwords, definitions, the foreign
         terms in a lineage. Sans for CHROME -- buttons, inputs, percentage
         bars, anything that is an instrument rather than an entry. Keeping
         those two jobs on different faces is most of what makes a reference
         page read like one; the rest is whitespace and hairlines.
         Every --c-* bucket colour below is deliberately UNCHANGED: they are
         load-bearing (validated hue/lightness steps, see BUCKET_SLUGS) and
         a restyle is no reason to disturb them. */
      --serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua",
               Georgia, Cambria, "Times New Roman", serif;
      --sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      --rule: #ddd8c9;          /* hairlines under headings */
      --accent: #7a3323;        /* muted oxblood, for links only */
      --surface: #fbf9f3;       /* warm paper, was near-white */
      --surface-2: #f2eee2;
      --text-primary: #16150f;
      --text-secondary: #56534a;
      --track-bg: #e2ddcd;
      --c-germanic: #2a78d6;
      --c-norse: #eb6834;
      --c-french: #1baf7a;
      --c-latin: #eda100;
      --c-greek: #e87ba4;
      --c-romance-other: #008300;
      --c-celtic: #4a3aa7;
      --c-pie: #e34948;
      --c-muted: #898781;
      /* "Unknown" (a true lookup failure) -- deliberately lighter/more
         washed-out than --c-muted, so it visually recedes as "nothing
         found" rather than reading as a real (if rare) category the way
         --c-muted's "Other"/Caribbean/etc. do. See bucket_slug() comment. */
      --c-unknown: #d6d4cc;
      /* Extended tier (hue~205, lower chroma -- see BUCKET_SLUGS comment in app.py) */
      --c-slavic: #156068;
      --c-indo-iranian: #30767e;
      --c-semitic: #488c94;
      --c-turkic: #5fa4ab;
      --c-east-asian: #77bbc3;
      /* Proto-language shades: validated lighter step of the parent hue */
      --c-proto-germanic: #75a7e9;
      --c-proto-west-germanic: #5391e0;
      --c-proto-italic: #a37734;
      --c-proto-celtic: #7d7ad1;
      --c-proto-slavic: #4e939a;
      --c-proto-indo-iranian: #61a5ad;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --rule: #38362f;
        --accent: #d99277;
        --surface: #171613;
        --surface-2: #221f1a;
        --text-primary: #f4f1e8;
        --text-secondary: #b8b4a6;
        --track-bg: #302c25;
        --c-germanic: #3987e5;
        --c-norse: #d95926;
        --c-french: #199e70;
        --c-latin: #c98500;
        --c-greek: #d55181;
        --c-romance-other: #008300;
        --c-celtic: #9085e9;
        --c-pie: #e66767;
        --c-muted: #898781;
        --c-unknown: #3a3a37;
        --c-slavic: #156068;
        --c-indo-iranian: #30767e;
        --c-semitic: #488c94;
        --c-turkic: #5fa4ab;
        --c-east-asian: #77bbc3;
        --c-proto-germanic: #75a7e9;
        --c-proto-west-germanic: #5391e0;
        --c-proto-italic: #a37734;
        --c-proto-celtic: #7d7ad1;
        --c-proto-slavic: #4e939a;
        --c-proto-indo-iranian: #61a5ad;
      }
    }
"""


