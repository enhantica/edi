"""Exercise the actual window's shared chart, navigation and deferred drawing."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = {
    'observer_control': ['test_actual_chart_observers_and_input'],
    'structure_tab': ['test_structure_pattern_requires_experiment'],
    'identity': ['test_all_hosts_follow_one_shared_view'],
    'state': [
        f'{case}:{page}'
        for case in (
            'test_view_change_follows_every_page',
            'test_toolbar_toggles_follow_every_page',
        )
        for page in ('experiment', 'analysis', 'structure')
    ],
    'hidden_work': ['test_hidden_pages_do_no_chart_work'],
}


@pytest.fixture(scope='module')
def shared_chart_receipts(request):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Shared-chart acceptance requires the current native Qt test host'
    selected = {
        item.callspec.params['group']
        for item in request.session.items
        if item.module is request.module and hasattr(item, 'callspec')
    }
    receipts = {}
    for group, cases in CASES.items():
        if group not in selected:
            continue
        parts = []
        for case in cases:
            command = [
                str(binary),
                '-input',
                str(ROOT / 'tests/unit/app/tst_shared_pattern_chart.qml'),
                '-o',
                '-,txt',
                'SharedPatternChart::' + case,
            ]
            try:
                result = subprocess.run(
                    command,
                    env={
                        **os.environ,
                        'QT_QPA_PLATFORM': 'offscreen',
                        'QT_QUICK_BACKEND': 'software',
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=25,
                )
                parts.append((result.returncode, result.stdout + result.stderr))
            except subprocess.TimeoutExpired as error:
                parts.append((
                    124,
                    (error.stdout or b'').decode(errors='replace')
                    + (error.stderr or b'').decode(errors='replace')
                    + '\nThe shared-chart actor exceeded its watchdog',
                ))
            except OSError as error:
                parts.append((
                    127,
                    'The required native test host became unavailable: ' + str(error),
                ))
            print(f'Shared-chart phase {case}: status={parts[-1][0]}', flush=True)
            print(parts[-1][1], flush=True)
        receipts[group] = parts
    return receipts


@pytest.mark.parametrize('group', CASES)
def test_shared_chart_acceptance(shared_chart_receipts, group):
    parts = shared_chart_receipts[group]
    assert parts and len(parts) == len(CASES[group]), (
        'Every requested shared-chart phase must produce its own receipt'
    )
    for case, (status, output) in zip(CASES[group], parts, strict=True):
        assert status == 0, 'The actual shared-chart view satisfies its acceptance: ' + output
        name, _, tag = case.partition(':')
        witness = f'::SharedPatternChart::{name}(' + (tag + ')' if tag else ')')
        assert witness in output and '0 failed' in output, (
            'The shared-chart actor executes the requested real acceptance case: ' + output
        )
        assert not any(line.startswith('SKIP') for line in output.splitlines()), (
            'Shared-chart requirements cannot pass through skipped cases'
        )
