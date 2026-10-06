"""Closed-form geometry after first declarations and warmed owner transitions."""

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


def target_of(child, family):
    return child.cell.length_a if family == 'cell' else child.atom_sites[0].fract_x


def attach(project, family, expression):
    child = project.structures[0]
    project.analysis.aliases.create(id='u', param=child.atom_sites[0].adp_iso)
    project.analysis.aliases.create(id='v', param=target_of(child, family))
    project.analysis.constraints.create(expression=expression)


def check_geometry(geometry, family, value):
    atoms = geometry.expanded_atom_sites
    indices = [i for i, name in enumerate(atoms.atom_site_id) if name == 'A']
    expected = value * 0.17 if family == 'cell' else 4.1 * value
    assert indices, 'The warmed-context witness must retain atom A'
    assert all(abs(atoms.cartn_x[i] - expected) < 2e-11 for i in indices), (
        'Lazy geometry must use the current owner relation and its closed-form Cartesian value'
    )


@pytest.mark.parametrize('family', ['coordinate', 'cell'])
@pytest.mark.parametrize('entry', ['stored', 'window'])
def test_first_declarations_revoke_no_loop_geometry(tmp_path, family, entry):
    project = edi.Project.load(MATERIALIZE(tmp_path))
    child = project.structures[0]
    target = target_of(child, family)
    _ = child.expanded_atom_sites
    held = child.geometry()
    assert held.is_current(), 'No-loop geometry must start current before first declarations'
    before = target.value
    attach(project, family, 'v = 4+2*u' if family == 'cell' else 'v = .1+.8*u')
    unchanged = target.value == before
    stale = not held.is_current()
    result = child if entry == 'stored' else child.geometry()
    expected = 4.6 if family == 'cell' else 0.34
    check_geometry(result, family, expected)
    assert target.value == pytest.approx(expected, abs=2e-13), (
        'The first relation must complete before a stored or window geometry read'
    )
    assert unchanged, 'First declarations must not incidentally write the geometry target'
    assert stale, 'First declaration admission must revoke a held no-loop window'


@pytest.mark.parametrize('entry', ['geometry', 'data', 'refln'])
def test_alias_only_calculation_and_lazy_reads_are_current(tmp_path, entry):
    project = edi.Project.load(MATERIALIZE(tmp_path))
    child = project.structures[0]
    project.analysis.aliases.create(id='u', param=child.atom_sites[0].adp_iso)
    project.analysis.calculate()
    held = child.geometry()
    assert held.is_current(), 'Alias-only geometry must be current with absent constraint records'
    if entry == 'geometry':
        _ = child.expanded_atom_sites
    else:
        category = getattr(project.experiments[0], entry)
        field = 'intensity_calc' if entry == 'data' else 'f_squared_calc'
        before = list(getattr(category, field))
        assert list(getattr(category, field)) == before, (
            'Repeated alias-only reads must retain the calculated contents'
        )
    assert held.is_current(), 'An unchanged alias-only read must not renew geometry inputs'


@pytest.mark.parametrize('family', ['coordinate', 'cell'])
@pytest.mark.parametrize('source_kind', ['constrained', 'no-loop', 'standalone'])
@pytest.mark.parametrize('route', ['insert', 'replace', 'assign', 'remove', 'destroy'])
@pytest.mark.parametrize('entry', ['stored', 'window'])
def test_warmed_geometry_follows_current_relation_owner(
    tmp_path, family, source_kind, route, entry
):
    donor = edi.Project.load(MATERIALIZE(tmp_path / 'donor'))
    child = donor.structures[0]
    if source_kind == 'constrained':
        attach(donor, family, 'v = 4.3' if family == 'cell' else 'v = .23')
    if source_kind == 'standalone':
        unlink_structure(donor, child.name)
        donor.structures.remove(child.name)
    target = target_of(child, family)
    _ = child.expanded_atom_sites
    held = child.geometry()
    assert held.is_current(), 'Each donor geometry must be warm and current before owner change'
    before = target.value
    if route in {'insert', 'replace', 'assign'}:
        destination = edi.Project.load(MATERIALIZE(tmp_path / 'destination'))
        attach(destination, family, 'v = 4.7' if family == 'cell' else 'v = .37')
        sink = destination.structures
        if source_kind != 'standalone':
            unlink_structure(donor, child.name)
            donor.structures.remove(child.name)
        if route == 'insert':
            unlink_structure(destination, child.name)
            sink.remove(child.name)
        if route == 'assign':
            sink._assign([child])
        else:
            sink.add(child)
        expected = 4.7 if family == 'cell' else 0.37
        changed_owner = True
    else:
        if route == 'remove' and source_kind != 'standalone':
            unlink_structure(donor, child.name)
            donor.structures.remove(child.name)
        if route == 'destroy':
            del donor
            gc.collect()
        expected = before
        changed_owner = source_kind != 'standalone'
    # Inspect the warmed result before any fresh geometry call can mask a missed renewal.
    current = held.is_current()
    assert target.value == before, 'Membership transitions must not write geometry parameters'
    assert current == (not changed_owner), (
        'A held window must certify exactly its live relation owner, including no owner'
    )
    result = child if entry == 'stored' else child.geometry()
    check_geometry(result, family, expected)
    assert target.value == pytest.approx(expected, abs=2e-13), (
        'The first retained-child geometry read must complete only the current owner relation'
    )
    assert not changed_owner or not held.is_current(), (
        'Renewing live geometry must not re-certify a snapshot made under the former owner'
    )
