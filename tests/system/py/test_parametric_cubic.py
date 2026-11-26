"""Noiseless inverse recovery uses frozen observations and authored parameter truth."""

import json
import shutil
from pathlib import Path

import edi as engine
import pytest

from tests.fixtures.parametric_series import cases

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures/parametric_series'


def test_five_cubic_patterns_recover_shared_profile_and_local_parameters(tmp_path):
    truth = json.loads((FIXTURE / 'cubic-truth.json').read_text())
    root = tmp_path / 'series'
    shutil.copytree(FIXTURE / 'cubic', root)
    engine.Project.load(root).analysis.fit()
    rows = cases.rows(root)
    assert len(rows) == 5, 'Every frozen cubic pattern participates in the parametric solution'
    for index, row in enumerate(rows):
        values = {
            'phase.cell.length_a': truth['cell'][index],
            'phase.atom_site.A.adp_iso': truth['biso'][index],
            'zeta.linked_structure.phase.scale': truth['scale'][index],
            **{'zeta.peak.' + key: value for key, value in truth['profile'].items()},
        }
        for name, expected in values.items():
            assert float(row[name]) == pytest.approx(expected, rel=1e-6), (
                'The noiseless inverse fit recovers the authored shared and per-point truth'
            )
