#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "Python 3 is required to deploy this Worker." >&2
    exit 1
  fi
fi

"${PYTHON_BIN}" --version

if ! command -v uv >/dev/null 2>&1; then
  "${PYTHON_BIN}" -m pip install --user uv
  export PATH="${HOME}/.local/bin:${PATH}"
fi

uv --version
uv run pywrangler deploy
