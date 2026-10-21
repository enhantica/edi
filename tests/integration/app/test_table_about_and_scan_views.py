"""Run the production QML actors for row numbers, licence links and scan views."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ACTORS = [
    ('tst_current_row_numbers.qml', 'CurrentRowNumbers'),
    ('tst_about_licence_links.qml', 'AboutLicenceLinks'),
    ('tst_structure_scan_views.qml', 'StructureScanViews'),
]


@pytest.fixture(scope='module')
def view_receipts():
    override = os.environ.get('EDI_APP_TEST_RUNNER')
    candidates = (
        [Path(override)]
        if override
        else [ROOT / 'build/app/app/edi_app_tests', ROOT / 'build/app/edi_app_tests']
    )
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, 'Rendered acceptance requires the current edi Qt Quick Test host'
    receipts = {}
    for file, suite in ACTORS:
        phases = (
            [
                'StructureScanViews::test_fresh_engine_observer_loads_the_actual_calculated_page',
                'StructureScanViews::test_scan_tabs',
                'StructureScanViews::test_structure_toolbar_toggle_and_saved_state:on',
                'StructureScanViews::test_structure_toolbar_toggle_and_saved_state:off',
            ]
            if suite == 'StructureScanViews'
            else [None]
        )
        parts = [run_view_phase(binary, file, phase) for phase in phases]
        receipts[suite] = subprocess.CompletedProcess(
            args=[str(binary), file],
            returncode=next((part.returncode for part in parts if part.returncode), 0),
            stdout='\n'.join(part.stdout for part in parts),
            stderr='\n'.join(part.stderr for part in parts),
        )
    return receipts


def run_view_phase(binary, file, phase):
    command = [str(binary), '-input', str(ROOT / 'tests/unit/app' / file), '-o', '-,txt']
    if phase:
        command.append(phase)
    try:
        return subprocess.run(
            command,
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except subprocess.TimeoutExpired as error:
        # Each reload phase has its own bound and cannot suppress other receipts.
        return subprocess.CompletedProcess(
            error.cmd,
            124,
            (error.stdout or b'').decode(errors='replace'),
            (error.stderr or b'').decode(errors='replace') + '\nThe actor exceeded its watchdog',
        )
    except OSError as error:
        return subprocess.CompletedProcess(
            command,
            127,
            '',
            'The required Qt Quick Test host became unavailable: ' + str(error),
        )


@pytest.mark.parametrize('suite', [suite for _, suite in ACTORS])
def test_production_view_actor_executes_every_case(view_receipts, suite):
    result = view_receipts[suite]
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The production view must satisfy its rendered acceptance: ' + output
    )
    skips = [line for line in output.splitlines() if line.startswith('SKIP')]
    if suite == 'CurrentRowNumbers':
        assert len(skips) == 2 and all(
            f'test_current_number(parameters-{theme})' in skips[index]
            and 'Waiting for the updated Analysis Parameters table' in skips[index]
            for index, theme in enumerate(('light', 'dark'))
        ), 'Only the two explicitly waiting Analysis Parameters cases may be skipped'
    else:
        assert not skips, 'An available view actor must execute every acceptance case'
    assert f'::{suite}::test_' in output and '0 failed' in output, (
        'Each Qt actor must execute real cases; an empty run supplies no evidence'
    )
