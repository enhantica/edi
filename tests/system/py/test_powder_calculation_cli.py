"""The published powder projects exercise the ordinary fit command and its saved state."""

import math
import os
import shutil
import subprocess
from pathlib import Path

import edi
import gemmi
import pytest

ROOT = Path(__file__).resolve().parents[3]
METHOD = '_structure.calc_method'
INTENSITY_FIELDS = ('structure_id', 'index_h', 'index_k', 'index_l', 'f_squared')


@pytest.mark.parametrize(
    ('example', 'method'),
    [
        ('pd-neut-cwl_lbco-hrpt_le-bail', 'le_bail'),
        ('pd-xray-cwl_pbso4-lab_pawley', 'pawley'),
    ],
)
def test_example_fits_and_saves_extracted_rows(tmp_path, example, method):
    source = ROOT / 'docs/user/cli' / example / 'project'
    assert (source / 'project.edi').is_file(), (
        'The documented powder fit supplies a native project'
    )
    work = tmp_path / 'project'
    shutil.copytree(source, work)
    phase = only_block(work / 'structures')
    detector = only_block(work / 'experiments')
    structure = read_block(phase).name
    assert read_block(phase).find_value(METHOD) == method, (
        'The shipped project declares its intended calculation method on the structure'
    )
    run = subprocess.run(
        [str(cli()), 'fit', str(work), '--report', 'machine'],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert run.returncode == 0, (
        'The ordinary fit command runs the declared powder method: ' + run.stdout + run.stderr
    )
    assert 'converged=true' in run.stdout.splitlines(), (
        'The shipped measured powder fit reports convergence through the CLI'
    )
    assert read_block(phase).find_value(METHOD) == method, 'CLI write-back preserves the method'
    data = read_block(detector)
    rows = data.find([f'_extracted_intensity.{name}' for name in INTENSITY_FIELDS])
    assert len(rows) > 0, 'The fit command publishes the native extracted-intensity loop'
    keys = [(row[0], *(int(row[index]) for index in range(1, 4))) for row in rows]
    assert len(keys) == len(set(keys)), (
        'CLI output stores one squared factor per structure and hkl'
    )
    assert all(key[0] == structure for key in keys), 'The CLI fit state names its owning structure'
    reopened = edi.Project.load(work).experiment.extracted_intensities
    assert {(row.structure_id, row.index_h, row.index_k, row.index_l) for row in reopened} == set(
        keys
    ), 'The native reader restores every orbit written by the CLI'
    strengths = [row.f_squared for row in reopened]
    assert all(math.isfinite(value) and value >= 0 for value in strengths), (
        'The fitted CLI example saves finite nonnegative squared factors'
    )
    assert any(value > 0 for value in strengths), (
        'The measured CLI fit extracts at least one positive squared factor'
    )
    if method == 'pawley':
        assert any(
            row.f_squared_su is not None
            and math.isfinite(row.f_squared_su)
            and row.f_squared_su > 0
            for row in reopened
        ), 'The Pawley CLI example retains a positive fitted intensity standard uncertainty'


def only_block(folder):
    paths = sorted(folder.glob('*.edi'))
    assert len(paths) == 1, 'Each shipped powder fit defines one structure and one experiment'
    return paths[0]


def read_block(path):
    return gemmi.cif.read_file(str(path)).sole_block()


def cli():
    candidates = [
        os.environ.get('EDI_CLI_EXECUTABLE'),
        ROOT / 'build/ci-consumer/cli/easydiffraction',
        ROOT / 'build/ci/cli/easydiffraction',
    ]
    binary = next((Path(path) for path in candidates if path and Path(path).is_file()), None)
    assert binary is not None, 'The published powder projects run through the standalone command'
    return binary
