#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Explicit scientific slow cadence; these files are outside bounded PR discovery.
set -euo pipefail
cd "$(dirname "$0")/../.."
group="${1:?usage: slow-seeded-series.sh <cadence-group>}"
paths="$(python - "$group" <<'PYCODE'
import fnmatch
import json
import sys
import tomllib
from pathlib import Path
root = Path.cwd()
policy = json.loads((root / 'tests/test-groups.json').read_text())['groups'][sys.argv[1]]
paths = policy['slow_paths']
patterns = tomllib.loads((root / 'pyproject.toml').read_text())['tool']['pytest']['ini_options'].get(
    'python_files', ['test_*.py', '*_test.py'])
if isinstance(patterns, str):
    patterns = patterns.split()
if not paths or len(paths) != len(set(paths)):
    raise ValueError('Slow cadence needs unique explicitly declared files')
for name in paths:
    path = Path(name)
    if not name.startswith('tests/system/slow/') or '..' in path.parts or not path.is_file():
        raise ValueError('Slow cadence files must remain in their dedicated source directory')
    if name not in policy['paths'] or any(fnmatch.fnmatch(path.name, p) for p in patterns):
        raise ValueError('Slow cadence must be declared and excluded from PR filename discovery')
print('\n'.join(paths))
PYCODE
)"
set --
while IFS= read -r path; do set -- "$@" "$path"; done <<< "$paths"
exec python -m pytest "$@" -q
