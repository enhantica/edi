"""Minimal real pre-id writer outputs must remain loadable."""

import json
import shlex
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/legacy_project_load'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_pre_id_engine_save_recovers_every_background_start_by_row(kind, tmp_path):
    source = FIXTURE / kind
    project = engine.Project.load(source)
    bank = project.experiments['bank']
    parameters = (
        [row.intensity for row in bank.background]
        if kind == 'line-segment'
        else [row.coef for row in bank.background_terms]
    )
    actual = [(float(row.start_value), float(row.start_uncertainty)) for row in parameters]
    assert actual == [tuple(values) for values in REFERENCE['projects'][kind]['starts']], (
        'An old engine save must migrate each positional start-state slot to the same declared row'
    )
    saved = tmp_path / 'saved'
    project.save_as(saved)
    tokens = shlex.split((saved / 'analysis/analysis.edi').read_text())
    assert '_fit_parameter.id' in tokens, 'A migrated pre-fit snapshot must remain persistable'
    second = tmp_path / 'second'
    engine.Project.load(saved).save_as(second)
    assert (saved / 'analysis/analysis.edi').read_bytes() == (
        second / 'analysis/analysis.edi'
    ).read_bytes(), 'Migrated start states must reach a stable saved representation'
