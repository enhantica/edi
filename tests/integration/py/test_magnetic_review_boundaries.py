"""Magnetic fit and input boundaries against grammar and differential invariants."""

import warnings

import edi as api
import numpy as np
import pytest

from tests.fixtures.magnetic_pnma import commensurate as cases
from tests.fixtures.magnetic_pnma import reference as ref


def project(root, text=None):
    return api.Project.load(ref.project(root, text))


@pytest.mark.parametrize('route', ['factory', 'project'])
@pytest.mark.parametrize('loop', ['operation', 'centering'])
@pytest.mark.parametrize('token', ['x+1/2*x', 'x+0junk', 'x+1/0', 'x+nan', 'x+1/2junk'])
def test_complete_operator_grammar_refuses(tmp_path, route, loop, token):
    text = cases.structure()
    tag = '_space_group_symop_magn_' + loop + '.xyz\n1 x,y,z,+1\n'
    text = text.replace(tag, tag + '2 ' + token + ',y,z,+1\n')
    reader = (
        (lambda: api.StructureFactory.from_cif_str(text))
        if route == 'factory'
        else (lambda: project(tmp_path / 'input', text))
    )
    with pytest.raises((ValueError, RuntimeError)):
        reader()


@pytest.mark.parametrize('mode', ['j0', 'dipole', 'beyond_dipole'])
@pytest.mark.parametrize('order', [2, 4, 6])
@pytest.mark.parametrize('route', ['assignment', 'load'])
def test_radial_free_boundary_agrees_with_active_terms(tmp_path, mode, order, route):
    text = cases.structure()
    text = text.replace(
        '_magnetic_form_factor.j2_coefficient\nCo Co2+ 0',
        '_magnetic_form_factor.j2_coefficient\n_magnetic_form_factor.approximation\n'
        '_magnetic_form_factor.j4_coefficient\n_magnetic_form_factor.j6_coefficient\n'
        'Co Co2+ '
        + ('0()' if route == 'load' and order == 2 else '0')
        + ' '
        + mode
        + ' '
        + ('0()' if route == 'load' and order == 4 else '0')
        + ' '
        + ('0()' if route == 'load' and order == 6 else '0'),
    )
    p = project(tmp_path / 'input', text)
    coefficient = getattr(p.structure.magnetic_form_factor[0], f'j{order}_coefficient')
    allowed = (mode == 'dipole' and order == 2) or (mode == 'beyond_dipole' and order in {2, 4})
    if route == 'assignment':
        if allowed:
            coefficient.free = True
        else:
            with pytest.raises(
                ValueError, match=r'(?i)fit|coefficient|radial|approximation|capability'
            ):
                coefficient.free = True
    assert coefficient.free == allowed, (
        'Only active radial terms with a tabulated Co2+ integral enter the free set'
    )
    assert coefficient.value == 0, 'Eligibility checks preserve the supplied coefficient'
    if allowed:
        p.analysis.fit()


@pytest.mark.parametrize('family', ['moment', 'coefficient', 'within', 'across'])
def test_multiphase_magnetic_correspondence_and_relations(tmp_path, family):
    root = ref.project(tmp_path / 'input')
    (root / 'structures/other.edi').write_text(
        (root / 'structures/cosio.edi').read_text().replace('data_cosio', 'data_other')
    )
    bank = root / 'experiments/d20.edi'
    bank.write_text(bank.read_text().replace('cosio 1.817226', 'cosio 1.817226\nother .7'))
    p = api.Project.load(root)
    first = p.structures['cosio']
    second = p.structures['other']
    source = (
        first.magnetic_form_factor[0].j2_coefficient
        if family == 'coefficient'
        else first.atom_site_moment[0].crystalaxis_y
    )
    source.free = True
    if family in {'within', 'across'}:
        target_structure = first if family == 'within' else second
        target = target_structure.atom_site_moment[1].crystalaxis_y
        p.analysis.aliases.create(id='a', param=source)
        p.analysis.aliases.create(id='b', param=target)
        p.analysis.constraints.create(expression='b = 2*a + .17')
    p.analysis.fit()
    assert np.isfinite(source.value), (
        'Both magnetic families retain their phase-owned fit counterpart'
    )
    if family in {'within', 'across'}:
        assert target.value == pytest.approx(2 * source.value + 0.17, abs=1e-10), (
            'Within and across-phase magnetic dependents follow the declared affine relation'
        )


@pytest.mark.parametrize('fixed_site', ['same', 'other', 'dependent'])
def test_partial_zero_uses_ordinary_local_covariance(tmp_path, fixed_site, capfd):  # noqa: PLR0914 — explicit differential witness
    text = cases.structure(gamma=75, moment='0 1.3 -0.4' if fixed_site == 'same' else '0 0 0')
    if fixed_site in {'other', 'dependent'}:
        text = text.replace(
            'A Co a 0 0 0 1 .17 Biso', 'A Co a 0 0 0 1 .17 Biso\nB Co a .13 .21 .32 1 .17 Biso'
        )
        text += 'B .7 1.3 -.4\n'
    p = project(tmp_path / 'input', text)
    free = p.structure.atom_site_moment[0].crystalaxis_x
    free.free = True
    if fixed_site == 'dependent':
        p.analysis.aliases.create(id='a', param=free)
        p.analysis.aliases.create(id='b', param=p.structure.atom_site_moment[1].crystalaxis_x)
        p.analysis.constraints.create(expression='b = .5*a + .7')
    p.analysis.calculate()
    baseline = np.asarray(p.experiment.data.intensity_calc).copy()
    step = 1e-5
    profiles = []
    for value in (step, -step, 1):
        free.value = value
        p.analysis.calculate()
        profiles.append(np.asarray(p.experiment.data.intensity_calc).copy())
    selected = np.isfinite(baseline) & np.all(np.isfinite(profiles), axis=0)
    grid = np.asarray(p.experiment.data.two_theta)[selected]
    baseline = baseline[selected]
    profiles = [values[selected] for values in profiles]
    derivative = (profiles[0] - profiles[1]) / (2 * step)
    quadratic = profiles[2] - baseline - derivative
    assert np.linalg.norm(derivative) > 1e-6, (
        'Fixed transverse amplitudes give a nonzero interference derivative at the free zero'
    )
    # I(t)=I(0)+L*t+Q*t², so the central difference is exactly L.
    noise = np.sin(np.arange(len(baseline)))
    basis = np.column_stack([derivative, quadratic])
    noise -= basis @ np.linalg.lstsq(basis, noise, rcond=None)[0]
    free.value = 0
    root = tmp_path / 'measured'
    p.save_as(root)
    bank = root / 'experiments/d20.edi'
    original = bank.read_text()
    start = original.index('loop_\n_data.')
    bank.write_text(
        original[:start]
        + 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        + ''.join(f'{x:.16g} {y:.16g} 1\n' for x, y in zip(grid, baseline + noise, strict=True))
    )
    p = api.Project.load(root)
    free = p.structure.atom_site_moment[0].crystalaxis_x
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as notes:
        warnings.simplefilter('always')
        p.analysis.fit()
    assert not any('moment_zero_start' in str(note.message) for note in notes), (
        'A fixed nonzero physical amplitude prevents a zero-subset restart'
    )
    assert abs(free.value) < 2e-4, (
        'An orthogonal residual keeps the stationary free component at zero'
    )
    expected = np.linalg.norm(noise) / np.sqrt(len(noise) - 1) / np.linalg.norm(derivative)
    assert free.uncertainty == pytest.approx(expected, rel=2e-3), (
        'A partial-zero state uses the ordinary inverse local Fisher information, not an M² bound'
    )
