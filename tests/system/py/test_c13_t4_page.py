"""notebook execution and CLI model consumption, scoped to this page."""

import subprocess
import sys
from pathlib import Path

import edi
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('mode', ['normal', 'disabled'])
def test_lbco_page_and_actual_kernel_disable(mode):
    result = subprocess.run(
        [sys.executable, str(ROOT / 'tests/system/manual/c13_t4_page.py'), mode],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        ' actual page must pass with March and fail agreement without it: '
        + result.stdout[-1000:]
        + result.stderr[-2000:]
    )
    assert ' actual page agreement and escape checked' in result.stdout, (
        ' page must reach the comparison and kernel-disable control'
    )


def test_cli_extension_consumes_free_march_ratio(tmp_path):
    root = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2'
    project = edi.Project.load(root / 'project')
    experiment = project.experiments[0]
    assert hasattr(experiment, 'preferred_orientation'), (
        ' missing capability: CLI project must load March orientation'
    )
    rows = list(experiment.preferred_orientation)
    assert rows and any(row.march_r.free for row in rows), (
        ' CLI exercise march_r must be loaded as a free model parameter'
    )
    row = rows[0]
    row.march_r.value = 0.73
    project.analysis.calculate()
    corrected = np.asarray(experiment.data.intensity_calc).copy()
    row.march_r.value = 1.0
    project.analysis.calculate()
    assert not np.allclose(corrected, experiment.data.intensity_calc, rtol=1e-7, atol=1e-7), (
        ' CLI march_r exercise must change the calculated pattern'
    )
    project.save_as(tmp_path / 'saved')
    restored = edi.Project.load(tmp_path / 'saved')
    assert restored.experiments[0].preferred_orientation[0].march_r.free, (
        ' CLI free declaration must survive project persistence'
    )
