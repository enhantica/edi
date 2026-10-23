"""Observe every new scan contract in one real rendering session."""

import os
import re
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = (
    'test_default_and_group_order',
    'test_each_mode_marks:band-light',
    'test_each_mode_marks:band-dark',
    'test_each_mode_marks:line-light',
    'test_each_mode_marks:line-dark',
    'test_each_mode_marks:points-light',
    'test_each_mode_marks:points-dark',
    'test_each_mode_marks:linePoints-light',
    'test_each_mode_marks:linePoints-dark',
    'test_choice_shared_and_remembered:structure-band',
    'test_choice_shared_and_remembered:structure-line',
    'test_choice_shared_and_remembered:structure-points',
    'test_choice_shared_and_remembered:structure-linePoints',
    'test_choice_shared_and_remembered:experiment-band',
    'test_choice_shared_and_remembered:experiment-line',
    'test_choice_shared_and_remembered:experiment-points',
    'test_choice_shared_and_remembered:experiment-linePoints',
    'test_choice_shared_and_remembered:analysis-band',
    'test_choice_shared_and_remembered:analysis-line',
    'test_choice_shared_and_remembered:analysis-points',
    'test_choice_shared_and_remembered:analysis-linePoints',
    'test_background_and_legend_dashed:structure-light',
    'test_background_and_legend_dashed:structure-dark',
    'test_background_and_legend_dashed:experiment-light',
    'test_background_and_legend_dashed:experiment-dark',
    'test_background_and_legend_dashed:analysis-light',
    'test_background_and_legend_dashed:analysis-dark',
    'test_background_and_legend_dashed:report-light',
    'test_background_and_legend_dashed:report-dark',
)


@pytest.fixture(scope='module')
def scan_receipt(request):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Scan content acceptance requires the actual native test host'
    groups = {}
    for item in request.session.items:
        if item.module is request.module and hasattr(item, 'callspec'):
            case = item.callspec.params['case']
            groups.setdefault(case.partition(':')[0], []).append(case)

    def run(cases):
        command = [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_pattern_owner_styles.qml'),
            '-o',
            '-,txt',
            *['PatternOwnerStyles::' + case for case in cases],
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        print(f'Acceptance actor process group {process.pid}: {cases}', flush=True)
        try:
            output, _ = process.communicate(timeout=40)
            status = process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate()
            output += '\nThe acceptance function exceeded its unchanged actor watchdog'
            status = 124
        print(output)
        return cases, status, output

    receipts = {}
    batches = [
        cases[index : index + 2] for cases in groups.values() for index in range(0, len(cases), 2)
    ]
    batches.sort(
        key=lambda cases: (
            not cases[0].startswith('test_offered_maps'),
            not cases[0].startswith('test_background_to_experiment'),
            -len(cases),
        )
    )
    with ThreadPoolExecutor(max_workers=3) as pool:
        for cases, status, output in pool.map(run, batches):
            for case in cases:
                receipts[case] = status, output
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_pattern_owner_style(scan_receipt, case):
    status, output = scan_receipt[case]
    assert (
        0 <= status < 128
        and status != 124
        and 'Totals:' in output
        and '::PatternOwnerStyles::cleanupTestCase()' in output
    ), (
        'A crashed, skipped or incomplete acceptance function cannot supply passing receipts: '
        + output
    )
    name, _, tag = case.partition(':')
    witness = f'::PatternOwnerStyles::{name}({tag})'
    lines = [line for line in output.splitlines() if witness in line]
    assert any(line.startswith('PASS ') for line in lines) and not any(
        re.match(r'FAIL|SKIP', line) for line in lines
    ), 'The requested production scan contract executes and passes without skipping: ' + '\n'.join(
        lines
    )
