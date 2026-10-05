"""Profile selection reaches the project-first calculation command."""

import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('token', profiles.TOKENS)
def test_each_cw_profile_is_selectable_from_the_cli(tmp_path, token):
    project = profiles.write_project(tmp_path / 'project', token)
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'calc', str(project)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, (
        'Every declared CW profile must calculate through the native CLI: ' + result.stderr
    )
    assert '_data.intensity_calc' in (project / 'experiments/bank.edi').read_text(), (
        'A successful profile CLI calculation must publish its calculated pattern'
    )
