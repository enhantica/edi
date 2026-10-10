"""Executed identities and provenance are required, even beside a green summary."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HEAD = '73' * 20


def verify(tmp_path, report, expected=None):
    policy = json.loads((ROOT / 'tests/test-groups.json').read_text())
    command = policy.get('execution_report', {}).get('command')
    assert isinstance(command, list), (
        'CI policy: declare execution_report.command as documented in the visible cadence fixture'
    )
    assert command, (
        'CI policy: declare execution_report.command as documented in the visible cadence fixture'
    )
    command = [sys.executable if word in {'python', 'python3'} else word for word in command]
    want = tmp_path / 'expected.json'
    seen = tmp_path / 'report.json'
    want.write_text(
        json.dumps(expected if expected is not None else ['unit::arm64-pin', 'system::scan'])
    )
    seen.write_text(json.dumps(report))
    return subprocess.run(
        [
            *command,
            '--expected',
            str(want),
            '--report',
            str(seen),
            '--head',
            HEAD,
            '--run-id',
            '790',
            '--attempt',
            '2',
            '--platform',
            'osx-arm64',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
    )


def receipt():
    return {
        'head': HEAD,
        'run_id': 790,
        'attempt': 2,
        'platform': 'osx-arm64',
        'tests': [
            {'nodeid': 'unit::arm64-pin', 'outcome': 'passed'},
            {'nodeid': 'system::scan', 'outcome': 'passed'},
        ],
    }


@pytest.mark.parametrize(
    'damage',
    [
        'omit',
        'duplicate',
        'empty',
        'skip',
        'xfail',
        'fail',
        'unknown',
        'head',
        'platform',
        'attempt',
        'run',
        'malformed',
    ],
)
def test_executed_identity_receipt_requires_full_results_and_current_provenance(tmp_path, damage):
    good = receipt()
    admitted = verify(tmp_path, good)
    assert admitted.returncode == 0, (
        'CI policy: the exact complete successful result receipt must be '
        'accepted before each refusal control'
    )
    bad = copy.deepcopy(good)
    if damage == 'omit':
        bad['tests'].pop()
    elif damage == 'duplicate':
        bad['tests'].append(copy.deepcopy(bad['tests'][0]))
    elif damage == 'empty':
        bad['tests'] = []
    elif damage in {'skip', 'xfail', 'fail'}:
        bad['tests'][0]['outcome'] = {'skip': 'skipped', 'xfail': 'xfailed', 'fail': 'failed'}[
            damage
        ]
    elif damage == 'unknown':
        bad['tests'][0]['nodeid'] = 'same-count::wrong-identity'
    elif damage == 'head':
        bad['head'] = '42' * 20
    elif damage == 'platform':
        bad['platform'] = 'linux-64'
    elif damage == 'attempt':
        bad['attempt'] = 1
    elif damage == 'run':
        bad['run_id'] = 789
    else:
        bad = {'tests': None}
    result = verify(tmp_path, bad)
    assert result.returncode != 0, (
        'CI policy: omitted, unexecuted or foreign-provenance identities '
        'cannot pass on counts or summary alone'
    )


def test_empty_expected_selection_is_rejected_even_with_empty_green_report(tmp_path):
    report = receipt()
    report['tests'] = []
    result = verify(tmp_path, report, [])
    assert result.returncode != 0, (
        'CI policy: neither an empty smoke nor an empty nightly selection '
        'is valid execution evidence'
    )
