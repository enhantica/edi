"""Ordinary CLI fit/save/calculate must retain fitted Auto values as the saved baseline."""

# Saved Auto inputs now include the series basis in their independently authored
# provenance. The fit/retention assertions and numerical bounds remain unchanged.

import shutil
import subprocess
import sys
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.fitted_baseline import (
    HERE,
    KINDS,
    stored_pattern,
    values,
)
from tests.fixtures.background_estimate.readonly import snapshot

ROOT = Path(__file__).resolve().parents[3]


def command(project, operation):
    return [sys.executable, '-m', 'edi', operation, str(project)]


def run(project, operation):
    result = subprocess.run(
        command(project, operation), capture_output=True, text=True, check=False, timeout=2
    )
    assert result.returncode == 0, (
        'CLI fit/calculate/save of free Auto backgrounds must succeed; refusal reason: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('kind', KINDS)
def test_cli_fit_publishes_fitted_auto_rows_and_the_next_calculation_retains_them(tmp_path, kind):
    auto = tmp_path / 'auto'
    shutil.copytree(HERE / 'projects' / ('fitted-auto-' + kind), auto)
    manual = tmp_path / 'manual'
    shutil.copytree(auto, manual)
    file = manual / 'experiments/d20.edi'
    file.write_text(
        file.read_text().replace(
            '_background_estimate.mode auto', '_background_estimate.mode manual'
        )
    )
    before = values(engine.Project.load(manual))
    run(manual, 'fit')
    expected = values(engine.Project.load(manual))
    assert np.max(np.abs(expected - before)) > 1e-5, (
        'The ordinary Manual CLI control must really change the free background values'
    )
    control_pattern = stored_pattern(manual)
    assert len(control_pattern) > 100, 'The successful Manual CLI must publish its fitted pattern'
    run(auto, 'fit')
    fitted = engine.Project.load(auto)
    np.testing.assert_allclose(
        values(fitted),
        expected,
        rtol=1e-11,
        atol=1e-8,
        err_msg='CLI Auto fit must save the same fitted values as the identical Manual control',
    )
    observed = snapshot(fitted)
    assert fitted.experiment.background_estimate.mode == 'auto', (
        'CLI fitting must preserve the saved Auto estimation mode'
    )
    pattern = stored_pattern(auto)
    assert len(pattern) > 100, 'CLI fit must publish included calculated samples after fitting'
    assert np.isfinite(pattern).all(), 'The stored fitted CLI pattern must be finite'
    assert np.max(np.abs(pattern[:, 0] - pattern[:, 1])) > 1e-5, (
        'The stored CLI fit must contain nonzero calculated crystal peaks'
    )
    np.testing.assert_allclose(
        pattern[:, 1],
        control_pattern[:, 1],
        rtol=1e-11,
        atol=1e-8,
        err_msg='Auto and Manual CLI fitting must publish the same fitted background curve',
    )
    run(auto, 'calc')
    assert snapshot(engine.Project.load(auto)) == observed, (
        'A later ordinary CLI calculation must keep the fitted saved Auto baseline exactly'
    )
