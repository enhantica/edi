"""Closed-form one-reflection controls for the starting-moment note.

A long c axis isolates 001. Pmmm at the origin permits only Mz in
Stokes-Campbell 47.252 (Pm'm'm), hence I_M/I_bound = 0; its rotated
embeddings allow a transverse moment and give ratio 1. Uniform occupancy
cancels from this ratio. P1 controls tilt c so the seeded moment has a
specified transverse fraction on either side of the cancellation threshold.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).parent
MASK = (1 << 64) - 1


def draw(axis):
    value = 14695981039346656037
    for byte in f'1.1#1|Co1|{axis}'.encode():
        value = ((value ^ byte) * 1099511628211) & MASK
    value = (value + 0x9E3779B97F4A7C15) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return 1 + ((value ^ (value >> 31)) / 2**64)


def tilted(ratio):
    mx, my, mz = (draw(axis) for axis in range(3))
    gamma = math.radians(170)
    cx = -(mx + my * math.cos(gamma)) / mz
    cy = -my * math.sin(gamma) / mz
    base_z2 = 1 - cx * cx - cy * cy
    if base_z2 <= 0:
        raise ValueError('The independent seeded vector must admit this unit-axis metric')
    delta = -ratio * cx + math.sqrt(ratio * ratio * cx * cx + ratio * base_z2)
    cx += delta
    cz = math.sqrt(1 - cx * cx - cy * cy)
    alpha = math.degrees(math.acos(cx * math.cos(gamma) + cy * math.sin(gamma)))
    beta = math.degrees(math.acos(cx))
    return (alpha, beta, 170), cz, (mx, my, mz)


def main():
    for name, group, occupancy, ratio in [
        ('note-longitudinal', 'P m m m', 1, 0),
        ('note-diluted', 'P m m m', 1e-12, 1),
        ('note-below', 'P 1', 1, 0.5e-12),
        ('note-above', 'P 1', 1, 2e-12),
        ('note-unlinked', 'P 1', 1, None),
    ]:
        angles, cz, moments = ((90, 90, 90), 1, None)
        if name in {'note-below', 'note-above'}:
            angles, cz, moments = tilted(ratio)
        folder = ROOT / 'gui' / name
        (folder / 'structures').mkdir(parents=True, exist_ok=True)
        (folder / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name start_note\n')
        (folder / 'structures/parent.edi').write_text(f'''data_parent
_edi.schema_version 3
_cell.length_a 1
_cell.length_b 1
_cell.length_c 10
_cell.angle_alpha {angles[0]:.17g}
_cell.angle_beta {angles[1]:.17g}
_cell.angle_gamma {angles[2]:.17g}
_space_group.name_h_m "{group}"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
Co1 Co . 0 0 0 {occupancy:.17g} .17 Biso
''')
        if ratio is not None:
            (folder / 'experiments').mkdir(exist_ok=True)
            position = math.degrees(2 * math.asin(3 / (20 * cz)))
            header = (ROOT.parent / 'adp_site_symmetry/gui/cubic/experiments/bank.edi').read_text()
            header = header[: header.index('loop_\n_data.two_theta')]
            header = header.replace('structure 1', 'parent 1').replace('1.54822', '3')
            data = '\n'.join(f'{position - 0.1 + 0.002 * i:.17g} 1 1' for i in range(101))
            (folder / 'experiments/bank.edi').write_text(
                header
                + 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
                + data
                + '\n'
            )
        (folder / 'PROVENANCE.json').write_text(
            json.dumps(
                {
                    'source': 'Closed form perpendicular projection at the sole line 001',
                    'ratio': ratio,
                    'occupancy': occupancy,
                    'seeded_unit_axis_moment': moments,
                    'cell_angles_degrees': angles,
                    'c_unit_normal_component': cz,
                },
                indent=2,
            )
            + '\n'
        )


if __name__ == '__main__':
    main()
