"""Retain complete committed pin bytes across the documented release retake."""

import functools
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from tests.fixtures.path_keys import repository_key

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[2]
REVISION = 'ec587609746b50823c048463f353b1767cbfa5f9'
LATER_INPUT_CASE = 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/expected.json'
ITERATION_CASE = 'docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/expected.json'


def references(value, trail=()):
    """Independent-reference subtrees remain exact, including their tolerances."""
    if isinstance(value, list):
        return {
            key: item
            for index, child in enumerate(value)
            for key, item in references(child, (*trail, index)).items()
        }
    if not isinstance(value, dict):
        return {}
    if value.get('kind') == 'reference':
        return {trail: value}
    return {
        key: item
        for name, child in value.items()
        for key, item in references(child, (*trail, name)).items()
    }


def validate(before, after, name):
    """Keep all physical references; admit one source-documented iteration retag."""
    old = references(before)
    new = references(after)
    if name == ITERATION_CASE:
        key = ('edi', 'quantities', 'iterations')
        assert old.pop(key) == {
            'value': 7.0,
            'kind': 'reference',
            'tol_abs': 0.0,
            'tol_rel': None,
        }
        assert after['edi']['quantities']['iterations'] == {
            'value': 4.0,
            'kind': 'regression-pin',
            'tol_abs': 0.0,
            'tol_rel': None,
        }
        assert before['source']['engine'] == after['source']['engine'] == 'crysta'
        assert before['edi']['source'] == after['edi']['source']
        assert 'crysta CLI' in before['edi']['source']
    assert old == new, 'The release source projection must retain every physical reference'


@functools.cache
def rows():
    manifest = json.loads((HERE / 'release-pins.json').read_text())
    assert manifest['source_commit'] == REVISION
    return manifest['files']


def previous_bytes(name, data):
    """Reverse only complete source-qualified before/after documents."""
    name = repository_key(name)
    row = rows().get(name)
    if row is None:
        return data
    digest = hashlib.sha256(data).hexdigest()
    if digest == row['before_sha256']:
        return data
    assert digest == row['after_sha256'], 'A release pin must retain every committed source byte'
    with zipfile.ZipFile(HERE / 'release-pins.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert hashlib.sha256(before).hexdigest() == row['before_sha256']
    validate(json.loads(before), json.loads(data), name)
    return before


def generate():
    """Archive existing Git source only; never run a fit or rewrite an expectation."""
    names = subprocess.check_output(
        [
            'git',
            'diff-tree',
            '--no-commit-id',
            '--name-only',
            '-r',
            REVISION,
            '--',
            'docs/user/cli/**/expected.json',
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    manifest = {}
    content = {}
    for name in names:
        if name == LATER_INPUT_CASE:
            continue
        before, after = (
            subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
            for revision in (REVISION + '^', REVISION)
        )
        validate(json.loads(before), json.loads(after), name)
        left, right = (hashlib.sha256(data).hexdigest() for data in (before, after))
        manifest[name] = {'before_sha256': left, 'after_sha256': right}
        content[left] = before
        content[right] = after
    with zipfile.ZipFile(HERE / 'release-pins.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for digest, data in sorted(content.items()):
            info = zipfile.ZipInfo(digest, (2026, 11, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    (HERE / 'release-pins.json').write_text(
        json.dumps(
            {
                'claim': (
                    'Complete committed regression-retake source bytes; '
                    'no new fit or correctness claim'
                ),
                'source_commit': REVISION,
                'files': manifest,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    generate()
