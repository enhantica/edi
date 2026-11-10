"""gate 2: file-system save/load round trips preserve calculator declarations."""

from __future__ import annotations

import importlib
import shlex
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LIB = importlib.import_module('edi')
SEEDS = {
    'cosio-d20-s1': 'pd-neut-cwl_cosio-d20_start-1',
    'cosio-d20-s4': 'pd-neut-cwl_cosio-d20_start-4',
    'ncaf-wish-2bank-s3': 'pd-neut-tof_ncaf-wish-2bank_start-3',
    'si-sepd-s2': 'pd-neut-tof_si-sepd_start-2',
    'si-sepd-s5': 'pd-neut-tof_si-sepd_start-5',
}


def project_path(seed):
    if LIB.__name__ == 'crysta':
        return ROOT / 'tests/fitting' / seed / 'project'
    return ROOT / 'docs/user/cli' / SEEDS[seed] / 'project'


def calculators(path):
    return [
        shlex.split(line)[1]
        for line in path.read_text().splitlines()
        if line.startswith('_calculator.type ')
    ]


def test_e04_t5_writer_emits_calculator_on_each_experiment(tmp_path):
    project = LIB.Project.load(project_path('ncaf-wish-2bank-s3'))
    project.save_as(tmp_path / 'first')
    files = sorted((tmp_path / 'first/experiments').glob('*.edi'))
    assert len(files) == 2, ' gate 2 writer retains both input experiments'
    for path in files:
        assert calculators(path) == ['crysta'], (
            ' gate 2 the authoritative writer emits _calculator.type crysta per experiment'
        )
    LIB.Project.load(tmp_path / 'first').save_as(tmp_path / 'second')
    assert all(
        calculators(path) == ['crysta'] for path in (tmp_path / 'second/experiments').glob('*.edi')
    ), ' gate 2 supported calculator declaration survives another load/save round trip'


@pytest.mark.parametrize('declared', ['cryspy', 'unsupported-backend', 'crysta', None])
def test_e04_t5_unsupported_calculator_warns_and_saves_crysta(tmp_path, capfd, declared):
    source = tmp_path / 'input'
    shutil.copytree(project_path('si-sepd-s2'), source)
    experiment = next((source / 'experiments').glob('*.edi'))
    lines = [
        line
        for line in experiment.read_text().splitlines()
        if not line.startswith('_calculator.type ')
    ]
    if declared is not None:
        lines.insert(1, '_calculator.type ' + declared)
    experiment.write_text('\n'.join(lines) + '\n')
    project = LIB.Project.load(source)
    warning = capfd.readouterr().err
    expected = (
        ''
        if declared in {None, 'crysta'}
        else (f'Warning: unsupported _calculator.type "{declared}" - using crysta\n')
    )
    assert warning == expected, (
        ' gate 2 load preserves the owner-declared unsupported-calculator warning'
    )
    project.save_as(tmp_path / 'saved')
    output = list((tmp_path / 'saved/experiments').glob('*.edi'))
    assert len(output) == 1, ' gate 2 saving retains the input experiment'
    assert calculators(output[0]) == ['crysta'], (
        ' gate 2 supported, missing and unsupported inputs all save the supported calculator'
    )
