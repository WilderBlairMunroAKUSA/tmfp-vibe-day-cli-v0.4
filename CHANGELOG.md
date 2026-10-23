# Changelog

## v0.4.0 — daily dataset as primary relational entity

- Each new civil day receives an immutable day number and display title: **Vibe-Inventing World Peace | Day N of ???**.
- Introduced `dataset.json`: identity, parent series, contextual/provenance assertions and scope.
- New `member`: generic recursively structured K:V, arbitrary JSON values, optional nested subject/relative context.
- New `context`, `need`, `answer`: append-only assertions and later discoverable research needs.
- New `anchor`: manual video/media time to UTC anchors.
- New derived `datasets`, `members`, `lm_chunks` Hugging Face configurations and corpus `series_members` index. The whole day is the query-entity; HF tables are different projections of that one entity.
- Preserved v0.3 CLI's Git commit/Merkle manifest, source artifacts, events, OBS overlay, relations, and optional expectation/outcome journaling.
- Renamed original special-purpose joined prediction view to `qkv_predictions` (still exports `qkv` compatibility alias). Generic member keys/values are not interpreted as predicted expectations/outcomes.
- Public remote publishing now requires an explicit `--reviewed` acknowledgment, without pretending this performs consent/security scanning.
- Verified snapshot requirement on *both* days for including cross-day prediction training examples in a daily export.
- Older v0.3 day indexes can be **read** without rewriting source files; v0.4 new-day schema is distinct. No migration or reconstruction of old event times is performed automatically.

## v0.3.0 — previous implementation

- `expect` and `resolve`, timestamp-separated Q/K-before-V prediction records and cross-day supervised view.
- Integrity and Git snapshot chain, OBS overlay, Hugging Face daily and corpus exports.
