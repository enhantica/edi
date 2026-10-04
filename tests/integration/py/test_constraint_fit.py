"""Dependent covariance and write-back against rational normal equations."""

import json
import math
import runpy
from pathlib import Path

import edi as engine
import pytest

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/constraint_expressions'
MATERIALIZE = runpy.run_path(str(FIXTURE / 'project.py'))['materialize']
REFERENCE = json.loads((FIXTURE / 'covariance.json').read_text())
ALIASES = [
    ('a', 'bank.background.base.coef'),
    ('b', 'bank.background.ramp.coef'),
    ('c', 'bank.background.curve.coef'),
]


def coefficient_project():
    return engine.Project.load(corpus_case_dir('constraint-covariance') / 'project')


def test_full_covariance_reaches_dependent_writeback_and_undo(tmp_path):
    project = coefficient_project()
    assert len(project.free_parameters) == 2, (
        'the dependent LINEAR coefficient must have no descent column'
    )
    assert REFERENCE['covariance'][0][1] != 0, (
        'the independent least-squares witness must carry cross-covariance'
    )
    assert not math.isclose(
        REFERENCE['dependent_variance'], REFERENCE['diagonal_only_variance'], rel_tol=0.05
    ), 'discarding covariance must measurably change the dependent uncertainty'
    project.analysis.fit()
    terms = dict(zip(('base', 'ramp', 'curve'), project.experiment.background_terms, strict=True))
    for name, expected in zip(('base', 'ramp', 'curve'), (5, 2, 3), strict=True):
        assert terms[name].coef.value == pytest.approx(expected, abs=2e-5), (
            'the constrained polynomial fit must recover the independent rational solution'
        )
    assert terms['curve'].coef.value == terms['base'].coef.value - terms['ramp'].coef.value, (
        'fit write-back must satisfy the declared relation exactly'
    )
    expected_sigma = math.sqrt(REFERENCE['dependent_variance'])
    assert terms['curve'].coef.uncertainty == pytest.approx(expected_sigma, rel=2e-4, abs=1e-8), (
        'dependent uncertainty must retain the independently derived off-diagonal covariance'
    )
    for index, name in enumerate(('base', 'ramp')):
        assert terms[name].coef.uncertainty == pytest.approx(
            math.sqrt(REFERENCE['covariance'][index][index]), rel=2e-4
        ), (
            'independent uncertainties must use the rational normal equations '
            'and the independent degrees of freedom'
        )
    assert not terms['curve'].coef.free, (
        'a participating LINEAR dependent must remain outside every solve'
    )
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert '_fit_parameter.id' in text, 'the fit must persist its independent start rows'
    fit_rows = [
        line.split()[0]
        for line in text.splitlines()
        if line.startswith(('bank.background', 'experiment.background'))
    ]
    assert len(fit_rows) == 2, 'only the two independent coefficients may own fit-start rows'
    assert not any('curve' in row or '[2]' in row for row in fit_rows), (
        'a dependent must never acquire an independent fit-start row'
    )
    project.undo_fit()
    assert terms['base'].coef.value == 4, 'undo must restore the first independent start'
    assert terms['ramp'].coef.value == 1, 'undo must restore both independent starts'
    assert terms['curve'].coef.value == 3, (
        'undo must recompute the non-identity dependent from restored independents'
    )


def test_independent_covariance_generator_reproduces_the_committed_reference():
    actual = runpy.run_path(str(FIXTURE / 'generate.py'))['reference']()
    assert actual == REFERENCE, (
        'the covariance fixture must remain reproducible without either engine'
    )
