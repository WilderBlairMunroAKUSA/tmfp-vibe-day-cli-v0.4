# TMFP Vibe Day CLI v0.4

**Vibe-Inventing World Peace | Day N of ???**

A local-first, zero-mandatory-Python-dependency CLI (Python 3.10+, Git, macOS/Linux) for recording a livestream **as one addressable, provenance-bearing daily dataset**, with Git history and a Hugging Face-ready export for each observer-defined civil day.

The fundamental learning unit is **the daily dataset as an entity**, not a narrowly defined training triple and not necessarily one JSONL row. Every recorded member, artifact, event, source link, and context inquiry belongs to that entity and may in turn be queried as an entity. Its historical world context is partly represented and partly open to further research. The recorder is not the physical world and cannot preserve all of an Individual's experience.

## Minimal first-stream workflow

Unzip and enter this folder. OBS Studio, Hugging Face, and GitHub accounts are *not required* for local recording.

```bash
# One-time setup. Use a new workspace to avoid changing sealed v0.3 archives.
python3 tmfp.py --home ~/tmfp-vibe init --timezone America/Anchorage

# Start a session (the first dataset will be Day 1 of ???).
python3 tmfp.py --home ~/tmfp-vibe start \
  --mode LIVE_WORKBENCH --topic 'Vibe-Inventing World Peace' \
  --address 'aurora-future,wilder-present'

# A spontaneous annotation.
python3 tmfp.py --home ~/tmfp-vibe mark \
  'One actual piece at a time.' --key spoken_reflection

# Arbitrary nested experience data; no expectation/outcome semantics required.
python3 tmfp.py --home ~/tmfp-vibe member --key world_piece \
  --value-json '{"piecebrain":{"activity":"prototype"},"pieceprocess":["observe","revise"],"piecespace":{"source":"workbench"}}'

# Record contextual provenance associated with the day dataset.
python3 tmfp.py --home ~/tmfp-vibe context --key origin \
  --value 'Livestream workbench; author-supplied record' \
  --source-ref 'https://example.org/REPLACE-WITH-YOUR-SOURCE'

# A learning entity or human can record a need for missing context.
python3 tmfp.py --home ~/tmfp-vibe need \
  'Which original document defined this term?' --source-hint 'Look in project archive'
# Save the printed need:... ID. Later:
python3 tmfp.py --home ~/tmfp-vibe answer 'need:PRINTED_ID' \
  --value 'Found in the manuscript' --source-ref 'piece:SOURCE_ID'

# Register a source: small file copied + hashed; large stream replay: pointer only.
python3 tmfp.py --home ~/tmfp-vibe add --file ./README.md \
  --key reference_file --description 'Current tool documentation'
python3 tmfp.py --home ~/tmfp-vibe add \
  --uri 'https://www.youtube.com/watch?v=REPLACE_ME' \
  --key replay --kind video --description 'Livestream replay (unverified URL)'

# Optional manually observed recording time alignment; not frame-exact synchronization.
python3 tmfp.py --home ~/tmfp-vibe anchor \
  --recording 'piece:REPLAY_ID' --media-time-ms 2500

# Optional outcome-prediction experiment (NOT the basic meaning of Q:K:V).
python3 tmfp.py --home ~/tmfp-vibe expect \
  --q 'Running a test' --k 'I expect it to pass'
# Later, referencing the printed experience:... ID:
python3 tmfp.py --home ~/tmfp-vibe resolve 'experience:PRINTED_ID' \
  --v 'The test failed'

python3 tmfp.py --home ~/tmfp-vibe stop
python3 tmfp.py --home ~/tmfp-vibe seal
python3 tmfp.py --home ~/tmfp-vibe verify
python3 tmfp.py --home ~/tmfp-vibe export-hf
python3 tmfp.py --home ~/tmfp-vibe export-corpus
python3 tmfp.py --home ~/tmfp-vibe status
```

**OBS:** Add a Text (FreeType 2) source using **Read from file** at `~/tmfp-vibe/obs/current.txt`. It shows episode title, mode, addressee, session, and topic. It updates when CLI commands run, not continuously. Run `tick` periodically if a long session crosses a day boundary. Sessions may span days, but each local civil day gets its **own dataset**.

**Day numbering:** numbered in *creation order*, starting with `--first-day-number` (default 1). Each day's number is stored in `day.json` and `dataset.json`. Creating backfilled dates out of order does not renumber earlier days. To assign Day 42 as your first day, use `init --first-day-number 42`. `--date` is supported for deliberate backfill; it does **not** falsify the UTC capture timestamp.

## The structure we are recording

**The day itself is `Q`: an addressable entity or query-of-interest.** It is associated with historical, partially knowable `P` (world/provenance context) and an indefinitely extensible set of nested K:V records. Any value can point to another Q. The naming analogy is deliberate and is not an assertion that JSON keys are the learned keys inside Transformer attention.

```text
P: world/historical/provenance context (partially recorded, partly researchable)
  |
  +-- Q: tmfp:dataset:day:0001:YYYY-MM-DD
       |-- dataset.json: identity, title, parent, declared context
       |-- members.jsonl: arbitrary structured K:V, nested OXI, subentities
       |-- contexts.jsonl: declared contextual/provenance associations
       |-- context_requests.jsonl: outstanding inquiries and later answers
       |-- pieces.jsonl: artifact refs / spoken annotations / local hashes
       |-- events.jsonl: event timeline, session, time since session start
       |-- relations.jsonl: relationships across records and days
       +-- experiences.jsonl: OPTIONAL prediction/expectation/outcome journal
```

`expect`/`resolve` from v0.3 are retained, but their `q`, `k`, `v` fields are **task-specific legacy labels**. Their `Q=world moment / K=expectation / V=outcome` interpretation is *not* the definition of generic relational K:V in this release. The generic `member` command is the primary new recording primitive.

## What is exported?

The daily Git repository is `~/tmfp-vibe/days/tmfp-YYYY-MM-DD/`.

The Hugging Face-ready directory is `~/tmfp-vibe/exports/YYYY-MM-DD/`. **One such directory is intended as one HF dataset repository**, with multiple named configurations:

| Config | Meaning |
|---|---|
| `datasets` (default) | **One row** naming the entire day as a query-entity, including its member references and verified index snapshot |
| `members` | Universal time-ordered representation of record contents as addressable K:V data |
| `lm_chunks` | Contextualized JSON text chunks for ordinary causal next-token learning |
| `kv` | Original generic `member` journal, preserving any nested JSON values |
| `contexts` | Explicit provenance/contextual annotations |
| `context_requests` | Missing-context questions and subsequent researched answers |
| `pieces` / `events` / `relations` | Original, structured source journals |
| `experiences` | Optional, append-only expectation/outcome journal |
| `qkv_predictions` | Optional joined supervised prediction view, when both days are sealed |
| `qkv` | Backward-compatible alias for `qkv_predictions`; not generic QKV nor Transformer internals |
| `days` | Backward-compatible day index |

Some configurations are omitted when empty. **All views have `full` only; no train/test split is asserted.** `lm_chunks` are token-budget-friendly slices of a **single day entity**, not independent physical samples or training/evaluation partitions. Each chunk repeats the root dataset metadata and contains complete recorded members. If a single member is large, one chunk may exceed the target character count. For long documents/assets, use `add` pointers and ingest those separately under explicit review.

The longitudinal export `~/tmfp-vibe/exports/corpus/` contains one day-entity row per verified daily dataset, `series_members` binding the days to the parent series, plus cross-day relations, contextual records and resolved optional prediction tasks. It is an **index**, not a monolithic replacement for individual daily datasets.

Example: inspect dataset metadata and source members without installing Hugging Face packages:

```bash
python3 -m json.tool ~/tmfp-vibe/days/tmfp-YYYY-MM-DD/dataset.json
head -n 1 ~/tmfp-vibe/exports/YYYY-MM-DD/data/datasets.jsonl
head -n 1 ~/tmfp-vibe/exports/YYYY-MM-DD/data/lm_chunks.jsonl
```

For an optional Hugging Face local load: `pip install datasets`, then `load_dataset('json', data_files='path/to/lm_chunks.jsonl', split='train')`. For Hub datasets: `load_dataset('YOUR_USER/DAY_DATASET', 'lm_chunks', split='full')`. **No training is performed by this CLI.** See [TRAINING.md](TRAINING.md).

## Publishing (deliberate, manual)

The intended format is a **separate HF dataset repo each day**. Prepare the local export, read its `README.md` and content, inspect the recorded objects, then publish. GitHub day repos are an optional, separate provenance mirror. For example:

```bash
# Remote operations NOT attempted by included tests.
python3 tmfp.py --home ~/tmfp-vibe publish-hf \
  --repo YOUR_USER/vibe-inventing-world-peace-day-0001

# Public publication requires an explicit human review affirmation:
python3 tmfp.py --home ~/tmfp-vibe publish-hf \
  --repo YOUR_USER/vibe-inventing-world-peace-day-0001 \
  --public --reviewed

python3 tmfp.py --home ~/tmfp-vibe publish-github --owner YOUR_GH_NAME

# After several verified days:
python3 tmfp.py --home ~/tmfp-vibe publish-hf --corpus \
  --repo YOUR_USER/vibe-inventing-world-peace-index
```

`publish-hf` needs `pip install huggingface_hub` plus `hf auth login`. `publish-github` needs `gh auth login`. **Private by default** for newly created repos. Existing remote repo visibility is not changed by a later publish. The `--reviewed` flag affirms human review; it is not a privacy scanner, rights clearance, consent record, or security assessment. See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

**No automated scraping, model inference, transcript extraction, training, device recording, OBS control, GitHub publication, or HF publication is triggered merely by using `start` or `mark`.** The CLI is a foundation for those future adapters. Remote URIs remain unverified pointers. Local file import is limited to 5 MiB per artifact and is content-addressed by SHA-256.

## Snapshot and lineage guarantees

- Daily journals are appended to and persisted under one Git repository per day.
- `checkpoint` commits an intermediate state; `seal` computes the domain-separated Merkle hash of tracked managed local files (excluding the manifest) and commits it.
- `verify` checks the hashes and Git cleanliness; `verify --ancestors` additionally checks the preceding recorded day snapshot when available.
- New records added after `seal` make verification fail until you `seal` again. A later re-seal changes the snapshot root; **earlier public snapshots are not silently equivalent to later ones**, and successor lineage may require explicit reconciliation.
- For v0.3 workspaces, original day repositories are readable without rewriting their immutable history. New days created with v0.4 have the new metadata and journals. New members attached to older v0.3 days are treated as new edits requiring re-sealing; consider preserving original sealed days untouched.
- Local file checksums prove integrity of bytes in this index, not truth, copyright ownership, participant consent, verifiable UTC or permanence of remote media.

## Test locally

```bash
python3 -m unittest discover -v -s . -p 'test_tmfp*.py'
```

Tests use disposable Git repos and make no network publication calls. Run `bash examples/demo.sh` for a completely disposable end-to-end demo; it prints the exported dataset location.

**One actual piece at a time. The dataset is an addressable piece of the recorded world; the model chooses how to learn from it.** ☮️
