#!/usr/bin/env bash
# Load the OpenRouter key into the environment from ~/.openrouter (outside the
# repo - see .env comments for why). Run this before anything that needs the
# key: ./scripts/load_key.sh, or `source scripts/load_key.sh` in a shell.
#
# If OPENROUTER_API_KEY is already set, nothing happens - the environment wins,
# matching slice/config.py's precedence. If the event desk hands
# you a real key, export it directly or paste it into .env and skip this script.
set -euo pipefail
if [ -z "${OPENROUTER_API_KEY:-}" ] && [ -f "${HOME}/.openrouter" ]; then
    export OPENROUTER_API_KEY="$(tr -d '[:space:]' < "${HOME}/.openrouter")"
fi
