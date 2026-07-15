#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  echo "Backend virtual environment not found. Run ./scripts/setup.sh first."
  exit 1
fi

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Frontend dependencies not found. Run ./scripts/setup.sh first."
  exit 1
fi

cleanup() {
  trap - INT TERM EXIT
  kill 0 2>/dev/null || true
}
trap cleanup INT TERM EXIT

printf 'Starting backend: http://localhost:8000\n'
(
  cd "$ROOT_DIR/backend"
  "$BACKEND_PYTHON" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &

printf 'Starting frontend: http://localhost:5173\n'
(
  cd "$ROOT_DIR/frontend"
  npm run dev
) &

wait
