"""Author single-atom inputs and independent reciprocal-metric and magnetic references."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from tests.fixtures.chart_controls.generate_bragg import published_palettes

CELL = (4.3, 5.1, 6.7)
ROWS = ((1, 0, 0, 0.25, 0.02), (0, 1, 1, 0.64, 0.03), (1, 1, 1, 1.21, 0.04), (0, 0, 2, 0.09, 0.01))
HERE = Path(__file__).resolve().parent


def table(path, key, value):
    content = path.read_text()
    rows = csv.DictReader(
        io.StringIO('\n'.join(line for line in content.splitlines() if not line.startswith('#'))),
        delimiter='\t',
    )
    return next(row for row in rows if row[key] == value), hashlib.sha256(
        content.encode()
    ).hexdigest()


def sequential_sum(values):
    # Preserve the original producer's declared addition order across Python sum implementations.
    total = 0.0
    for value in values:
        total += value
    return total


def reference(engine_source):
    magnetic, digest = table(
        engine_source / 'data/scattering/magnetic_form_factor.tsv', 'ion', 'Co2+'
    )
    # Sears (1992), as the independently committed carrier's Co row; no application is imported.
    nuclear = (2.4900 / 10) ** 2
    # CODATA 2018 |mu_n/mu_N| and classical electron radius in fm, NIST reference values.
    p = 1.91304273 * 2.8179403262 / 20
    rows = []
    for h, k, index_l, measured, su in ROWS:
        reciprocal = [index / cell for index, cell in zip((h, k, index_l), CELL, strict=True)]
        inverse_d2 = sequential_sum(value**2 for value in reciprocal)
        sine = math.sqrt(inverse_d2) / 2
        j0 = sequential_sum(
            float(magnetic['j0_' + letter])
            * math.exp(-float(magnetic['j0_' + letter.lower()]) * sine**2)
            for letter in 'ABC'
        ) + float(magnetic['j0_D'])
        perpendicular = 1 - reciprocal[2] ** 2 / inverse_d2
        m2 = (p * 2 * j0) ** 2 * perpendicular
        rows.append({
            'hkl': [h, k, index_l],
            'sine': sine,
            'q': 4 * math.pi * sine,
            'measured': measured,
            'su': su,
            'nuclear': nuclear,
            'magnetic': m2,
            'total': nuclear + m2,
        })
    return {
        'claim': 'Closed forms for a P1 atom at the origin, Biso=0, unit scale, unpolarised beam',
        'cell': CELL,
        'intensity_units': '10^-24 cm^2 (1 fm = 0.1 times 10^-12 cm)',
        'neutron_source': 'Sears (1992), Co b=2.4900 fm',
        'magnetic_source': 'Brown, International Tables C (2006), Co2+ j0; j2 coefficient zero',
        'magnetic_table_sha256': digest,
        'constant_source': 'CODATA 2018, NIST neutron magnetic moment and electron radius',
        'relations': 's=1/(2d), Q=4*pi*s, F2_total=F2_nuclear+F2_magnetic',
        'rows': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-source', type=Path, required=True)
    args = parser.parse_args()
    (HERE / 'powder-colours.json').write_text(
        json.dumps(
            {
                'source': 'Independently published powder palette reference',
                'tokens': ['main', 'colourBlindSafe'],
                'palettes': published_palettes(),
            },
            indent=2,
        )
        + '\n'
    )
    (HERE / 'reference.json').write_text(
        json.dumps(reference(args.engine_source), indent=2) + '\n'
    )
    for magnetic in (False, True):
        structure = """data_cosio
_edi.schema_version 3
_cell.length_a 4.3
_cell.length_b 5.1
_cell.length_c 6.7
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_type
_atom_site.adp_iso
Co1 Co a 0 0 0 1 Biso 0
"""
        if magnetic:
            structure += """loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
1 x,y,z,+1
loop_
_atom_site_moment.label
_atom_site_moment.crystalaxis_x
_atom_site_moment.crystalaxis_y
_atom_site_moment.crystalaxis_z
Co1 0 0 2
loop_
_magnetic_form_factor.type_symbol
_magnetic_form_factor.ion
_magnetic_form_factor.j2_coefficient
Co Co2+ 0
"""
        (HERE / ('magnetic.edi' if magnetic else 'nuclear.edi')).write_text(structure)
    header = """data_d20
_edi.schema_version 3
_experiment_type.sample_form "single crystal"
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_experiment_type.polarisation unpolarised
_scattering_source.neutron_scattering_length sears1992
_instrument.setup_wavelength 1.87
_extinction.type none
loop_
_linked_structure.structure_id
_linked_structure.scale
cosio 1
"""
    (HERE / 'simulation.edi').write_text(header)
    header += 'loop_\n' + ''.join(
        '_refln.' + name + '\n'
        for name in ('index_h', 'index_k', 'index_l', 'intensity_meas', 'intensity_meas_su')
    )
    (HERE / 'measured.edi').write_text(
        header + ''.join(' '.join(map(str, row)) + '\n' for row in ROWS)
    )


if __name__ == '__main__':
    main()
