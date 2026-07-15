#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf '\n[1/2] Setting up the FastAPI backend...\n'
python3 -m venv "$ROOT_DIR/backend/.venv"
"$ROOT_DIR/backend/.venv/bin/python" -m pip install --upgrade pip
"$ROOT_DIR/backend/.venv/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"

printf '\n[2/2] Installing frontend dependencies...\n'
cd "$ROOT_DIR/frontend"
npm install

printf '\nSetup complete. Start both services with:\n  ./scripts/dev.sh\n\n'
