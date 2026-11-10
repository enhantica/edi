"""Author bounded loader inputs; model templates are inputs, not fit references.

Run in the example repository at the recorded input commit:
python tests/fixtures/background_estimate/generate_basis_loader_inputs.py
The emitted fixture tree is copied byte-for-byte to the engine repository.
"""

import json
import math
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def generate():
    output = HERE / 'basis-loader'
    records = {}
    for beam, source, experiment, start, stop, origin, low, high in [
        ('cwl', HERE / 'projects/fitted-auto-polynomial', 'd20', 20, 100, 80.125, 17.5, 105.25),
        (
            'tof',
            ROOT / 'docs/user/cli/pd-neut-tof_ceo2-pearl_polynomial/project',
            'pearl',
            2000,
            18000,
            8000.125,
            1750,
            18250,
        ),
    ]:
        target = output / beam
        (target / 'experiments').mkdir(parents=True, exist_ok=True)
        (target / 'analysis').mkdir(exist_ok=True)
        shutil.copytree(source / 'structures', target / 'structures', dirs_exist_ok=True)
        for path in (target / 'structures').glob('*.edi'):
            path.write_text(re.sub(r'(?<=\d)\([^)]*\)', '', path.read_text()))
        header = (
            (source / 'experiments' / (experiment + '.edi'))
            .read_text()
            .split('_background.type')[0]
        )
        header = re.sub(r'(?m)^_background_estimate\..*\n', '', header)
        header = re.sub(
            r'loop_\n_excluded_region\.id\n_excluded_region\.start\n'
            r'_excluded_region\.end\n(?:[^_\n][^\n]*\n)+',
            '',
            header,
        )
        header = re.sub(r'(?<=\d)\([^)]*\)', '', header)
        header += (
            '_background_estimate.mode auto\n_background_estimate.method snip\n'
            '_background_estimate.width 3\n_background_estimate.tolerance 2\n'
            '_background_estimate.max_terms 3\n_background_estimate.use_model ignore\n'
            '_background.type polynomial\n_background.origin ' + str(origin) + '\n\n'
            'loop_\n_background.id\n_background.order\n_background.coef\n'
            'floor 0 450\nslope 1 -3\nbend 2 2\n\n'
        )
        grid = [start + (stop - start) * index / 64 for index in range(65)]
        header += (
            'loop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n'
            f'left {grid[0]} {grid[1]}\nright {grid[-2]} {grid[-1]}\n\n'
        )
        axis = 'two_theta' if beam == 'cwl' else 'time_of_flight'
        header += f'loop_\n_data.{axis}\n_data.intensity_meas\n_data.intensity_meas_su\n'
        # Closed form with nonzero deterministic noise and two separated peaks;
        # only parsing/derivation and lifecycle seams are judged in its consumers.
        for index, x in enumerate(grid):
            z = index / 64
            y = 450 - 30 * z + 8 * z * z + 0.7 * math.sin(1.7 * index)
            y += 95 * math.exp(-(((z - 0.31) / 0.022) ** 2))
            y += 70 * math.exp(-(((z - 0.72) / 0.025) ** 2))
            header += f'{x:.17g} {y:.17g} 1.5\n'
        (target / 'experiments' / (experiment + '.edi')).write_text(header)
        (target / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name basis-loader\n')
        (target / 'analysis/analysis.edi').write_text(
            '_edi.schema_version 3\n_fitting_mode.type single\n_minimizer.max_iterations 1\n'
        )
        records[beam] = {
            'experiment': experiment,
            'grid': grid,
            'included': grid[2:-2],
            'origin': origin,
            'x_min': low,
            'x_max': high,
        }
    (output / 'inputs.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    generate()
