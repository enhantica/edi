"""Observe physical x values through the actual chart selector."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('beam', ['cw', 'tof'])
@pytest.mark.parametrize('axis', ['native', 'd', 'q', 'sine'])
def test_pattern_x_values_follow_independent_relations(beam, axis):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Physical-axis acceptance requires the current Qt chart host'
    case = 'PatternPhysicalAxes::test_axes_follow_independent_bragg_and_tof_relations'
    result = subprocess.run(
        [
            binary,
            '-input',
            ROOT / 'tests/unit/app/tst_pattern_axes.qml',
            f'{case}:{beam}-{axis}',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The real chart satisfies the independent physical x conversion: ' + output
    )
    assert f'{case}({beam}-{axis})' in output and '0 failed' in output, (
        'The requested physical-axis witness executes without an empty native selection'
    )
    assert 'SKIP' not in output, 'Each physical x quantity is exercised rather than skipped'
