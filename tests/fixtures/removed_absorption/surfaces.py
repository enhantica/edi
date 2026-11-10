"""Check the retired absorption field across declared public files."""

import json
import re
from pathlib import Path

FIELD = re.compile(r'abscor[\s_-]*2', re.IGNORECASE)
FULLPROF_INPUTS = {'.pcr', '.inp', '.new'}


def surface_text(path):
    raw = path.read_bytes().decode('utf-8', errors='replace')
    if path.suffix.lower() in {'.json', '.ipynb'}:
        data = json.loads(raw)
        if path.name == 'python-surface.json':
            assert 'public' in data, 'A Python declaration must prove its live public surface'
            # The manifest also records retired names as historical metadata.
            data = {
                'public': data['public'],
                'members': data.get('classification', {}).get('members', {}),
            }
        return json.dumps(data, ensure_ascii=False)
    return raw


def violations(root, scopes):
    root = Path(root)
    hits = []
    for name in scopes:
        target = root / name
        assert target.exists(), 'Each declared public surface must exist: ' + name
        candidates = sorted(target.rglob('*')) if target.is_dir() else [target]
        checked = []
        for path in candidates:
            assert not (path.is_symlink() and path.is_dir()), (
                'A public surface must not hide an unenumerated linked directory: ' + str(path)
            )
            if path.is_dir():
                continue
            if path.suffix.lower() in FULLPROF_INPUTS:
                text = surface_text(path)
                titled = re.match(r'COMM\s', text.lstrip(), re.IGNORECASE)
                patterns = re.search(r'^\s*NPATT\s+[1-9]\d*\b', text, re.MULTILINE)
                weights = re.search(r'^\s*W_PAT\s+[-+.\d]', text, re.MULTILINE)
                jobs = re.search(r'^\s*!\s*Job\b.*\bNpr\b', text, re.IGNORECASE | re.MULTILINE)
                if jobs and (titled or (patterns and weights)):
                    continue
            checked.append(path)
            if FIELD.search(surface_text(path)):
                hits.append(str(path.relative_to(root)))
        assert checked, 'Each public surface must contain nonexempt content: ' + name
    return sorted(set(hits))
