"""Add archival pin-document provenance without recapturing regression values."""

import functools
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import yaml

from tests.fixtures.path_keys import repository_key

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[2]
BASE = '398a48e2b53a074e745956cee6e5399f963788f5'


def insertion(metadata):
    return (
        '    "pins": '
        + json.dumps(metadata, ensure_ascii=False, indent=2).replace('\n', '\n    ')
        + ',\n'
    ).encode()


@functools.cache
def rows():
    return json.loads((HERE / 'pin-sources.json').read_text(encoding='utf-8'))['files']


def previous_bytes(name, data):
    row = rows().get(repository_key(name))
    if row is None:
        return data
    digest = hashlib.sha256(data).hexdigest()
    if digest == row['before_sha256']:
        return data
    assert digest == row['after_sha256'], 'Pin provenance requires every committed source byte'
    with zipfile.ZipFile(HERE / 'pin-sources.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert hashlib.sha256(before).hexdigest() == row['before_sha256']
    added = insertion(row['metadata'])
    assert data.count(added) == 1 and data.replace(added, b'', 1) == before
    original, annotated = json.loads(before), json.loads(data)
    assert annotated['source'].pop('pins') == row['metadata']
    assert annotated == original, (
        'Pin provenance cannot change a reference, tolerance or regression value'
    )
    return before


def generate():
    """Read already committed source objects; no numerical engine is invoked."""

    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT)

    registry = yaml.safe_load(git('show', BASE + ':docs/user/cli/projects.yml'))['projects']
    files, contents = {}, {}
    for case in (row['id'] for row in registry if row.get('user-facing') is True):
        name = 'docs/user/cli/' + case + '/expected.json'
        before = git('show', BASE + ':' + name)
        assert 'pins' not in json.loads(before)['source']
        commit = git('log', '-1', '--format=%H', BASE, '--', name).decode().strip()
        assert git('show', commit + ':' + name) == before
        subject = git('show', '-s', '--format=%s', commit).decode('utf-8').strip()
        digest = hashlib.sha256(before).hexdigest()
        metadata = {
            'commit': commit,
            'reason': 'Existing published pin source: '
            + subject
            + '. See PROVENANCE.md for the original conditions; no fit rerun.',
            'kind': 'committed-document',
            'record_sha256': digest,
        }
        marker = b'  "source": {\n'
        assert before.count(marker) == 1
        after = before.replace(marker, marker + insertion(metadata), 1)
        path = ROOT / name
        assert path.read_bytes() in {before, after}
        path.write_bytes(after)
        files[name] = {
            'before_sha256': digest,
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'metadata': metadata,
        }
        contents[digest] = before
    with zipfile.ZipFile(HERE / 'pin-sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for digest, raw in sorted(contents.items()):
            info = zipfile.ZipInfo(digest, (2026, 11, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    (HERE / 'pin-sources.json').write_text(
        json.dumps(
            {
                'baseline': BASE,
                'claim': (
                    'Committed document provenance only; no new fit, binary identity '
                    'or independent scientific correctness claim'
                ),
                'files': files,
            },
            ensure_ascii=False,
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    generate()
