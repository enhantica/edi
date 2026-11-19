"""Magnetic CIF identity and geometry against COMCIFS and ISODISTORT."""

import json
from collections import Counter
from operator import itemgetter
from pathlib import Path

import edi as api
import gemmi
import pytest

from tests.fixtures.magnetic_pnma.reference import columns, project
from tests.fixtures.magnetic_type.inputs import SOURCE, source

EXPECTED = (
    ('Co1_1', 'a', 4, (False, False, False)),
    ('Co2_1', 'c', 4, (True, False, True)),
    ('Si_1', 'c', 4, (True, False, True)),
    ('O1_1', 'c', 4, (True, False, True)),
    ('O2_1', 'c', 4, (True, False, True)),
    ('O3_1', 'd', 8, (True, True, True)),
)
MAGNETIC_PREFIXES = (
    '_space_group_magn.',
    '_space_group_magn_transforms.',
    '_space_group_symop_magn_',
    '_parent_space_group.',
    '_parent_propagation_vector.',
    '_atom_site_moment.',
    '_atom_type_scat.neutron_magnetic_',
)


def load(tmp_path, *, shifted=False, scalar=False):
    return api.Project.load(project(tmp_path / 'input', source(shifted=shifted, scalar=scalar)))


def saved_columns(model, folder):
    model.save_as(folder)
    return columns((folder / 'structures/cosio.edi').read_text())


def test_shifted_reference_is_the_same_crystal_in_a_translated_frame():
    ordinary = gemmi.cif.read_string(source()).sole_block()
    shifted = gemmi.cif.read_string(source(shifted=True)).sole_block()
    xs = [float(value) for value in ordinary.find_values('_atom_site_fract_x')]
    moved = [float(value) for value in shifted.find_values('_atom_site_fract_x')]
    assert moved == pytest.approx([value + 0.25 for value in xs], abs=1e-12), (
        'The origin witness moves every authored site by exactly one quarter cell'
    )
    for before, after in zip(
        ordinary.find_values('_space_group_symop_magn_operation.xyz'),
        shifted.find_values('_space_group_symop_magn_operation.xyz'),
        strict=True,
    ):
        op = gemmi.Op(gemmi.cif.as_string(before).rsplit(',', 1)[0])
        moved_op = gemmi.Op(gemmi.cif.as_string(after).rsplit(',', 1)[0])
        point = [0.173, 0.287, 0.391]
        original = op.apply_to_xyz(point)
        actual = moved_op.apply_to_xyz([point[0] + 0.25, *point[1:]])
        assert actual == pytest.approx([original[0] + 0.25, *original[1:]], abs=1e-12), (
            'The shifted operations intertwine the original symmetry with the same translation'
        )


def test_two_native_saves_keep_the_published_metric_sites_and_moments(tmp_path):
    expected = columns(SOURCE.read_text())
    model = load(tmp_path)
    for index in range(2):
        destination = tmp_path / f'geometry-{index}'
        saved_columns(model, destination)
        model = api.Project.load(destination)
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        ):
            assert getattr(model.structure.cell, name).value == float(
                expected['_cell_' + name][0]
            ), 'A native magnetic round trip keeps the independently declared cell metric'
        for row, name in enumerate(expected['_atom_site_label']):
            atom = model.structure.atom_sites[name]
            for axis in 'xyz':
                observed = getattr(atom, 'fract_' + axis).value % 1
                reference = float(expected['_atom_site_fract_' + axis][row]) % 1
                assert observed == pytest.approx(reference, abs=1e-12), (
                    'A native magnetic round trip preserves every published position '
                    'modulo a lattice period'
                )
        for row, name in enumerate(expected['_atom_site_moment.label']):
            for axis in 'xyz':
                parameter = getattr(model.structure.atom_site_moment[name], 'crystalaxis_' + axis)
                assert parameter.value == float(
                    expected['_atom_site_moment.crystalaxis_' + axis][row]
                ), (
                    'A native magnetic round trip preserves the independently supplied '
                    'moment components'
                )


@pytest.mark.parametrize('shifted', [False, True])
def test_isodistort_sites_resolve_their_magnetic_table_positions(tmp_path, shifted):
    model = load(tmp_path, shifted=shifted)
    saved = saved_columns(model, tmp_path / 'saved')
    actual = dict(
        zip(
            saved['_atom_site.id'],
            zip(saved['_atom_site.wyckoff_letter'], saved['_atom_site.multiplicity'], strict=True),
            strict=True,
        )
    )
    assert actual == {name: (letter, str(count)) for name, letter, count, _ in EXPECTED}, (
        'ISODISTORT magnetic sites retain their 4a/4c/8d table identities in either origin'
    )
    expanded = model.structure.expanded_atom_sites
    identities = {
        (name, *(round(value % 1, 8) % 1 for value in xyz))
        for name, *xyz in zip(
            expanded.atom_site_id,
            expanded.fract_x,
            expanded.fract_y,
            expanded.fract_z,
            strict=True,
        )
    }
    assert Counter(row[0] for row in identities) == {
        name: count for name, _, count, _ in EXPECTED
    }, 'Each ISODISTORT site has exactly its independently declared magnetic orbit multiplicity'


@pytest.mark.parametrize('site', EXPECTED, ids=itemgetter(0))
def test_coordinate_ties_follow_isodistort_displacement_forms(tmp_path, site):
    model = load(tmp_path)
    atom = model.structure.atom_sites[site[0]]
    for axis, independent in zip('xyz', site[3], strict=True):
        parameter = getattr(atom, 'fract_' + axis)
        assert parameter.symmetry_constrained == (not independent), (
            'ISODISTORT fract_symmform sets the exact independent coordinate subspace'
        )


@pytest.mark.parametrize('field', ['length_a', 'length_b', 'length_c'])
def test_magnetic_powder_cell_lengths_remain_fittable(tmp_path, field):
    model = load(tmp_path)
    parameter = getattr(model.structure.cell, field)
    parameter.free = True
    assert parameter.free, 'Table-resolved magnetic powder cell lengths can enter the fit'
    target = tmp_path / 'free-cell'
    model.save_as(target)
    restored = api.Project.load(target)
    assert getattr(restored.structure.cell, field).free, (
        'Saving a table-resolved magnetic structure retains its independent cell free flag'
    )


@pytest.mark.parametrize(('name', 'axis'), [('Co2_1', 'x'), ('Co2_1', 'z'), ('O3_1', 'y')])
def test_independent_magnetic_positions_remain_fittable(tmp_path, name, axis):
    model = load(tmp_path)
    parameter = getattr(model.structure.atom_sites[name], 'fract_' + axis)
    parameter.free = True
    assert parameter.free, 'ISODISTORT independent magnetic coordinates can enter the fit'
    target = tmp_path / 'free-position'
    model.save_as(target)
    restored = api.Project.load(target)
    assert getattr(restored.structure.atom_sites[name], 'fract_' + axis).free, (
        'Saving a table-resolved magnetic structure retains its independent coordinate free flag'
    )


@pytest.mark.parametrize('scalar', [False, True], ids=['loop', 'scalar'])
@pytest.mark.parametrize('shifted', [False, True], ids=['standard', 'quarter-origin'])
def test_both_transform_inputs_write_the_bns_loop_on_two_saves(tmp_path, scalar, shifted):
    model = load(tmp_path, shifted=shifted, scalar=scalar)
    expected = 'a,b,c;1/4,0,0' if shifted else 'a,b,c;0,0,0'
    for index in range(2):
        folder = tmp_path / f'saved-{index}'
        values = saved_columns(model, folder)
        sources = values.get('_space_group_magn_transforms.source', [])
        transforms = values.get('_space_group_magn_transforms.pp_abc', [])
        assert len(sources) == len(transforms) and sources.count('BNS') == 1, (
            'Either dictionary transform input writes one unambiguous BNS transform loop row'
        )
        assert transforms[sources.index('BNS')] == expected, (
            'The BNS transform loop retains the independent nontrivial origin as well as identity'
        )
        assert '_space_group_magn.transform_bns_pp_abc' not in values, (
            'Native saving uses the ISODISTORT loop representation for the setting'
        )
        model = api.Project.load(folder)


def test_magnetic_native_file_has_no_crystal_space_group(tmp_path):
    model = load(tmp_path)
    expected = columns(SOURCE.read_text())
    for index in range(2):
        folder = tmp_path / f'saved-{index}'
        values = saved_columns(model, folder)
        assert not any(tag.startswith('_space_group.') for tag in values), (
            'A magnetic native file has no competing crystal space-group category'
        )
        for tag in (
            '_space_group_magn.number_bns',
            '_space_group_magn.name_bns',
            '_space_group_magn.name_uni',
            '_space_group_magn.number_og',
            '_space_group_magn.name_og',
            '_space_group_magn.point_group_name_uni',
            '_space_group_magn.point_group_number_litvin',
        ):
            assert values.get(tag) == expected[tag], (
                'Magnetic identifiers and derived symbols retain the independent ISODISTORT values'
            )
        assert values.get('_parent_space_group.it_number') == ['62'], (
            'A magnetic file without a parent receives its own space group as the parent'
        )
        model = api.Project.load(folder)


def test_saved_magnetic_categories_use_only_defined_dictionary_items(tmp_path):
    values = saved_columns(load(tmp_path), tmp_path / 'saved')
    dictionary = json.loads(
        (
            Path(__file__).resolve().parents[2] / 'fixtures/magnetic_type/dictionary.json'
        ).read_text()
    )
    observed = {tag for tag in values if tag.startswith(MAGNETIC_PREFIXES)}
    assert observed, 'The dictionary audit reaches actual saved magnetic categories'
    assert observed <= set(dictionary['tags']), (
        'Every item saved as a magnetic dictionary item is defined by COMCIFS'
    )
    assert not any('crystal_system' in tag for tag in values), (
        'The displayed magnetic crystal system is derived and never saved'
    )
