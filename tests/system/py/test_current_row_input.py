"""Every production table follows the owner's current-row input convention."""

import json
import os
import re
import signal
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from tests.integration.py.test_table_and_about_contract import table_census

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = json.loads((ROOT / 'tests/fixtures/current_row_input/catalogue.json').read_text())
CASES = [
    row['table'] + '-' + mode + '-' + theme
    for row in CATALOGUE
    for theme in ('light', 'dark')
    for mode in (
        ['passive']
        if row['passive']
        else ['readonly', 'keyboard', 'background', 'hover']
        + ['editable' + str(column) for column in row['editable']]
        + (['cursor'] if row['textColumn'] is not None else [])
    )
]
CASES += [
    'window.' + table + '-' + mode + '-' + theme
    for table in ('atomSites.list', 'parameters.list')
    for mode in ('selection', 'cursor', 'background')
    for theme in ('light', 'dark')
]


def test_every_production_table_has_a_real_input_case():
    assert Counter(path for path, _ in table_census()) == Counter(
        row['path'] for row in CATALOGUE
    ), 'The real-input inventory covers every production table, including both background forms'
    assert len(CASES) == len(set(CASES)), (
        'Every production table, input path and theme has one distinct runtime witness'
    )


def receipt(output, case):
    suite = 'CurrentRowWindow' if case.startswith('window.') else 'CurrentRowInput'
    identity = r'(?:edi_app::)?' + re.escape(suite + '::test_input(' + case + ')')
    passed = re.findall(r'^PASS\s*:\s*' + identity + r'\s*$', output, re.MULTILINE)
    failed = re.findall(r'^(?:FAIL!|SKIP|QFATAL)\s*:\s*' + identity, output, re.MULTILINE)
    return len(passed) == 1 and not failed


def test_input_receipt_refuses_missing_duplicate_and_failed_rows():
    case = CASES[0]
    line = 'PASS   : CurrentRowInput::test_input(' + case + ')\n'
    assert receipt(line, case), 'One completed real-input case is recognized'
    assert not receipt('', case), 'An unexecuted input path cannot count as a pass'
    assert not receipt(line * 2, case), 'Duplicate observations cannot impersonate one input path'
    assert not receipt(line + line.replace('PASS   ', 'FAIL!  '), case), (
        'A failed current-row input case cannot count as a passing receipt'
    )


@pytest.fixture(scope='module')
def input_output(request):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    groups = {}
    for item in request.session.items:
        if item.module is request.module and hasattr(item, 'callspec'):
            case = item.callspec.params['case']
            groups.setdefault(case.partition('-')[0], []).append(case)
    receipts = {}
    for table, cases in groups.items():
        suite = 'CurrentRowWindow' if table.startswith('window.') else 'CurrentRowInput'
        qml = (
            'tst_current_row_window.qml'
            if table.startswith('window.')
            else 'tst_current_row_input.qml'
        )
        process = subprocess.Popen(
            [
                'bash',
                str(ROOT / 'tests/fixtures/scan_views/run.sh'),
                str(runner),
                '-input',
                str(ROOT / 'tests/unit/app' / qml),
                '-o',
                '-,txt',
                *[suite + '::test_input:' + case for case in cases],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        print(f'Real-input actor {process.pid}: {table}', flush=True)
        try:
            output, _ = process.communicate(timeout=60)
            code = process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
            code = -999
        print(output, flush=True)
        for case in cases:
            receipts[case] = (code, output, suite)
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_each_table_uses_one_current_row_for_real_input(input_output, case):
    code, output, suite = input_output[case]
    assert 0 <= code < 128 and suite + '::cleanupTestCase()' in output, (
        'The real table input actor must finish without a crash or watchdog expiry: ' + case
    )
    assert receipt(output, case), (
        'A real cell click or keyboard move must put the marker and bold accent number on '
        'exactly its current row; passive tables must retain no current row: ' + case
    )
