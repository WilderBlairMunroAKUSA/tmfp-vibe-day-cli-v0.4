#!/usr/bin/env bash
# Offline end-to-end demonstration of v0.4; never contacts a network destination.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/tmfp-vibe-demo.XXXXXX")"
CLI="$HERE/tmfp.py"
run() { python3 "$CLI" --home "$WORK" "$@"; }
run init --timezone UTC
run start --mode EXPERIMENT --address aurora-future --topic 'Vibe-Inventing World Peace'
run mark 'The first day is itself an addressable piece of experience.' --key commentary
MEMBER="$(run member --key experiment --value-json '{"situation":"prototype","iterations":1,"observation":{"status":"recorded"}}')"
run context --subject "$MEMBER" --key provenance --value 'Human-declared demonstration'
NEED="$(run need 'Where was this model first described?' --subject "$MEMBER")"
run answer "$NEED" --value 'This is only a demonstration record'
run anchor --recording 'piece:example-recording-ref' --media-time-ms 1000
PRED="$(run expect --q 'Dry run' --k 'CLI works')"
run resolve "$PRED" --v 'CLI recorded the test outcome'
run stop
run seal
run verify
run export-hf
run export-corpus
run status
printf '\nDemo workspace (not deleted): %s\n' "$WORK"
printf 'Inspect the exports directory above. No uploads occurred.\n'
