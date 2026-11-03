"""Materialise the native magnetic input for the rendered app gates."""

import json
from itertools import product
from operator import itemgetter
from pathlib import Path

import numpy as np

from tests.fixtures.magnetic_pnma import commensurate, reference

if __name__ == '__main__':
    root = Path(__file__).parent / 'app-project'
    if not root.exists():
        reference.project(root)

    # Use the fixed 2.3 K structure that supplied the tick witness and the published D20 grid.
    # Bragg's law and the signed Pnma expansion supply the expected reflection positions.
    project = root.parents[3] / 'docs/user/cli/pd-neut-cwl_cosio-d20_2k/project'
    structure = reference.columns((root.parent / 'cosio-2k-reference.edi').read_text())
    structure = {key: [value.split('(')[0] for value in row] for key, row in structure.items()}
    experiment = reference.columns((project / 'experiments/d20.edi').read_text())
    cell = np.array([float(structure['_cell.length_' + axis][0]) for axis in 'abc'])
    wavelength = float(experiment['_instrument.setup_wavelength'][0])
    offset = float(experiment['_instrument.calib_twotheta_offset'][0].split('(')[0])
    exclusions = list(
        zip(
            map(float, experiment['_excluded_region.start']),
            map(float, experiment['_excluded_region.end']),
            strict=True,
        )
    )
    angles = []
    for hkl in product(*(range(int(2 * length / wavelength) + 1) for length in cell)):
        if not any(hkl):
            continue
        sine = wavelength * np.linalg.norm(np.array(hkl) / cell) / 2
        if sine >= 1 or reference.magnetic_squared(hkl, source=structure) < 1e-10:
            continue
        angle = float(2 * np.degrees(np.arcsin(sine)) + offset)
        angles.append({'hkl': hkl, 'angle': round(angle, 10)})
    reflections = ',\n'.join(
        '    ' + json.dumps(row) for row in sorted(angles, key=itemgetter('angle'))
    )
    (root.parent / 'magnetic-ticks.json').write_text(
        '{\n  "excluded": '
        + json.dumps(exclusions)
        + ',\n  "reflections": [\n'
        + reflections
        + '\n  ]\n}\n'
    )

    edit_root = root.parent / 'propagation-project'
    if not edit_root.exists():
        experiment = (
            (root.parent / 'experiment.edi').read_text().split('loop_\n_data.two_theta')[0]
        )
        experiment += (
            '_data_range.two_theta_min 10\n_data_range.two_theta_max 30\n'
            '_data_range.two_theta_step .5\n'
        )
        reference.project(
            edit_root, commensurate.structure(period=22, vectors=('1/2,0,0',)), experiment
        )
