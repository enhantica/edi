"""Disposable lifecycle inputs and observations; no new numerical oracle."""

import csv
import importlib
import json
import re
import shlex
import shutil
import sys
from pathlib import Path

import numpy as np

from tests.fixtures.background_estimate.settings import (
    DEFAULTS,
    points,
    write_settings,
)

OPTIONS = {
    **DEFAULTS,
    'mode': 'manual',
    'method': 'snip',
    'width': 7.25,
    'n_points': 9,
    'use_model': True,
}
INVALID = [
    ('width', 'nan'),
    ('width', 'inf'),
    ('width', '-inf'),
    ('width', '8589934592.25'),
    ('smoothness', 'nan'),
    ('smoothness', 'inf'),
    ('smoothness', '-inf'),
]


def model_input(destination, source, *, mode='manual'):
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('README.md'))
    metadata = destination / 'project.edi'
    metadata.write_text(
        re.sub(r'(?m)^_metadata.purpose .*$', '_metadata.purpose "fitting"', metadata.read_text())
    )
    write_settings(destination, {**OPTIONS, 'mode': mode}, experiment='hrpt')
    return destination


def prime(engine, destination, source):
    project = engine.Project.load(model_input(destination, source))
    for point in project.experiment.background:
        point.intensity.value = 0
        point.intensity.free = False
    project.analysis.calculate()
    data = project.experiment.data
    if not np.any(np.abs(np.asarray(data.intensity_calc) - np.asarray(data.intensity_bkg)) > 1e-8):
        message = 'The lifecycle input must calculate nonzero crystal-model peaks'
        raise ValueError(message)
    settings = project.experiment.background_estimate
    settings.mode = 'auto'
    return project


def expected_background(project):
    anchors = points(project)
    axis = np.asarray(project.experiment.data.two_theta)
    return np.interp(axis, [row[0] for row in anchors], [row[1] for row in anchors])


def edit(project, engine, kind):
    background = project.experiment.background
    if kind == 'position':
        background[0].position += 0.0625
    elif kind == 'intensity':
        background[0].intensity.value += 0.125
    elif kind == 'free':
        background[0].intensity.free = not background[0].intensity.free
    elif kind == 'add':
        new = engine.LineSegment()
        new.position = 37.25
        new.intensity.value = 42.125
        project.experiment.background = [*background, new]
    elif kind == 'remove':
        project.experiment.background = list(background)[1:]
    else:
        message = 'Unknown authored background edit'
        raise ValueError(message)


def persisted_points(directory, *, experiment='hrpt'):
    tags, result, active = [], [], False
    path = Path(directory) / 'experiments' / (experiment + '.edi')
    for line in path.read_text().splitlines():
        cells = shlex.split(line, comments=True)
        if cells == ['loop_']:
            tags, active = [], True
        elif active and cells and cells[0].startswith('_'):
            if len(cells) == 1:
                tags.append(cells[0])
            else:
                active = False
        elif active and cells and '_background.position' in tags:
            if len(tags) != len(cells):
                message = 'Persisted background rows must retain their complete columns'
                raise ValueError(message)
            row = dict(zip(tags, cells, strict=True))
            result.append(
                tuple(
                    float(re.sub(r'\([^)]*\)', '', row[field]))
                    for field in ['_background.position', '_background.intensity']
                )
            )
    return result


def stored_values(project):
    settings = project.experiment.background_estimate
    return {name: getattr(settings, name) for name in DEFAULTS}


def scan_input(destination, source, engine, mode):
    seed = destination.with_name(destination.name + '-seed')
    model_input(seed, source)
    experiment = seed / 'experiments/hrpt.edi'
    text = re.sub(r'(?<=\d)\([^()]*\)', '', experiment.read_text())
    text = re.sub(r'(_linked_structure.scale\n)(\S+)\s+\S+', r'\1\2 0.75()', text)
    experiment.write_text(text)
    write_settings(
        seed,
        {**OPTIONS, 'mode': 'auto', 'width': 3.25, 'n_points': None, 'use_model': False},
        experiment='hrpt',
    )
    project = engine.Project.load(seed)
    project.analysis.calculate()
    data = project.experiment.data
    axis = np.asarray(data.two_theta).copy()
    peaks = np.asarray(data.intensity_calc) - np.asarray(data.intensity_bkg)
    project.save_as(destination)
    scan = destination / 'experiments/scan'
    scan.mkdir()
    counts = []
    for index in range(3):
        baseline = 37.125 + 0.025 * axis
        baseline += 0.0375 * (axis - 83.25) ** 2 if index == 1 else index * 11.25
        y = baseline + peaks * (2.5 / 0.75)
        np.savetxt(scan / (str(index) + '.xy'), np.column_stack([axis, y, np.ones(len(axis))]))
        control = engine.Project.load(seed)
        control.experiment.data = engine.PdCwlData(
            two_theta=axis, intensity_meas=y, intensity_meas_su=np.ones(len(axis))
        )
        control.experiment.background.auto_estimate(method='snip', width=3.25, use_model=False)
        counts.append(len(control.experiment.background))
    analysis = destination / 'analysis/analysis.edi'
    text = re.sub(
        r'(?m)^_fitting_mode.type .*$', '_fitting_mode.type ' + mode, analysis.read_text()
    )
    text = re.sub(r'(?m)^_minimizer.max_iterations .*$', '_minimizer.max_iterations 4', text)
    analysis.write_text(
        text + '\n_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.xy\n'
    )
    shutil.rmtree(seed)
    return counts


def scan_probe(package, source, fail_first):
    engine = importlib.import_module(package)
    project = engine.Project.load(source)
    project.analysis.calculate()
    original = points(project)
    held = list(project.experiment.background)
    calls = []
    mode = re.search(
        r'(?m)^_fitting_mode.type (\w+)', (source / 'analysis/analysis.edi').read_text()
    )[1]
    fitter = project.fit if package == 'crysta' else getattr(project, 'fit_' + mode)
    callbacks = {'on_scan_start': lambda _record: None} if package == 'edi' else {}
    injected = False

    def iteration(_record):
        nonlocal injected
        if fail_first and not injected:
            injected = True
            message = 'Authored failed predecessor after a solver step'
            raise RuntimeError(message)

    def run():
        fitter(on_iteration=iteration, on_file_complete=calls.append, **callbacks)
        csv_path = source / 'analysis/results.csv'
        initial = csv_path.read_bytes()
        with csv_path.open() as stream:
            rows = list(csv.DictReader(stream))
        result = {
            'files': [row['file_path'] for row in rows],
            'original': original,
            'points': points(project),
            'mode': project.experiment.background_estimate.mode,
            'identity': all(
                a is b for a, b in zip(held, project.experiment.background, strict=False)
            ),
            'injected': injected,
            'first_failed': rows[0]['fit_result.success'] == 'False',
        }
        fitter(on_file_complete=calls.append, **callbacks)
        result['resume_unchanged'] = csv_path.read_bytes() == initial
        result['completed_before_restart'] = len(calls)
        csv_path.write_bytes(b''.join(initial.splitlines(keepends=True)[:-1]))
        fitter(on_file_complete=calls.append, **callbacks)
        result['completed_after_restart'] = len(calls)
        return result

    try:
        result = run()
    except (ValueError, RuntimeError) as error:
        return {'error': str(error), 'injected': injected, 'completed': len(calls)}

    return result


def invalid_probe(package, source, route, field, token, method='snip'):
    engine = importlib.import_module(package)
    if route == 'load':
        path = source / 'experiments/hrpt.edi'
        text = path.read_text()

        path.write_text(
            re.sub(
                r'(?m)^_background_estimate\.' + field + r' .*$',
                '_background_estimate.' + field + ' ' + token,
                text,
            )
        )
        before = path.read_bytes()
        try:
            engine.Project.load(source)
        except (ValueError, OverflowError, TypeError) as error:
            return {
                'refused': True,
                'unchanged': path.read_bytes() == before,
                'diagnostic': str(error),
            }
        return {'refused': False, 'unchanged': path.read_bytes() == before}
    project = engine.Project.load(source)
    before = points(project), stored_values(project)
    try:
        if route == 'direct':
            project.experiment.background.auto_estimate(method=method, **{field: float(token)})
        else:
            setattr(project.experiment.background_estimate, field, float(token))
    except (ValueError, OverflowError, TypeError) as error:
        return {
            'refused': True,
            'unchanged': before == (points(project), stored_values(project)),
            'diagnostic': str(error),
        }
    after = points(project), stored_values(project)
    return {'refused': False, 'unchanged': before == after}


if __name__ == '__main__':
    result = (
        scan_probe(sys.argv[1], Path(sys.argv[2]), sys.argv[4] == 'true')
        if sys.argv[3] == 'scan'
        else invalid_probe(sys.argv[1], Path(sys.argv[2]), *sys.argv[3:])
    )
    print(json.dumps(result))
