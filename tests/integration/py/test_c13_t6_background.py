"""independent background traces, declared dispatch and linear invariants.

FullProf owns the .bac values; NumPy's documented polynomial definitions own
basis/derivative values. No correctness value comes from the engine under test.
"""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c13_t6_background'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())
CASES = tuple(REFERENCE['cases'])
MATERIALIZE = runpy.run_path(str(FIXTURE / 'project.py'))['materialize']


def _trace(case):
    row = REFERENCE['cases'][case]
    x, y = np.loadtxt(FIXTURE / (case + '.bac'), comments='!').T
    # Ppl=2 writes the axis minus Zero; the polynomial uses the observed axis.
    return row, x + row['zero'], y


def basis(row, x):
    count = len(row['coefficients'])
    if row['type'] == 'chebyshev':
        z = (2 * x - row['x_min'] - row['x_max']) / (row['x_max'] - row['x_min'])
        return np.polynomial.chebyshev.chebvander(z, count - 1)
    return np.polynomial.polynomial.polyvander(x / row['origin'] - 1, count - 1)


def load_project(tmp_path, row, x, observed=None, **kwargs):
    if observed is None:
        observed = np.zeros_like(x)
    return engine.Project.load(MATERIALIZE(tmp_path, row, x, observed, **kwargs))


def _background(project):
    project.analysis.calculate()
    return np.asarray(project.experiment.data.intensity_bkg).copy()


@pytest.mark.parametrize('case', CASES)
def test_independent_trace_and_closed_form_control(case):
    row, x, expected = _trace(case)
    for filename, digest in row['sha256'].items():
        assert hashlib.sha256((FIXTURE / filename).read_bytes()).hexdigest() == digest, (
            ' independent FullProf artifacts must retain their authoring hashes'
        )
    actual = basis(row, x) @ np.asarray(row['coefficients'])
    assert np.max(np.abs(actual - expected)) < row['bac_tolerance'], (
        ' the FullProf trace must match its independently evaluated background definition '
        'within the declared single-precision and printed-coordinate allowance'
    )


@pytest.mark.parametrize('case', CASES)
def test_declared_kernel_matches_every_fullprof_background_point(tmp_path, case):
    row, x, expected = _trace(case)
    project = load_project(tmp_path / 'input', row, x)
    actual = _background(project)
    assert actual.shape == expected.shape, (
        ' background calculation must retain every independent FullProf coordinate'
    )
    assert np.isfinite(actual).all(), ' each background value must remain finite'
    assert np.max(np.abs(actual - expected)) < row['bac_tolerance'], (
        ' declared Chebyshev/plain polynomial dispatch must match the FullProf Ppl=2 trace '
        'over the whole pattern, including nontrivial origin/range normalization'
    )


@pytest.mark.parametrize('case', CASES)
def test_line_segment_prior_art_remains_declared_and_distinct(tmp_path, case):
    row, x, _ = _trace(case)
    x = x[:: max(1, len(x) // 41)]
    project = load_project(tmp_path / 'line', row, x, kind='line-segment')
    expected = 10 + 25 * (x - x[0]) / (x[-1] - x[0])
    assert np.allclose(_background(project), expected, rtol=0, atol=1e-10), (
        ' the original declared line-segment kernel must retain linear interpolation'
    )
    polynomial = load_project(tmp_path / 'polynomial', row, x)
    assert not np.allclose(_background(polynomial), expected, rtol=0, atol=1), (
        ' switching the background declaration on the same structural/instrument model '
        'must select a different calculation'
    )


@pytest.mark.parametrize('case', CASES)
def test_nonconstant_zero_intercept_does_not_select_line_segment(tmp_path, case):
    row, _, _ = _trace(case)
    x = np.linspace(row['x_min'], row['x_max'], 43)
    coefficients = np.zeros(len(row['coefficients']))
    coefficients[1] = 17.3
    project = load_project(tmp_path, row, x, coefficients=coefficients)
    assert np.allclose(_background(project), basis(row, x) @ coefficients, rtol=0, atol=1e-10), (
        ' a zero intercept must retain the declared nonconstant model'
    )


@pytest.mark.parametrize('case', CASES)
def test_background_declaration_values_and_free_flags_survive_two_saves(tmp_path, case):
    row, _, _ = _trace(case)
    x = np.linspace(row['x_min'], row['x_max'], 43)
    coefficients = np.asarray(row['coefficients']) + np.arange(len(row['coefficients'])) / 10
    selected = [0, len(coefficients) // 2, len(coefficients) - 1]
    project = load_project(tmp_path / 'input', row, x, coefficients=coefficients, free=selected)
    expected = basis(row, x) @ coefficients
    for generation in range(2):
        destination = tmp_path / f'save-{generation}'
        project.save_as(destination)
        project = engine.Project.load(destination)
        assert len(project.free_parameters) == len(selected), (
            ' both saves must preserve the mixed fixed/free coefficient set'
        )
        actual_free = np.asarray([parameter.value for parameter in project.free_parameters])
        assert np.allclose(actual_free, coefficients[selected], rtol=0, atol=1e-10), (
            ' both saves must retain the identities of the free coefficients'
        )
        assert np.allclose(_background(project), expected, rtol=0, atol=1e-8), (
            ' saved coefficient values, type and normalization must preserve the calculation'
        )


@pytest.mark.parametrize('case', CASES)
def test_public_fit_recovers_all_coefficients_from_independentbasis(case):
    row, _, _ = _trace(case)
    x = np.linspace(row['x_min'], row['x_max'], 71)
    target = np.asarray(row['coefficients'])
    observed = basis(row, x) @ target
    # Same independent coefficient target/start/free set, now a manifest-declared corpus case.
    source = corpus_case_dir('background-' + case) / 'project'
    # The runtime policy supplies a session-private corpus copy. Public fit does not save.
    project = engine.Project.load(source)
    assert np.allclose(project.experiment.data.intensity_meas, observed, rtol=0, atol=1e-10), (
        ' the corpus must retain the same independent closed-form observations'
    )
    start = np.asarray([parameter.value for parameter in project.free_parameters])
    assert np.allclose(start, target + np.linspace(0.1, 0.7, len(target)), rtol=0, atol=1e-10), (
        ' every corpus coefficient must start displaced from its independent target'
    )
    assert len(project.free_parameters) == len(target), (
        ' a coefficient-only fit must include every coefficient, including zero high orders'
    )
    project.analysis.fit()
    actual = np.asarray([parameter.value for parameter in project.free_parameters])
    assert np.allclose(actual, target, rtol=0, atol=2e-5), (
        ' the public fit with its linear seed and polish must recover every coefficient '
        'from independent closed-form observations'
    )
    assert np.allclose(_background(project), observed, rtol=0, atol=2e-5), (
        ' the fitted background must consume the recovered model-owned coefficients'
    )


def _load_and_calculate(directory):
    project = engine.Project.load(directory)
    project.analysis.calculate()


@pytest.mark.parametrize(
    'damage', ['missing-type', 'unknown-type', 'zero-origin', 'nan-coef', 'duplicate-order']
)
def test_invalid_polynomial_declarations_refuse_before_calculation(tmp_path, damage):
    row, _, _ = _trace('pearl')
    x = np.linspace(row['x_min'], row['x_max'], 31)
    directory = MATERIALIZE(tmp_path, row, x, np.zeros_like(x))
    file = directory / 'experiments/experiment.edi'
    text = file.read_text()
    replacement = {
        'missing-type': ('_background.type polynomial\n', ''),
        'unknown-type': ('_background.type polynomial', '_background.type unsupported-polynomial'),
        'zero-origin': ('_background.origin 7000', '_background.origin 0'),
        'nan-coef': ('0 2181.025', '0 nan'),
        'duplicate-order': ('1 221.414', '0 221.414'),
    }
    old, new = replacement[damage]
    assert old in text, ' each malformed-input witness must reach the named declaration'
    file.write_text(text.replace(old, new, 1))
    with pytest.raises((ValueError, RuntimeError)):
        _load_and_calculate(directory)
