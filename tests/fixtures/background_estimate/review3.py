"""Disposable lifecycle controls; no fit result claims physical correctness."""

import re
import shlex
import shutil
from pathlib import Path

from tests.fixtures.background_estimate.fitted_baseline import HERE

KINDS = ['line-segment', 'polynomial', 'chebyshev']


def materialize(destination, kind, *, second=False, simulation=False, mode='single'):
    destination = Path(destination)
    shutil.copytree(HERE / 'projects' / ('fitted-auto-' + kind), destination)
    if second:
        text = (destination / 'experiments/d20.edi').read_text()
        text = text.replace('data_d20', 'data_other')
        text = text.replace('_background_estimate.mode auto', '_background_estimate.mode manual')
        # The second bank only witnesses a current delegated calculation.
        text = re.sub(r'(?<=[0-9.])\([^)]*\)', '', text)
        if simulation:
            before = text.split('loop_\n_data.two_theta\n', 1)[0]
            text = before + (
                '_data_range.two_theta_min 8.0953\n'
                '_data_range.two_theta_max 149.7953\n'
                '_data_range.two_theta_step 0.1\n'
            )
        (destination / 'experiments/other.edi').write_text(text)
    file = destination / 'analysis/analysis.edi'
    file.write_text(
        re.sub(r'(?m)^_fitting_mode.type .*$', '_fitting_mode.type ' + mode, file.read_text())
    )
    return destination


def rows(experiment):
    if experiment.background_type == 'line-segment':
        return [
            (r.id, r.position, r.intensity.value, r.intensity.free) for r in experiment.background
        ]
    return [(r.id, r.order, r.coef.value, r.coef.free) for r in experiment.background_terms]


def state(experiment):
    return (
        experiment.background_type,
        experiment.background_origin,
        experiment.background_x_min,
        experiment.background_x_max,
        experiment.background_estimate.mode,
        rows(experiment),
    )


def options(experiment):
    s = experiment.background_estimate
    return {
        name: getattr(s, name)
        for name in [
            'method',
            'width',
            'smoothness',
            'n_points',
            'tolerance',
            'in_peaks',
            'max_terms',
            'use_model',
        ]
    }


def basis(experiment, change):
    if change == 'origin':
        experiment.background_origin = 105.25
    elif change == 'x_min':
        experiment.background_x_min = 3.375
    else:
        experiment.background_x_max = 160.625


def estimate_control(project):
    e = project.experiment
    e.background_estimate.mode = 'manual'
    e.background.auto_estimate(**options(e))
    return rows(e)


def persisted_settings(directory, name='d20'):
    result = {}
    for line in (Path(directory) / 'experiments' / (name + '.edi')).read_text().splitlines():
        if line.startswith('_background_estimate.'):
            key, value = line.split(maxsplit=1)
            result[key] = value
    return result


def calculated(directory):
    result = {'_data': [], '_data_calc': []}
    tags = []
    for line in (Path(directory) / 'experiments/d20.edi').read_text().splitlines():
        words = shlex.split(line, comments=True)
        if words == ['loop_']:
            tags = []
        elif len(words) == 1 and words[0].startswith('_'):
            tags.append(words[0])
        elif words and len(words) == len(tags):
            for prefix, samples in result.items():
                if prefix + '.intensity_calc' in tags:
                    samples.append(float(words[tags.index(prefix + '.intensity_calc')]))
    return result['_data_calc'] or result['_data']
