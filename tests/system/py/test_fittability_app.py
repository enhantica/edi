"""Observe fitting eligibility through the real Analysis components."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    *(
        'test_reasons:' + name
        for name in (
            'radius',
            'limit',
            'cell',
            'tied-cell',
            'coordinate',
            'constraint',
            'dispersion',
        )
    ),
    'test_exact_inventory_and_partition',
    *('test_readonly_descriptors:' + name for name in ('position', 'cutoff', 'order', 'texture')),
    'test_context_change_keeps_a_clearable_free_flag',
]


@pytest.mark.parametrize('case', CASES)
def test_analysis_inputs_and_free_controls(case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Fit eligibility acceptance requires the built production Qt host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_fittability.qml'),
            'Fittability::' + case,
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The real Analysis table retains every input and enforces its shared fit reason: ' + output
    )
    assert 'PASS' in output and '0 failed' in output, (
        'The selected Analysis actor completes its assertions in the production Qt host'
    )
