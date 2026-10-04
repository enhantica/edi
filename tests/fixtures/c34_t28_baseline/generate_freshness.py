"""Capture Python freshness regression pins from the named pre-move build.

Only calculated-unit presence and held-window currentness are observed. No
calculated number from this vehicle is an independent physical expectation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import shutil
import tempfile
from pathlib import Path

from .generate_bytes import BASE, PACKAGE, corpus_root, hashes, require_baseline_closure

HERE = Path(__file__).resolve().parent
ROUTES = (
    'cell-equal',
    'cell-changed',
    'uncertainty-zero',
    'free-flag',
    'fit-start',
    'site-equal',
    'site-id-equal',
    'site-id-changed',
    'background',
    'scale-equal',
    'offset',
    'measured-equal',
    'sigma-equal',
    'exclusions-equal',
    'geom-equal',
    'geom-changed',
    'scattering-equal',
    'whole-structure',
    'whole-data',
    'fit',
    'sequential',
)

if PACKAGE == 'edi':
    ROUTES += ('undo',)


def input_hashes(directory):
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob('*'))
        if p.is_file()
    }


def prepared(package, directory, route, root):
    source = HERE / 'freshness-input'
    if route in {'fit', 'undo'}:
        source = corpus_root(root) / 'cosio-d20-s1/project'
    if route == 'sequential':
        source = corpus_root(root) / 'cosio-d20-scan-3f/project'
    target = directory / 'input'
    shutil.copytree(source, target)
    project = package.Project.load(target)
    if route in {'fit', 'undo'}:
        for parameter in project.parameters:
            parameter.free = False
        project.experiment.linked_structure.scale.free = True
    if route == 'undo':
        project.analysis.fit()
    # Capture each unit in the public API before the write. A read after the
    # write could recalculate and conceal stale state, so observations use save.
    project.analysis.calculate()
    _ = project.structure.expanded_atom_sites
    window = project.structure.geometry()
    return project, window


def mutate(project, route):  # noqa: PLR0912 — explicit public write-route census
    parameter = project.structure.cell.length_a
    experiment = project.experiment
    site = project.structure.atom_sites[0]
    if route == 'cell-equal':
        parameter.value = parameter.value
    elif route == 'cell-changed':
        parameter.value += 0.125
    elif route == 'uncertainty-zero':
        parameter.uncertainty = 0.0
    elif route == 'free-flag':
        parameter.free = not parameter.free
    elif route == 'fit-start':
        parameter.start_value, parameter.start_uncertainty = 3.75, 0.0
    elif route == 'site-equal':
        site.occupancy.value = site.occupancy.value
    elif route == 'site-id-equal':
        site.id = site.id
    elif route == 'site-id-changed':
        site.id = 'renamed'
    elif route == 'background':
        experiment.background[0].intensity.value += 0.125
    elif route == 'scale-equal':
        experiment.linked_structure.scale.value = experiment.linked_structure.scale.value
    elif route == 'offset':
        experiment.instrument.calib_twotheta_offset.value += 0.125
    elif route == 'measured-equal':
        experiment.data.intensity_meas = list(experiment.data.intensity_meas)
    elif route == 'sigma-equal':
        experiment.data.intensity_meas_su = list(experiment.data.intensity_meas_su)
    elif route == 'exclusions-equal':
        experiment.excluded_regions = experiment.excluded_regions
    elif route == 'geom-equal':
        project.structure.geom.bond_distance_inc = project.structure.geom.bond_distance_inc
    elif route == 'geom-changed':
        project.structure.geom.bond_distance_inc = 0.3125
    elif route == 'scattering-equal':
        project.structure.scattering_lengths_fm = project.structure.scattering_lengths_fm
    elif route == 'whole-structure':
        project.structure = project.structure
    elif route == 'whole-data':
        experiment.data = experiment.data
    elif route in {'fit', 'sequential'}:
        project.analysis.fit()
    elif route == 'undo':
        project._undo_fit()
    else:
        raise ValueError('unrepresented freshness route: ' + route)


def state(project, window, destination):
    current = bool(window.is_current())
    project.save_as(destination)
    structure = next((destination / 'structures').glob('*.edi')).read_text()
    experiment = next((destination / 'experiments').glob('*.edi')).read_text()
    return {
        'held_window_current': current,
        'geometry_saved': '_expanded_atom_site.id' in structure,
        'pattern_saved': '_data.intensity_calc' in experiment,
        'reflections_saved': '_refln.id' in experiment,
    }


def observe(route, directory, root):
    package = importlib.import_module(PACKAGE)
    directory.mkdir(parents=True)
    project, window = prepared(package, directory, route, root)
    before = state(project, window, directory / 'before')
    refused = None
    try:
        mutate(project, route)
    except AttributeError as error:
        if PACKAGE != 'crysta' or route not in {'measured-equal', 'sigma-equal'}:
            raise
        refused = type(error).__name__  # crysta exposes immutable Python measured reads
    return {
        'before': before,
        'after': state(project, window, directory / 'after'),
        'refused': refused,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true', required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    git = shutil.which('git')
    if not git:
        parser.error('Git is required to prove the baseline source')
    require_baseline_closure(root)
    package = importlib.import_module(PACKAGE)
    if not Path(package.__file__).resolve().is_relative_to(root):
        parser.error('the imported pre-move package must resolve inside its source checkout')
    result = {
        'kind': 'pre-move Python freshness regression pin',
        'source_commit': BASE,
        'input_sha256': hashes(HERE / 'freshness-input'),
        'fit_sha256': input_hashes(corpus_root(root) / 'cosio-d20-s1/project'),
        'scan_sha256': input_hashes(corpus_root(root) / 'cosio-d20-scan-3f/project'),
        'routes': {},
    }
    with tempfile.TemporaryDirectory() as temporary:
        for route in ROUTES:
            result['routes'][route] = observe(route, Path(temporary) / route, root)
            print('captured', route, flush=True)
    (HERE / 'freshness.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
