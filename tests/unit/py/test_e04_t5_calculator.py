"""gate 2: calculator declarations are read from CIF, never engine output pins."""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = 'edi'
SEEDS = {
    'cosio-d20-s1': 'pd-neut-cwl_cosio-d20_start-1',
    'cosio-d20-s4': 'pd-neut-cwl_cosio-d20_start-4',
    'ncaf-wish-2bank-s3': 'pd-neut-tof_ncaf-wish-2bank_start-3',
    'si-sepd-s2': 'pd-neut-tof_si-sepd_start-2',
    'si-sepd-s5': 'pd-neut-tof_si-sepd_start-5',
}


def project_path(seed):
    if PACKAGE == 'crysta':
        return ROOT / 'tests/fitting' / seed / 'project'
    return ROOT / 'docs/user/cli' / SEEDS[seed] / 'project'


def calculators(path):
    return [
        shlex.split(line)[1]
        for line in path.read_text().splitlines()
        if line.startswith('_calculator.type ')
    ]


@pytest.mark.parametrize('seed', sorted(SEEDS))
def test_e04_t5_seed_declares_supported_calculator(seed):
    files = sorted((project_path(seed) / 'experiments').glob('*.edi'))
    assert files, ' gate 2 each switched seed contains experiment files'
    for path in files:
        assert calculators(path) == ['crysta'], (
            ' gate 2 the five former cryspy seeds declare exactly one crysta calculator'
        )
