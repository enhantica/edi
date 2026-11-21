"""Real Qt Graphs hover and data freshness after the experiment row replaces data."""

import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.untitled_work.inputs import generate

ROOT = Path(__file__).resolve().parents[3]
NATIVE_FILE = 'tst_replaced_data_drawn.qml'
CASES = [
    'a_hover_all_chart_panes:powder',
    'a_hover_all_chart_panes:single',
    'b_replacement_recalculates_on_the_new_grid',
    'c_replacement_retires_old_quality_and_status',
]


@pytest.fixture(scope='module')
def replacement_observations(request, tmp_path_factory):
    folder = tmp_path_factory.mktemp('drawn-replacement')
    inputs = generate(folder / 'inputs')
    selected = [
        item.callspec.params['case']
        for item in request.session.items
        if getattr(item, 'module', None) is request.module
    ]
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Drawn replacement gates require the actual native application host'
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {'QT_QUICK_BACKEND', 'QT_QPA_PLATFORM'}
    }
    env['EDI_ACCEPTANCE_REFERENCE'] = str(inputs)
    env['EDI_CAPTURE_HEIGHT'] = '960'
    command = 'source tools/ci/app-platform.sh; app_capture_platform replaced-data || exit $?; '
    command += ' '.join(
        shlex.quote(value)
        for value in [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app' / NATIVE_FILE),
            *['ReplacedData::test_' + case for case in selected],
        ]
    )
    result = subprocess.run(
        ['bash', '-c', command],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = result.stdout + result.stderr
    (folder / 'native.log').write_text(output)
    return result.returncode, output, selected


@pytest.mark.parametrize('case', CASES)
def test_replaced_data(case, replacement_observations):
    code, output, selected = replacement_observations
    totals = re.findall(r'Totals: (\d+) passed, (\d+) failed, (\d+) skipped', output)
    assert totals, 'The actual drawn native batch reaches its Qt Test completion record: ' + output
    passed, failed, skipped = map(int, totals[-1])
    assert passed + failed == len(selected) + 2 and skipped == 0, (
        'The native batch executes every selected replacement case and both lifecycle controls'
    )
    assert code >= 0 and (code == 0) == (failed == 0), (
        'The drawn native host rejects crashes and preserves its observed failures: ' + output
    )
    function, separator, tag = case.partition(':')
    marker = '::ReplacedData::test_' + function + '(' + (tag if separator else '') + ')'
    rows = [line for line in output.splitlines() if marker in line]
    assert any(line.startswith('PASS ') for line in rows) and not any(
        line.startswith(('FAIL!', 'SKIP')) for line in rows
    ), 'The requested real row-replacement and native-hover case passes: ' + '\n'.join(rows)
