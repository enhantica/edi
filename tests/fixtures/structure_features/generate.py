"""Write independent cubic geometry and active-scattering-table UI inputs."""

import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITES = [
    ('Fe1', 'Fe', (0.5, 0.5, 0.5)),
    ('O1', 'O', (0.84001, 0.5, 0.5)),
    ('O2', 'O', (0.15999, 0.5, 0.5)),
    ('O3', 'O', (0.5, 0.84001, 0.5)),
    ('O4', 'O', (0.5, 0.15999, 0.5)),
    ('O5', 'O', (0.5, 0.5, 0.84001)),
    ('O6', 'O', (0.5, 0.5, 0.15999)),
]


def keys(path, *, neutron):
    data = path.read_bytes()
    rows = [
        line.split('\t')
        for line in data.decode().splitlines()
        if line and not line.startswith(('#', '@'))
    ]
    return sorted(
        row[0] for row in rows if not neutron or math.isfinite(float(row[2]))
    ), hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-source', type=Path, required=True)
    args = parser.parse_args()
    reference = {
        'claim': 'Declared cubic input and closed Euclidean distances, not app output',
        'cell_edge_angstrom': 6,
        'min_distance': 0.1,
        'distance_increment': 0.15,
        'radii_source': 'Published Cordero covalent radii, Fe=1.32 A and O=0.66 A',
        'bonds': [],
        'atom_types': {},
        'table_sha256': {},
    }
    for index, first in enumerate(SITES):
        for second in SITES[index + 1 :]:
            distance = math.dist(first[2], second[2]) * 6
            radii = {'Fe': 1.32, 'O': 0.66}
            if 0.1 <= distance <= radii[first[1]] + radii[second[1]] + 0.15:
                reference['bonds'].append({'sites': [first[0], second[0]], 'distance': distance})
    paths = {
        'neutron': 'crysta-default/neutron.tsv',
        'neutron-sears': 'cryspy-compat/neutron.tsv',
        'xray': 'crysta-default/xray_f0.tsv',
    }
    for name, relative in paths.items():
        symbols, digest = keys(
            args.engine_source / 'data/scattering' / relative, neutron=name.startswith('neutron')
        )
        reference['atom_types'][name] = symbols
        reference['table_sha256'][name] = digest
    (HERE / 'reference.json').write_text(json.dumps(reference, indent=2) + '\n')
    structure = """data_cosio
_edi.schema_version 3
_cell.length_a 6
_cell.length_b 6
_cell.length_c 6
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.wyckoff_letter
_atom_site.occupancy
_atom_site.adp_type
_atom_site.adp_iso
"""
    structure += ''.join(
        f'{name} {symbol} ' + ' '.join(map(str, xyz)) + ' a 1 Biso 0\n'
        for name, symbol, xyz in SITES
    )
    (HERE / 'cubic.edi').write_text(structure)
    (HERE / 'cubic-bonded.edi').write_text(
        structure + '_geom.min_bond_distance_cutoff .1\n_geom.bond_distance_inc .15\n'
    )
    for name in paths:
        source = 'sears1992' if name == 'neutron-sears' else 'rauch2003ext'
        probe = 'xray' if name == 'xray' else 'neutron'
        text = f"""data_d20
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe {probe}
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_instrument.setup_wavelength 1.87
_instrument.calib_twotheta_offset 0
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w .15
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
loop_
_linked_structure.structure_id
_linked_structure.scale
cosio 0
_background.type line-segment
loop_
_background.id
_background.position
_background.intensity
left 40 6
right 64 6
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
40 20 2
52 33 3
64 25 4
"""
        if probe == 'neutron':
            text += f'_scattering_source.neutron_scattering_length {source}\n'
        else:
            text += (
                '_scattering_source.xray_form_factor wk1995\n'
                '_scattering_source.xray_dispersion none\n'
            )
        (HERE / (name + '.edi')).write_text(text)


if __name__ == '__main__':
    main()
