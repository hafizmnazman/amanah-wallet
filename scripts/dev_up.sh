#!/usr/bin/env bash
# Starts Anvil with lane A's fixture, then the auditor, the sentinel and the API (CLAUDE.md).
# Options are in scripts/dev_up.py. PYTHON picks the interpreter; the default is .venv/bin/python.
set -euo pipefail
python="${PYTHON:-}"
# A relative path is taken from where the script was called, before the cd below
if [[ "$python" == */* && "$python" != /* ]]; then python="$PWD/$python"; fi
cd "$(dirname "$0")/.."
[ -n "$python" ] || python=.venv/bin/python
[ -x "$python" ] || command -v "$python" > /dev/null || python=python3
exec "$python" scripts/dev_up.py "$@"
