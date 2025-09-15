#!/usr/bin/env bash
set -euo pipefail

# Tags the repo using the version from pyproject.toml (project.version).

ver=$(python - <<'PY'
import re,sys
with open('pyproject.toml','r',encoding='utf-8') as f:
    t=f.read()
m=re.search(r"^version\s*=\s*\"([^\"]+)\"", t, re.M)
if not m:
    sys.exit("version not found in pyproject.toml")
print(m.group(1))
PY
)

echo "Tagging version v$ver"
git tag "v$ver"
echo "Created tag v$ver. Push with: git push origin v$ver"

