"""ADR-0108 decision 13: computed family symmetry, with no table completion fallback."""

import warnings
from fractions import Fraction

import edi as api
import gemmi
import numpy as np
import pytest

from tests.fixtures.magnetic_pnma import commensurate, reference
from tests.fixtures.magnetic_pnma import operator_contract as inputs


@pytest.mark.parametrize('syntax', ['native', 'magcif'])
@pytest.mark.parametrize('route', ['project', 'factory'])
def test_identity_family_does_not_take_pnma_cell_or_position_ties(tmp_path, syntax, route, capfd):
    source = inputs.identity()
    if syntax == 'magcif':
        source = inputs.cif(source)
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        if route == 'factory':
            detached = api.StructureFactory.from_cif_str(source)
            assert detached.cell.angle_gamma.value == 73, (
                'ADR-0108 the detached importer does not coerce an identity family to Pnma metric'
            )
        model = api.Project.load(reference.project(tmp_path / 'input', source))
    cell = model.structure.cell
    assert [getattr(cell, 'angle_' + axis).value for axis in ['alpha', 'beta', 'gamma']] == [
        79,
        91,
        73,
    ], 'ADR-0108 the identity operators preserve the full supplied metric instead of table angles'
    assert model.structure.atom_sites[0].fract_y.value == pytest.approx(0.37, abs=1e-14), (
        'ADR-0108 the supplied old c letter cannot impose the table mirror y=one-quarter'
    )
    captured = capfd.readouterr()
    assert (
        'wyckoff'
        in (captured.out + captured.err + ' '.join(str(w.message) for w in notices)).lower()
    ), 'ADR-0108 an operator-defined structure reports its supplied Wyckoff letter as not taken'
    for index in range(2):
        target = tmp_path / ('saved' + str(index))
        model.save_as(target)
        text = (target / 'structures/cosio.edi').read_text()
        block = gemmi.cif.read_string(text).sole_block()
        assert list(block.find_values('_atom_site.wyckoff_letter')) == ['.'], (
            'ADR-0108 an operator-defined save writes the absent-letter token'
        )
        assert list(block.find_values('_atom_site.multiplicity')) == ['1'], (
            'ADR-0108 identity has one image, independently of the declared Pnma table'
        )
        assert reference.columns(text)['_space_group.name_h_m'] == ['P n m a'], (
            'ADR-0108 the declared table group is retained without becoming the geometry source'
        )
        assert not any('operator_defined' in key for key in reference.columns(text)), (
            'ADR-0108 computed symmetry status is not persisted as a second authority'
        )
        model = api.Project.load(target)


def test_operator_defined_load_clears_forbidden_cell_and_position_free_flags(tmp_path):
    model = api.Project.load(reference.project(tmp_path / 'input', inputs.identity(free=True)))
    assert not model.structure.cell.length_a.free, (
        'ADR-0108 operator-defined cell freedom is unfittable'
    )
    assert not model.structure.atom_sites[0].fract_y.free, (
        'ADR-0108 operator-defined positions are unfittable despite their untied layout'
    )


@pytest.mark.parametrize('route', ['project', 'factory'])
def test_operator_defined_anisotropic_row_is_refused_by_each_reader(tmp_path, route):
    source = inputs.identity(aniso=True)
    action = (
        (lambda: api.Project.load(reference.project(tmp_path / 'input', source)))
        if route == 'project'
        else (lambda: api.StructureFactory.from_cif_str(source))
    )
    with pytest.raises(
        (ValueError, RuntimeError),
        match=r'(?i)(aniso|tensor|displacement).*A|A.*(aniso|tensor|displacement)',
    ):
        action()


@pytest.mark.parametrize('denominator', [97, 101, 997])
def test_shifted_inversion_is_exact_in_geometry_factors_and_second_save(tmp_path, denominator):
    source = inputs.shifted_inversion(denominator)
    model = api.Project.load(reference.project(tmp_path / 'input', source))
    for index in range(2):
        model.analysis.calculate()
        expanded = model.structure.expanded_atom_sites
        xyz = np.column_stack([expanded.fract_x, expanded.fract_y, expanded.fract_z])
        unit_cell = xyz[np.all((xyz >= -1e-12) & (xyz < 1 - 1e-12), axis=1)]
        assert sorted(unit_cell[:, 0]) == pytest.approx(
            [0, float(Fraction(1, denominator))], abs=1e-12
        ), 'ADR-0108 the exact shifted inversion supplies two images, never the P1 fallback'
        refl = model.experiment.refln
        found = 0
        for h, k, ell, value in zip(
            refl.index_h, refl.index_k, refl.index_l, refl.f_squared_calc, strict=True
        ):
            if k == 0 and ell == 0:
                expected = (
                    4
                    * 2.49**2
                    * np.cos(np.pi * h / denominator) ** 2
                    * np.exp(-2 * 0.17 * (h / 4) ** 2 / 4)
                    / 100
                )
                assert value == pytest.approx(expected, rel=1e-10, abs=1e-12), (
                    'ADR-0108 nuclear scattering follows the independent two-site phase sum'
                )
                found += 1
        assert found > 0, 'ADR-0108 the phase-sum comparison reaches measured h00 reflections'
        target = tmp_path / ('saved' + str(index))
        model.save_as(target)
        saved = (target / 'structures/cosio.edi').read_text()
        assert f'-x+1/{denominator},-y,-z,+1' in saved, (
            'ADR-0108 an admitted exact translation is written without a denominator cap'
        )
        model = api.Project.load(target)


@pytest.mark.parametrize('setter', ['operators', 'selector'])
def test_rejected_anisotropic_transition_keeps_the_warm_project(tmp_path, setter):
    model = api.Project.load(reference.project(tmp_path / 'input', inputs.tensor_table()))
    # Finish Save's adopted-schema setup and materialize the derived geometry first.
    model.save_as(tmp_path / 'prepared')
    model.analysis.calculate()
    model.save_as(tmp_path / 'before')
    # The refused edit is the only operation between the warm profile snapshots.
    model.analysis.calculate()
    before = np.asarray(model.experiment.data.intensity_calc).copy()
    action = (
        (lambda: model.structure.set_magnetic_symmetry(['x,y,z,+1'], ['x,y,z,+1']))
        if setter == 'operators'
        else (lambda: model.structure.set_magnetic_space_group('1.1'))
    )
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)aniso|tensor|displacement'):
        action()
    model.analysis.calculate()
    assert np.array_equal(before, model.experiment.data.intensity_calc, equal_nan=True), (
        'ADR-0108 refused tensor transitions preserve every included and excluded cached point'
    )
    model.save_as(tmp_path / 'after')
    assert (tmp_path / 'after/structures/cosio.edi').read_bytes() == (
        tmp_path / 'before/structures/cosio.edi'
    ).read_bytes(), (
        'ADR-0108 a refused operator or selector change preserves every saved structure field'
    )


def test_operator_metric_edits_are_validated_atomically_without_table_coercion(tmp_path):
    source = commensurate.structure(
        b=4, gamma=60, operations=('x,y,z,+1', 'x+y,-y,z,+1'), moment='-.5 1 0'
    )
    source = source.replace(
        '_parent_space_group.derived false', '_parent_space_group.derived true'
    )
    model = api.Project.load(reference.project(tmp_path / 'input', source))
    model.analysis.calculate()
    before = np.asarray(model.experiment.data.intensity_calc).copy()
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)metric|cell|symmetry'):
        model.structure.cell.length_b.value = 8
    assert model.structure.cell.length_b.value == 4, (
        'ADR-0108 a rejected metric edit writes nothing'
    )
    model.analysis.calculate()
    assert np.array_equal(before, model.experiment.data.intensity_calc, equal_nan=True), (
        'ADR-0108 rejected metric edits preserve the warm calculation including excluded points'
    )
    model.structure.cell.length_c.value = 7
    assert model.structure.cell.length_c.value == 7, (
        'ADR-0108 a metric-preserving edit is admitted'
    )
    assert model.structure.cell.angle_gamma.value == 60, (
        'ADR-0108 the table never coerces a valid metric'
    )


def test_table_identity_retains_its_anisotropic_support(tmp_path):
    source = (
        inputs.identity(aniso=True).replace('"P n m a"', '"P 1"').replace('A Co c ', 'A Co a ')
    )
    model = api.Project.load(reference.project(tmp_path / 'input', source))
    assert model.structure.cell.angle_gamma.value == 73, (
        'ADR-0108 a matching P1 identity family permits a general metric and tensor'
    )
    model.save_as(tmp_path / 'saved')
    assert '_atom_site_aniso.adp_11' in (tmp_path / 'saved/structures/cosio.edi').read_text(), (
        'ADR-0108 anisotropic refusal is specific to operator-defined families'
    )


def test_omitted_nuclear_group_stays_absent_on_second_save(tmp_path):
    model = api.Project.load(reference.project(tmp_path / 'input', inputs.identity(omitted=True)))
    for index in range(2):
        target = tmp_path / ('saved' + str(index))
        model.save_as(target)
        text = (target / 'structures/cosio.edi').read_text()
        columns = reference.columns(text)
        assert '_space_group.name_h_m' not in columns, (
            'ADR-0108 a convenience P1 holder is not a declared nuclear group'
        )
        assert list(
            gemmi.cif.read_string(text).sole_block().find_values('_atom_site.wyckoff_letter')
        ) == ['.'], 'ADR-0108 omitted-group operator geometry does not acquire a table letter'
        model = api.Project.load(target)


def test_selector_back_to_table_refuses_an_incompatible_metric_atomically(tmp_path):
    source = (
        inputs
        .identity()
        .replace('_cell.angle_alpha 79', '_cell.angle_alpha 90')
        .replace('_cell.angle_beta 91', '_cell.angle_beta 90')
    )
    model = api.Project.load(reference.project(tmp_path / 'input', source))
    # Finish Save's adopted-schema setup and materialize the derived geometry first.
    model.save_as(tmp_path / 'prepared')
    model.analysis.calculate()
    model.save_as(tmp_path / 'before')
    # The refused edit is the only operation between the warm profile snapshots.
    model.analysis.calculate()
    before = np.asarray(model.experiment.data.intensity_calc).copy()
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)metric|cell|symmetry'):
        model.structure.set_magnetic_space_group('62.441')
    assert model.structure.cell.angle_gamma.value == 73, (
        'ADR-0108 transition back to a table cannot coerce the supplied metric'
    )
    model.analysis.calculate()
    assert np.array_equal(before, model.experiment.data.intensity_calc, equal_nan=True), (
        'ADR-0108 a refused reverse transition preserves warm calculations'
    )
    model.save_as(tmp_path / 'after')
    assert (tmp_path / 'after/structures/cosio.edi').read_bytes() == (
        tmp_path / 'before/structures/cosio.edi'
    ).read_bytes(), 'ADR-0108 a refused reverse transition preserves every persisted field'


@pytest.mark.parametrize('syntax', ['native', 'magcif'])
@pytest.mark.parametrize('route', ['project', 'factory'])
def test_large_exact_family_is_preserved_or_refused_without_a_table_fallback(
    tmp_path, syntax, route
):
    # This finite inversion group is valid over Q. Its integers exceed uint64.
    # A representation may support it exactly or refuse it, never round/fall back.
    denominator = 2**64 + 13
    numerator = denominator // 2
    operation = f'-x+{numerator}/{denominator},-y,-z,+1'
    source = inputs.shifted_inversion(97).replace('-x+1/97,-y,-z,+1', operation)
    if syntax == 'magcif':
        source = inputs.cif(source)
    refusal = None
    try:
        if route == 'factory':
            api.StructureFactory.from_cif_str(source)
        model = api.Project.load(reference.project(tmp_path / 'input', source))
    except (ValueError, RuntimeError) as error:
        refusal = str(error)
    if refusal is not None:
        assert str(numerator) in refusal or str(denominator) in refusal or operation in refusal, (
            'ADR-0108 an unrepresentable family refuses naming the offending exact operation'
        )
        return
    expanded = model.structure.expanded_atom_sites
    xyz = np.column_stack([expanded.fract_x, expanded.fract_y, expanded.fract_z])
    unit_cell = xyz[np.all((xyz >= -1e-12) & (xyz < 1 - 1e-12), axis=1)]
    assert sorted(unit_cell[:, 0]) == pytest.approx(
        [0, float(Fraction(numerator, denominator))], abs=1e-12
    ), 'ADR-0108 an admitted exact inversion has its two images and cannot use P1'
    model.save_as(tmp_path / 'saved')
    assert operation in (tmp_path / 'saved/structures/cosio.edi').read_text(), (
        'ADR-0108 an admitted exact operation is not persisted as its rounded half translation'
    )
