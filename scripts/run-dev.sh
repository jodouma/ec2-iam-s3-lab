#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python3"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtual environment not found. Create it first:"
  echo "  cd $ROOT_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

export HOST=127.0.0.1
export PORT=5000
export FLASK_ENV=development

cd "$ROOT_DIR"
exec "$VENV_PYTHON" app.py