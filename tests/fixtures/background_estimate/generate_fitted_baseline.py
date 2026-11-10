"""Generate disposable-fit regression inputs and a labelled Manual-fit comparison once."""

import argparse
import hashlib
import importlib
import json
import platform
import re
import shutil
from pathlib import Path

import numpy as np

from tests.fixtures.background_estimate.fitted_baseline import KINDS, fit, values
from tests.fixtures.background_estimate.readonly import snapshot
from tests.fixtures.background_estimate.settings import DEFAULTS, write_settings

HERE = Path(__file__).resolve().parent


def generate(module, source, engine_source_commit):
    engine = importlib.import_module(module)
    receipt = {
        'purpose': 'REGRESSION INPUT and Manual-fit REGRESSION PIN; no fit-correctness claim',
        'source_repository': 'https://github.com/enhantica/edi',
        'source_commit': '550e48422a66a060f9ef35997ad060a00187d973',
        'source_project': 'docs/user/cli/pd-neut-cwl_cosio-d20_start-4/project',
        'source_files': {
            str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source.rglob('*')
            if p.is_file()
            and p.relative_to(source).parts[0] in {'experiments', 'structures', 'analysis'}
        },
        'engine': 'Crysta C++ engine, Python surface ' + module,
        'python_version': platform.python_version(),
        'engine_provenance_limit': 'The compiled producer was sealed from a local build. '
        'Its embedded stamp does not establish complete source closure; '
        'the binary SHA-256 is the exact writer identity.',
        'engine_stamp': engine.__build_commit__,
        'engine_source_commit': engine_source_commit,
        'engine_binary_sha256': hashlib.sha256(Path(engine.__file__).read_bytes()).hexdigest(),
        'command': 'python -m tests.fixtures.background_estimate.generate_fitted_baseline '
        '--module crysta --source tests/fitting/cosio-d20-s4/project '
        '--engine-source-commit ' + engine_source_commit,
        'parameters': 'only background free; arpls, width=6, smoothness=1000, tolerance=2, '
        'in_peaks=move, use_model=auto, n_points=9, max_terms=3, fit iterations=3',
        'cases': {},
    }
    for kind in KINDS:
        destination = HERE / 'projects' / ('fitted-auto-' + kind)
        if destination.exists():
            message = 'Authoring inputs are generated once; destination already exists'
            raise ValueError(message)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns('README.md'))
        for path in destination.rglob('*.edi'):
            text = re.sub(r'(?<=[0-9.])\([^)]*\)', '', path.read_text())
            path.write_text(text)
        analysis = destination / 'analysis/analysis.edi'
        analysis.write_text(
            '_edi.schema_version 3\n_fitting_mode.type single\n'
            '_minimizer.type crysta\n_minimizer.max_iterations 3\n'
        )
        experiment = destination / 'experiments/d20.edi'
        text = experiment.read_text()
        if kind != 'line-segment':
            begin = text.index('_background.type')
            end = text.index('\nloop_\n_data.', begin)
            geometry = (
                '_background.origin 80\n'
                if kind == 'polynomial'
                else ('_background.x_min 8.0953\n_background.x_max 149.7953\n')
            )
            text = (
                text[:begin]
                + '_background.type '
                + kind
                + '\n'
                + geometry
                + (
                    'loop_\n_background.id\n_background.order\n_background.coef\n'
                    'floor 0 500\nramp 1 0\nbend 2 0\n'
                )
                + text[end:]
            )
            experiment.write_text(text)
        write_settings(
            destination,
            {
                **DEFAULTS,
                'mode': 'auto',
                'method': 'arpls',
                'width': 6,
                'smoothness': 1000,
                'n_points': 9,
                'max_terms': 3,
                'in_peaks': 'move',
                'use_model': 'auto',
            },
            experiment='d20',
        )
        project = engine.Project.load(destination)
        project.analysis.calculate()
        project.analysis.calculate()  # Settle the model-guided input before freezing its baseline.
        rows = (
            project.experiment.background
            if kind == 'line-segment'
            else project.experiment.background_terms
        )
        for row in rows:
            (row.intensity if kind == 'line-segment' else row.coef).free = True
        project.save_as(destination)
        if kind == 'line-segment':
            data = project.experiment.data
            np.savetxt(
                HERE / 'fitted-baseline-shifted.xye',
                np.column_stack((
                    data.two_theta,
                    np.asarray(data.intensity_meas) + 125,
                    data.intensity_meas_su,
                )),
                fmt='%.17g',
            )
        (destination / 'project.edi').write_text(
            '_edi.schema_version 3\n_metadata.name fitted-background-input\n'
            '_metadata.purpose fitting\n'
        )
        control = engine.Project.load(destination)
        control.experiment.background_estimate.mode = 'manual'
        initial = values(control).copy()
        fit(control)
        receipt['cases'][kind] = {
            'initial': snapshot(project),
            'manual_fitted_regression_pin': snapshot(control),
            'maximum_fit_change': float(max(abs(values(control) - initial))),
            'files': {
                str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in destination.rglob('*')
                if p.is_file()
            },
        }
    receipt['input_projection'] = (
        'The scientific source files match the public repository; '
        'project metadata is neutral authored scaffolding and README is omitted.'
    )
    receipt['shifted_data'] = {
        'file': 'fitted-baseline-shifted.xye',
        'construction': 'same measured grid and sigma, intensity +125 counts',
        'sha256': hashlib.sha256((HERE / 'fitted-baseline-shifted.xye').read_bytes()).hexdigest(),
    }
    (HERE / 'fitted-baseline.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', required=True)
    parser.add_argument('--engine-source-commit', required=True)
    parser.add_argument('--source', type=Path, required=True)
    arguments = parser.parse_args()
    generate(arguments.module, arguments.source, arguments.engine_source_commit)
