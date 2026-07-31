"""
Manual corrections for confirmed false-positive entries in wikt_words.json.

Root cause: etymology-db parses per-page relation edges from Wiktionary, and
Wiktionary pages are organized by SPELLING across all languages, not just
English. Short, common English words often collide with an unrelated word in
another language that happens to be spelled identically on the same page --
e.g. "she" also names a Japanese romanization (katakana she) and a nonstandard
Mandarin pinyin reading on the same Wiktionary page; "so", "or", "no", "as",
"many", "can", "may", "must", "could", "mine", "none", "are", "an" show the
same pattern. The scraper appears to pick up a "donor" edge from that
coincidental homograph instead of a real etymological relation.

Every entry here was individually verified against Wiktionary's live
Etymology section for the English word (2026-07-22) before being added.
One candidate that failed the same automated scan was deliberately NOT
added: "because" -- its French/Latin proximate is actually correct
(Middle English "bi cause" = native "by" + "cause", and "cause" really is
from Old French < Latin causa).

UPDATE 2026-07-23: the real root cause turned out to be different (see
CLAUDE.md known issue #6) -- it wasn't Wiktionary/etymology-db's scraper,
it was this project's own old case-insensitive merge key in convert_wikt.py,
which has since been fixed structurally (case-sensitive storage, no merging
at conversion time). After rebuilding wikt_words.json from the raw
etymology-db relation table, 25 of the entries below turned out to now be
fully redundant (the pipeline produces the identical p/d/chain on its own)
and were removed from this file the same day, so they stop suppressing the
richer per-word data the new pipeline provides (e.g. the "Deepest Root"
proto-language detail added the same night). Removed as redundant: can, she,
look, ox, chin, lop, wall, deep, even, pretty, saw, lot, ham, baron, acre,
split, soy, said, reggae, hurricane, barbecue, iguana, cannibal, potato,
irie, zero. Each was re-verified against the rebuilt data (both `p`/`d` AND
the full `chain` array had to match exactly, not just the summary bucket --
several near-misses like "kin"/"tar"/"tell"/"get"/"bark" still had a
different, still-wrong chain interior despite matching p/d, so those STAYED
in this file). The remaining entries below are still genuinely needed --
this is a narrower, better-understood residual (see CLAUDE.md issue #6),
mostly real multi-sense collisions (e.g. `die`/`bull`) rather than the
cross-language homograph collisions originally suspected.
"""

WORD_CORRECTIONS = {
    "an":    {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "are":   {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "as":    {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "could": {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "many":  {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "may":   {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "mine":  {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "must":  {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "no":    {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "none":  {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "or":    {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "so":    {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},

    # Second pass, 2026-07-22 (same bug, found via a full-database scan for the
    # signature "exotic proximate bucket + a real Germanic link later in the
    # chain" -- see scan below). These are ordinary content words, not just
    # closed-class function words, so the bug's reach is broader than first
    # scoped. Each verified individually against Wiktionary before adding.
    "girl":  {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "go":    {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "kin":   {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "nut":   {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "roof":  {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "sun":   {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "beg":   {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "woo":   {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "wang":  {"p": "Germanic", "d": "Germanic", "chain": [],                  "prox_kind": "core"},

    # Third pass, 2026-07-22: Joe asked why the remaining ~24 scan hits from
    # pass 2 weren't checked automatically. Answer: the scan signature alone
    # isn't reliable enough to auto-apply -- "aa" and "tong" from pass 2 both
    # matched it and were genuinely correct, so blind bulk-correction would
    # have introduced new errors. Went through the rest individually instead.
    # Of 18 checked this pass, only 2 were real bugs:
    "ding":  {"p": "Germanic", "d": "Germanic", "chain": [],                  "prox_kind": "core"},  # purely onomatopoeic, no foreign donor at all
    "rie":   {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},  # obsolete spelling of "rye" (Old English ryge); the English Wiktionary entry for "rie" itself has no etymology section, so it was fully hijacked

    # Fourth pass, 2026-07-22: broadened the scan to Slavic/Indo-Iranian/
    # Semitic families too (excluded from pass 2 since those have a lot of
    # genuine loanwords -- coffee/sugar/algebra are real Semitic borrowings).
    # 70 new hits; most were proper nouns, place names, surnames, or genuine
    # Jewish/Slavic cultural terms (Herzegovina, Stalin, Pasternak, mohel,
    # challah, tsar, commissar, etc. -- plausibly correct, not checked
    # individually). Filtered to everyday words and verified each one:
    "bench": {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "bridge":{"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "iron":  {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "moth":  {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "tar":   {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "tell":  {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "bath":  {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "ye":    {"p": "Germanic", "d": "PIE",      "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},
    "ken":   {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    "brim":  {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"],        "prox_kind": "inherited"},
    # "cheese" is a "wall"-shaped special case: Old English already borrowed
    # it from Latin (cAseus) in the Proto-West-Germanic period, before
    # English existed as its own language -- so proximate correctly stays
    # Germanic (that's what English itself inherited), but the real deep
    # lineage runs through Latin.
    "cheese":{"p": "Germanic", "d": "Latin",    "chain": ["Germanic", "Latin"], "prox_kind": "inherited"},

    # Fifth pass, 2026-07-22: found while building the new 3-level view
    # ("Notable Influence"). That feature surfaces whatever's in a chain's
    # interior as the culturally-interesting middle donor -- which means an
    # interior collision bug now actively produces a wrong "linguist's
    # answer", not just a wrong deep/root reading. Scanned for words with a
    # core-language direct donor, an exotic-family bucket somewhere in the
    # interior, and PIE as the root (the shape that flagged "increase" ->
    # bogus Semitic in the first place). 81 words matched; checked the ~40
    # most common ones individually. 17 real bugs, fixed below. Policy: only
    # remove the specifically-disproven bucket and keep the rest of the
    # existing chain, rather than re-deriving the whole thing from a partial
    # fetch -- except where the fetched etymology was clean and total enough
    # (e.g. "acre") to be confident the *other* chain entries were also
    # spurious, not just the one checked.
    "pie":     {"p": "Germanic", "d": "Germanic", "chain": [], "prox_kind": "core"},  # food sense: "further origin uncertain" -- no real Indo-Iranian link, speculative magpie theory not the primary etymology
    "on":      {"p": "Norse", "d": "PIE", "chain": ["Norse", "Germanic", "PIE"], "prox_kind": "derived"},  # no East Asian connection at all
    "lake":    {"p": "French", "d": "PIE", "chain": ["French", "Germanic", "PIE"], "prox_kind": "borrowed"},  # Wiktionary explicitly denies the Indo-Iranian link
    "get":     {"p": "Norse", "d": "PIE", "chain": ["Norse", "Germanic", "PIE"], "prox_kind": "derived"},  # no Semitic connection
    "bark":    {"p": "Norse", "d": "PIE", "chain": ["Norse", "Germanic", "PIE"], "prox_kind": "derived"},  # neither real sense (tree bark / dog bark) has any Afro-Asiatic, French, Latin, or Greek connection
    "grab":    {"p": "Germanic", "d": "PIE", "chain": ["Germanic", "PIE"], "prox_kind": "derived"},  # the common verb has no Semitic link; a separate, rare noun "grab" (a ship type) does -- different word
    "bun":     {"p": "French", "d": "PIE", "chain": ["French", "Germanic", "Celtic", "PIE"], "prox_kind": "borrowed"},  # no East Asian connection
    "phase":   {"p": "Latin", "d": "Greek", "chain": ["Latin", "Greek"], "prox_kind": "derived"},  # no Semitic connection for this sense; a separate word "Pasch"/Passover (Hebrew) shares no real link to "phase"
    "gross":   {"p": "French", "d": "Latin", "chain": ["French", "Latin"], "prox_kind": "derived"},  # no Semitic connection; ultimate origin beyond Latin is "uncertain" per Wiktionary, not PIE
    "progress":{"p": "French", "d": "Latin", "chain": ["French", "Latin"], "prox_kind": "derived"},  # no Slavic connection
    "slack":   {"p": "Norse", "d": "Germanic", "chain": ["Norse", "Germanic"], "prox_kind": "derived"},  # no Slavic connection in any of its five etymologies
    "kennel":  {"p": "French", "d": "PIE", "chain": ["French", "Latin", "PIE"], "prox_kind": "derived"},  # no Semitic connection; PIE root *ḱwṓ ("dog") explicitly unrelated to Semitic
    "bar":     {"p": "Latin", "d": "Latin", "chain": ["Latin"], "prox_kind": "derived"},  # no Slavic connection; Vulgar Latin *barra is "of uncertain origin", a dead end
    "tap":     {"p": "French", "d": "PIE", "chain": ["French", "Germanic", "PIE"], "prox_kind": "derived"},  # no Indo-Iranian connection

    # Sixth pass, 2026-07-22: Joe asked for one broad unified scan instead of
    # rediscovering new scan shapes reactively. Tried "exotic bucket anywhere
    # in chain" first -- 11,487 hits, useless (mostly genuine loanwords and
    # proper nouns). Tightened to "chain has BOTH Germanic and an exotic
    # bucket" (the actual bug signature: a word with a genuine native
    # inheritance thread that ALSO picked up a stray foreign edge) -- 309
    # hits. Most are legitimate clusters already validated by the pattern in
    # earlier passes (real Yiddish/Hebrew cultural terms: kosher, mohel,
    # shiksa, tuchus, etc.; real Slavic loanwords: pogrom, quark, kludge,
    # knish, etc.; real Malay/Turkish terms: sambal, toko, deel, oda, etc.)
    # -- not re-verified individually, same reasoning as pass 4. Checked the
    # new everyday words not covered by any prior pass: 6 real bugs fixed
    # below. Left alone as genuine: tea (Dutch<-Hokkien, real), tattoo
    # (two real senses: Polynesian skin-marking + Dutch military-drum),
    # curry (two real senses: Tamil food + Germanic/Latin "curry favor"),
    # monkey (a documented if disputed Arabic theory), junk (two real
    # senses: uncertain-origin "refuse" + real Malay/Javanese ship chain),
    # lime (two real senses: Semitic/Persian/Sanskrit fruit + pure Germanic
    # mineral), poke (real senses merged: Germanic jab + genuine Hawaiian
    # food loanword), cravat (genuinely French<-German<-Serbo-Croatian),
    # racket (a documented if disputed Arabic theory for the sports sense),
    # quartz (genuinely German<-West Slavic "hard"), amen (genuinely Hebrew
    # -- the buckets are all real, just possibly mis-ordered, which is
    # known issue #2, not this one), horde (a genuine multi-hop chain:
    # French<-German<-Polish<-Russian<-Turkic), rook (two real senses:
    # Germanic bird + genuinely Persian chess piece).
    "boss":  {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"], "prox_kind": "borrowed"},  # Dutch "baas" only; the East Asian entry was backwards -- "boss" was borrowed INTO Japanese, not from it
    "stir":  {"p": "Germanic", "d": "PIE", "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},  # no Indo-Iranian connection, purely Old English/Proto-Germanic/PIE
    "coach": {"p": "French", "d": "Other", "chain": ["French", "Germanic", "Other"], "prox_kind": "borrowed"},  # no Turkic connection; real chain is French<-German<-Hungarian (Hungarian has no bucket of its own, correctly "Other")
    "gill":  {"p": "French", "d": "Germanic", "chain": ["French", "Latin", "Norse", "Germanic"], "prox_kind": "borrowed"},  # two real senses (Old French liquid-measure + North Germanic fish-organ) but no Semitic or Celtic connection in either
    "ban":   {"p": "Germanic", "d": "PIE", "chain": ["Germanic", "PIE"], "prox_kind": "inherited"},  # the common verb (to prohibit) is purely Germanic/PIE; the Slavic link belongs to an unrelated homonym (a noble title, "ban")

    # New "Caribbean" bucket, 2026-07-22 -- Joe asked whether Caribbean-origin
    # words (his examples: "limbo", "bomboclat") had a home. They didn't --
    # buckets_wikt.py had no Caribbean/Creole/Taino entries at all, so any
    # such word fell into the vague "Other" catch-all. Added the bucket to
    # buckets_wikt.py (for whenever convert_wikt.py can be re-run against the
    # raw CSV) and wired these specific verified words in here so it's live
    # tonight, same mechanism as every other fix. NOT the same issue as the
    # cross-language collision bug (#6) -- this is closing a real coverage
    # gap, not correcting a wrong answer.
    "voodoo":   {"p": "Caribbean", "d": "African (other)", "chain": ["Caribbean", "African (other)"], "prox_kind": "borrowed"},  # Louisiana Creole <- Haitian Creole <- West African (Ewe/Fon/Kwa)
    "canoe":    {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish canoa <- Taino *kanowa
    "cay":      {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish cayo <- Taino (the Taino link was missing from the raw chain entirely, added here after verifying it directly)
    # Second batch, same night, 2026-07-22: Joe asked for a list of Caribbean
    # words to try in the app -- verified a batch, wiring the clean ones in.
    "hammock":  {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish hamaca <- Taino *hamaka
    "maize":    {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish maiz <- Taino *mahis
    "guava":    {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish guayaba <- Taino *wayaba
    "cassava":  {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish cazabe <- Taino *kasabi
    "cacique":  {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish cacique <- Taino/Lokono *kasike ("chieftain")
    "papaya":   {"p": "Romance (other)", "d": "Caribbean", "chain": ["Romance (other)", "Caribbean"], "prox_kind": "borrowed"},  # Spanish papaya <- Lokono papaia (Arawakan, same family as Taino)
    "obeah":    {"p": "Caribbean", "d": "African (other)", "chain": ["Caribbean", "African (other)"], "prox_kind": "borrowed"},  # via a Caribbean creole, ultimately West African (Igbo) -- same shape as "voodoo"
    "duppy":    {"p": "African (other)", "d": "African (other)", "chain": ["African (other)"], "prox_kind": "borrowed"},  # despite the strong Jamaican cultural association, the documented donor is directly Bube (Equatorial Guinea) -- no separate Caribbean-language hop
    # "calypso" turned out to be its own collision bug, caught while
    # checking it for this feature: raw data showed chain=['Other', 'Greek',
    # 'PIE'] -- the Greek/PIE tail belongs to the unrelated Greek
    # mythological nymph Calypso, not the music genre, which really traces
    # to Ibibio (West African) via Trinidad English (itself just a register
    # of English, not a separate donor language).
    "calypso":  {"p": "African (other)", "d": "African (other)", "chain": ["African (other)"], "prox_kind": "derived"},

    # 2026-07-23: Joe flagged known issue #2 (chain ordering) via candy, zero,
    # sandal, die, bull. Investigating found only "zero" was really a #2
    # ordering bug -- and once the pipeline was rebuilt from the raw
    # etymology-db relation table that same night (real per-word graph
    # structure instead of a static depth table), "zero" started resolving
    # correctly on its own and its override here was removed as redundant.
    # The other four turned out to be different bug shapes entirely, each
    # verified against live Wiktionary before correcting, and still needed:
    # candy/sandal: #6-shaped -- spurious edges from an unrelated collision,
    # not a real donor. Wiktionary's actual chains have no Latin/Greek for
    # candy, no Semitic/Indo-Iranian for sandal at all.
    "candy":  {"p": "French", "d": "Indo-Iranian", "chain": ["French", "Semitic", "Indo-Iranian"], "prox_kind": "derived"},  # Old French sucre candi <- Arabic qandi <- Persian/Sanskrit qand/khanda; no Latin or Greek in the real chain
    "sandal": {"p": "French", "d": "Greek", "chain": ["French", "Latin", "Greek"], "prox_kind": "derived"},  # Old French sandale <- Latin sandalium <- Ancient Greek sandalion, "of unknown origin" beyond that -- no Semitic, no Persian/Indo-Iranian on the live Wiktionary page
    # die/bull: #5-shaped -- real distinct senses merged into one chain.
    # Picked the sense dominant in ordinary running text (verb "to die" /
    # the animal), dropped the rare/specialized sense that was contaminating
    # the chain (dice-cube noun <- Latin datum; papal bull <- Latin bulla).
    "die":  {"p": "Norse", "d": "Germanic", "chain": ["Norse", "Germanic"], "prox_kind": "derived"},  # verb sense: Middle English deyen <- Old Norse deyja <- Proto-Germanic *dawjana; PIE ancestor is genuinely disputed (Kroonen prefers a Hittite connection over *dhew-), so left at Germanic rather than guessing
    "bull": {"p": "Norse", "d": "PIE", "chain": ["Norse", "Germanic", "PIE"], "prox_kind": "derived"},  # animal sense: Old English bula / Old Norse boli (conflated) <- Proto-Germanic *bulon <- PIE *bhel- "to blow, swell"; dropped the unrelated papal-bull sense's Latin/French

    # Caught 2026-07-23 (Joe, testing Direct Source mode): "and" showed Norse.
    # Same #5-shape as die/bull -- the term_id bundles the common conjunction
    # (clean native chain: Middle English/Old English "and" <- Proto-Germanic
    # *andi <- PIE *h2enti, verified against live Wiktionary, zero Norse
    # content) with two rare, unrelated archaic senses that genuinely ARE
    # Norse-derived: "ande" (obsolete noun "breath/zeal/envy", related to
    # Latin animus) and "anden" (obsolete verb "to envy"), both <- Old Norse
    # <- a DIFFERENT Proto-Germanic root (*anadô/*anadōną, not *andi) <- a
    # DIFFERENT PIE root (*h2enh1- "to breathe", not *h2enti). Root cause was
    # subtler than a typical die/bull merge: the conjunction's own real
    # Proto-Germanic/PIE content got sorted to appear AFTER the archaic
    # senses' Old Norse content, because Norse's depth-hint rank is shallower
    # than Proto-Germanic's -- the hint tiebreak (meant only for ordering
    # genuinely-unrelated top-level siblings within ONE sense, see
    # convert_wikt.py) doesn't know these top-level items belong to
    # different senses entirely.
    "and":  {"p": "Germanic", "d": "PIE", "chain": ["Germanic", "PIE"], "prox_kind": "inherited",
             "root_lang": "Proto-Germanic", "root_term": "*andi", "root_pie": True},

    # 2026-07-23: found while building the compound-word split feature (a word
    # that resolves to Unknown gets displayed as its two component words
    # instead). Two of the needed component words were themselves missing
    # entirely from wikt_words.json/ety (a coverage gap, not a collision) but
    # common and cleanly verifiable against live Wiktionary, so added directly
    # rather than left as an unresolved compound part:
    "zoo":  {"p": "Greek", "d": "Greek", "chain": ["Greek"], "prox_kind": "clipping"},  # clipping of "zoological garden" <- "zoology" <- Greek zoion + logia
    "plow": {"p": "Norse", "d": "Germanic", "chain": ["Norse", "Germanic"], "prox_kind": "inherited",
             "root_lang": "Proto-Germanic", "root_pie": False},  # American spelling of "plough" -- Wiktionary explicitly cross-references it as an alternative spelling; mirrors plough's own entry exactly
    # "selves" REMOVED 2026-07-25: it existed only because the resolver's
    # suffix-stripping couldn't undo the f->v plural alternation (self ->
    # selves), the same gap later generalized into a `_fv_candidates` rule.
    # Both are now obsolete -- wiktextract records "selves" as a plural-tagged
    # form of "self" outright (see inflections.py), and removal was verified
    # by dry run first: "selves" still resolves Germanic, and ourselves/
    # themselves still split into their component words correctly.
    # Other missing compound-part words checked and deliberately NOT added --
    # each is genuinely disputed/uncertain/unwritten on live Wiktionary itself,
    # so filling one in would be guessing, not verifying: "grid" (back-
    # formation/clipping of griddle or gridiron, no donor language stated),
    # "lumber" ("exact origin unknown" per Wiktionary itself, several
    # competing unconfirmed theories), "longshore" (aphesis of "alongshore",
    # no separate donor chain of its own), "nog" (Wiktionary's own etymology
    # section is marked missing/incomplete), "shuffle" (relation to
    # scuffle/shove stated but no donor language given), "surf" ("etymology
    # uncertain", multiple unconfirmed theories per Wiktionary). Their
    # compound words (gridlock, lumberjack, longshoreman, eggnog, shuffleboard,
    # surfboard) stay Unknown rather than getting a fabricated split.

    # 2026-07-23, Joe's bug list (bar-graph/tree redesign session): two more
    # #6-shaped (multi-sense/spurious-edge) bugs caught testing Deepest Root.
    "with": {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"], "prox_kind": "inherited",
             "root_lang": "Proto-Germanic", "root_term": "*wiþrą", "root_pie": False},
    # Old Norse is NOT a real ancestor of "with" -- Wiktionary cites it only
    # as a COGNATE, offering a parallel semantic-shift example ("an earlier
    # model of this meaning shift exists in cognate Old Norse við"), not a
    # donor. Real chain: Middle English <- Old English wiþ <- Proto-West
    # Germanic *wiþi <- Proto-Germanic *wiþrą. No PIE connection stated on
    # the page, so root stays honestly at Proto-Germanic.
    "back": {"p": "Germanic", "d": "PIE", "chain": ["Germanic", "PIE"], "prox_kind": "inherited",
             "root_lang": "Proto-West Germanic", "root_term": "*bak", "root_pie": True},
    # Found 2026-07-23 via regression-testing the depth-hint/PIE-invariant
    # fixes (not one of Joe's originally-reported bugs). Direct Source is
    # correctly Germanic now, but Deepest Root showed "French (from PIE)" --
    # a #6/#5-shaped multi-sense collision: "back"'s term_id bundles the
    # common native word (clean single lineage per the raw data: Middle
    # English bak <- Old English bæc <- Proto-West Germanic *bak <- Proto-
    # Germanic *baką <- PIE *bʰogo) with an unrelated, much rarer sense
    # borrowed_from French "bac" (a vat/ferry, not the common word). Because
    # that French edge happens to sort right before the native branch's own
    # has_root PIE pointer, root_lang picked "French" as "the step before
    # PIE" even though it isn't part of the real native lineage. Dropped the
    # French content, kept the clean native chain.
    "low": {"p": "Norse", "d": "PIE", "chain": ["Norse", "Germanic", "PIE"], "prox_kind": "derived",
            "root_lang": "Proto-Germanic", "root_term": "*lēgaz", "root_pie": True},
    # "low" (the "not high" adjective) genuinely has SIX separate etymologies
    # on Wiktionary for unrelated senses sharing one page/term_id (adjective,
    # the verb "to moo", etc.) -- same shape as and/die/bull. Etymology 1 (the
    # common adjective) has a clean single chain: PIE *legʰ- -> Proto-Germanic
    # *lēgaz -> Old Norse lágr -> Middle English -> English. Our raw data had
    # the right three buckets but the wrong order (PIE sorted before Norse,
    # backwards) -- a rogue edge from one of the other 5 etymologies bled in
    # and the depth-hint tiebreak (meant for ordering fragments within ONE
    # sense) sorted across senses that were never meant to be compared.

    # Caught 2026-07-23 (Joe: "why does 'seen' show up as arabic?"). Verified
    # against live Wiktionary: the page for "seen" genuinely bundles TWO
    # unrelated entries -- the common English past participle ("see" + "-n")
    # and a separate borrowed transliteration of the Arabic letter name سِين
    # (sīn) -- and etymology-db's raw data for this term_id only carried the
    # Arabic sense (chain: ["Semitic"], root_term the Arabic letter itself).
    # Same #5-shape multi-sense collision as die/bull/tong, just never
    # flagged by any prior scan since "seen" isn't an obviously-exotic-looking
    # word. Real chain per Wiktionary: Middle English seen <- Old English
    # sēon <- Proto-West Germanic *sehwan <- Proto-Germanic *sehwaną -- no
    # PIE step stated on the page, so root stays honestly at Proto-Germanic
    # rather than guessing one.
    "seen": {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"], "prox_kind": "inherited",
             "root_lang": "Proto-Germanic", "root_term": "*sehwaną", "root_pie": False},

    # Found 2026-07-24 while widening convert_wikt.py's stub-patching to
    # cover no-entry-at-all terms (Joe: "professional"/"mindset" showing
    # Unknown). That widening turns common short words into "hub" roots
    # inherited by dozens-to-hundreds of derived terms (e.g. "detag" ->
    # "tag"), so a pre-existing collision in the hub word now has much
    # bigger blast radius. "tag"'s raw etymology-db data was ONLY the rare
    # sense (Etymology 2 on Wiktionary: borrowed_from Aramaic תגא "crown",
    # the decorative mark drawn over certain Hebrew letters) -- the common
    # everyday sense (label/game/graffiti, Etymology 1: Middle English tagge,
    # "probably of North Germanic origin" per Wiktionary's own hedge, cognate
    # with Norwegian/Swedish/Icelandic tagg/tág) was never captured as its
    # own ancestry edge in the source data at all. Verified directly against
    # live Wiktionary before fixing. No PIE step stated for this sense, so
    # root stays honestly at Middle English rather than guessing one.
    "tag": {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"], "prox_kind": "inherited",
            "root_lang": "Middle English", "root_term": "tagge", "root_pie": False},

    # Found alongside "tag" (same widening, same discovery method): "auto"'s
    # raw data has a real derived_from Ancient Greek αὐτός edge (the correct
    # answer for the "auto-" combining form used in words like "autopilot"/
    # "autocide"), but ALSO a circular etymology-db artifact -- a
    # clipping_of "autorickshaw" row nested with a derived_from Hindi
    # ऑटो रिक्शा row -- where "autorickshaw" is itself a modern English
    # compound (auto + rickshaw) that got borrowed INTO Hindi and is here
    # cited backwards, as if the Hindi form were an ancestor of "auto"
    # rather than a re-borrowing of it. The old depth-hint tiebreak sorted
    # that Hindi edge (unlisted language, default tier 10) ahead of the real
    # Ancient Greek edge (tier 14), making "auto" resolve Indo-Iranian
    # instead of Greek. Verified against live Wiktionary (three legitimate
    # senses -- clippings of "automatic"/"automobile"/Indian-English
    # "autorickshaw" -- none of which trace to Hindi as an ancestor) before
    # fixing. Chain stays the single verified hop; no further PIE
    # connection recorded for αὐτός itself in this data.
    "auto": {"p": "Greek", "d": "Greek", "chain": ["Greek"], "prox_kind": "derived",
             "root_lang": "Ancient Greek", "root_term": "αὐτός", "root_pie": False},

    # Found 2026-07-24 (Joe: "generate" read Unknown for Direct Source,
    # PIE for Deepest Root -- the bare-has_root-stub shape, issue #14).
    # Raw data has a real has_root -> PIE *ǵenh₁- pointer (correctly
    # suppressed from Direct Source per issue #14's fix) plus two
    # etymologically_related_to Latin mentions (generō, genus) -- a hedge,
    # not asserted ancestry, so convert_wikt.py correctly didn't use them on
    # its own (same category as the still-open 1,245-word residual in issue
    # #14). Individually verified against live Wiktionary rather than left
    # in that residual, since the real etymology here isn't actually in
    # doubt: "From Latin generō ('beget, procreate, produce') + -ate...,
    # from genus ('a kind, race, family')" -- ordinary, well-documented
    # Latin derivation, plus "English terms derived from the PIE root
    # *ǵenh₁-" confirming the same PIE root the raw data already had.
    "generate": {"p": "Latin", "d": "PIE", "chain": ["Latin", "PIE"], "prox_kind": "derived",
                 "root_lang": "Latin", "root_term": "genus", "root_pie": True},

    # Found 2026-07-24 (Joe: run 347 real paragraphs through the analyzer,
    # find everything that shouldn't be Unknown -- issue #17). Ten words
    # individually hand-verified against live Wiktionary, each a genuinely
    # DIFFERENT gap shape than a mechanical fix could close on its own:

    # "previous": absent from the raw parquet entirely (zero rows, same
    # shape as "consistency" -- not rare, just missing). Live Wiktionary:
    # "From Latin praevius." No further PIE connection stated.
    "previous": {"p": "Latin", "d": "Latin", "chain": ["Latin"], "prox_kind": "derived",
                 "root_lang": "Latin", "root_term": "praevius", "root_pie": False},

    # "mom": also absent entirely. Live Wiktionary: "Clipping of momma."
    # "momma" itself only has a HEDGE relation to "mama" in the raw data
    # (etymologically_related_to, not real ancestry), so the automated
    # pipeline correctly can't inherit through it on its own -- but "mama"
    # DOES have a real, already-verified chain in this project's own data
    # (Middle English mome <- Old English *mome <- Proto-West Germanic
    # *moma <- Proto-Germanic <- PIE *meh2-meh2, tagged is_onomatopoeic).
    # "mom" being a clipping of a word closely tied to "mama" is a
    # well-established, verifiable claim (matches this project's existing
    # "zoo" clipping precedent), not a guess -- inherits mama's exact
    # already-resolved chain.
    "mom": {"p": "Germanic", "d": "PIE", "chain": ["Germanic", "PIE"], "prox_kind": "derived",
            "root_lang": "Proto-West Germanic", "root_term": "*mōmā", "root_pie": True},

    # "package": also absent entirely. Live Wiktionary: "Equivalent to pack
    # + -age. Possibly influenced by Anglo-Latin paccagium or Old French
    # pacquage" -- the "possibly influenced by" is a hedge Wiktionary itself
    # doesn't commit to, so this inherits "pack"'s own already-resolved
    # chain (the part of the etymology actually asserted, not hedged) rather
    # than claiming an unconfirmed French/Latin connection.
    "package": {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"], "prox_kind": "derived",
                "root_lang": "Middle Dutch", "root_term": "pak", "root_pie": False},

    # "movie": the ONE case where a build-time fix is provably impossible, so
    # it earns a hand entry rather than waiting for a better builder.
    # Wiktionary's own dump entry is `{{suffix|en|""|ie}}` -- the base word is
    # an EMPTY STRING in the source data, so `moving` was never recorded and
    # there is nothing for any parser to recover. That left the whole word
    # resolving through the suffix `ie` alone (issues #19 and #22).
    # Live Wiktionary, checked 2026-07-30: "From moving (picture) +' -ie.
    # Attested since at least 1912 (if not 1908), originally in American
    # English." So the ancestry runs through `move`, whose own chain is
    # already fully verified in this project's database: English move <-
    # Middle English moven <- Old Northern French mover <- Old French mouver
    # <- Latin moveo <- PIE *m(y)ewh1-. Inherits that exact resolved chain --
    # the same "a clipping/derivation of a word with real data is a verifiable
    # claim, not a guess" precedent as "zoo" and "mom" above.
    # Deepest Root reads Latin, not PIE, because a root is a citation and not
    # a donor -- matching what `move` itself already reports.
    "movie": {"p": "French", "d": "Latin", "chain": ["French", "Latin"], "prox_kind": "derived",
              "root_lang": "Latin", "root_term": "moveō", "root_pie": True},

    # "incident": bare has_root PIE stub in the raw data (issue #14 shape).
    # Live Wiktionary: "from Middle French incident, from Latin incidens...
    # from in- + -cido, the combining form of cado ('to fall')," explicitly
    # categorized under PIE root *keh2d-.
    "incident": {"p": "French", "d": "PIE", "chain": ["French", "Latin", "PIE"], "prox_kind": "borrowed",
                 "root_lang": "Latin", "root_term": "cadō", "root_pie": True},

    # "expert": same bare-stub shape. Live Wiktionary: "Inherited from Middle
    # English expert, derived from Old French expert, espert, from Latin
    # expertus... from ex- + *-perior." PIE root (*per-) appears only in the
    # page's CATEGORY tags, not the main etymology prose -- per this
    # project's standing rule (only surface a PIE connection when the word's
    # own recorded chain states it explicitly, never inferred from a
    # category tag), root_pie stays False here.
    "expert": {"p": "French", "d": "Latin", "chain": ["French", "Latin"], "prox_kind": "borrowed",
               "root_lang": "Latin", "root_term": "expertus", "root_pie": False},

    # "metaphor": same bare-stub shape. Live Wiktionary: "From Middle French
    # metaphore, from Latin metaphora, from Ancient Greek metaphora, from
    # metaphero ('to transfer')." PIE root (*bher-) again only in category
    # tags, not the main prose -- root_pie False for the same reason as
    # "expert".
    "metaphor": {"p": "French", "d": "Greek", "chain": ["French", "Latin", "Greek"], "prox_kind": "borrowed",
                 "root_lang": "Ancient Greek", "root_term": "μεταφορά", "root_pie": False},

    # "adult": same bare-stub shape. Live Wiktionary: "From French adulte,
    # from Latin adultus... perfect passive participle of adolesco." PIE
    # roots again only in category tags (*h2el-, *h2ed-), not main prose --
    # root_pie False, same reasoning as "expert"/"metaphor".
    "adult": {"p": "French", "d": "Latin", "chain": ["French", "Latin"], "prox_kind": "borrowed",
              "root_lang": "Latin", "root_term": "adultus", "root_pie": False},

    # "puppy": same bare-stub shape. Live Wiktionary: "From earlier puppie
    # ('a woman's pet dog'), of uncertain origin, but probably from Middle
    # English *puppee, *poupee, from Old French poupee, popee ('a doll;
    # puppet')." Wiktionary's own hedge ("of uncertain origin, but
    # probably") is softer than a flat assertion, but still the
    # best-documented path stated on the page, not a guess of our own.
    "puppy": {"p": "French", "d": "French", "chain": ["French"], "prox_kind": "borrowed",
              "root_lang": "Old French", "root_term": "poupée", "root_pie": False},

    # "presence": raw data has ONLY etymologically_related_to (hedge, not
    # ancestry) rows -- no entry at all in `words`. Live Wiktionary: "Through
    # Old French presence, from Latin praesentia."
    "presence": {"p": "French", "d": "Latin", "chain": ["French", "Latin"], "prox_kind": "derived",
                 "root_lang": "Latin", "root_term": "praesentia", "root_pie": False},

    # "familiar": bare has_root PIE stub. Live Wiktionary: "Middle English
    # familiar, familier, from Latin familiaris" -- no French/Anglo-Norman
    # intermediate stage named. The page's PIE tree (*dheh1-) is explicitly
    # labeled as belonging to the PORTUGUESE section of the same page, not
    # English -- confirmed by reading the actual page structure, not
    # assumed, and root_pie is False here specifically because of that
    # mislabeling risk. Fixing this also fixes "unfamiliar" for free (it
    # cites "familiar" as its root via has_prefix_with_root, and
    # corrections.py is applied before the inheritance patches run).
    "familiar": {"p": "Latin", "d": "Latin", "chain": ["Latin"], "prox_kind": "borrowed",
                 "root_lang": "Latin", "root_term": "familiāris", "root_pie": False},

    # "unless": absent entirely, and -- verified before assuming otherwise --
    # NOT actually a live "un" + "less" compound despite the spelling.  Live
    # Wiktionary: "From Middle English unlesse, earlier on lesse (modern on
    # + less)... The quality of negation in the word and the lack of stress
    # changed on to un-." A single native English-internal formation, not a
    # borrowing and not a transparent modern compound (compounds.py would be
    # the wrong mechanism -- it would literally fabricate the folk etymology
    # this correction exists to avoid).
    "unless": {"p": "Germanic", "d": "Germanic", "chain": ["Germanic"], "prox_kind": "inherited",
               "root_lang": "Middle English", "root_term": "unlesse", "root_pie": False},
}

# Hub words EXCLUDED from convert_wikt.py's root-inheritance patches
# (_patch_root_stubs / _extract_auto_compounds), separate from WORD_CORRECTIONS
# above -- these are cases where the term_id's OWN correct standalone answer
# (left untouched here) is a genuinely different sense than the one derived
# words actually need, so no single WORD_CORRECTIONS entry could serve both
# purposes without being wrong for one of them. Verified against live
# Wiktionary 2026-07-24 (found via the same hub-word audit as tag/auto
# above):
#   - "logy": the term_id's real, correct standalone answer is the Dutch-
#     derived adjective ("sluggish, lethargic", from Dutch "log") -- that's
#     genuinely correct for anyone looking up "logy" itself. But dozens of
#     "-logy" derived words (the Greek-derived combining form, as in
#     "biology") point to this SAME term_id for their root, and the source
#     data has NO ancestry edge at all for that Greek sense under this
#     term_id (only an `etymologically_related_to "-logy"` cross-reference,
#     not real ancestry) -- there's nothing correct to inherit from here for
#     that purpose.
#   - "poly": similarly, the term_id's only real ancestry edge is an
#     unrelated Latin botanical plant name (*polium*); the "poly-" (many)
#     Greek combining form used by dozens of derived words has no ancestry
#     data recorded under this term_id either.
# Both left as honestly Unknown for the derived words that would otherwise
# have inherited the wrong sense, per CLAUDE.md rule 2 -- no guessing at a
# chain this term_id's own data doesn't support.
HUB_EXCLUSIONS = {"logy", "poly"}

# Checked for the Caribbean bucket and deliberately left alone: "limbo" (Joe's other
# example) resolves to Latin currently -- that's the "in limbo" theological
# sense; the dance-craze sense has no confidently documented origin and
# appears merged into the same entry (case-merge, issue #5), not something
# to force into Caribbean without real evidence. "rum" was NOT touched --
# Wiktionary itself calls its origin genuinely uncertain among several
# competing theories (Dutch, Romani, Latin), and the Caribbean connection is
# about where "rumbullion" was first attested, not a documented donor
# language -- inventing a confident Caribbean answer would be guessing.

# Checked in pass 5 and left alone as genuine, documented connections (some
# surprisingly interesting): date (fruit sense, Semitic-adjacent per a
# documented if hedged Arabic/Hebrew theory), rose (real Old Persian/Sanskrit
# root), race (a disputed but Wiktionary-documented Arabic theory -- academic
# uncertainty, not a pipeline collision), mole (the culinary sauce sense
# really is Nahuatl/Indigenous American -- another real sense-merge like
# "tong"), cash (historical coin sense really is Tamil/Sanskrit), mate
# (checkmate sense really is Persian, "shah mat"), risk (a documented if
# disputed Arabic theory), caravan (genuinely Persian), talisman (genuinely
# part-Arabic), mandarin (genuinely Sanskrit via Malay/Portuguese), tulip
# (genuinely Persian via Ottoman Turkish, doublet of "turban"), medicine (the
# extended "Indigenous magic" sense really is an Ojibwe calque), compound
# (the enclosure sense really is Malay), migraine (a hedged but documented
# Egyptian calque theory), apricot (genuinely Arabic via Catalan), genie
# (genuinely part-Arabic via French), musk (genuinely Sanskrit), loot
# (genuinely Hindi/Sanskrit), check/checkmate (genuinely Persian, "shah").
# ~40 of the original 81 scan hits (mostly rarer/technical words --
# azimuth, saga, millet, rugby, turban, háček, ganges, etc.) were not
# individually checked this pass.

# Checked in pass 4 and left alone: "jute" is a genuine Bengali loanword
# (Indo-Iranian bucket is correct); its "deepest" bucket showing Germanic is
# a separate, already-documented issue (known issue #2, chain ordering), not
# this collision bug -- not touched here.
# The other ~53 pass-4 hits (place names, surnames, and Jewish/Slavic
# cultural terms like Herzegovina, Stalin, Pasternak, mohel, challah, tsar,
# commissar, feldscher, etc.) were judged plausible on their face and not
# individually verified -- lower priority since they're rare in typical
# English prose compared to the everyday words above.

# Checked in pass 3 and left alone as genuinely correct real loanwords:
#   erekiteru, freeter, ponzu, randoseru (Japanese) -- kurus, oda (Turkish) --
#   preman, proa, semur (Indonesian/Malay) -- deel (Mongolian, bucketed
#   Turkic by this project's existing scheme).
# Checked and left alone as genuine sense-merges (issue #5, not #6 -- two
# real different-origin senses collapsed into one entry, so no single bucket
# is "the" right answer): cun (Germanic verb + Chinese unit of length), ming
# (Old English + Chinese "fate"), ou (Hawaiian bird + Afrikaans "guy"), sate
# (Old English "satisfy" + Malay "satay").
# Checked and left alone as UNVERIFIABLE: betawi (Wiktionary page 404s --
# doesn't currently exist), wie (no English-language section on the page as
# of 2026-07-22, though our database has an entry -- may reflect drift since
# etymology-db's Dec-2023 snapshot).
# This closes out all 37 words the pass-2 scan flagged.

# Scanned but deliberately NOT corrected -- verified as either genuinely
# correct or too ambiguous to hand-fix without more care:
#   "aa"   -- the lava term really is a Hawaiian loanword; Austronesian is right.
#   "tong" -- two real senses merged into one entry (the tool, Germanic; a
#             real Cantonese-derived secret-society sense, East Asian) --
#             this is known issue #5 (case/sense-merge noise), not #6.
# ~24 more words matched the scan's suspicion signature but weren't
# individually verified yet (mostly rare loanword-shaped terms like
# "randoseru", "ponzu", "freeter" that are plausibly genuine and low-impact
# for typical English text) -- see CLAUDE.md known issue #6 for the full list
# and status.
