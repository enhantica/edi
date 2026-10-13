"""Hill-Howard fractions from unequal scales, cell masses and volumes."""

import math
import re

import edi as engine
import numpy as np
import pytest

from tests.fixtures.multiphase import support as case


def weighted_project(path):
    case.write_project(path)
    beta = path / 'structures/beta.edi'
    beta.write_text(beta.read_text() + 'Y a Gd Biso 0.23 0.31 0.47 0.35 0.8\n')
    project = engine.Project.load(path)
    rows = case.links(project.experiments[0])
    rows['alpha'].scale.uncertainty = 0.03
    rows['beta'].scale.uncertainty = 0.012
    return project


def expected(scales):
    cell_masses = (0.7, 1.05)
    q = [
        math.prod(case.LENGTHS[name]) * mass
        for name, mass in zip(('alpha', 'beta'), cell_masses, strict=True)
    ]
    denominator = sum(s * mass_volume for s, mass_volume in zip(scales, q, strict=True))
    fractions = [s * mass_volume / denominator for s, mass_volume in zip(scales, q, strict=True)]
    error = q[0] * q[1] * math.hypot(scales[1] * 0.03, scales[0] * 0.012) / denominator**2
    return fractions, error


def fractions(project):
    project.analysis.calculate()
    rows = case.links(project.experiments[0])
    for name in ('alpha', 'beta'):
        assert hasattr(rows[name], 'weight_fraction'), (
            'Linked structures must expose the Hill-Howard weight fraction with its uncertainty'
        )
    return [rows[name].weight_fraction for name in ('alpha', 'beta')]


def test_hill_howard_values_uncertainties_and_warm_scale_changes(tmp_path):
    project = weighted_project(tmp_path / 'input')
    rows = case.links(project.experiments[0])
    for scales in ((2.75, 0.375), (1.125, 0.875), (2.75, 0.375)):
        for name, scale in zip(('alpha', 'beta'), scales, strict=True):
            rows[name].scale.value = scale
        wanted, error = expected(scales)
        actual = fractions(project)
        np.testing.assert_allclose(
            [item.value for item in actual],
            wanted,
            rtol=2e-12,
            atol=1e-14,
            err_msg='Weight fractions must include scale, occupied cell mass and unit-cell volume',
        )
        np.testing.assert_allclose(
            [item.uncertainty for item in actual],
            [error, error],
            rtol=2e-10,
            atol=1e-14,
            err_msg='Weight-fraction uncertainties must propagate scales through normalization',
        )
        assert sum(item.value for item in actual) == pytest.approx(1.0, abs=1e-14), (
            'Calculated phase weight fractions must sum to unity'
        )


def test_derived_weight_fraction_and_su_are_written_to_edi(tmp_path):
    project = weighted_project(tmp_path / 'input')
    before = [(item.value, item.uncertainty) for item in fractions(project)]
    saved = tmp_path / 'saved'
    project.save_as(saved)
    text = '\n'.join(p.read_text() for p in (saved / 'experiments').glob('*.edi'))
    assert '_linked_structure.weight_fraction' in text, (
        'Saved experiment must carry the derived linked-structure weight fraction'
    )
    lines = text.splitlines()
    index = lines.index('_linked_structure.weight_fraction')
    headers = []
    start = index
    while start and lines[start - 1].startswith('_linked_structure.'):
        start -= 1
    while start < len(lines) and lines[start].startswith('_linked_structure.'):
        headers.append(lines[start])
        start += 1
    column = headers.index('_linked_structure.weight_fraction')
    rows = [line.split() for line in lines[start:] if line.strip()][:2]
    assert len(rows) == 2, 'Saved weight fractions must cover both linked structures'
    assert all(re.fullmatch(r'[-+\d.eE]+\(\d+\)', row[column]) for row in rows), (
        'Each saved weight fraction must include a numeric standard uncertainty'
    )
    restored = engine.Project.load(saved)
    np.testing.assert_allclose(
        [(item.value, item.uncertainty) for item in fractions(restored)],
        before,
        rtol=5e-5,
        atol=1e-9,
        err_msg='Reopened derived fractions must retain their values and nonzero uncertainties',
    )
