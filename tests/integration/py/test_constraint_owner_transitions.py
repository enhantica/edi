"""Retained rows agree on dependence and free writes across ownership changes."""

import gc
import runpy
from pathlib import Path

import edi
import pytest

from tests.fixtures.constraint_expressions.project import unlink_structure

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]
TARGETS = [
    ('site', 'phase.atom_site.A.adp_iso', 0.3),
    ('cell', 'phase.cell.length_a', 4.1),
    ('instrument', 'bank.instrument.setup_wavelength', 1.54),
    ('profile', 'bank.peak.broad_gauss_w', 0.15),
    ('scale', 'bank.linked_structure.phase.scale', 1.0),
    ('point', 'bank.background.left.intensity', 3.0),
    ('term', 'bank.background.1.coef', 4.0),
    ('texture', 'bank.preferred_orientation.phase.march_r', 0.9),
    ('absorption', 'bank.absorption.mu_r', 0.1),
]


def model(directory, kind, target, expression=()):
    MATERIALIZE(directory, [('held', target)], expression, polynomial=kind == 'term')
    bank = directory / 'experiments/bank.edi'
    if kind == 'texture':
        bank.write_text(
            bank.read_text()
            + '\nloop_\n_preferred_orientation.structure_id\n_preferred_orientation.march_r\n'
            '_preferred_orientation.index_h\n_preferred_orientation.index_k\n'
            '_preferred_orientation.index_l\n_preferred_orientation.march_random_fract\n'
            'phase .9 0 0 1 .1\n'
        )
    if kind == 'absorption':
        bank.write_text(
            bank.read_text() + '\n_absorption.type cylinder-hewat\n_absorption.mu_r .1\n'
        )
    return edi.Project.load(directory)


@pytest.mark.parametrize(('kind', 'target', 'value'), TARGETS, ids=[r[0] for r in TARGETS])
@pytest.mark.parametrize('route', ['destroy', 'remove'])
@pytest.mark.parametrize('order', ['read-first', 'write-first'])
def test_retained_child_free_setter_agrees_with_dependence_after_owner_exit(
    tmp_path, kind, target, value, route, order
):
    project = model(tmp_path, kind, target, [f'held = {value}'])
    child = project.structures[0] if kind in {'site', 'cell'} else project.experiments[0]
    parameter = project.analysis.aliases['held'].param
    assert parameter.user_constrained, (
        'The retained child must start with an active user dependent'
    )
    if route == 'remove':
        collection = project.structures if kind in {'site', 'cell'} else project.experiments
        if kind in {'site', 'cell'}:
            unlink_structure(project, child.name)
        collection.remove(child.name)
    else:
        del project
    gc.collect()
    if order == 'read-first':
        flags = (parameter.user_constrained, parameter.symmetry_constrained)
    attached = parameter.is_attached()
    if attached:
        parameter.free = True
    else:
        with pytest.raises(RuntimeError, match='detached'):
            parameter.free = True
    if order == 'write-first':
        flags = (parameter.user_constrained, parameter.symmetry_constrained)
    assert flags == (False, False), (
        'Retained children without project membership must report independence'
    )
    if attached:
        assert parameter.free, (
            'An independent retained child must accept free writes without a stale dependent mark'
        )


@pytest.mark.parametrize(('kind', 'target', 'value'), TARGETS, ids=[r[0] for r in TARGETS])
@pytest.mark.parametrize('route', ['insert', 'replace', 'transfer', 'assign'])
@pytest.mark.parametrize('entry', ['dependence', 'free'])
def test_saved_collection_rebinds_retained_parameters_without_accessor(
    tmp_path, kind, target, value, route, entry
):
    donor = model(tmp_path / 'donor', kind, target)
    destination = model(tmp_path / 'destination', kind, target, [f'held = {value + 0.125}'])
    structural = kind in {'site', 'cell'}
    source = donor.structures if structural else donor.experiments
    sink = destination.structures if structural else destination.experiments
    child = source[0]
    parameter = donor.analysis.aliases['held'].param
    parameter.free = False
    if route in {'insert', 'transfer'}:
        if structural:
            unlink_structure(destination, child.name)
        sink.remove(child.name)
    if structural:
        unlink_structure(donor, child.name)
    source.remove(child.name)
    if route == 'assign':
        sink._assign([child])
    else:
        sink.add(child)
    if route == 'transfer':
        del donor
        gc.collect()
    # No destination accessor occurs between mutation and this retained-handle entry.
    if entry == 'free':
        parameter.free = True
        assert not parameter.free, (
            'The destination relation must govern a retained child free setter immediately'
        )
    else:
        assert parameter.user_constrained, (
            'Saved collection mutations must bind children to the destination relation'
        )
        assert not parameter.symmetry_constrained, (
            'A destination user relation must not invent a symmetry follower'
        )


@pytest.mark.parametrize('family', ['site', 'cell'])
@pytest.mark.parametrize('route', ['insert', 'replace', 'transfer', 'assign'])
@pytest.mark.parametrize('entry', ['stored', 'window'])
def test_saved_collection_rebinds_retained_geometry_without_accessor(
    tmp_path, family, route, entry
):
    target = 'phase.cell.length_a' if family == 'cell' else 'phase.atom_site.A.fract_x'
    value = 4.7 if family == 'cell' else 0.37
    donor = model(tmp_path / 'donor', family, target)
    destination = model(tmp_path / 'destination', family, target, [f'held = {value}'])
    source, sink = donor.structures, destination.structures
    child = source[0]
    parameter = donor.analysis.aliases['held'].param
    if route in {'insert', 'transfer'}:
        unlink_structure(destination, child.name)
        sink.remove(child.name)
    unlink_structure(donor, child.name)
    source.remove(child.name)
    if route == 'assign':
        sink._assign([child])
    else:
        sink.add(child)
    if route == 'transfer':
        del donor
        gc.collect()
    geometry = child if entry == 'stored' else child.geometry()
    rows = geometry.expanded_atom_sites
    indices = [i for i, name in enumerate(rows.atom_site_id) if name == 'A']
    assert indices, 'The transferred geometry must retain its source atom'
    expected_x = 4.7 * 0.17 if family == 'cell' else 4.1 * 0.37
    assert all(abs(rows.cartn_x[i] - expected_x) < 2e-11 for i in indices), (
        'Geometry through a retained child must use the destination relation before '
        'any project accessor'
    )
    assert parameter.value == pytest.approx(value, abs=2e-13), (
        'Rebinding must complete the retained destination target'
    )
