# SPDX-License-Identifier: BSD-3-Clause
"""Build the Co2SiO4 HEiDi project: three temperatures, each its own structure and dataset.

Sazonov et al., Acta Cryst. B 64 (2008) 661-668, measured one Co2SiO4 crystal on HEiDi (MLZ) at
300 K, 55 K and 2.5 K. The supplementary CIF gives the Pnma structure at each temperature and the
three reflection files their F2 and sigma. The 2.5 K data, below the ordering of the moments, hold
magnetic reflections, (1 0 0) among them; the moments are compared with Sazonov et al., Acta
Cryst. B 65 (2009) 664-675, Table 4. The 2.5 K file has 2-theta where sigma should be, so its
sigma is estimated (tools/data/estimate_cosio_heidi_su.py).

The project fits the three experiments independently. It starts every structure from the published
positions with one isotropic-equivalent U on every site, no extinction, a rough scale and, at
2.5 K, zero moments.

    python tools/cli_projects/build_cosio_heidi.py <folder with bp5014sup1.cif and the .hkl files>
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

import gemmi

ROOT = Path(__file__).resolve().parents[2]
CASE = 'sc-neut-cwl_cosio-heidi'
sys.path.insert(0, str(ROOT / 'tools' / 'data'))
import estimate_cosio_heidi_su as estimate  # noqa: E402

# Temperature, CIF block, structure and experiment ids, data file in the case's data/ folder.
TEMPERATURES = (
    ('300 K', '300K', 'cosio_300k', 'heidi_300k', 'heidi_300k.hkl'),
    ('55 K', '55K', 'cosio_55k', 'heidi_55k', 'heidi_55k.hkl'),
    ('2.5 K', '2point5K', 'cosio_2k5', 'heidi_2k5', 'heidi_2k5.hkl'),
)
WAVELENGTH = '0.552'
START_U = '0.003'  # one isotropic-equivalent start on every site
START_SCALE = '10'
WYCKOFF = {'Co1': 'a', 'Co2': 'c', 'Si': 'c', 'O1': 'c', 'O2': 'c', 'O3': 'd'}
# Free tensor components per Wyckoff position in Pnma: 4a (-1) all six, 4c (.m.) 11 22 33 13,
# 4d (1) all six. The others follow by symmetry.
FREE_TENSOR = {'a': (1, 1, 1, 1, 1, 1), 'c': (1, 1, 1, 0, 1, 0), 'd': (1, 1, 1, 1, 1, 1)}
# Free coordinates: 4a none, 4c x and z, 4d all three.
FREE_XYZ = {'a': (0, 0, 0), 'c': (1, 0, 1), 'd': (1, 1, 1)}
CREATED = '09 Nov 2026 18:00:00'


def number(text: str) -> str:
    """A CIF number without its bracketed s.u."""
    return text.split('(', 1)[0]


def free(value: str, *, is_free: bool) -> str:
    return f'{value}()' if is_free else value


def structure_text(block: gemmi.cif.Block, name: str, *, magnetic: bool) -> str:
    cell = [number(block.find_value(f'_cell_length_{axis}')) for axis in 'abc']
    lines = [f'data_{name}', '', '_edi.schema_version 3', '']
    lines += [f'_cell.length_{axis} {value}' for axis, value in zip('abc', cell, strict=True)]
    lines += ['_cell.angle_alpha 90', '_cell.angle_beta 90', '_cell.angle_gamma 90', '']
    lines += ['_space_group.name_h_m "P n m a"', '_space_group.coord_system_code abc', '']
    lines += ['loop_'] + [
        f'_atom_site.{item}'
        for item in (
            'id',
            'type_symbol',
            'fract_x',
            'fract_y',
            'fract_z',
            'wyckoff_letter',
            'occupancy',
            'adp_type',
            'adp_iso',
        )
    ]
    table = block.find('_atom_site_', ['label', 'type_symbol', 'fract_x', 'fract_y', 'fract_z'])
    labels = []
    for row in table:
        label = row[0]
        labels.append(label)
        letter = WYCKOFF[label]
        xyz = [free(number(row[2 + k]), is_free=bool(FREE_XYZ[letter][k])) for k in range(3)]
        element = row[1].capitalize()
        lines.append(f'{label} {element} {" ".join(xyz)} {letter} 1 Uani {START_U}')
    lines += ['', 'loop_', '_atom_site_aniso.id'] + [
        f'_atom_site_aniso.adp_{ij}' for ij in ('11', '22', '33', '12', '13', '23')
    ]
    for label in labels:
        mask = FREE_TENSOR[WYCKOFF[label]]
        start = [START_U, START_U, START_U, '0', '0', '0']
        lines.append(
            label
            + ' '
            + ' '.join(free(value, is_free=bool(m)) for value, m in zip(start, mask, strict=True))
        )
    if magnetic:
        lines += ['', MAGNETIC]
    return '\n'.join(lines) + '\n'


# Pnma with every operation time-even (BNS 62.441, k = 0): Co1 (Mx, My, Mz), Co2 (0, My, 0),
# Sazonov et al. 2009. The moments start at zero; the fit frees them.
MAGNETIC = """_space_group_magn.number_BNS "62.441"
_space_group_magn.name_BNS Pnma
_space_group_magn.name_UNI Pnma.1
_space_group_magn.number_OG "62.1.502"
_space_group_magn.name_OG Pnma
_parent_space_group.name_H-M_alt Pnma
_parent_space_group.IT_number 62
_parent_space_group.transform_Pp_abc "a,b,c;0,0,0"
_parent_space_group.child_transform_Pp_abc "a,b,c;0,0,0"
_parent_space_group.reference_setting standard
_parent_space_group.derived false
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
1 x,y,z,+1
2 x+1/2,-y+1/2,-z+1/2,+1
3 -x,y+1/2,-z,+1
4 -x+1/2,-y,z+1/2,+1
5 -x,-y,-z,+1
6 -x+1/2,y+1/2,z+1/2,+1
7 x,-y+1/2,z,+1
8 x+1/2,y,-z+1/2,+1
loop_
_space_group_symop_magn_centering.id
_space_group_symop_magn_centering.xyz
1 x,y,z,+1
loop_
_parent_propagation_vector.id
_parent_propagation_vector.kxkykz
1 0,0,0
loop_
_magnetic_form_factor.type_symbol
_magnetic_form_factor.ion
_magnetic_form_factor.j2_coefficient
Co Co2+ 0
loop_
_atom_site_moment.label
_atom_site_moment.crystalaxis_x
_atom_site_moment.crystalaxis_y
_atom_site_moment.crystalaxis_z
_atom_site_moment.symmform
Co1 0() 0() 0() Mx,My,Mz
Co2 0 0() 0 0,My,0"""


def experiment_text(name: str, structure: str, rows: list) -> str:
    lines = [
        f'data_{name}',
        '',
        '_edi.schema_version 3',
        '',
        '_experiment_type.sample_form "single crystal"',
        '_experiment_type.beam_mode "constant wavelength"',
        '_experiment_type.radiation_probe "neutron"',
        '_experiment_type.scattering_type "bragg"',
        '_experiment_type.dimensionality 1d',
        '_experiment_type.polarisation unpolarised',
        '_instrument.name HEiDi',
        '_instrument.facility "MLZ (FRM II)"',
        '_scattering_source.neutron_scattering_length sears1992',
        '',
        '_calculator.type crysta',
        '',
        f'_instrument.setup_wavelength {WAVELENGTH}',
        '',
        '_extinction.type larson-anisotropic',
    ]
    lines += [f'_extinction.coefficient_{ij} 0()' for ij in ('11', '22', '33', '12', '13', '23')]
    lines += ['', 'loop_', '_linked_structure.structure_id', '_linked_structure.scale']
    lines += [f'{structure} {START_SCALE}()', '']
    lines += ['loop_'] + [
        f'_refln.{item}'
        for item in ('id', 'index_h', 'index_k', 'index_l', 'intensity_meas', 'intensity_meas_su')
    ]
    for index, (hkl, f2, sigma) in enumerate(rows, 1):
        lines.append(f'{index} {hkl[0]} {hkl[1]} {hkl[2]} {f2} {sigma}')
    return '\n'.join(lines) + '\n'


def reflections(path: Path) -> list:
    """The h k l, F2meas and sigma of a _refln loop, each as written."""
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        fields = line.split()
        if len(fields) == 7 and fields[6] in {'o', '<'}:
            rows.append(((int(fields[0]), int(fields[1]), int(fields[2])), fields[4], fields[5]))
    return rows


PROJECT = """_edi.schema_version 3

_metadata.name             {case}
_metadata.title "Co₂SiO₄ [Pnma] at 300 K, 55 K and 2.5 K · HEiDi @ MLZ (FRM II)"
_metadata.description "Single crystal · Three temperatures fitted independently, moments at 2.5 K"
_metadata.authors .
_metadata.created          "{created}"
_metadata.last_modified    "{created}"
_metadata.timestamp        ?
"""

ANALYSIS = """_edi.schema_version 3

_fitting_mode.type independent
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'source', type=Path, help='the folder holding bp5014sup1.cif and the .hkl files'
    )
    parser.add_argument('--out', type=Path, default=ROOT / 'docs' / 'user' / 'cli' / CASE)
    args = parser.parse_args()
    data = args.out / 'data'
    project = args.out / 'project'
    for folder in (data, project / 'structures', project / 'experiments', project / 'analysis'):
        folder.mkdir(parents=True, exist_ok=True)
    # Each data file is named after its experiment, as the collection's data entries are.
    for source, name in (
        ('bp5014-300K.hkl', 'heidi_300k.hkl'),
        ('bp5014-55K.hkl', 'heidi_55k.hkl'),
    ):
        shutil.copyfile(args.source / source, data / name)
    estimated = data / 'heidi_2k5.hkl'
    sys.argv = ['estimate', str(args.source), str(estimated)]
    estimate.main()
    document = gemmi.cif.read(str(args.source / 'bp5014sup1.cif'))
    for _, block_name, structure, experiment, data_file in TEMPERATURES:
        block = document.find_block(block_name)
        text = structure_text(block, structure, magnetic=block_name == '2point5K')
        (project / 'structures' / f'{structure}.edi').write_text(text, encoding='utf-8')
        rows = reflections(data / data_file)
        text = experiment_text(experiment, structure, rows)
        (project / 'experiments' / f'{experiment}.edi').write_text(text, encoding='utf-8')
    (project / 'project.edi').write_text(
        PROJECT.format(case=CASE, created=CREATED), encoding='utf-8'
    )
    (project / 'analysis' / 'analysis.edi').write_text(ANALYSIS, encoding='utf-8')
    for path in sorted(data.iterdir()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f'{path.relative_to(args.out)} sha256 {digest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
