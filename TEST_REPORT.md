# Offline verification record — TMFP Vibe Day v0.4

The following end-to-end tests were executed individually or in small batches against `tmfp.py` using temporary Git workspaces. **All nine test methods passed**:

**Legacy continuity (4):** day rollover/OBS/piece capture/local hash/seal/verification/tamper detection; cross-day relations and ancestor seal checks; optional Q/K-before-V prediction journal and cross-day outcomes; empty-day export.

**New v0.4 behavior (5):** one day-root query entity with nested arbitrary JSON member, context and need/answer/recording anchors; monotonic day numbers and series membership; optional prediction projection excluded when prior day is unsealed; public-release review flag enforcement before any upload; many member records resolving to one root dataset identity.

A complete `unittest discover` invocation was attempted but hit the execution environment's command time limit before finishing. Subsequently, tests were run in smaller batches and the remaining methods completed successfully. This distinction matters: **there was no single completed full-suite command output**, although each test method was observed passing.

A disposable `examples/demo.sh` run also completed successfully: created Day 1, recorded 18 normalized member/event/context records, sealed and verified the source Git snapshot, exported a daily Hugging Face-ready dataset and a longitudinal index, and printed a valid `dataset_id`. No online publishing was performed.

The generated JSONL data files were inspected as valid JSON lines, and the source `tmfp.py` compiled with Python. The export README YAML configuration format was checked against current Hugging Face documentation, but **a real Hugging Face dataset load was not executed** because the `datasets` Python package is not installed in this environment. Authentication and live GitHub/Hugging Face uploads were not tested. This is a CLI prototype, not a hardened continuous-ingestion system.
