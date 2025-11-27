#!/usr/bin/env bash
set -euo pipefail

# Run from repo root even if invoked elsewhere
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

export PYTHONPATH=$REPO_ROOT
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
