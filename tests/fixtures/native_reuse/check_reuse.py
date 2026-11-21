# SPDX-License-Identifier: BSD-3-Clause
"""Documentation reuse admission, without network or native compilation."""

import importlib.util
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools/ci' / f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


finder = module('find_native_artifact')
native = module('edi_native')


def run(number, **changes):
    return {
        'id': number,
        'head_sha': 'a' * 40,
        'head_repository': {'full_name': 'enhantica/edi'},
        'status': 'completed',
    } | changes


def artifact(name='edi-native-linux-64', *, expired=False):
    return {'name': name, 'expired': expired}


def find_mocked(runs, artifacts):
    calls = []

    def api(path):
        calls.append(path)
        if '/workflows/ci.yml/' in path:
            return [{'workflow_runs': runs}, {'workflow_runs': []}]
        if '/workflows/installers.yml/' in path:
            return [{'workflow_runs': []}]
        number = int(path.split('/runs/')[1].split('/')[0])
        return [{'artifacts': artifacts.get(number, [])}]

    with patch.object(finder, 'api', api):
        selected = finder.find('enhantica/edi', 'a' * 40, 'linux-64')
    return selected, calls


def test_newest_completed_matching_artifact():
    selected, calls = find_mocked(
        [run(20), run(21), run(22)],
        {20: [artifact()], 21: [artifact()], 22: [artifact(expired=True)]},
    )
    assert selected == '21'
    assert not any('/runs/20/' in call for call in calls)


def test_foreign_or_running_runs_and_other_platforms_are_not_reused():
    selected, _ = find_mocked(
        [
            run(20, head_sha='b' * 40),
            run(21, status='in_progress'),
            run(22, head_repository={'full_name': 'someone/edi'}),
            run(23),
        ],
        {
            20: [artifact()],
            21: [artifact()],
            22: [artifact()],
            23: [artifact('edi-native-osx-arm64')],
        },
    )
    assert not selected


def test_absent_artifact_builds_without_waiting():
    assert not find_mocked([], {})[0]
    assert not find_mocked([run(20)], {})[0]


def test_api_failure_is_not_absence():
    with (
        patch.object(finder, 'api', side_effect=RuntimeError('API unavailable')),
        pytest.raises(RuntimeError),
    ):
        finder.find('enhantica/edi', 'a' * 40, 'linux-64')


def test_restore_rejects_wrong_producer_or_source():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / native.TAR).write_bytes(b'not extracted')
        expected = {
            'run_id': '123',
            'source_sha': 'a' * 40,
            'sha256': native.sha256(root / native.TAR),
        }
        for field, wrong in [('run_id', '456'), ('source_sha', 'b' * 40)]:
            record = expected | {field: wrong}
            (root / native.MANIFEST).write_text(json.dumps(record))
            with (
                patch.object(native, 'observed', return_value=expected),
                pytest.raises(native.RefusedError, match=field),
            ):
                native.restore(root)


def test_explicit_producer_retains_other_identity_fields():
    base = {'GITHUB_RUN_ID': '456', 'GITHUB_WORKSPACE': str(native.ROOT)}
    with (
        patch.dict(os.environ, base, clear=True),
        patch.object(native, 'sdk_platform', return_value='linux-64'),
        patch.object(native, 'git', return_value='a' * 40),
        patch.object(native.crysta_sdk, 'pinned', return_value='a' * 40),
        patch.object(native.crysta_sdk, 'check', return_value={'source_sha': 'a' * 40}),
        patch.object(native.crysta_sdk, 'tested_paths', return_value=['lib/crysta.so']),
        patch.object(native, 'sha256', return_value='digest'),
    ):
        current = native.observed()
        with patch.dict(os.environ, {'EDI_NATIVE_PRODUCER_RUN_ID': '123'}):
            producer = native.observed()
    assert current['run_id'] == '456'
    assert producer == current | {'run_id': '123'}
