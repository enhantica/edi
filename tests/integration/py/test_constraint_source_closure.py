"""Relation input closure and refusal precede every lazy geometry read."""

import runpy
from pathlib import Path

import edi as engine
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]
SOURCES = ['background.left.intensity', 'peak.broad_gauss_w', 'instrument.setup_wavelength']


def source_model(directory, source, family, route):
    bank = 'second' if route == 'cross-bank' else 'bank'
    target = 'phase.cell.length_b' if family == 'cell' else 'phase.atom_site.B.fract_y'
    aliases = [('a', bank + '.' + source), ('b', target)]
    if route == 'chain':
        aliases.append(('c', 'phase.atom_site.A.occupancy'))
        expressions = ['c = .1 + .01*a', 'b = 4+2*c' if family == 'cell' else 'b = .1+2*c']
    else:
        expressions = ['b = 4+.03*a' if family == 'cell' else 'b = .2+.03*a']
    MATERIALIZE(directory, aliases, expressions)
    if route == 'cross-bank':
        first = directory / 'experiments/bank.edi'
        (directory / 'experiments/second.edi').write_text(
            first.read_text().replace('data_bank', 'data_second')
        )
    return engine.Project.load(directory)


@pytest.mark.parametrize('source', SOURCES)
@pytest.mark.parametrize('family', ['coordinate', 'cell'])
@pytest.mark.parametrize('route', ['direct', 'chain', 'cross-bank'])
@pytest.mark.parametrize('entry', ['stored', 'window', 'refln', 'data'])
def test_experiment_source_edit_revokes_each_dependent_consumer(  # noqa: PLR0914
    tmp_path, source, family, route, entry
):
    project = source_model(tmp_path, source, family, route)
    source_parameter = project.analysis.aliases['a'].param
    target = project.analysis.aliases['b'].param
    project.analysis.calculate()
    structure = project.structure
    window = structure.geometry()
    category = project.experiments[0].refln if entry == 'refln' else project.experiments[0].data
    field = 'f_squared_calc' if entry == 'refln' else 'intensity_calc'
    before = np.asarray(getattr(category, field)).copy()
    previous = target.value
    source_parameter.value += 0.07
    source_value = source_parameter.value
    untouched = target.value == previous
    stale = not window.is_current()
    expected = (
        (4 if family == 'cell' else 0.1) + 2 * (0.1 + 0.01 * source_value)
        if route == 'chain'
        else (4 if family == 'cell' else 0.2) + 0.03 * source_value
    )
    if entry in {'stored', 'window'}:
        geometry = structure if entry == 'stored' else structure.geometry()
        atoms = geometry.expanded_atom_sites
        indices = [i for i, name in enumerate(atoms.atom_site_id) if name == 'B']
        assert indices, 'The geometry renewal must retain the dependent atom'
        expected_y = expected * 0.23 if family == 'cell' else expected * 4.1
        assert all(abs(atoms.cartn_y[i] - expected_y) < 2e-11 for i in indices), (
            'Source-only edits must renew stored and window geometry from the affine closed form'
        )
    else:
        after = np.asarray(getattr(category, field)).copy()
        assert before.shape != after.shape or not np.allclose(
            before, after, rtol=1e-12, atol=1e-12
        ), 'A held data or reflection category must renew after a transitive source edit'
    assert target.value == pytest.approx(expected, rel=0, abs=2e-13), (
        'Every lazy consumer must complete the relation from the edited experiment source'
    )
    assert untouched, 'The witness must edit only the source before any dependent consumer runs'
    assert stale, 'Experiment sources reached by relations must stale held geometry immediately'


@pytest.mark.parametrize('source', SOURCES)
@pytest.mark.parametrize('family', ['coordinate', 'cell'])
def test_equal_source_write_still_revokes_held_geometry(tmp_path, source, family):
    project = source_model(tmp_path, source, family, 'direct')
    source_parameter = project.analysis.aliases['a'].param
    project.analysis.calculate()
    window = project.structure.geometry()
    source_parameter.value = source_parameter.value
    assert not window.is_current(), 'An equal source write must retain its invalidation identity'


@pytest.mark.parametrize('entry', ['stored', 'window'])
def test_wyckoff_letter_change_renews_completed_coordinates(tmp_path, entry):
    project = engine.Project.load(MATERIALIZE(tmp_path, symmetry=True))
    structure = project.structure
    atom = structure.atom_sites[1]
    project.analysis.calculate()
    held = structure.geometry()
    atom.wyckoff_letter = 'b'
    unchanged = atom.fract_x.value == 0
    stale = not held.is_current()
    geometry = structure if entry == 'stored' else structure.geometry()
    rows = geometry.expanded_atom_sites
    indices = [i for i, name in enumerate(rows.atom_site_id) if name == 'B']
    assert indices, 'The changed Wyckoff site must remain in the expanded geometry'
    assert all(abs(rows.fract_x[i] - 0.5) < 2e-13 for i in indices), (
        'Pm-3m position b must complete to the body centre after only a letter edit'
    )
    assert atom.fract_x.value == pytest.approx(0.5, abs=2e-13), (
        'The live site must share its completed Wyckoff coordinate'
    )
    assert unchanged, 'Changing a letter must not incidentally write the coordinate in the witness'
    assert stale, 'Wyckoff selection must be an input of completed geometry'


@pytest.mark.parametrize('entry', ['stored', 'window'])
def test_out_of_range_relation_refuses_before_any_dependent_write(tmp_path, entry):
    aliases = [
        ('a', 'phase.atom_site.A.adp_iso'),
        ('b', 'phase.atom_site.B.fract_y'),
        ('c', 'phase.atom_site.B.occupancy'),
    ]
    project = engine.Project.load(MATERIALIZE(tmp_path, aliases, ['b = 2*a+.1', 'c = a']))
    project.analysis.calculate()
    structure = project.structure
    first, second = project.analysis.aliases['b'].param, project.analysis.aliases['c'].param
    before = (first.value, second.value)
    project.analysis.constraints['b'].expression = 'b = 3*a+.1'
    project.analysis.constraints['c'].expression = 'c = 2'
    refused = False
    try:
        _ = structure.expanded_atom_sites if entry == 'stored' else structure.geometry()
    except (ValueError, RuntimeError):
        refused = True
    assert (first.value, second.value) == before, (
        'An inadmissible later dependent must prevent writes to every earlier target'
    )
    assert refused, 'Finite occupancy outside its declared range must refuse geometry completion'


@pytest.mark.parametrize(
    'window',
    [((1, 0), (0, 1), (0, 1)), ((0, float('nan')), (0, 1), (0, 1))],
    ids=['inverted', 'nonfinite'],
)
def test_invalid_window_refuses_before_relation_completion(tmp_path, window):
    project = engine.Project.load(
        MATERIALIZE(
            tmp_path,
            [('a', 'phase.atom_site.A.adp_iso'), ('b', 'phase.atom_site.B.fract_y')],
            ['b = 2*a+.1'],
        )
    )
    project.analysis.calculate()
    target = project.analysis.aliases['b'].param
    before = target.value
    project.analysis.constraints['b'].expression = 'b = 3*a+.1'
    with pytest.raises((ValueError, RuntimeError)):
        project.structure.geometry(view_range=window)
    assert target.value == before, (
        'An invalid window must refuse before writing any completed dependent'
    )
