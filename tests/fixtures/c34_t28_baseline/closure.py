"""Content identity for the retained pre-move source closure, without Git history."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def require_baseline_closure(root):
    reference = ROOT / 'tests/fixtures/e04_t12_public_release/history/manifest.json'
    expected = json.loads(reference.read_text())['closure']
    actual = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for prefix in ('src', 'include', 'core', 'lib')
        for p in (root / prefix).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts
    }
    if actual != expected:
        raise ValueError(
            'the authoring source must equal the complete retained pre-move code closure'
        )
