#!/usr/bin/env bash
set -euo pipefail

# Run the classroom lab for public/classroom access on 0.0.0.0:80.
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python3"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtual environment not found. Create it first:"
  echo "  cd $ROOT_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

export HOST=0.0.0.0
export PORT=80
export FLASK_ENV=production

cd "$ROOT_DIR"
exec "$VENV_PYTHON" app.py