# First livestream — short version ☮️

One observer-defined local day = **one addressable dataset** named **Vibe-Inventing World Peace | Day N of ???**. The day is Q; its recorded K:V members are the growing experience; contextual links P point to an incompletely recorded surrounding world.

## Before going live

In Terminal inside the unzipped package:

```bash
python3 tmfp.py --home ~/tmfp-vibe init --timezone America/Anchorage
```

In OBS, add a **Text (FreeType 2)** source → **Read from file** → `~/tmfp-vibe/obs/current.txt`.

## During the day

```bash
python3 tmfp.py --home ~/tmfp-vibe start --topic 'Vibe-Inventing World Peace'
python3 tmfp.py --home ~/tmfp-vibe mark 'Something worth timestamping'
python3 tmfp.py --home ~/tmfp-vibe member --key observation \
  --value-json '{"what":"interesting","refs":[]}'
python3 tmfp.py --home ~/tmfp-vibe need 'Where did this claim originate?'
```

If a session crosses midnight in the configured local time zone, run `tick` so it initializes the new day's dataset and refreshes the overlay. The tool doesn't automatically ingest audio/video; record those in OBS independently. Use `add --uri ...` after uploading a replay.

## End of day

```bash
python3 tmfp.py --home ~/tmfp-vibe stop
python3 tmfp.py --home ~/tmfp-vibe seal
python3 tmfp.py --home ~/tmfp-vibe verify
python3 tmfp.py --home ~/tmfp-vibe export-hf
python3 tmfp.py --home ~/tmfp-vibe status
```

Inspect `~/tmfp-vibe/exports/YYYY-MM-DD/` **before publication**. The default dataset config is `datasets` (one row representing the entire day). `members` are its addressable internals; `lm_chunks` are a self-supervised next-token-friendly JSON serialization. **All configs belong to the same single day dataset.**

When ready for public release, review [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), authenticate Hugging Face, then:

```bash
python3 tmfp.py --home ~/tmfp-vibe publish-hf \
  --repo YOUR_USER/vibe-inventing-world-peace-day-0001 \
  --public --reviewed
```

The tool does not grant copyright permission, verify consent, redact private content, or publish without that explicit remote command. If you edit after sealing, seal and verify again before export. See [README.md](README.md) for the complete interface.
