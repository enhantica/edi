"""Preserve the cctbx site tensor through the public model lifecycle."""

import importlib

import numpy as np
import pytest

from tests.fixtures.adp_site_symmetry import model

ENGINE = importlib.import_module('edi')
CASES = [(name, kind) for name in model.SITES for kind in model.KINDS]


def assert_subspace(values, row, kind):
    basis = model.basis(row, kind)
    np.testing.assert_allclose(
        basis @ np.linalg.pinv(basis) @ values,
        values,
        rtol=2e-12,
        atol=2e-13,
        err_msg='Every live tensor must obey its independently tabulated site symmetry',
    )


def assert_tensor(project, row, kind, atom, expected=None):
    assert model.site(project, atom).adp_type == kind, (
        'Every tensor must retain its declared ADP representation'
    )
    values = model.components(project, atom)
    basis = model.basis(row, kind)
    assert_subspace(values, row, kind)
    if expected is not None:
        np.testing.assert_allclose(
            values,
            expected,
            rtol=2e-12,
            atol=2e-13,
            err_msg='All six components must follow the authored independent tensor values',
        )
    parameters = model.parameters(project, atom)
    independent = [
        i for i, parameter in enumerate(parameters) if not parameter.symmetry_constrained
    ]
    assert len(independent) == row['rank'], (
        'The editable tensor dimensions must equal the cctbx site rank'
    )
    assert np.linalg.matrix_rank(basis[independent]) == row['rank'], (
        'Editable components must span the complete allowed tensor'
    )
    if row['it'] == 221:
        assert independent == [0], (
            'The reported m-3m site edits ani11 with ani22 and ani33 as followers'
        )
    for parameter in parameters:
        if parameter.symmetry_constrained:
            parameter.free = True
            assert not parameter.free, 'A symmetry follower must remain outside the free set'
    iso = model.site(project, atom).adp_iso
    assert iso.value == pytest.approx(model.equivalent(row, kind, values), rel=2e-12, abs=2e-13), (
        'Beq or Ueq must use the complete tensor and the nonorthogonal metric'
    )
    assert not iso.free, 'A tensor equivalent must remain read-only in the fit model'
    return independent


def load(root, row, kind, **kwargs):
    return ENGINE.Project.load(model.materialize(root, row, kind, **kwargs))


@pytest.mark.parametrize(('name', 'kind'), CASES)
def test_loaded_same_site_atoms_retain_each_complete_tensor(tmp_path, name, kind):
    row = model.SITES[name]
    project = load(tmp_path / 'input', row, kind)
    for atom in range(2):
        assert_tensor(project, row, kind, atom, model.tensor(row, kind, atom))


@pytest.mark.parametrize('source', ['Uiso', 'Biso', *model.KINDS])
@pytest.mark.parametrize(('name', 'kind'), CASES)
def test_each_adp_conversion_completes_both_same_site_tensors(tmp_path, name, kind, source):
    row = model.SITES[name]
    expected = {atom: model.tensor(row, kind, atom) for atom in range(2)}
    overrides = {}
    if source in model.KINDS:
        original_basis = model.basis(row, source)
        leaders = []
        for index in range(6):
            if np.linalg.matrix_rank(original_basis[[*leaders, index]]) > len(leaders):
                leaders.append(index)
        for atom in range(2):
            value = model.tensor(row, source, atom).copy()
            value[leaders[0]] *= 1.17
            coefficients = np.linalg.solve(original_basis[leaders], value[leaders])
            overrides[atom] = original_basis @ coefficients
            expected[atom] = model.basis(row, kind) @ coefficients
    project = load(tmp_path / 'input', row, source, overrides=overrides)
    for atom in range(2):
        model.site(project, atom).adp_type = kind
        assert_tensor(project, row, kind, atom, expected[atom])
        for previous in range(atom):
            assert_tensor(project, row, kind, previous, expected[previous])


@pytest.mark.parametrize(('name', 'kind'), CASES)
def test_each_edit_updates_followers_equivalent_and_saved_reload(tmp_path, name, kind):
    row = model.SITES[name]
    project = load(tmp_path / 'input', row, kind)
    for atom in range(2):
        indices = assert_tensor(project, row, kind, atom)
        basis = model.basis(row, kind)
        for generation, index in enumerate(indices):
            old_other = model.components(project, 1 - atom).copy()
            values = model.components(project, atom).copy()
            values[index] += max(abs(values[index]), np.max(np.abs(values)) * 0.1) * 0.17
            expected = basis @ np.linalg.solve(basis[indices], values[indices])
            model.parameters(project, atom)[index].value = float(values[index])
            assert_tensor(project, row, kind, atom, expected)
            assert_tensor(project, row, kind, 1 - atom, old_other)
            destination = tmp_path / f'saved-{atom}-{generation}'
            project.save_as(destination)
            project = ENGINE.Project.load(destination)
            assert_tensor(project, row, kind, atom, expected)
            assert_tensor(project, row, kind, 1 - atom, old_other)


@pytest.mark.parametrize(
    ('name', 'kind', 'ordinal'),
    [
        (name, kind, ordinal)
        for name, kind in CASES
        for ordinal in range(model.SITES[name]['rank'])
    ],
)
def test_a_completed_fit_moves_each_seed_and_preserves_its_full_site_tensor(
    tmp_path, name, kind, ordinal
):
    row = model.SITES[name]
    probe = load(tmp_path / 'probe', row, kind)
    indices = assert_tensor(probe, row, kind, 0)
    index = indices[ordinal]
    basis = model.basis(row, kind)
    for atom in range(2):
        original = model.tensor(row, kind, atom)
        desired = original.copy()
        desired[index] += max(abs(desired[index]), np.max(np.abs(desired)) * 0.1) * 0.17
        target = basis @ np.linalg.solve(basis[indices], desired[indices])
        stimulus = load(tmp_path / f'stimulus-{atom}', row, kind, overrides={atom: target})
        stimulus.analysis.calculate()
        # Calculated intensities are fit stimuli, never an independent diffraction accuracy oracle.
        measured = np.asarray(stimulus.experiments[0].data.intensity_calc).copy()
        project = load(tmp_path / f'fit-{atom}', row, kind, measured=measured)
        for parameter in project.parameters:
            parameter.free = False
        parameter = model.parameters(project, atom)[index]
        start = parameter.value
        parameter.free = True
        result = project.analysis.fit()
        assert result.success, 'The site-symmetry witness must reach successful fit completion'
        assert abs(parameter.value - start) > abs(desired[index] - start) * 0.01, (
            'The completed fit must actually move the selected free component'
        )
        assert_tensor(project, row, kind, atom)
        assert_tensor(project, row, kind, 1 - atom, model.tensor(row, kind, 1 - atom))
        project.save_as(tmp_path / f'fit-saved-{atom}')
        reopened = ENGINE.Project.load(tmp_path / f'fit-saved-{atom}')
        assert_tensor(reopened, row, kind, atom, model.components(project, atom))


@pytest.mark.parametrize('name', ['cubic', 'tetragonal', 'hexagonal'])
@pytest.mark.parametrize('kind', model.KINDS)
def test_independent_subspace_refuses_the_reported_missing_follower(name, kind):
    row = model.SITES[name]
    values = model.tensor(row, kind).copy()
    assert_subspace(values, row, kind)
    values[1] = 0
    with pytest.raises(AssertionError, match='independently tabulated site symmetry'):
        assert_subspace(values, row, kind)


@pytest.mark.parametrize('name', ['hexagonal', 'general'])
@pytest.mark.parametrize('kind', model.KINDS)
def test_full_metric_trace_distinguishes_omitted_cross_terms(name, kind):
    row = model.SITES[name]
    values = model.tensor(row, kind).copy()
    expected = 0.023 if kind == 'Uani' else model.BISO
    assert model.equivalent(row, kind, values) == pytest.approx(expected, rel=2e-14), (
        'The trace of the independently tabulated isotropic tensor must recover its cctbx scalar'
    )
    values[3:] = 0
    assert abs(model.equivalent(row, kind, values) - expected) > expected * 0.01, (
        'The nonorthogonal fixture must expose an equivalent computed without the cross terms'
    )
