# SPDX-License-Identifier: BSD-3-Clause
"""The app's actual online loader is driven only by an injected local transport."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'authored_collection_fixture', ROOT / 'tests/fixtures/download_reference/build.py'
)
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


def app_result(root, scenario, entry='alpha-data'):
    suffix = '.exe' if os.name == 'nt' else ''
    binary = ROOT / f'build/app/assistant-ui-probe/assistant_collection_probe{suffix}'
    result = subprocess.run(
        [str(binary), str(root), entry, scenario],
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
            'QT_QUICK_BACKEND': 'software',
        },
    )
    assert result.returncode == 0, (
        'The actual app collection carrier must return its transport receipt: ' + result.stderr
    )
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.parametrize('scenario', ['primary', 'fallback'])
def test_app_entry_and_download_match_the_independent_fixture(tmp_path, scenario):
    index = FIXTURE.build(tmp_path / 'collection')
    expected = index['entries'][1]
    actual = app_result(tmp_path / 'collection', scenario)
    assert actual['found'] and actual['id'] == expected['id'], (
        'The app must resolve the same independently authored id as the public interfaces'
    )
    assert (
        actual['file'] == expected['files'][0]['path']
        and actual['sha256'] == expected['files'][0]['sha256']
    ), 'The app must retain the authored file identity and digest'
    assert actual['received'] and bytes.fromhex(actual['hex']) == FIXTURE.MEASUREMENT, (
        'The app download must yield the independently authored file bytes'
    )
    if scenario == 'fallback':
        assert actual['fallback_requests'] > 0, (
            'An unreachable primary must reach the injected live mirror in the app transport'
        )


def test_app_bad_digest_refuses_before_publishing_a_file(tmp_path):
    root = tmp_path / 'collection'
    index = FIXTURE.build(root)
    index['entries'][1]['files'][0]['sha256'] = '0' * 64
    (root / 'index.json').write_text(json.dumps(index))
    actual = app_result(root, 'primary')
    assert actual['found'] and not actual['received'] and 'hex' not in actual, (
        'The app must refuse a wrong digest before giving any file to its ordinary loader'
    )
    assert actual['error'], 'The app must disclose the failed content verification'


def test_app_refuses_the_same_verified_unsafe_archive(tmp_path):
    root = tmp_path / 'collection'
    index = FIXTURE.build(root)
    FIXTURE.refuse_archive(root, index)
    actual = app_result(root, 'primary', 'proj-reference')
    assert actual['found'] and actual['received'], (
        'The app must reach extraction with the digest-verified unsafe archive'
    )
    assert 'project_hex' not in actual and actual['error'], (
        'The ordinary app loader must refuse the same unsafe archive as Python and the CLIs'
    )
    assert not (tmp_path / 'outside.edi').exists(), (
        'The app extraction refusal must not publish the archive escape member'
    )
