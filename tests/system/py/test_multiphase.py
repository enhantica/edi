"""Multiphase loading, persistence, scales and phase-local texture."""

import edi as engine
import numpy as np

from tests.fixtures.multiphase import support as case


def test_two_named_phases_load_and_roundtrip(tmp_path):
    project = engine.Project.load(case.write_project(tmp_path / 'input'))
    assert hasattr(project.structures, 'keys'), (
        'Structures must follow the keyed experiment protocol'
    )
    assert list(project.structures.keys()) == ['alpha', 'beta'], (
        'Both named structures must load in stable order'
    )
    rows = case.links(project.experiments[0])
    assert list(rows.keys()) == ['alpha', 'beta'], 'Both phase links must survive loading'
    before = case.pattern(project)
    assert set(project.experiments[0].refln.structure_id) == {'alpha', 'beta'}, (
        'Calculated reflections must retain both phase names for the chart'
    )
    for iteration in range(2):
        path = tmp_path / f'saved-{iteration}'
        project.save_as(path)
        project = engine.Project.load(path)
        assert list(project.structures.keys()) == ['alpha', 'beta'], (
            'Saving must retain every keyed structure'
        )
        assert {p.name for p in (path / 'structures').glob('*.edi')} == {
            'alpha.edi',
            'beta.edi',
        }, 'Both structures need their own persisted block'
        assert [
            case.links(project.experiments[0])[name].scale.value for name in case.SCALES
        ] == list(case.SCALES.values()), 'Saving must retain each independent phase scale'
        np.testing.assert_array_equal(
            case.pattern(project),
            before,
            err_msg='Reopening must preserve the calculated phase sum',
        )


def test_phase_sum_is_linear_and_warm_edits_reach_only_their_phase(tmp_path):
    singles = {
        name: case.pattern(engine.Project.load(case.write_project(tmp_path / name, (name,))))
        for name in case.SCALES
    }
    project = engine.Project.load(case.write_project(tmp_path / 'both'))
    np.testing.assert_allclose(
        case.pattern(project),
        singles['alpha'] + singles['beta'],
        rtol=2e-13,
        atol=1e-12,
        err_msg='Independent phase intensities must add without rescaling',
    )
    rows = case.links(project.experiments[0])
    rows['beta'].scale.value *= 1.625
    np.testing.assert_allclose(
        case.pattern(project),
        singles['alpha'] + 1.625 * singles['beta'],
        rtol=2e-13,
        atol=1e-12,
        err_msg='A warm scale edit must invalidate only its phase contribution',
    )
    project.structures['beta'].atom_sites['X'].occupancy.value *= 0.625
    np.testing.assert_allclose(
        case.pattern(project),
        singles['alpha'] + 1.625 * 0.625**2 * singles['beta'],
        rtol=2e-13,
        atol=1e-12,
        err_msg='Occupancy enters only its phase amplitude before squaring',
    )


def test_two_free_scales_recover_unequal_independent_contributions(tmp_path):
    measured = sum(
        case.pattern(engine.Project.load(case.write_project(tmp_path / name, (name,))))
        for name in case.SCALES
    )
    starts = {'alpha': '1.125()', 'beta': '0.875()'}
    project = engine.Project.load(
        case.write_project(tmp_path / 'fit', scales=starts, measured=measured)
    )
    free = project.free_parameters
    assert len(free) == 2, 'Each declared free phase scale needs its own fitting column'
    assert (
        case.links(project.experiments[0])['alpha'].scale
        is not case.links(project.experiments[0])['beta'].scale
    ), 'Phase scales cannot alias one parameter'
    project.fit()
    actual = [case.links(project.experiments[0])[name].scale.value for name in case.SCALES]
    np.testing.assert_allclose(
        actual,
        list(case.SCALES.values()),
        rtol=2e-7,
        atol=1e-9,
        err_msg='Two independent free scales must recover unequal phase contributions',
    )
    saved = tmp_path / 'fit-saved'
    project.save_as(saved)
    carried = engine.Project.load(saved)
    assert all(case.links(carried.experiments[0])[name].scale.free for name in case.SCALES), (
        'Fitted scale flags must persist for both phases'
    )
    np.testing.assert_array_equal(
        [case.links(carried.experiments[0])[name].scale.value for name in case.SCALES],
        actual,
        err_msg='Fitted scale values must survive saving exactly',
    )


def test_disabled_link_is_retained_but_excluded_from_calculation_and_fit(tmp_path):
    alpha = case.pattern(engine.Project.load(case.write_project(tmp_path / 'alpha', ('alpha',))))
    project = engine.Project.load(
        case.write_project(tmp_path / 'both', scales={'alpha': '2.75()', 'beta': '0.375()'})
    )
    row = case.links(project.experiments[0])['beta']
    case.enable(row, value=False)
    assert len(project.free_parameters) == 1, (
        'A disabled phase must contribute no free fitting column'
    )
    np.testing.assert_array_equal(
        case.pattern(project), alpha, err_msg='Disabled phases must be absent from the calculation'
    )
    saved = tmp_path / 'disabled'
    project.save_as(saved)
    carried = engine.Project.load(saved)
    assert 'beta' in case.links(carried.experiments[0]), (
        'Disabling must retain the phase link on disk'
    )
    assert len(carried.free_parameters) == 1, (
        'Reopening must retain the disabled fitting exclusion'
    )
    np.testing.assert_array_equal(
        case.pattern(carried), alpha, err_msg='Disabled phase exclusion must survive reopening'
    )
    case.enable(case.links(carried.experiments[0])['beta'], value=True)
    assert len(carried.free_parameters) == 2, (
        'Re-enabling must restore its independent fitting column'
    )


def test_texture_is_local_to_phase_and_invariant_under_axis_sign(tmp_path):
    plain = {
        name: case.pattern(engine.Project.load(case.write_project(tmp_path / name, (name,))))
        for name in case.SCALES
    }
    textured = case.pattern(
        engine.Project.load(
            case.write_project(
                tmp_path / 'textured-alpha', ('alpha',), texture={'alpha': (0.73, 0.3, (0, 0, 1))}
            )
        )
    )
    two = engine.Project.load(
        case.write_project(tmp_path / 'both', texture={'alpha': (0.73, 0.3, (0, 0, 1))})
    )
    np.testing.assert_allclose(
        case.pattern(two),
        textured + plain['beta'],
        rtol=2e-13,
        atol=1e-12,
        err_msg='Alpha texture must not change beta reflections',
    )
    signed = engine.Project.load(
        case.write_project(tmp_path / 'signed', texture={'alpha': (0.73, 0.3, (0, 0, -1))})
    )
    np.testing.assert_array_equal(
        case.pattern(signed),
        case.pattern(two),
        err_msg='A phase texture is unchanged under an axis sign flip',
    )
    assert not np.array_equal(textured, plain['alpha']), (
        'The texture witness must have a nonzero physical effect'
    )


def test_single_phase_negative_biso_is_preserved_and_has_its_physical_effect(tmp_path):
    zero = engine.Project.load(case.write_project(tmp_path / 'zero', ('alpha',), biso=0))
    negative = engine.Project.load(
        case.write_project(tmp_path / 'negative', ('alpha',), biso=-0.143)
    )
    assert negative.structure.atom_sites[0].adp_iso.value.hex() == (-0.143).hex(), (
        'Saved negative Biso is admitted without clamping'
    )
    expected = np.exp(2 * 0.143 * (np.sin(np.radians(case.grid() / 2)) / 1.54) ** 2)
    actual = case.pattern(negative)
    baseline = case.pattern(zero)
    selected = baseline > 1e-10
    np.testing.assert_allclose(
        actual[selected] / baseline[selected],
        expected[selected],
        rtol=2e-7,
        err_msg='Negative Biso must enter the Debye-Waller exponent without clamping',
    )
