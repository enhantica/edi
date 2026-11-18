"""Recover exact pre-default example inputs without admitting other byte edits."""

import functools
import hashlib
import json
from pathlib import Path

from tests.fixtures.path_keys import repository_key

HERE = Path(__file__).parent


@functools.cache
def rows():
    return json.loads((HERE / 'example-inputs.json').read_text())['files']


def previous_bytes(name, data):
    row = rows().get(repository_key(name))
    if row is None:
        return data
    before = row['before_text'].encode()
    assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
        'Default adaptation retains the complete committed former example input'
    )
    if data == before:
        return before
    assert hashlib.sha256(data).hexdigest() == row['after_sha256'], (
        'Default adaptation requires the entire independently archived source, '
        'including every scientific byte'
    )
    removed = b'_minimizer.max_iterations 1000\n'
    assert before.count(removed) == 1 and before.replace(removed, b'', 1) == data, (
        'The example transition removes only the former saved default budget'
    )
    return before


def composed_bytes(name, data):
    row = rows().get(repository_key(name))
    if row is not None and hashlib.sha256(data).hexdigest() == row['after_sha256']:
        return previous_bytes(name, data)
    return data


def previous_content(data):
    digest = hashlib.sha256(data).hexdigest()
    matches = [name for name, row in rows().items() if row['after_sha256'] == digest]
    return previous_bytes(matches[0], data) if matches else data


def generate():
    """Archive the committed example edit; never run an engine or alter a pin."""
    import subprocess  # noqa: PLC0415

    root = HERE.resolve().parents[2]
    revision = 'af1fc034'
    names = subprocess.check_output(
        ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', revision],
        cwd=root,
        text=True,
    ).splitlines()
    files = {}
    for name in names:
        if not name.endswith('/analysis/analysis.edi'):
            continue
        before, after = (
            subprocess.check_output(['git', 'show', ref + ':' + name], cwd=root)
            for ref in (revision + '^', revision)
        )
        assert (root / name).read_bytes() == after, (
            'The input adaptation archives the exact committed current example'
        )
        files[name] = {
            'before_text': before.decode(),
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
        }
    (HERE / 'example-inputs.json').write_text(
        json.dumps(
            {
                'source_commit': revision,
                'authority': '91facae70',
                'claim': 'Saved default 1000 omitted; default 50. All other bytes retained.',
                'files': files,
            },
            indent=2,
        )
        + '\n'
    )
    rows.cache_clear()
    for name in files:
        previous_bytes(name, (root / name).read_bytes())


if __name__ == '__main__':
    generate()
