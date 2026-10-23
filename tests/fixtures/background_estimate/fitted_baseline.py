"""Fit lifecycle invariants; frozen Manual results are labelled regression controls."""

import shlex
import shutil
from pathlib import Path

import numpy as np

from tests.fixtures.background_estimate.readonly import snapshot

HERE = Path(__file__).resolve().parent
KINDS = ['line-segment', 'polynomial', 'chebyshev']


def load(engine, destination, kind):
    shutil.copytree(HERE / 'projects' / ('fitted-auto-' + kind), destination)
    return engine.Project.load(destination)


def values(project):
    return np.asarray([row[2] for row in snapshot(project)])


def curve(project):
    experiment = project.experiment
    x = np.asarray(experiment.data.two_theta)
    rows = snapshot(project)
    if experiment.background_type == 'line-segment':
        return np.interp(x, [r[1] for r in rows], [r[2] for r in rows])
    coefficients = np.zeros(max(r[1] for r in rows) + 1)
    for _, order, value, _ in rows:
        coefficients[order] = value
    if experiment.background_type == 'polynomial':
        return np.polynomial.polynomial.polyval(x / 80 - 1, coefficients)
    # Authored domain in the input generator; it is not inferred from estimator output.
    return np.polynomial.chebyshev.chebval(
        2 * (x - 8.0953) / (149.7953 - 8.0953) - 1, coefficients
    )


def fit(project, route='analysis'):
    return project.analysis.fit() if route == 'analysis' else project.fit()


def refresh(project, engine, trigger):
    experiment = project.experiment
    if trigger == 'settings':
        if experiment.background_type == 'line-segment':
            experiment.background_estimate.n_points = 11
        else:
            experiment.background_estimate.max_terms = 1
    else:
        data = experiment.data
        experiment.data = engine.PdCwlData(
            two_theta=np.asarray(data.two_theta),
            intensity_meas=np.asarray(data.intensity_meas) + 125,
            intensity_meas_su=np.asarray(data.intensity_meas_su),
        )


def stored_pattern(directory):
    tags, result = [], {'_data': [], '_data_calc': []}
    for line in (Path(directory) / 'experiments/d20.edi').read_text().splitlines():
        words = shlex.split(line, comments=True)
        if words == ['loop_']:
            tags = []
        elif len(words) == 1 and words[0].startswith('_'):
            tags.append(words[0])
        elif len(words) == len(tags):
            for prefix, samples in result.items():
                if prefix + '.intensity_calc' in tags:
                    row = dict(zip(tags, words, strict=True))
                    samples.append([
                        float(row[prefix + '.intensity_calc']),
                        float(row[prefix + '.intensity_bkg']),
                    ])
    return np.asarray(result['_data_calc'] or result['_data'])
