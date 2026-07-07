#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

if [[ ! -f config.yaml ]]; then
  cp config.yaml.example config.yaml
fi

python - <<'PY'
from app.config import load_settings
load_settings().ensure_dirs()
print("BookForge install complete.")
PY
