"""Compare a real manually built model with an independently saved case input."""

import math

import gemmi


def model_errors(record, reference):
    errors = []
    actual = gemmi.cif.read_string(record['structure']).sole_block()
    expected = gemmi.cif.read_file(str(reference)).sole_block()
    for axis in ['length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma']:
        tag = '_cell.' + axis
        if not math.isclose(
            gemmi.cif.as_number(actual.find_value(tag)),
            gemmi.cif.as_number(expected.find_value(tag)),
            rel_tol=0,
            abs_tol=1e-9,
        ):
            errors.append('cell ' + axis)
    if gemmi.cif.as_string(actual.find_value('_space_group.name_h_m')).replace(' ', '') != (
        gemmi.cif.as_string(expected.find_value('_space_group.name_h_m')).replace(' ', '')
    ):
        errors.append('space group')
    tags = [
        '_atom_site.' + field
        for field in ['id', 'type_symbol', 'fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso']
    ]
    got = {gemmi.cif.as_string(row[0]): list(row)[1:] for row in actual.find(tags)}
    want = {gemmi.cif.as_string(row[0]): list(row)[1:] for row in expected.find(tags)}
    if got.keys() != want.keys():
        errors.append('atom inventory')
    for label in got.keys() & want.keys():
        if gemmi.cif.as_string(got[label][0]) != gemmi.cif.as_string(want[label][0]):
            errors.append('atom species ' + label)
        if any(
            not math.isclose(
                gemmi.cif.as_number(a), gemmi.cif.as_number(b), rel_tol=0, abs_tol=1e-9
            )
            for a, b in zip(got[label][1:], want[label][1:], strict=True)
        ):
            errors.append('site coordinates/occupancy/displacement ' + label)
    if record['links'] != [expected.name]:
        errors.append('structure links')
    if record['measured'] != 0 or not record['positiveCalculated']:
        errors.append('data-free calculated pattern')
    return errors
