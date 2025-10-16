#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install . '.[dev]'
python -m playwright install chromium
echo "Dev setup complete. Use: source .venv/bin/activate"
