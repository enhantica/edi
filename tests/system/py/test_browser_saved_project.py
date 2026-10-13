"""Browser protocol counterfactuals; actual packed-kit runs remain required for UI claims."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    'script', ['web_saved_fit_controls.mjs', 'web_control_geometry_controls.mjs']
)
def test_saved_browser_reference_and_real_row_refuse_wrong_operands(script):
    node = shutil.which('node')
    assert node, 'Browser protocol controls must execute with the declared Node runtime'
    run = subprocess.run(
        [node, str(ROOT / 'tests/system/manual' / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    assert run.returncode == 0, (
        'Actual browser helpers must refuse wrong project, scientific and row-geometry operands: '
        + run.stdout
        + run.stderr
    )
