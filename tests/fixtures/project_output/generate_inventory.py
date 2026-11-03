"""Reproduce the frozen pre-helper source inventory from its recorded Git revision."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOLDER = Path(__file__).resolve().parent


def main():
    contract = json.loads((FOLDER / 'contract.json').read_text())
    previous = json.loads((FOLDER / 'source_inventory.json').read_text())
    revision = previous['regression_source_revision']
    result = subprocess.run(
        [shutil.which('git'), 'ls-tree', '-r', '--name-only', revision, '--', *contract['roots']],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = sorted(
        name
        for name in result.stdout.splitlines()
        if Path(name).suffix in {'.cpp', '.hpp', '.h', '.py'}
    )
    (FOLDER / 'source_inventory.json').write_text(
        json.dumps(
            {'regression_source_revision': revision, 'regression_source_inventory': paths},
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
