# Review before publishing *each* daily dataset

The tool intentionally does **not** automate public publication. The `--public --reviewed` flags affirm that a responsible human reviewed this specific export; this does not automatically clear any risk.

- Inspect **all** exported `data/*.jsonl` tables, the `lm_chunks` serialized views, and `objects/` contents. Sensitive data can recur in several projections.
- Confirm rights to redistribute every file, quoted work, conversation export, image, or linked artifact. Public availability, CC0 status of a particular authored work, and permission to train on third-party materials are **different things**.
- Review participant and bystander consent before publishing identifying conversation text, voice, faces, screens, contact details, or personal details of others.
- Look for API keys, passwords, session cookies, private project paths, private chat excerpts, location and metadata embedded in source content. `.gitignore` is **not** a secret scanner.
- Confirm external URLs are appropriate to share; remote URLs are not verified by the CLI. Hashed local files prove only byte identity.
- Verify recording/OBS time offsets, noted gaps, transcription disclaimers, and any links to a session; they are **not** automatically frame-accurate.
- Verify the day was `stop`ped, then `seal`ed and `verify` passed. If content was added after sealing, seal again and recheck any predecessor-linked indexes.
- Confirm `data/qkv_predictions.jsonl` is described as **reported** outcomes, not independently established causal ground truth.
- Confirm the destination repository's actual visibility on GitHub/Hugging Face; `--public` does not change an **existing** remote's visibility.
- Review applicable platform policy and applicable local privacy and copyright obligations.
- Save independent backups of critical source media and primary recordings; the CLI's 5 MiB object limit and URL references do not archive livestream footage.

For daily episode naming, use: `Vibe-Inventing World Peace | Day N of ???` (the recorded `title` field). The publishing repository slug must use simple URL-safe characters such as `vibe-inventing-world-peace-day-0001`.
