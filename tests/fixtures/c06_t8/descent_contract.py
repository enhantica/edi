"""Retired descents may be migration prose, never advertised choices or examples."""

import json
import re
from pathlib import Path

RETIRED = ('fast_descent_linear_snap', 'fast_descent_guarded_linear_snap')
VALID = {'ladder', 'fast_descent', 'multistart_prune'}
SNAP = re.compile(
    r'fast[_\s-]+descent(?:[_\s-]+with)?[_\s-]+(?:guarded[_\s-]+)?linear[_\s-]+snap', re.IGNORECASE
)
RETIRED_NOTICE = re.compile(
    r'\b(?:is|are|was|were)\s+(?:retired|removed)\b|^\s*(?:Retired|Removed):', re.IGNORECASE
)


def advertisements(root, scopes):
    root = Path(root)
    found = []
    for name in scopes:
        target = root / name
        assert target.exists(), 'Each descent surface must exist: ' + name
        paths = sorted(target.rglob('*')) if target.is_dir() else [target]
        checked = 0
        for path in paths:
            assert not (path.is_symlink() and path.is_dir()), (
                'Descent surfaces must not conceal linked directory contents'
            )
            if path.is_dir():
                continue
            raw = path.read_bytes().decode('utf-8', errors='replace')
            checked += 1
            structured = path.suffix.lower() in {'.json', '.ipynb'}
            if structured:
                raw = json.dumps(json.loads(raw), ensure_ascii=False)
            found.extend(
                str(path.relative_to(root))
                for line in raw.splitlines()
                if SNAP.search(line) and (structured or not RETIRED_NOTICE.search(line))
            )
        assert checked, 'Each descent surface must contain checked files: ' + name
    return sorted(set(found))
