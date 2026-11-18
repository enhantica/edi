"""Reflection admission against exact structure factors and least squares."""

import importlib

import numpy as np

from tests.fixtures.fitting_correctness.admission import column
from tests.fixtures.fitting_correctness.project import materialize

ENGINE = 'edi'
B_SQUARED = 1.03**2
OBSERVED = np.array([1000.0, 10.0, 14.0, -2.0])


def load(root, **options):
    return importlib.import_module(ENGINE).Project.load(materialize(root, **options))


def test_exclusion_survives_save_reload_without_changing_measurements(tmp_path):
    project = load(tmp_path / 'input', status=True)
    project.save_as(tmp_path / 'declared')
    declared = (tmp_path / 'declared/experiments/bank.edi').read_text()
    for tag, expected in (('index_h', ['1']), ('index_k', ['0']), ('index_l', ['0'])):
        assert column(declared, '_excluded_reflection.' + tag) == expected, (
            'An uncalculated save preserves the complete declared exclusion tuple'
        )
    project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    saved = (tmp_path / 'saved/experiments/bank.edi').read_text()
    assert column(saved, '_refln.include_status')[0] == 'x', (
        'A calculated save marks the user-excluded measurement in its computed status column'
    )
    reloaded = importlib.import_module(ENGINE).Project.load(tmp_path / 'saved')
    assert list(reloaded.experiments[0].refln.intensity_meas) == OBSERVED.tolist(), (
        'An exclusion round trip must retain every signed measured intensity'
    )


def test_single_crystal_scale_derivative_matches_finite_difference(tmp_path):
    project = load(tmp_path)
    scale = project.experiments[0].linked_structure.scale
    values = []
    for value in (2.3 - 1e-4, 2.3 + 1e-4):
        scale.value = value
        project.analysis.calculate()
        values.append(np.array(project.experiments[0].refln.intensity_calc, copy=True))
    np.testing.assert_allclose(
        (values[1] - values[0]) / 2e-4,
        np.full(4, B_SQUARED),
        rtol=1e-9,
        err_msg='At a non-unit scale, dI/dscale must equal the one-atom closed-form F squared',
    )


def test_opening_saved_single_crystal_keeps_its_declared_scale(tmp_path):
    project = load(tmp_path)
    assert project.experiments[0].linked_structure.scale.value.hex() == (2.3).hex(), (
        'Opening a saved project must preserve its declared scale; only '
        'measured-data and phase edits initialize it'
    )
