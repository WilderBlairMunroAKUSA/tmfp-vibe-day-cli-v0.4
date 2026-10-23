# TMFP Vibe Day v0.4 — schema contract

## Identities and nesting

**Daily dataset** (`dataset.json`) is the root addressable entity for one observer-defined day. `dataset_id`, `day_id`, `day_number`, `title`, `parent_query`, declared `context`, and `provenance` are fixed upon day creation. In this design, `Q` describes a **query/entity of interest**, not necessarily a question or a prediction. `P` refers to the surrounding historical context of that entity; recording is always partial. A daily dataset can itself be the value associated with a key in a containing longitudinal series. `dataset.json` is identity metadata, not the complete dataset content; member relationships reside in append-only journals.

**Day** (`day.json`) adds timezone, observer-defined local civil date, creation UTC, predecessor sealed index pointer, snapshot scope, and immutable episode number. No claim is made that observer time or day boundaries are fundamental physics.

**Member** (`members.jsonl`) is the general primitive: `{id,dataset_id,day_id,utc,subject_id,key,value_json,kind,description,context_json,source_ref,assertion_status,evidence_status}`. `value_json` and `context_json` contain serialized JSON strings because tabular datasets often need stable column types; decoding restores arbitrary nested values. `subject_id` defaults to the day dataset; it may name another member, event, object, or external entity. `key` is a human-readable named relationship; keys are not necessarily unique. Historical ambiguity or conflicting assertions must remain representable. **This is not an internal Transformer key vector.**

**Context** (`contexts.jsonl`) is an append-only `{id,dataset_id,day_id,utc,subject_id,key,value_json,source_ref,description,assertion_status,evidence_status}`. It records declared world/provenance context or additional contextual research; a pointer is not proof of its referent.

**Context research** (`context_requests.jsonl`) is an append-only `request` and optionally later `answer` with shared `request_id`; questions may span days. CLI `need` does not automatically browse the web or resolve anything; CLI `answer` records a declared answer and optional source reference. Historical context is not overwritten when a later answer appears.

**Piece** (`pieces.jsonl`) records annotations or source artifacts with OXI-like content/pointer/identity distinctions; copied local objects are SHA-256-addressed under `objects/<sha256>`. Remote URLs are references only. `mark` and `add` retain their v0.3 semantics.

**Event** (`events.jsonl`) records CLI actions, UTC timestamp, active session ID, elapsed milliseconds, speaker, intended addressee and focus, referent, and structured detail as `detail_json`. Elapsed milliseconds are session-clock estimates, **not** frame-exact video timestamps. `anchor` writes a member identifying one *manually asserted* correspondence between a recording's media timestamp and UTC.

**Relation** (`relations.jsonl`) declares subject–predicate–object links, including cross-day relations. Predicates are assertions, not automatically proven causal or epistemic relations.

**Prediction journal** (`experiences.jsonl`, backward-compatible v0.3) contains an append-only prior `expectation` entry and optional later `outcome` entry linked by `experience_id`. Here only, the legacy task labels mean Q=world moment, K=expected outcome, V=actual observed continuation. This is **not** the fundamental dataset Q/K/V ontology and does not map literally to internal attention query/key/value tensors. These examples are optional views and not required for recording a meaningful day.

## Derived projections

Each verified day exports *one dataset repository candidate* with:

- `datasets`: **one row per entire day**, including root entity and member references.
- `members`: a normalized, sortable union of generic members, contexts, source pieces, timeline events, relations, prediction journal entries and research questions/answers. All rows join by `dataset_id`; each retains a source ID.
- `lm_chunks`: contextualized JSON text for self-supervised causal next-token modeling; derived, reproducible from the day journals. Model input is still token IDs after tokenization. No explicit 'truth' target is assigned by the serialization itself.
- Raw source tables (`kv`, `contexts`, `context_requests`, `events`, `pieces`, `relations`, `experiences`) when present.
- `qkv_predictions` and backward-compatible `qkv` only when both expectation and outcome days have verified snapshots. These represent an *optional* supervised training objective, not the generic relational substrate.
- `days` for backward-compatible index consumers.

All configurations expose `full`, not train, validation or test. Train/test splits require independent experimental design; splitting records from one day or one shared event history can produce serious leakage.

`corpus` exports index records of sealed daily datasets, including `series_members` where the series is a containing parent and the day dataset is a nested value. Source datasets are separate Git repositories with independent SHA-256 Merkle snapshots. No training-data rights or licensing permissions are inferred from this structure.

## Practical caveats

- `Q`, `K`, `V`, and `P` are modeling vocabulary, **not** literal learnable Q/K/V projection matrices in a Transformer.
- A JSON value can itself refer to another dataset, file or physical entity; the record does not imply existence of a verified referent.
- The physical event is not the same as the recorded artifact. Provenance assertions are defeasible, and re-interpretation should append new context rather than rewrite history.
- Context retrieval, internet research, model fine-tuning, ingesting video/audio, alignment to encoder timecodes, truth evaluation, and consent processing are outside the v0.4 CLI.
- `lm_chunks` split on complete member boundaries to bound typical text size; a single large member may exceed the target size. Streaming massive JSON records and distributed high-throughput logging are not yet supported.
- The `day_number` is the sequence of *created datasets*, not derived by re-sorting past dates. Public-facing episodes read `Vibe-Inventing World Peace | Day N of ???`.
