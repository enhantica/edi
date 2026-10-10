"""Smoke executes both paths in edi's selected, SDK-linked native image."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
PROBE = r"""
import ctypes,json,sys,shutil,tempfile
from pathlib import Path
import edi
import edi._edi as native
import numpy as np
from tests.model_calculation import calculate_on_grid
image=ctypes.CDLL(native.__file__)
lanes=image._ZN6crysta17crysta_simd_lanesEv
lanes.restype=ctypes.c_int
count=image._ZN6crysta20jvd_simd_invocationsEv
count.restype=ctypes.c_size_t
image._ZN6crysta26reset_jvd_simd_invocationsEv()
scratch_owner=tempfile.TemporaryDirectory()
scratch=Path(scratch_owner.name)/'project'
shutil.copytree(sys.argv[1],scratch)
profile='\n'.join(['_peak.type tof-jorgensen-von-dreele',
 '_peak.broad_lorentz_gamma_0 0.37', '_peak.broad_lorentz_gamma_1 0',
 '_peak.broad_lorentz_gamma_2 0', '_peak.broad_lorentz_size 0', '_peak.broad_lorentz_strain 0'])
for file in (scratch/'experiments').glob('*.edi'):
    file.write_text(file.read_text().replace('_peak.type tof-jorgensen',profile))
project=edi.Project.load(scratch)
project.experiment.peak.broad_lorentz_gamma_0.value=0.37
grid=np.linspace(21600.0,23780.0,149)
values=calculate_on_grid(edi,project,grid)
print(json.dumps({'lanes':lanes(),'calls':count(),'values':values.tolist()}))
"""


def payload(mode):
    env = os.environ.copy()
    env['CRYSTA_SIMD_LANES'] = '0' if mode == 'scalar' else '8'
    env['OMP_NUM_THREADS'] = '1'
    result = subprocess.run(
        [sys.executable, '-c', PROBE, str(ROOT / 'tests/fixtures/e02_t2_ncaf_5bank/project')],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
    )
    assert result.returncode == 0, (
        'CI policy: smoke must import and execute the actually selected SDK-linked edi image: '
        + result.stdout
        + result.stderr
    )
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.parametrize('mode', ['scalar', 'simd'])
def test_selected_sdk_executes_scalar_and_simd_values(mode):
    observed = payload(mode)
    other = payload('simd' if mode == 'scalar' else 'scalar')
    assert observed['lanes'] == 0 if mode == 'scalar' else observed['lanes'] >= 2, (
        'CI policy: scalar and SIMD smoke must exercise their declared live dispatch widths'
    )
    assert observed['calls'] == 0 if mode == 'scalar' else observed['calls'] > 0, (
        'CI policy: SIMD smoke observes real wide-kernel invocations and scalar '
        'smoke observes none'
    )
    values = np.asarray(observed['values'])
    assert values.shape == (149,) and np.isfinite(values).all() and np.any(values > 0), (
        'CI policy: both dispatch modes calculate a nontrivial finite physical pattern'
    )
    # Same-operation invariant; tolerance is the frozen ADR-0035 scalar/SIMD comparison.
    np.testing.assert_allclose(
        values,
        other['values'],
        rtol=2e-11,
        atol=2e-7,
        err_msg='CI policy: SIMD and scalar values agree within the prior numerical budget',
    )
