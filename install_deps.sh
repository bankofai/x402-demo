#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ_FILE="$ROOT_DIR/requirements.txt"
VENV_DIR="$ROOT_DIR/.venv"
PY_BIN="$VENV_DIR/bin/python"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "requirements.txt not found: $REQ_FILE" >&2
  exit 1
fi

if [[ ! -x "$PY_BIN" ]]; then
  echo "Creating virtual environment at: $VENV_DIR" >&2
  python3 -m venv "$VENV_DIR"
fi

echo "Using Python: $PY_BIN" >&2
"$PY_BIN" -m pip install --upgrade pip
"$PY_BIN" -m pip install -r "$REQ_FILE"

# TypeScript client dependencies
TS_DIR="$ROOT_DIR/client/typescript"
if [[ -f "$TS_DIR/package.json" ]]; then
  echo ""
  echo "Installing TypeScript client dependencies..." >&2
  (cd "$TS_DIR" && npm install)
fi
