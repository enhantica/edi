# SPDX-License-Identifier: BSD-3-Clause
"""Caught event errors report their diagnostic and leave the application running."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.application_errors.prepare import identity, prepare
from tests.fixtures.onboarding.build_native import require_native

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('kind', ['standard', 'unknown'])
def test_production_event_boundary_reports_and_continues(tmp_path, kind):
    build = ROOT / 'build/onboarding-native'
    expected = tmp_path / 'provider'
    prepare(ROOT, expected)
    assert (build / 'application_provider.inc').is_file(), (
        'ADR-0062: build the native event-boundary prerequisite before the gate'
    )
    assert (build / 'application_provider.inc').read_bytes() == (
        expected / 'application_provider.inc'
    ).read_bytes(), (
        'ADR-0062: the event probe compiles the current complete production catch boundary'
    )
    assert json.loads((build / 'error_boundary.identity.json').read_text()) == identity(
        ROOT, build
    ), 'ADR-0062: event-boundary source, fixture and binary bytes must match their build identity'
    binary = build / ('error_boundary_probe.exe' if os.name == 'nt' else 'error_boundary_probe')
    result = subprocess.run(
        [str(binary), kind],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, 'ADR-0062: caught event errors never terminate the application'
    outcome = json.loads(result.stdout)
    assert not outcome['accepted'] and outcome['continued'] and outcome['subsequent'] == 1, (
        'ADR-0062: the failed event is refused and a later event still reaches its receiver'
    )
    assert outcome['reports'] == 1 and outcome['message'], (
        'ADR-0062: both standard and unknown exceptions produce one nonempty diagnostic'
    )
    if kind == 'standard':
        assert outcome['message'] == 'injected event error at item 17', (
            'ADR-0062: the event boundary retains the actual caught exception message'
        )


def test_real_reporter_emits_the_caught_error_signal(tmp_path):
    binary = require_native(ROOT, ROOT / 'build/onboarding-native', 'log_probe')
    message = 'injected event error at item 17'
    request = tmp_path / 'caught.json'
    request.write_text(
        json.dumps({
            'operation': 'caught',
            'time': '2026-07-18T09:41:26Z',
            'directory': str(tmp_path / 'logs'),
            'message': message,
        })
    )
    result = subprocess.run(
        [str(binary), str(request)], capture_output=True, text=True, timeout=10, check=False
    )
    assert result.returncode == 0, (
        'ADR-0062: the production caught-error reporter executes offline'
    )
    assert json.loads(result.stdout)['caught'] == message, (
        'ADR-0062: the real run log emits the diagnostic the popup subscribes to'
    )
