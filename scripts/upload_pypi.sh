#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TWINE_USERNAME:-}" || -z "${TWINE_PASSWORD:-}" ]]; then
  echo "Set TWINE_USERNAME and TWINE_PASSWORD (PyPI token as __token__)." >&2
  exit 1
fi

python -m twine upload dist/*

