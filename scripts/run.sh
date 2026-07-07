#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run ./scripts/install.sh first."
  exit 1
fi

source .venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port 8787
