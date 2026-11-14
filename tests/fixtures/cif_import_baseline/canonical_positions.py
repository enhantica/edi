"""Named regression transitions checked against independent Gemmi group operations.

Crysta ADR-0106 permits a different representative of the same Wyckoff orbit;
ADR-0092 requires symmetry followers to use their rounded independent leader.
The archived scalar zero of the retired absorption coefficient may be omitted.
Every other reader column and saved byte remains exact.
"""

import re
from decimal import Decimal

import gemmi

from tests.fixtures.metadata_transition import task_inputs

SILICON = 'docs/user/cli/pd-neut-tof_lbco-si-mcstas/project'
PRASEODYMIUM = {
    'tests/fixtures/single_crystal/fitting/fullprof/sc-neut-cwl_pr2nio4-5c2_basic/project',
    'tests/fixtures/single_crystal/powder',
    'tests/fixtures/single_crystal/projects/sc-neut-cwl_pr2nio4_basic',
}
FOLLOWERS = {
    'tests/fixtures/fit_tables/five/structures/ncaf.edi',
    'tests/fixtures/fit_tables/one/structures/ncaf.edi',
}


def orbit_transition(case):
    if case == SILICON:
        group, operation = 'F d -3 m:1', '-x+1/4,-y+1/4,-z+1/4'
        before, after = ['0', '0', '0'], ['0.25', '0.25', '0.25']
    elif case in PRASEODYMIUM:
        group, operation = 'F m m m', 'x+1/2,y+1/2,z'
        before, after = ['0.5', '0.5', '0.35973'], ['0', '0', '0.35973']
    else:
        return None
    op = gemmi.Op(operation)
    if op.triplet() not in {item.triplet() for item in gemmi.SpaceGroup(group).operations()}:
        raise ValueError(
            'A regression transition must be a real independent space-group operation'
        )
    transformed = op.apply_to_xyz([float(value) for value in before])
    if any(
        abs((value - float(target)) % 1) > 1e-12
        for value, target in zip(transformed, after, strict=True)
    ):
        raise ValueError('The named representative must belong to the identical periodic orbit')
    return before, after


def reader_values(path, expected, frozen):
    expected = {name: list(values) for name, values in expected.items()}
    retired = expected.pop('_absorption_abscor2', None)
    if retired is not None and retired != ['0']:
        raise ValueError(
            'Only the retired fixed-zero absorption coefficient may leave a reader pin'
        )
    transition = task_inputs.rows().get(path)
    if transition is not None and transition['source_commit'] == 'b9bdbf9a2':
        values = []
        for endpoint in ('before_sha256', 'after_sha256'):
            raw = task_inputs.archived(transition[endpoint])
            matching = re.findall(rb'(?m)^_peak\.broad_lorentz_y ([^\r\n]+)$', raw)
            if len(matching) != 1:
                raise ValueError('The declared scan Y transition must bind one input coefficient')
            values.append(matching[0].decode())
        name = '_peak_broad_lorentz_y'
        if expected[name] != [values[0]]:
            raise ValueError('The scan reader transition must retain its exact older Y pin')
        expected[name] = [values[1]]
    # A project can contain both the transformed Si model and unrelated LBCO.
    # Bind the exact structure identity, never every structure in that folder.
    case, separator, filename = path.rpartition('/structures/')
    selected = separator and (
        (case == SILICON and filename == 'si.edi')
        or (case in PRASEODYMIUM and filename == 'structure.edi')
    )
    change = orbit_transition(case) if selected else None
    if change is not None:
        for axis, before, after in zip('xyz', *change, strict=True):
            name = '_atom_site_fract_' + axis
            if expected[name][0] != before:
                raise ValueError('The orbit transition must bind the exact frozen representative')
            expected[name][0] = after
    if path in FOLLOWERS:
        # These three sites have x=y=z in the original file; y/z are symmetry
        # followers. Their expected rounded x is already independently pinned.
        for axis in 'yz':
            for row in (1, 2, 5):
                name = '_atom_site_fract_' + axis
                leader = re.sub(r'\([^)]*\)', '', frozen['_atom_site_fract_x'][row])
                value = Decimal(frozen[name][row])
                if value.quantize(Decimal(leader)) != Decimal(leader):
                    raise ValueError('The original follower must round to its frozen leader')
                expected[name][row] = re.sub(r'\([^)]*\)', '', expected['_atom_site_fract_x'][row])
    return expected


def restore_representative(content, case):
    change = orbit_transition(case)
    if change is None:
        return content
    before, after = change
    label = 'Si Si' if case == SILICON else 'Pr Pr'
    pattern = rb'(?m)^(' + label.encode() + rb'[ \t]+)(\S+)([ \t]+)(\S+)([ \t]+)(\S+)'

    def restore(match):
        if [match[index].decode() for index in (2, 4, 6)] != after:
            raise ValueError('The saved representative must match the exact orbit transition')
        return b''.join((
            match[1],
            before[0].encode(),
            match[3],
            before[1].encode(),
            match[5],
            before[2].encode(),
        ))

    restored, count = re.subn(pattern, restore, content)
    if count != 1:
        raise ValueError('Exactly one pinned atom row may change its orbit representative')
    return restored
