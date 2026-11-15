"""Authenticate the exact variant-key rename before historical byte projections."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = '5a2a33367f376f105ea12a27743c4ba26726b75e'


def main():
    paths = subprocess.check_output(
        ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', SOURCE],
        cwd=ROOT,
        text=True,
    ).splitlines()
    rows = {}
    for path in paths:
        if not path.endswith('/expected.json'):
            continue
        before = subprocess.check_output(['git', 'show', SOURCE + '^:' + path], cwd=ROOT)
        after = subprocess.check_output(['git', 'show', SOURCE + ':' + path], cwd=ROOT)
        assert (
            before.count(b'"multistart-prune"') == after.count(b'"fast-descent-and-ladder"') == 1
        ), 'Each source rename must retain exactly one old and new default variant key'
        assert before.replace(b'"multistart-prune"', b'"fast-descent-and-ladder"') == after, (
            'The source rename must preserve every numerical value, reference and tolerance byte'
        )
        rows[path] = {
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
        }
    assert len(rows) == 5, 'The committed variant rename covers exactly its five declared inputs'
    output = Path(__file__).with_name('variant-name-projection.json')
    output.write_text(
        json.dumps(
            {
                'source_commit': SOURCE,
                'claim': 'Exact variant-key rename only; every numerical value, reference and '
                'tolerance unchanged',
                'files': rows,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
