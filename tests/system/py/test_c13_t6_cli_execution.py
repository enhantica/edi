"""executes each independent background project through the public CLI runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = json.loads((ROOT / 'tests/fixtures/c13_t6_background/reference.json').read_text())


@pytest.mark.parametrize('case', tuple(REFERENCE['cases']))
def test_fullprof_project_fits_through_real_cli_and_records_runtime(tmp_path, case):
    project_id = REFERENCE['cases'][case]['project']
    entries = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    assert any(
        row['id'] == project_id and row['executing'] and not row.get('offline', False)
        for row in entries
    ), ' every FullProf background project must execute in the public CI/verify CLI job'
    bank = tmp_path / 'cli-runtimes.tsv'
    result = subprocess.run(
        [
            sys.executable,
            'tools/checks/cli_projects.py',
            '--project',
            project_id,
            '--bank',
            str(bank),
        ],
        cwd=ROOT,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        ' the real CLI fit must agree with its independent FullProf parameter expectations: '
        + result.stdout
        + result.stderr
    )
    assert bank.is_file() and project_id in bank.read_text(), (
        ' each executed CLI project must record its measured runtime for banking'
    )
