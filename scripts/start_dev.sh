#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pushd backend >/dev/null
uvicorn main:app --reload &
BACKEND_PID=$!
popd >/dev/null

pushd frontend/session-app >/dev/null
npm install
npm run dev -- --host &
SESSION_PID=$!
popd >/dev/null

pushd frontend/admin-app >/dev/null
npm install
npm run dev -- --host &
ADMIN_PID=$!
popd >/dev/null

trap 'kill $BACKEND_PID $SESSION_PID $ADMIN_PID' EXIT
wait
