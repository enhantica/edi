"""Small authored inputs isolate UI stability from unrelated diffraction work.

The hover vehicle reuses the independent fit-policy P1 powder declarations. The
relation vehicle uses the committed P1 magnetic uncertainty fixture. The cobalt
vehicle retains the two published cobalt sites and cell of the bundled Co2SiO4
input, with Co2 translated by one exact lattice period. No engine output is used.
"""

import json
from decimal import Decimal
from pathlib import Path

from tests.fixtures.cif_import_cases import columns
from tests.fixtures.fittability.inputs import experiment, materialize

ROOT = Path(__file__).resolve().parents[3]


def project(root, name):
    path = root / name
    for folder in ('structures', 'experiments', 'analysis'):
        (path / folder).mkdir(parents=True, exist_ok=True)
    (path / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name stability\n')
    return path


def cobalt_input(root, small_pattern):
    cobalt = project(root, 'cobalt')
    declared = columns(
        (ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/project/structures/cosio.edi').read_text()
    )
    fields = (
        'id',
        'type_symbol',
        'fract_x',
        'fract_y',
        'fract_z',
        'occupancy',
        'adp_iso',
        'adp_type',
    )
    lines = ['data_cosio', '_edi.schema_version 3']
    lines += [
        tag.replace('_cell_', '_cell.', 1) + ' ' + values[0]
        for tag, values in declared.items()
        if tag.startswith('_cell_')
    ]
    lines += ['_space_group.name_h_m "P n m a"', '_space_group.coord_system_code abc', 'loop_']
    lines += ['_atom_site.' + field for field in fields]
    proof = {}
    for name in ('Co1', 'Co2'):
        index = declared['_atom_site_id'].index(name)
        values = [declared['_atom_site_' + field][index] for field in fields]
        if name == 'Co2':
            before = values[4].removesuffix('()')
            after = Decimal(before) - 1
            if not 0 <= Decimal(before) < 1 or not -1 <= after < 0:
                raise ValueError(
                    'The cobalt witness translates its in-cell position by one period'
                )
            values[4] = str(after) + ('()' if values[4].endswith('()') else '')
            proof = {'original_z': float(before), 'translated_z': float(after), 'period': 1}
        lines.append(' '.join(values))
    (cobalt / 'structures/cosio.edi').write_text('\n'.join(lines) + '\n')
    (cobalt / 'experiments/bank.edi').write_text(small_pattern)
    return proof


def generate(root):
    root = Path(root)
    hover = materialize(root / 'hover', single=False)
    source = (hover / 'structures/phase.edi').read_text()
    for index in range(2, 7):
        (hover / f'structures/phase{index}.edi').write_text(
            source.replace('data_phase', f'data_phase{index}')
        )
    relations = project(root, 'relations')
    source = (
        ROOT / 'tests/fixtures/magnetic_pnma/uncertainty-states/fixed-structure.edi'
    ).read_text()
    site = 'A Co a 0 0 0 1 .17 Biso\n'
    moment = 'A 1.00(20) 0 1\n'
    if source.count(site) != 1 or source.count(moment) != 1:
        raise ValueError(
            'The independent P1 fixture must retain its exact authored site and moment'
        )
    source = source.replace(site, site + 'B Co a .31 .27 .17 1 .29 Biso\n')
    source = source.replace(moment, 'A 1() 0 1\nB 0 2 0\n')
    (relations / 'structures/cosio.edi').write_text(source)
    small_pattern = experiment('bank', single=False, linked='cosio', measured=False) + (
        '_data_range.two_theta_min 10\n_data_range.two_theta_max 30\n'
        '_data_range.two_theta_step 5\n'
    )
    (relations / 'experiments/bank.edi').write_text(small_pattern)
    (relations / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        'a cosio.atom_site_moment.A.crystalaxis_x\n'
        'b cosio.atom_site_moment.B.crystalaxis_y\n\n'
        'loop_\n_constraint.id\n_constraint.expression\nb "b = 2*a"\n'
    )
    proof = cobalt_input(root, small_pattern)
    materialize(root / 'empty', single=False)
    (root / 'inputs.json').write_text(json.dumps({'cobalt': proof}, indent=2) + '\n')
    return root
