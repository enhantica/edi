"""Derived uncertainties use full input covariance after composing typed relations."""

import itertools
import math
import re

import edi as engine
import gemmi
import numpy as np
import pytest

from tests.fixtures.joint_series import cases, oracle


@pytest.mark.parametrize('source', ['member', 'leader'])
@pytest.mark.parametrize('reopen', [False, True])
def test_shared_ratio_weight_fraction_uses_the_leader_covariance(tmp_path, source, reopen):
    project = cases.ratio_covariance_project(tmp_path / 'input', engine, source=source)
    if reopen:
        project.save_as(tmp_path / 'saved')
        project = engine.Project.load(tmp_path / 'saved')
    project.analysis.calculate()
    expected_sigma = 0.0
    if source == 'leader':
        du, dv = -1 / 9, 2 / 9
        expected_sigma = math.sqrt(
            (du * 0.04) ** 2 + (dv * 0.03) ** 2 + 2 * du * dv * 0.5 * 0.04 * 0.03
        )
    actual = [
        project.experiments[bank].linked_structures['other'].weight_fraction
        for bank in cases.BANKS
    ]
    for bank, value in zip(cases.BANKS, actual, strict=True):
        assert value.value == pytest.approx(1 / 3, abs=1e-12), (
            'Equal ZMV phases with scales u,v and t,t*v/u must have fraction v/(u+v)'
        )
        if source == 'member' and bank == 'zeta':
            assert value.uncertainty in {None, 0}, (
                'Exact leader inputs must not acquire an uncertainty from the member scale'
            )
        else:
            assert value.uncertainty == pytest.approx(expected_sigma, abs=1e-12, rel=1e-5), (
                'The member scale must cancel and the signed leader covariance must propagate'
            )
    assert actual[1].uncertainty == pytest.approx(actual[0].uncertainty or 0, abs=1e-12), (
        'Banks constrained to the same phase ratio must report the same fraction uncertainty'
    )


def moment_project(root):
    cases.base_project(root)
    (root / 'experiments/1_alpha.edi').unlink()
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text().replace('alpha 1\n', ''))
    inputs = np.array([1.2, -0.7, 2.3, 5.1, 6.2, 7.3, 90.0, 100.5, 90.0])
    sigma = np.array([0.04, 0.05, 0.06, 0.01, 0.02, 0.03, 0.07, 0.09, 0.06])
    correlation = np.eye(9)
    for i, j, rho in ((0, 1, 0.35), (1, 4, -0.2), (2, 7, 0.3)):
        correlation[i, j] = correlation[j, i] = rho
    covariance = correlation * np.outer(sigma, sigma)
    names = ['phase.atom_site_moment.A.crystalaxis_' + axis for axis in 'xyz']
    names += [
        'phase.cell.' + name
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ]
    structure = cases.structure(a=5.1, free=False)
    for name, value, su in zip(
        ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'),
        inputs[3:],
        sigma[3:],
        strict=True,
    ):
        structure = re.sub(
            r'(?m)^_cell\.' + name + r' .*$', f'_cell.{name} {value}({su})', structure
        )
    structure += """
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
1 x,y,z,+1
loop_
_space_group_symop_magn_centering.id
_space_group_symop_magn_centering.xyz
1 x,y,z,+1
loop_
_magnetic_form_factor.type_symbol
_magnetic_form_factor.ion
_magnetic_form_factor.j2_coefficient
La La3+ 0
loop_
_atom_site_moment.label
_atom_site_moment.crystalaxis_x
_atom_site_moment.crystalaxis_y
_atom_site_moment.crystalaxis_z
A 1.2(0.04) -0.7(0.05) 2.3(0.06)
"""
    structure = structure.replace('A La a Biso', 'A Co a Biso').replace('La La3+', 'Co Co2+')
    (root / 'structures/phase.edi').write_text(structure)
    text = '\nloop_\n_fit_parameter_correlation.id\n_fit_parameter_correlation.source_kind\n'
    text += (
        '_fit_parameter_correlation.parameter_unique_name_i\n'
        '_fit_parameter_correlation.parameter_unique_name_j\n'
        '_fit_parameter_correlation.correlation\n'
    )
    for index, (i, j) in enumerate(itertools.combinations(range(9), 2)):
        text += f'c{index} deterministic {names[i]} {names[j]} {correlation[i, j]}\n'
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + text)
    return engine.Project.load(root), inputs, covariance


def test_oblique_moment_spherical_view_matches_independent_full_covariance(tmp_path):
    project, inputs, covariance = moment_project(tmp_path / 'input')
    moment = project.structure.atom_site_moment['A']
    assert hasattr(moment, 'spherical'), (
        'Every moment must expose its read-only spherical derived view'
    )
    expected, expected_sigma = cases.propagated_spherical(inputs, covariance)
    actual = moment.spherical
    values = [getattr(actual, name) for name in ('modulus', 'polar', 'azimuth')]
    np.testing.assert_allclose(
        [value.value for value in values],
        expected,
        rtol=1e-9,
        atol=1e-9,
        err_msg='The nonorthogonal cell must enter the Cartesian moment basis',
    )
    np.testing.assert_allclose(
        [value.uncertainty for value in values],
        expected_sigma,
        rtol=3e-5,
        atol=1e-8,
        err_msg='Moment uncertainties must include component and cell cross-covariance',
    )
    with pytest.raises((AttributeError, TypeError)):
        moment.spherical = actual


def test_moment_category_columns_are_saved_and_recomputed_on_load(tmp_path):
    project, inputs, covariance = moment_project(tmp_path / 'input')
    project.save_as(tmp_path / 'saved')
    path = tmp_path / 'saved/structures/phase.edi'
    text = path.read_text()
    block = gemmi.cif.read_string(text).sole_block()
    expected, expected_sigma = cases.propagated_spherical(inputs, covariance)
    for index, item in enumerate(('spherical_modulus', 'spherical_polar', 'spherical_azimuthal')):
        values = list(block.find_values('_atom_site_moment.' + item))
        assert len(values) == 1, 'Each saved moment must carry all three derived category columns'
        oracle.category(
            path.read_text(), '_atom_site_moment.' + item, expected[index], expected_sigma[index]
        )
        assert '(' in values[0], 'A nondegenerate moment column must include its uncertainty'
        text = text.replace(values[0], '9999', 1)
    path.write_text(text)
    expected, expected_sigma = persisted_moment_reference(tmp_path / 'saved')
    restored = engine.Project.load(tmp_path / 'saved')
    assert hasattr(restored.structure.atom_site_moment['A'], 'spherical'), (
        'Reopening must expose derived moment values from the stored independent components'
    )
    view = restored.structure.atom_site_moment['A'].spherical
    np.testing.assert_allclose(
        [view.modulus.value, view.polar.value, view.azimuth.value],
        expected,
        rtol=1e-7,
        atol=1e-7,
        err_msg='Saved derived columns must never override independent moment components',
    )

    np.testing.assert_allclose(
        [view.modulus.uncertainty, view.polar.uncertainty, view.azimuth.uncertainty],
        expected_sigma,
        rtol=3e-5,
        atol=1e-8,
        err_msg='Reload must retain the full supplied component and cell covariance',
    )

    for actual, expected_error in zip(
        (view.modulus.uncertainty, view.polar.uncertainty, view.azimuth.uncertainty),
        expected_sigma,
        strict=True,
    ):
        oracle.numeric_error(actual, expected_error, tolerance=3e-5)


def persisted_moment_reference(root):
    # Reload owns persisted inputs and rounded correlations, not the pre-save marginals.
    saved = gemmi.cif.read_file(str(root / 'structures/phase.edi')).sole_block()
    tags = ['_atom_site_moment.crystalaxis_' + axis for axis in 'xyz']
    tags += [
        '_cell.' + item
        for item in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ]
    pairs = [oracle.token_pair(next(iter(saved.find_values(tag)))) for tag in tags]
    stored_values, stored_errors = np.array(pairs).T
    names = ['phase.atom_site_moment.A.crystalaxis_' + axis for axis in 'xyz']
    names += [
        'phase.cell.' + item
        for item in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ]
    correlation = np.eye(9)
    analysis = gemmi.cif.read_string(
        'data_analysis\n' + (root / 'analysis/analysis.edi').read_text()
    ).sole_block()
    for row in analysis.find([
        '_fit_parameter_correlation.parameter_unique_name_i',
        '_fit_parameter_correlation.parameter_unique_name_j',
        '_fit_parameter_correlation.correlation',
    ]):
        i, j = names.index(row[0]), names.index(row[1])
        correlation[i, j] = correlation[j, i] = float(row[2])
    return cases.propagated_spherical(
        stored_values, correlation * np.outer(stored_errors, stored_errors)
    )
