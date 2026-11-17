"""Retain complete pre-retake documents without depending on branch history later."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def main():
    files = {}
    changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, text=True)
    for name in changed.splitlines():
        if not (name.startswith('docs/user/cli/') and name.endswith('/expected.json')):
            continue
        before = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
        after = (ROOT / name).read_bytes()
        files[name] = {
            'before_text': before.decode(),
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
        }
    if not files:
        raise ValueError('Retake generation requires explicit uncommitted CLI pin changes')
    (HERE / 'retakes.json').write_text(
        json.dumps(
            {
                'claim': 'Regression pins at explicit former 1e-6 versus current default 1e-4; '
                'all scientific references and bounds retained.',
                'files': files,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
