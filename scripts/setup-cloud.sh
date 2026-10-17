#!/usr/bin/env bash
# Prepare the outreach CLI without overwriting local inputs or credentials.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv_dir="${OUTREACH_VENV_DIR:-/workspace/.venvs/neil-agents}"
cd "$repo_dir"
python3 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --no-cache-dir -e .
if [ ! -e contacts.csv ]; then cp contacts.example.csv contacts.csv; fi
if [ ! -e me.md ]; then cp me.example.md me.md; fi
"$venv_dir/bin/python" -m pip check
"$venv_dir/bin/outreach" draft --limit 1 --dry-run
