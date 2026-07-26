-- Canonical word database. Single source of truth for the DDL; applied by
-- build_etymology_db.py. Read only through etymology_db.py.
--
-- WHY THIS EXISTS (2026-07-25): the per-word data layer had grown into five
-- JSON files with three different key conventions, built by four scripts from
-- two sources. The paragraph analyzer and the Word Search read DIFFERENT
-- files, and disagreed in eleven measurable ways -- 65,665 words carried two
-- independently-derived chains, ~75 hand-corrected words had a corrected
-- analyzer answer and an uncorrected tree, and `mile` rendered a false edge.
--
-- The fix is structural, not disciplinary: move every fallback decision from
-- QUERY time to BUILD time and store the outcome as rows. Looking a word up
-- becomes one indexed SELECT with no branching, so two features calling the
-- same non-branching function cannot disagree. That is goal 1 proved by
-- construction rather than policed by tests.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- provenance
-- Every fact records where it came from. That is what lets a source with
-- unclear reuse terms be filtered out later without archaeology.
CREATE TABLE IF NOT EXISTS source (
  source_id     INTEGER PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,   -- 'wiktextract.templates', 'curated', ...
  kind          TEXT NOT NULL,          -- extract | curated | derived
  licence       TEXT NOT NULL,          -- 'CC-BY-SA-3.0', 'CC-BY-4.0', 'none-stated'
  -- additive_only=1 means: may contribute word_relation / word_fact rows, but
  -- may NEVER supply an ety_node/ety_edge or win reconciliation. That single
  -- rule is what keeps "exclude the risky sources" a runtime filter instead of
  -- a rebuild -- nothing structural depends on their rows being present.
  additive_only INTEGER NOT NULL DEFAULT 0,
  version       TEXT,
  url           TEXT,
  ingested_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_precedence (
  source_id INTEGER PRIMARY KEY REFERENCES source(source_id),
  priority  INTEGER NOT NULL          -- lower wins; reconciliation is DATA
);

-- ------------------------------------------------------------------ language
-- ~111 curated rows (languages.csv). Bounded by number of languages, not by
-- vocabulary -- unlike the 189-entry irregular-verb table deleted 2026-07-25,
-- this does not grow as the dictionary grows. Top 50 rows cover 95.5% of all
-- chain steps.
--
-- era_start IS the depth ordering. There is deliberately no separate rank
-- column: a second field encoding the same ordering is a second thing that
-- can disagree with the first. It replaces convert_wikt._DEPTH_HINT, whose
-- tiers were only comparable within one family -- the bug that made `mile`
-- credit Proto-West Germanic with descent from PIE.
CREATE TABLE IF NOT EXISTS language (
  lang_id          INTEGER PRIMARY KEY,
  name             TEXT NOT NULL UNIQUE,
  wikt_code        TEXT UNIQUE,
  bucket           TEXT NOT NULL,
  family           TEXT,
  era_start        INTEGER NOT NULL,   -- year; negative = BCE
  era_end          INTEGER NOT NULL,   -- 9999 = still spoken
  era_label        TEXT NOT NULL,      -- what the timeline actually prints
  era_certain      INTEGER NOT NULL DEFAULT 1,  -- 0 => render with "c."
  is_proto         INTEGER NOT NULL DEFAULT 0,
  is_english_stage INTEGER NOT NULL DEFAULT 0,
  glottocode       TEXT,               -- join key to Glottolog / CLDF datasets
  source_url       TEXT
);
CREATE INDEX IF NOT EXISTS language_family ON language(family, era_start);

-- Names AND codes resolve to one language. Shape C parses rendered trees that
-- use display names ("Old English"), while templates use codes ("ang").
CREATE TABLE IF NOT EXISTS language_alias (
  alias   TEXT PRIMARY KEY COLLATE NOCASE,
  lang_id INTEGER NOT NULL REFERENCES language(lang_id)
);

-- -------------------------------------------------------------------- word
-- ONE ROW PER WORD -- identity only. Facts hang off it, so a new kind of
-- information is new rows, never a migration.
CREATE TABLE IF NOT EXISTS word (
  word_id    INTEGER PRIMARY KEY,
  headword   TEXT NOT NULL UNIQUE,     -- exact-case canonical spelling
  key_lower  TEXT NOT NULL,            -- NOT unique: she/She both fold here
  status     TEXT NOT NULL,            -- resolved | stub | none
  ety_count  INTEGER NOT NULL DEFAULT 0,
  -- Denormalised render cache so the hot path is a single-row fetch. Always
  -- rebuildable from ety_node/ety_edge; never the source of truth.
  tree_json  TEXT,
  built_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS word_key_lower ON word(key_lower);

-- THE CASCADE, MATERIALIZED. This one table replaces, in a single indexed
-- query: three different case-fallback policies (each of which shipped a bug
-- -- went/Went, ran/Ran, and _lookup_tree_direct's removed capitalize()), the
-- inflection lookup, the derivational stemmer's precedence, ChainResolver's
-- retry loop, and resolve_tree's five-branch cascade.
--
-- The stemmer RULES stay in code as a build-time input; only their OUTCOMES
-- are stored, which is bounded -- one row per surface form that resolves.
-- Lookup passes BOTH the typed string and its lowercase form in one
-- `form IN (?,?)`, so the query stays branch-free while a capitalised
-- headword keeps its own reachable key: `March` hits the rank-5 verbatim
-- row, `march` only ever hits the rank-10 lowercase one. Without that row
-- every proper noun is shadowed by its common-noun twin.
CREATE TABLE IF NOT EXISTS surface_form (
  form      TEXT NOT NULL,             -- lowercased key, except kind='verbatim'
  word_id   INTEGER NOT NULL REFERENCES word(word_id),
  kind      TEXT NOT NULL,             -- verbatim|exact|case|inflection|derivation|correction
  rank      INTEGER NOT NULL,          -- 0 curated,5 verbatim,10 exact,30 caps,40 infl,50 deriv
  note      TEXT,                      -- 'plural of wolf'
  source_id INTEGER NOT NULL REFERENCES source(source_id),
  PRIMARY KEY (form, word_id, kind)
);
CREATE INDEX IF NOT EXISTS surface_form_lookup ON surface_form(form, rank);

-- --------------------------------------------------------- etymology graph
-- Multiple etymologies are separate rows, never merged. `bow` the weapon and
-- `bow` the bend are different histories and forcing them together would be a
-- lie; Wiktionary numbers them and so do we.
CREATE TABLE IF NOT EXISTS etymology (
  ety_id       INTEGER PRIMARY KEY,
  word_id      INTEGER NOT NULL REFERENCES word(word_id),
  -- This word's own 1..n slot. Deliberately NOT Wiktionary's etymology
  -- number: one numbered etymology can split into several narratives (`march`
  -- yields 5 trees from 3 numbers), so keying uniqueness on the source number
  -- silently discarded every tree after the first in each group.
  ordinal      INTEGER NOT NULL,
  label        TEXT,                   -- Wiktionary's etymology_number, for display
  pos_list     TEXT,
  shape        TEXT NOT NULL,          -- chain|fork|mixed|rendered|stub
  confidence   TEXT NOT NULL DEFAULT 'attested',
  head_node_id INTEGER,
  source_id    INTEGER NOT NULL REFERENCES source(source_id),
  UNIQUE (word_id, ordinal)
);
CREATE INDEX IF NOT EXISTS etymology_word ON etymology(word_id, ordinal);

CREATE TABLE IF NOT EXISTS ety_node (
  node_id   INTEGER PRIMARY KEY,
  ety_id    INTEGER NOT NULL REFERENCES etymology(ety_id),
  lang_id   INTEGER NOT NULL REFERENCES language(lang_id),
  term      TEXT,                      -- NULL = language-only step
  gloss     TEXT,
  is_head   INTEGER NOT NULL DEFAULT 0,
  is_root   INTEGER NOT NULL DEFAULT 0,
  source_id INTEGER NOT NULL REFERENCES source(source_id)
);
CREATE INDEX IF NOT EXISTS ety_node_ety  ON ety_node(ety_id);
-- Powers "what else descends from *deru-" -- the root-family queries that a
-- single JSON blob per word could never answer.
CREATE INDEX IF NOT EXISTS ety_node_term ON ety_node(lang_id, term);

CREATE TABLE IF NOT EXISTS ety_edge (
  ety_id    INTEGER NOT NULL REFERENCES etymology(ety_id),
  parent_id INTEGER NOT NULL REFERENCES ety_node(node_id),  -- the ANCESTOR
  child_id  INTEGER NOT NULL REFERENCES ety_node(node_id),  -- the DESCENDANT
  rel       TEXT NOT NULL,   -- inherited|borrowed|derived|calque|root|formed_from
  -- 'direct' renders a SOLID edge and may be traversed by chain/percentage
  -- code. 'related' renders DOTTED and is display-only. This is the third
  -- option that makes "no floating nodes" achievable without fabricating a
  -- lineage -- branch merging was tried and reverted twice precisely because
  -- the code only had "invent an edge" or "leave it floating".
  certainty TEXT NOT NULL DEFAULT 'direct',
  ordinal   INTEGER NOT NULL DEFAULT 0,   -- sibling order under a fork
  note      TEXT,
  source_id INTEGER NOT NULL REFERENCES source(source_id),
  PRIMARY KEY (ety_id, parent_id, child_id)
);
CREATE INDEX IF NOT EXISTS ety_edge_child  ON ety_edge(ety_id, child_id);
CREATE INDEX IF NOT EXISTS ety_edge_parent ON ety_edge(ety_id, parent_id);

-- ---------------------------------------------------------- senses & facts
CREATE TABLE IF NOT EXISTS sense (
  sense_id    INTEGER PRIMARY KEY,
  word_id     INTEGER NOT NULL REFERENCES word(word_id),
  ety_ordinal INTEGER,
  pos         TEXT,
  gloss       TEXT,
  ordinal     INTEGER NOT NULL DEFAULT 0,
  source_id   INTEGER NOT NULL REFERENCES source(source_id)
);
CREATE INDEX IF NOT EXISTS sense_word ON sense(word_id, ordinal);

-- ONE table for every NON-ANCESTRY word relation. This is what makes "just
-- add another source" true: false friends, root families and "surprising
-- relatives" are later a new `kind`, not a migration.
--
-- HARD RULE: ancestry code never reads this table. A cognate is a sibling,
-- not an ancestor, and letting one into a lineage fabricates descent. Three
-- modules currently enforce that by hand; here it is enforced by structure.
--
-- `kind` is assigned by the SOURCE'S OWN loader, never inferred generically:
-- UT Austin's *ag- page lists act/action/actor (derivatives) beside
-- axis/axle/aisle (true doublets), and only a loader that understands that
-- source can tell them apart.
CREATE TABLE IF NOT EXISTS word_relation (
  word_id       INTEGER NOT NULL REFERENCES word(word_id),
  kind          TEXT NOT NULL,   -- cognate|doublet|derived_term|synonym|antonym
                                 -- |descendant|hyponym|hypernym|meronym
                                 -- |coordinate|related|false_friend|root_family
  other_word_id INTEGER REFERENCES word(word_id),   -- when the other side is English
  lang_id       INTEGER REFERENCES language(lang_id),
  term          TEXT,
  gloss         TEXT,
  note          TEXT,
  ordinal       INTEGER NOT NULL DEFAULT 0,
  source_id     INTEGER NOT NULL REFERENCES source(source_id)
);
CREATE INDEX IF NOT EXISTS word_relation_fwd ON word_relation(word_id, kind);
CREATE INDEX IF NOT EXISTS word_relation_rev ON word_relation(other_word_id, kind);

-- Scalar per-word facts: frequency, first attestation, disputed, eponym...
-- Every future fact type lands here with zero schema churn.
CREATE TABLE IF NOT EXISTS word_fact (
  word_id    INTEGER NOT NULL REFERENCES word(word_id),
  key        TEXT NOT NULL,
  value_num  REAL,
  value_text TEXT,
  confidence TEXT NOT NULL DEFAULT 'attested',
  source_id  INTEGER NOT NULL REFERENCES source(source_id),
  PRIMARY KEY (word_id, key, source_id)
);
CREATE INDEX IF NOT EXISTS word_fact_key ON word_fact(key, value_num);

CREATE TABLE IF NOT EXISTS build_meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);
