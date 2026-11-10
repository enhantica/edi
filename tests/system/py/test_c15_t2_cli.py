"""new CLI project is registered, carries both terms and actually executes."""

import subprocess
import sys
from pathlib import Path

import edi

from tools.checks.cli_projects import registry

ROOT = Path(__file__).resolve().parents[3]
PROJECT = 'pd-xray-cwl_lif_single'


def test_lif_cli_project_is_in_executing_set_and_reproduces_its_expectations():
    rows = [row for row in registry(ROOT) if row['id'] == PROJECT]
    assert len(rows) == 1 and rows[0]['executing'], (
        ' missing capability: pd-xray-cwl_lif_single in the CLI executing set'
    )
    project = edi.Project.load(ROOT / 'docs/user/cli' / PROJECT / 'project')
    instrument = project.experiment.instrument
    assert instrument.setup_polarization_coefficient.value != 0.0, (
        ' CLI project must exercise nonzero polarization coefficient'
    )
    assert instrument.setup_monochromator_twotheta.value != 0.0, (
        ' CLI project must exercise nonzero monochromator angle'
    )
    result = subprocess.run(
        [sys.executable, 'tools/checks/cli_projects.py', '--project', PROJECT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        ' new CLI project must run and reproduce its committed quantities: '
        + result.stdout
        + result.stderr
    )
