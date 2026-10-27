"""Check a copy's renewed geometry with physical forms and a fresh-calculation invariant.

The fresh engine calculation checks representation identity, not absolute physics.
Cell transforms, operation membership, expanded positions and bond lengths below
are checked independently from the written cell and atom coordinates.
"""

import math
import re

import gemmi
import numpy as np

from tests.fixtures.project_save.reference import six_digits


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(token):
    return float(token.split('(')[0])


def rows(block, category):
    table = block.find_mmcif_category(category + '.')
    return [dict(zip(table.tags, row, strict=True)) for row in table]


def input_bytes(body):
    # Computed categories are an appended section; no other byte is masked.
    head = body.split(b'\n_atom_sites_cartn_transform.', 1)[0].rstrip()
    return re.sub(rb'(?m)^_edi.schema_version [34]$', b'_edi.schema_version <3-or-4>', head)


def reflection_input_bytes(body):
    lines = body.splitlines(keepends=True)
    header = b'_refln.intensity_calc\n'
    if header in lines:
        index = lines.index(header)
        require(
            index + 1 < len(lines) and not lines[index + 1].startswith(b'_'),
            'The renewed reflection column is the last declared loop column',
        )
        del lines[index]
        while index < len(lines) and lines[index].strip():
            row = lines[index]
            if row.startswith((b'_', b'loop_', b'data_')):
                break
            match = re.fullmatch(rb'(.*\S)[ \t]+\S+(\r?\n)?', row)
            require(match is not None, 'Each calculated reflection retains its original input row')
            lines[index] = match[1] + (match[2] or b'')
            index += 1
    return re.sub(
        rb'(?m)^_edi.schema_version [34]$', b'_edi.schema_version <3-or-4>', b''.join(lines)
    )


def check_reflections(body, expected):
    block = gemmi.cif.read_string(body.decode()).sole_block()
    values = list(block.find_values('_refln.intensity_calc'))
    require(
        bool(values) and len(values) == len(expected),
        'Every calculated single-crystal reflection is written exactly once',
    )
    for text, value in zip(values, expected, strict=True):
        require(
            not math.isinf(float(value)),
            'The calculated copy witness has no infinite unit requiring uncomputed storage',
        )
        if math.isnan(float(value)):
            require(text == '.', 'A reflection not calculated remains an inapplicable dot')
        else:
            require(
                float(text).hex() == six_digits(float(value)).hex(),
                'Each saved reflection equals independent six-digit spelling of a fresh '
                'calculation from the unchanged written model',
            )


def close_saved(token, value):
    require(
        math.isclose(float(token), six_digits(float(value)), rel_tol=5e-12, abs_tol=1e-14),
        'Written geometry follows the independent cell/coordinate form at six saved digits',
    )


def check_geometry(body):  # noqa: PLR0914 - separate physical operands
    block = gemmi.cif.read_string(body.decode()).sole_block()
    require(block.find_value('_edi.schema_version') == '4', 'Renewed geometry declares schema 4')
    a, b, c = (number(block.find_value('_cell.length_' + key)) for key in 'abc')
    alpha, beta, gamma = (
        math.radians(number(block.find_value('_cell.angle_' + key)))
        for key in ('alpha', 'beta', 'gamma')
    )
    ca, cb, cg, sg = math.cos(alpha), math.cos(beta), math.cos(gamma), math.sin(gamma)
    matrix = np.array([
        [a, b * cg, c * cb],
        [0, b * sg, c * (ca - cb * cg) / sg],
        [0, 0, c * math.sqrt(1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg) / sg],
    ])
    for i in range(3):
        for j in range(3):
            close_saved(
                block.find_value(f'_atom_sites_cartn_transform.mat_{i + 1}{j + 1}'), matrix[i, j]
            )
    require(
        gemmi.cif.as_string(block.find_value('_atom_sites_cartn_transform.axes'))
        == 'a along x; b in the xy plane',
        'The saved transform declares the independently used Cartesian convention',
    )
    name = gemmi.cif.as_string(block.find_value('_space_group.name_h_m'))
    code = gemmi.cif.as_string(block.find_value('_space_group.coord_system_code'))
    # b1 and abc are standard monoclinic/orthorhombic axes; numeric codes select origins.
    group = gemmi.SpaceGroup(name + (':' + code if code and code not in {'b1', 'abc'} else ''))
    operations = rows(block, '_space_group_symop')
    ops = {
        row['_space_group_symop.id']: gemmi.Op(
            gemmi.cif.as_string(row['_space_group_symop.operation_xyz'])
        )
        for row in operations
    }
    require(
        len(ops) == len(operations)
        and {op.triplet() for op in ops.values()} == {op.triplet() for op in group.operations()},
        'The saved operations are exactly the independently tabulated selected space group',
    )
    sites = {row['_atom_site.id']: row for row in rows(block, '_atom_site')}
    positions = {}
    expanded = rows(block, '_expanded_atom_site')
    require(bool(expanded), 'A renewed structure retains actual expanded atom rows')
    for row in expanded:
        prefix = '_expanded_atom_site.'
        site = sites[row[prefix + 'atom_site_id']]
        operation, shift = row[prefix + 'site_symmetry'].split('_')
        xyz = [number(site['_atom_site.fract_' + axis]) for axis in 'xyz']
        xyz = np.asarray(ops[operation].apply_to_xyz(xyz)) + np.array([int(n) - 5 for n in shift])
        cart = matrix @ xyz
        for axis, value, cart_value in zip('xyz', xyz, cart, strict=True):
            close_saved(row[prefix + 'fract_' + axis], value)
            close_saved(row[prefix + 'cartn_' + axis], cart_value)
        require(row[prefix + 'id'] not in positions, 'Expanded atom IDs remain unique')
        positions[row[prefix + 'id']] = cart
    for row in rows(block, '_geom_bond'):
        left = positions[row['_geom_bond.expanded_atom_site_id_1']]
        right = positions[row['_geom_bond.expanded_atom_site_id_2']]
        close_saved(row['_geom_bond.distance'], np.linalg.norm(left - right))


def compare_members(before, after, directory, engine):
    require(before.keys() == after.keys(), 'A recalculated copy retains exactly every member name')
    source, output = directory / 'reference-input', directory / 'reference-calculated'
    for name, body in before.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    fresh = engine.Project.load(source)
    fresh.analysis.calculate()
    calculated = {}
    for name, body in before.items():
        if not (name.startswith('experiments/') and name.endswith('.edi')):
            continue
        block = gemmi.cif.read_string(body.decode()).sole_block()
        if (
            gemmi.cif.as_string(block.find_value('_experiment_type.sample_form'))
            != 'single crystal'
        ):
            continue
        bank = fresh.experiments[name.rsplit('/', 1)[-1][:-4]]
        calculated[name] = np.asarray(bank.refln.intensity_calc).copy()
    fresh.save_as(output)
    for name, body in before.items():
        actual = after[name]
        if name.startswith('structures/') and name.endswith('.edi'):
            require(
                input_bytes(body) == input_bytes(actual),
                'A recalculated copy retains every non-derived structure byte',
            )
            require(
                actual == (output / name).read_bytes(),
                'Copied geometry equals a fresh calculation from the written model '
                '(round-trip representation invariant)',
            )
            check_geometry(actual)
        elif name in calculated:
            require(
                reflection_input_bytes(body) == reflection_input_bytes(actual),
                'A recalculated copy retains every non-derived single-crystal byte',
            )
            check_reflections(actual, calculated[name])
            require(
                actual == (output / name).read_bytes(),
                'Copied reflection files equal the independently calculated representation',
            )
        else:
            require(actual == body, 'A copy retains every unrelated member byte: ' + name)
