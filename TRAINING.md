# Training views — the same archived experience, different learning tasks

**Preserve the source; choose the training projection afterward.** The CLI does not train a model. It exports JSONL that can feed whichever model and optimizer are selected.

## 1. Ordinary self-supervised language modeling

Use `data/lm_chunks.jsonl`, where `text` is the selected day dataset's contextualized JSON representation. Tokenize `text` and train a causal LM on shifted tokens. Training learns to predict the next token of the *recorded representation*, including keys, values, and provenance context. There is no manually labelled truth requirement for this objective. You may instead serialize source `members` in a custom format if experiments show the default JSON is inefficient.

```python
# Optional: pip install datasets
from datasets import load_dataset
records = load_dataset("json", data_files="path/to/export/data/lm_chunks.jsonl", split="train")
for row in records:
    text = row["text"]
    # Feed text to the tokenizer/model training loop of your choosing.
```

**Important:** Hugging Face's JSON loader calls this split `train` here only as a local loading convention. The CLI itself has an unsplit `full` dataset and asserts no independent evaluation set. Never mistake a random per-chunk holdout for an independent experiment.

## 2. Context-aware entity retrieval

Use `data/datasets.jsonl` for the addressable root Q (dataset identity), `members.jsonl` for nested addressable K:V and event relationships, `contexts.jsonl` to supply P, and `context_requests.jsonl` to identify unresolved questions. A retrieval agent can query references, look up external context, append answers/provenance, and build a new training view. The CLI records requests and answers but does not browse or run an agent. Evidence needs evaluation.

## 3. Optional consequence prediction

Use `data/qkv_predictions.jsonl`. A row contains a `prompt` (earlier observed situation and expectation) and `completion` (later declared observed continuation). During supervised fine-tuning, ensure only target/completion tokens contribute to the intended loss, and ensure the model cannot see future outcomes through surrounding context. This older task-specific Q/K/V naming is unrelated to the generic K:V semantics of member records.

## Study design

Compare matched data volumes and training budgets across: (A) plain text descriptions, (B) recursively structured contextual JSON, and (C) explicit retrieval over member IDs and provenance. Test on held-out *days / time periods / systems*, not random overlapping fragments. Evaluate retrieval, prediction, provenance correctness, and unwanted leakage separately.

**Record what can actually be known:** the source snapshot, extraction code, context included or withheld, software/model version, sampling criteria, declared observation time and, where possible, independent outcome evidence. A plausible completion is not proof of physical truth. Next-token training is compatible with Transformers, state-space models, RNNs and other systems; changing the optimizer doesn't alter the archival format.
