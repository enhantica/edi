"""Capture the existing example trees before the catalogue replacement."""

import hashlib
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = '3a6b4dc8'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    """Write content digests; the test needs no old Git objects at runtime."""
    git('merge-base', '--is-ancestor', BASE, 'origin/main')
    rows = yaml.safe_load(git('show', f'{BASE}:docs/user/cli/projects.yml'))['projects']
    retained = []
    for row in rows:
        prefix = f'docs/user/cli/{row["id"]}/'
        paths = git('ls-tree', '-r', '--name-only', BASE, '--', prefix).decode().splitlines()
        digests = {}
        for path in paths:
            relative = path.removeprefix(prefix)
            if relative.startswith('project/') or relative == 'expected.json':
                digests[relative] = hashlib.sha256(git('show', f'{BASE}:{path}')).hexdigest()
        retained.append({**row, 'sha256': digests})
    result = {'source': BASE, 'projects': retained}
    Path(__file__).with_name('retained-projects.json').write_text(
        json.dumps(result, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
