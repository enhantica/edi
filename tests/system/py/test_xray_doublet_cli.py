"""The existing LiF CLI project exercises the second wavelength and absorption."""

import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tools.checks.cli_projects import registry

ROOT = Path(__file__).resolve().parents[3]
PROJECTS = ('pd-xray-cwl_lif_single', 'pd-xray-cwl_pbso4-lab_round-robin')


@pytest.mark.parametrize('project_id', PROJECTS)
def test_cli_executes_doublet_and_declared_corrections(project_id):
    rows = [row for row in registry(ROOT) if row['id'] == project_id]
    assert len(rows) == 1, 'Each X-ray case must have its declared CLI project'
    assert rows[0]['executing'], 'Both X-ray projects must be in the CLI executing set'
    project = edi.Project.load(ROOT / 'docs/user/cli' / project_id / 'project')
    instrument = project.experiment.instrument
    assert hasattr(instrument, 'setup_wavelength_2'), (
        'The CLI instrument must carry the second wavelength'
    )
    assert instrument.setup_wavelength_2.value != instrument.setup_wavelength.value, (
        'The CLI must exercise distinct wavelengths'
    )
    assert instrument.setup_wavelength_2_to_1_ratio.value > 0, (
        'The CLI must exercise a nonzero second-component ratio'
    )
    if project_id == PROJECTS[0]:
        assert project.experiment.absorption.mu_r.value > 0, (
            'The LiF CLI must exercise nonzero X-ray absorption'
        )
    result = subprocess.run(
        [sys.executable, 'tools/checks/cli_projects.py', '--project', project_id],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'The CLI shipment check must execute and reproduce the project quantities: '
        + result.stdout
        + result.stderr
    )
