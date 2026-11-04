"""The exact signed-group and commensurate admission rule at native boundaries."""

import edi as api
import numpy as np
import pytest

from tests.fixtures.magnetic_pnma import commensurate as cases
from tests.fixtures.magnetic_pnma import reference as ref


@pytest.mark.parametrize('route', ['project', 'factory'])
@pytest.mark.parametrize('case', sorted(cases.INVALID))
def test_invalid_signed_groups_and_characters_refuse(tmp_path, route, case):
    text = cases.structure(**cases.INVALID[case])
    reader = (
        (lambda: api.Project.load(ref.project(tmp_path / 'input', text)))
        if route == 'project'
        else (lambda: api.StructureFactory.from_cif_str(text))
    )
    with pytest.raises(
        (ValueError, RuntimeError),
        match=r'(?i)magnetic|propagation|translation|centring|centering|duplicate|metric|identity|closed|theta',
    ):
        reader()


@pytest.mark.parametrize('route', ['project', 'factory'])
@pytest.mark.parametrize('case', sorted(cases.VALID))
def test_commensurate_and_strained_models_are_admitted(tmp_path, route, case):
    text = cases.structure(**cases.VALID[case])
    if route == 'project':
        model = api.Project.load(ref.project(tmp_path / 'input', text))
        structure = model.structure
        model.save_as(tmp_path / 'saved')
        saved = ref.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
        assert '_parent_propagation_vector.kxkykz' in saved, (
            'Accepted propagation rows must survive the native save boundary'
        )
    else:
        structure = api.StructureFactory.from_cif_str(text)
    assert hasattr(structure, 'atom_site_moment'), (
        'Admission must retain magnetic content rather than silently discard it'
    )


def test_grey_centred_structure_has_zero_moments_and_undoubled_nuclear_intensity(tmp_path):
    # Both time signs fix moments at zero; each nuclear image counts once.
    source = cases.structure(
        period=2, operations=('x,y,z,+1', 'x,y,z,-1'), centrings=('x,y,z,+1', 'x+1/2,y,z,+1')
    )
    model = api.Project.load(ref.project(tmp_path / 'input', source))
    model.analysis.calculate()
    moment = model.structure.atom_site_moment['A']
    assert all(getattr(moment, 'crystalaxis_' + axis).value == 0 for axis in 'xyz'), (
        'The grey-group identity with negative time sign fixes every moment to zero'
    )
    before = np.asarray(model.experiment.refln.f_squared_calc).copy()
    assert np.all(np.asarray(model.experiment.refln.f_m_perp_squared_calc) == 0), (
        'Grey groups scatter no magnetic intensity'
    )
    model.save_as(tmp_path / 'saved')
    restored = api.Project.load(tmp_path / 'saved')
    restored.analysis.calculate()
    assert np.array_equal(before, restored.experiment.refln.f_squared_calc), (
        'Saving a grey group cannot multiply its nuclear scattering'
    )
    refl = restored.experiment.refln
    for h, k, index_l, f2 in zip(
        refl.index_h, refl.index_k, refl.index_l, refl.f_squared_calc, strict=True
    ):
        s2 = ((h / 8) ** 2 + (k / 5) ** 2 + (index_l / 6) ** 2) / 4
        expected = (2 * 2.49 * np.exp(-0.17 * s2)) ** 2 / 100 if h % 2 == 0 else 0
        assert f2 == pytest.approx(expected, rel=1e-11, abs=1e-12), (
            'Grey centred nuclear factors equal the independent two-site interference sum'
        )


def test_dead_detector_cell_is_excluded_on_the_products_own_grid(tmp_path):
    model = api.Project.load(ref.project(tmp_path / 'input'))
    model.analysis.calculate()
    grid = np.asarray(model.experiment.data.two_theta)
    status = list(model.experiment.data.calc_status)
    for angle, wanted in [(64.5953, 'incl'), (64.6953, 'excl'), (64.7953, 'incl')]:
        indices = np.flatnonzero(np.abs(grid - angle) < 1e-5)
        assert len(indices) == 1, (
            'Each dead-cell control must exist on this engines own point list'
        )
        assert str(status[int(indices[0])]) == wanted, (
            'Only the dead detector point is excluded; both immediate neighbours remain included'
        )


@pytest.mark.parametrize('name', ['isodistort.mcif', 'cosio1.mcif'])
def test_named_magnetic_cif_imports_preserve_moments_and_iso_loops(tmp_path, name):
    text = (ref.ROOT / 'cosio' / name).read_text()
    root = ref.project(tmp_path / 'input')
    (root / 'structures/cosio.edi').write_text(text)
    model = api.Project.load(root)
    assert len(model.structure.atom_site_moment) == 2, (
        'Each independently supplied cobalt magCIF imports both magnetic sites'
    )
    model.save_as(tmp_path / 'saved')
    original = ref.columns(text)
    saved = ref.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
    for key, values in original.items():
        if key.startswith('_iso_'):
            assert saved.get(key) == values, (
                'Every imported ISODISTORT token survives the native save'
            )


def test_invalid_cell_edit_is_atomic_and_loading_rederives_moment_ties(tmp_path):
    # R=(x+y,-y,z), gamma=60 degrees, a=b: invariance of axial M requires Mx=-My/2.
    source = cases.structure(
        b=4, gamma=60, operations=('x,y,z,+1', 'x+y,-y,z,+1'), moment='-.5 1 0'
    )
    # This parent is derived from the operator-defined structure, not a declared P1 subgroup.
    source = source.replace(
        '_parent_space_group.derived false', '_parent_space_group.derived true'
    )
    model = api.Project.load(ref.project(tmp_path / 'input', source))
    moment = model.structure.atom_site_moment['A']
    assert moment.crystalaxis_x.value == pytest.approx(-0.5), (
        'The initial metric-dependent axial tie equals the hand stabiliser solution'
    )
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)metric|symmetry|cell'):
        model.structure.cell.length_b.value = 8
    assert model.structure.cell.length_b.value == 4, (
        'A refused cell edit leaves the old metric unchanged'
    )
    changed = source.replace('_cell.length_b 4', '_cell.length_b 8').replace(
        '_cell.angle_gamma 60', f'_cell.angle_gamma {np.degrees(np.arccos(0.25))}'
    )
    model = api.Project.load(ref.project(tmp_path / 'new-metric', changed))
    moment = model.structure.atom_site_moment['A']
    assert moment.crystalaxis_x.value == pytest.approx(-0.25), (
        'A valid cell replacement recompiles the unit-crystal-axis coefficient immediately'
    )
    model.save_as(tmp_path / 'saved')
    restored = api.Project.load(tmp_path / 'saved')
    assert restored.structure.atom_site_moment['A'].crystalaxis_x.value == pytest.approx(-0.25), (
        'Saving and reloading preserve the new metric-derived dependent component'
    )
