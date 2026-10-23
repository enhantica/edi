"""Background type-popup closure precedes an actually received append action."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('phase', ['polynomial', 'type-popup'])
def test_chebyshev_append_receives_real_input_after_the_type_popup_closes(phase):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Coefficient parity requires the actual production Qt host'
    polynomial = phase == 'polynomial'
    actor = (
        'tst_background_polynomial_editing.qml' if polynomial else 'tst_parameter_correlations.qml'
    )
    case = ('BackgroundPolynomialEditing::' if polynomial else 'ParameterCorrelations::') + (
        'test_background_coefficients_have_editing_parity'
        if phase == 'polynomial'
        else 'test_background_type_popup_append_has_editing_parity'
    )
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app' / actor),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'Real type confirmation must close before an actually received Chebyshev append; '
        'the existing count, order, value-edit, Cancel and remove properties must all hold: '
        + output
    )
    receipt = (
        'BACKGROUND_POLYNOMIAL_PARITY editing=typed append=clicked remove=clicked'
        if phase == 'polynomial'
        else 'BACKGROUND_COEFFICIENT_PARITY popup=closed append=clicked order=23 remove=clicked'
    )
    assert receipt in output, (
        'Each bounded phase must finish its unchanged editing or popup/received-click properties'
    )
