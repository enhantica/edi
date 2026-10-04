"""edi structure categories against closed forms at the Python seam."""

from __future__ import annotations

import math

import edi
import numpy as np
import pytest
import test_c13_t4_march as march


def structure_case(tmp_path, *, triclinic=False):
    """Build a small input; expected geometry below is independent of the engine."""
    path = tmp_path / 'input'
    march._project(path, None)
    source = path / 'structures/structure.edi'
    text = source.read_text()
    if triclinic:
        text = text.replace('"P m -3 m"', '"P 1"')
        for key, original, replacement in (
            ('length_a', '2', '5'),
            ('length_b', '2', '6'),
            ('length_c', '2', '7'),
            ('angle_alpha', '90', '80'),
            ('angle_beta', '90', '95'),
            ('angle_gamma', '90', '105'),
        ):
            text = text.replace(f'_cell.{key} {original}', f'_cell.{key} {replacement}')
        text = text.replace('X a Gd Biso 0 0 0 0.7 0.8', 'X1 a Si Biso 0.3 0.4 0.5 1 0.5')
    else:
        text = text.replace('"P m -3 m"', '"F m -3 m"')
        for key in ('length_a', 'length_b', 'length_c'):
            text = text.replace(f'_cell.{key} 2', f'_cell.{key} 5.64')
        text = text.replace(
            'X a Gd Biso 0 0 0 0.7 0.8',
            'Na1 a Na Biso 0 0 0 1 0.5\nCl1 b Cl Biso 0.5 0.5 0.5 1 1.2',
        )
    source.write_text(text)
    return edi.Project.load(path)


def test_edi_rock_salt_categories_geom_and_save(tmp_path):
    project = structure_case(tmp_path)
    atoms = project.structure.expanded_atom_sites
    bonds = project.structure.geom_bond
    assert len(atoms.id) == 27 and len(bonds.id) == 54, (
        ' edi must publish the closed-form 27 sites and 54 nearest-neighbour salt bonds'
    )
    assert tuple(bonds.distance) == pytest.approx((2.82,) * 54, abs=2e-8), (
        ' edi bond distances must use the 5.64 Å cubic frame'
    )
    assert np.asarray(atoms.fract_x).dtype == np.float64 and not atoms.fract_x.flags.writeable, (
        ' edi computed numeric columns are read-only float64 arrays'
    )
    assert tuple(atoms.u_iso[:1]) == pytest.approx((0.5 / (8 * math.pi**2),), abs=2e-9), (
        ' edi converts Biso to Uiso once at the structure seam'
    )
    project.analysis.calculate()
    saved = tmp_path / 'saved'
    project.save_as(saved)
    text = (saved / 'structures/structure.edi').read_text()
    assert '_expanded_atom_site.' in text and '_geom_bond.' in text, (
        ' edi writes current structure categories'
    )
    assert '_geom.bond_distance_inc' not in text, (
        ' undeclared geom defaults must not gain file tags on save'
    )
    carried = edi.Project.load(saved)
    assert len(carried.structure.expanded_atom_sites.id) == 27, (
        ' the first edi non-UI read recalculates a loaded structure unit'
    )
    project.structure.geom.bond_distance_inc = 0.10
    assert len(project.structure.geom_bond.id) == 0, (
        ' edi must pass the declared geom increment to crysta geometry'
    )
    project.save_as(tmp_path / 'geom-saved')
    geom_text = (tmp_path / 'geom-saved/structures/structure.edi').read_text()
    assert '_geom.bond_distance_inc' in geom_text, ' edi writes the declared bond increment'
    assert '_geom.min_bond_distance_cutoff' in geom_text, (
        ' edi writes the declared minimum bond cutoff'
    )


def test_edi_triclinic_frame_and_edit_currentness(tmp_path):
    project = structure_case(tmp_path, triclinic=True)
    atoms = project.structure.expanded_atom_sites
    assert (atoms.cartn_x[0], atoms.cartn_y[0], atoms.cartn_z[0]) == pytest.approx(
        (0.573789192, 2.865693772, 3.443431737), abs=2e-8
    ), " edi must expose crysta's triclinic Cartesian frame"
    before = np.asarray(atoms.cartn_x).copy()
    project.structure.cell.length_a.value = 5.7
    destination = tmp_path / 'stale'
    project.save_as(destination)
    assert '_expanded_atom_site.' not in (destination / 'structures/structure.edi').read_text(), (
        ' edi never saves structure geometry after an input edit and before recalculation'
    )
    after = project.structure.expanded_atom_sites
    assert not np.array_equal(np.asarray(after.cartn_x), before), (
        ' an edi non-UI geometry read recalculates after a cell edit'
    )
    assert np.array_equal(np.asarray(atoms.cartn_x), before), (
        ' a held edi category remains an immutable prior snapshot'
    )


def test_same_atom_site_removed_and_readded_stays_stale_for_view_and_save(tmp_path):
    project = structure_case(tmp_path, triclinic=True)
    previous = project.structure.expanded_atom_sites
    window = project.structure.geometry()
    assert window.is_current(), ' the starting view window describes the calculated structure'
    site = project.structure.atom_sites[0]
    site_id = site.id
    del project.structure.atom_sites[site_id]
    assert not window.is_current(), ' removing an atom site stales a held geometry window'
    project.structure.atom_sites.add(site)
    stale_before_save = not window.is_current()
    destination = tmp_path / 'same-site-stale'
    project.save_as(destination)
    saved = (destination / 'structures/structure.edi').read_text()
    defects = []
    if not stale_before_save or window.is_current():
        defects.append('held window became current after same-object readdition')
    if '_expanded_atom_site.' in saved or '_geom_bond.' in saved:
        defects.append('delegated save wrote the old computed geometry')
    assert not defects, (
        ' same-object atom-site readdition stales the held window and omits geometry '
        'from delegated save: ' + '; '.join(defects)
    )
    assert len(previous.id) > 0, ' the held prior geometry remains readable after the edit'


@pytest.mark.parametrize('value', ['-0.1', 'nan', 'inf'])
def test_edi_invalid_geom_input_refuses_at_load(tmp_path, value):
    structure_case(tmp_path)
    source = tmp_path / 'input/structures/structure.edi'
    text = source.read_text().replace(
        '_space_group.name_h_m "F m -3 m"',
        f'_space_group.name_h_m "F m -3 m"\n_geom.bond_distance_inc {value}',
    )
    source.write_text(text)
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)geom|bond|finite|negative'):
        edi.Project.load(tmp_path / 'input')
