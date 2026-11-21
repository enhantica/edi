"""ISODISTORT inputs with an independently applied quarter-cell origin shift."""

import json
from pathlib import Path

import gemmi

from tests.fixtures.magnetic_pnma.reference import project

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'data/collection/structures/cosio-magnetic.cif'


def source(*, shifted=False, scalar=False):
    block = gemmi.cif.read_file(str(SOURCE)).sole_block()
    block.name = 'cosio'
    if shifted:
        xs = block.find_values('_atom_site_fract_x')
        for index in range(len(xs)):
            xs[index] = format(float(xs[index]) + 0.25, '.8f')
        ops = block.find_values('_space_group_symop_magn_operation.xyz')
        for index in range(len(ops)):
            nuclear, theta = gemmi.cif.as_string(ops[index]).rsplit(',', 1)
            op = gemmi.Op(nuclear)
            translation = list(op.tran)
            translation[0] += 6 - op.rot[0][0] // 4
            op.tran = translation
            ops[index] = gemmi.cif.quote(op.triplet() + ',' + theta)
    transform = 'a,b,c;1/4,0,0' if shifted else 'a,b,c;0,0,0'
    if scalar:
        block.find_loop('_space_group_magn_transforms.id').get_loop().remove_column(
            '_space_group_magn_transforms.source'
        )
        block.find_loop('_space_group_magn_transforms.id').get_loop().remove_column(
            '_space_group_magn_transforms.Pp_abc'
        )
        block.find_loop('_space_group_magn_transforms.id').get_loop().remove_column(
            '_space_group_magn_transforms.id'
        )
        block.set_pair('_space_group_magn.transform_BNS_Pp_abc', gemmi.cif.quote(transform))
    else:
        transforms = block.find_values('_space_group_magn_transforms.Pp_abc')
        for index in range(len(transforms)):
            transforms[index] = gemmi.cif.quote(transform)
    return block.as_string()


def generate(root):
    root = Path(root)
    for name, shifted, scalar in (
        ('magnetic', False, False),
        ('shifted', True, False),
        ('scalar', True, True),
    ):
        text = source(shifted=shifted, scalar=scalar)
        if name == 'magnetic':
            block = gemmi.cif.read_string(text).sole_block()
            block.find_values('_atom_site_moment.crystalaxis_y')[1] = '2.37'
            text = block.as_string()
        project(root / name, text)
    project(root / 'crystal', (ROOT / 'tests/fixtures/magnetic_pnma/nuclear.edi').read_text())
    (root / 'reference.json').write_text(json.dumps({'source': str(SOURCE)}) + '\n')
    return root
