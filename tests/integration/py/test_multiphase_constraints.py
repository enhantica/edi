"""Keyed structures retain independent ownership through declared relations."""

import runpy
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]


def site(project, phase):
    return next(atom.adp_iso for atom in project.structures[phase].atom_sites if atom.id == 'A')


@pytest.mark.parametrize('address', ['datablock', 'structure'])
def test_same_site_id_in_two_structures_resolves_to_distinct_parameters(tmp_path, address):
    paths = (
        ['phase.atom_site.A.adp_iso', 'other.atom_site.A.adp_iso']
        if address == 'datablock'
        else ['structure.phase.A.adp_iso', 'structure.other.A.adp_iso']
    )
    directory = MATERIALIZE(
        tmp_path / 'input',
        list(zip(('a', 'b'), paths, strict=True)),
        ['b = 2*a + .17'],
        second_structure=True,
    )
    project = engine.Project.load(directory)
    for index, value in enumerate((0.41, 0.23)):
        site(project, 'phase').value = value
        project.analysis.calculate()
        assert site(project, 'other').value == pytest.approx(2 * value + 0.17, abs=1e-13), (
            'A cross-phase relation must resolve duplicate site ids by their structure keys'
        )
        assert site(project, 'phase').value == value, (
            'Applying a relation in another phase must preserve its independent source'
        )
        assert not site(project, 'phase').user_constrained, (
            'A shared site id must not mark the source in the other phase dependent'
        )
        assert site(project, 'other').user_constrained, (
            'Only the target phase must carry the declared dependence'
        )
        saved = tmp_path / f'saved-{index}'
        project.save_as(saved)
        project = engine.Project.load(saved)
        assert project.analysis.constraints['b'].expression == 'b = 2*a + .17', (
            'A cross-phase relation must retain its expression after each save cycle'
        )


def test_structure_added_after_project_creation_participates_in_constraints(tmp_path):
    project = engine.Project.load(MATERIALIZE(tmp_path / 'first'))
    donor = engine.Project.load(MATERIALIZE(tmp_path / 'donor', second_structure=True))
    project.structures.add(
        engine.StructureFactory.from_cif_path(tmp_path / 'donor/structures/other.edi')
    )
    project.analysis.aliases.create(id='a', param=site(project, 'phase'))
    project.analysis.aliases.create(id='b', param=site(project, 'other'))
    project.analysis.constraints.create(expression='b = a + .37')
    for value in (0.19, 0.61):
        site(project, 'phase').value = value
        project.analysis.calculate()
        assert site(project, 'other').value == pytest.approx(value + 0.37), (
            'A structure inserted after construction must join the owning project relation graph'
        )
        assert site(donor, 'other').value == pytest.approx(0.65, abs=0, rel=0), (
            'Adding a structure must not transfer relation writes into the donor project'
        )
    project.analysis.constraints['b'].enabled = False
    site(project, 'other').value = 0.29
    project.analysis.calculate()
    assert site(project, 'other').value == pytest.approx(0.29, abs=0, rel=0), (
        'Disabling a cross-phase relation must release the newly inserted target'
    )
    assert not site(project, 'other').user_constrained, (
        'Disabling a relation must clear the added structure dependence mark'
    )


def test_added_cubic_structure_keeps_symmetry_dependence(tmp_path):
    project = engine.Project.load(MATERIALIZE(tmp_path / 'first'))
    MATERIALIZE(tmp_path / 'donor', symmetry=True, second_structure=True)
    project.structures.add(
        engine.StructureFactory.from_cif_path(tmp_path / 'donor/structures/other.edi')
    )
    cell = project.structures['other'].cell
    assert cell.length_b.symmetry_constrained, (
        'An added cubic structure must inherit project context for its symmetry followers'
    )
    cell.length_a.value = 4.37
    project.analysis.calculate()
    assert cell.length_b.value == cell.length_c.value == cell.length_a.value, (
        'Symmetry in an added structure must update when its independent cell length changes'
    )


def test_cross_phase_cycle_is_refused_without_changing_loaded_files(tmp_path):
    directory = MATERIALIZE(
        tmp_path,
        [('a', 'phase.atom_site.A.adp_iso'), ('b', 'other.atom_site.A.adp_iso')],
        ['b = a', 'a = b'],
        second_structure=True,
    )
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*.edi')}
    with pytest.raises(engine.ValidationError, match='cycle'):
        engine.Project.load(directory)
    assert {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob('*.edi')
    } == before, 'A refused cross-phase cycle must leave every input file unchanged'


@pytest.mark.parametrize('entry', ['stored', 'window'])
def test_added_structure_geometry_applies_cross_phase_declarations(tmp_path, entry):
    project = engine.Project.load(MATERIALIZE(tmp_path / 'first'))
    MATERIALIZE(tmp_path / 'donor', second_structure=True)
    project.structures.add(
        engine.StructureFactory.from_cif_path(tmp_path / 'donor/structures/other.edi')
    )
    source = project.structures['phase'].atom_sites[0].fract_x
    target = project.structures['other'].atom_sites[1].fract_y
    project.analysis.aliases.create(id='a', param=source)
    project.analysis.aliases.create(id='b', param=target)
    project.analysis.constraints.create(expression='b = 2*a + .1')
    project.analysis.calculate()
    added = project.structures['other']
    held = added.geometry()
    project.analysis.constraints['b'].expression = 'b = 3*a + .1'
    geometry = added if entry == 'stored' else added.geometry()
    atoms = geometry.expanded_atom_sites
    assert target.value == pytest.approx(0.61, abs=2e-13), (
        'Reading an added structure geometry must apply declaration changes in its owning project'
    )
    indices = [i for i, name in enumerate(atoms.atom_site_id) if name == 'B']
    assert indices, 'The added structure geometry must retain the dependent atom'
    for i in indices:
        assert atoms.cartn_y[i] == pytest.approx(4.1 * 0.61, abs=2e-12), (
            'Added structure Cartesian coordinates must use the updated dependent fraction'
        )
    assert not held.is_current(), (
        'Editing a relation must revoke geometry held for a structure added after project creation'
    )
