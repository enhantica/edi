"""The FullProf writer emits the space-group spelling expected by FullProf."""

import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = ROOT / 'knowledge/verification/fullprof'


@pytest.mark.parametrize(
    ('case', 'control', 'symbol'),
    [
        ('pd-xray-cwl_lif_single', 'lif_single_unpolarized', 'F m -3 m'),
        ('pd-neut-tof_diamond-dream_basic', 'diamond', 'F d -3 m:1'),
        ('pd-neut-tof_si-sepd', 'fixed', 'F d -3 m'),
    ],
)
def test_fullprof_export_space_group(case, control, symbol, tmp_path):
    candidates = [
        os.environ.get('EDI_CLI_EXECUTABLE'),
        ROOT / 'build/ci-consumer/cli/easydiffraction',
        ROOT / 'build/ci/cli/easydiffraction',
    ]
    binary = next((Path(path) for path in candidates if path and Path(path).is_file()), None)
    assert binary is not None, 'FullProf export must be exercised through the built standalone command'
    source = REFERENCES / case / f'{control}.pcr'
    destination = tmp_path / 'fullprof'
    result = subprocess.run(
        [str(binary), 'export-fullprof', str(source), str(destination), '--fixed'],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    groups = [
        line.partition('<--Space group symbol')[0].strip()
        for line in (destination / 'project.pcr').read_text().splitlines()
        if '<--Space group symbol' in line
    ]
    assert groups == [symbol]
