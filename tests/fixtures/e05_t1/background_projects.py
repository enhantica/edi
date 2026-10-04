"""declared-background witnesses with closed-form observations, no engine output."""

import runpy
from pathlib import Path

import numpy as np


def materialize(root, models):
    root = Path(root)
    factory = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / 'c13_t6_background/project.py')
    )['materialize']
    x = np.linspace(23.0, 65.0, 19)
    row = {
        'project': 'pd-neut-cwl-background-provenance',
        'origin': 40.0,
        'x_min': 23.0,
        'x_max': 65.0,
        'coefficients': [10.0, 2.0],
    }
    for index, model in enumerate(models):
        row['type'] = model
        if model == 'line-segment':
            observed = 10.0 + 25.0 * (x - x[0]) / (x[-1] - x[0])
        elif model == 'polynomial':
            observed = 10.0 + 2.0 * (x / 40.0 - 1.0)
        else:
            observed = 10.0 + 2.0 * (2.0 * x - 23.0 - 65.0) / 42.0
        factory(root, row, x, observed, free=(0, 1), coefficients=[9.0, 1.0])
        original = root / 'experiments/experiment.edi'
        text = original.read_text().replace('data_experiment', f'data_bank_{index}')
        if model == 'line-segment':
            text = text.replace('23 10', '23 9(1)', 1).replace('65 35', '65 34(1)', 1)
        (root / f'experiments/bank_{index}.edi').write_text(text)
        original.unlink()
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type '
        + ('single' if len(models) == 1 else 'joint')
        + '\n_minimizer.max_iterations 3\n'
    )
    return root
