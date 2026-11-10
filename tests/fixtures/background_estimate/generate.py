"""Generate frozen references with diffraction-lib in an external environment."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import logging
import platform
import sys
import types
from pathlib import Path
from typing import NamedTuple
from urllib.request import urlopen

import numpy as np
import pybaselines
import scipy
from scipy.signal import find_peaks, peak_widths

COMMIT = 'c0654956a1281f1ea3f3467c3367167f93edee18'
REPRODUCTION_COMMAND = (
    '../background-reference/venv/bin/python tests/fixtures/background_estimate/generate.py '
    '--source ../background-reference/diffraction-lib --output ../background-reference/generated'
)
BACKGROUND = Path('src/easydiffraction/datablocks/experiment/categories/background')
CORPUS = Path('tests/integration/workflows/test_background_auto_estimate_corpus.py')
METHODS = ('arpls', 'snip', 'fabc')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def adapter(source, estimator):
    """Execute the upstream adapter method and helpers without its model imports."""
    path = source / BACKGROUND / 'line_segment.py'
    tree = ast.parse(path.read_text())
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        or (isinstance(node, ast.ClassDef) and node.name == '_EstimationArrays')
    ]
    owner = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'LineSegmentBackground'
    )
    nodes.append(next(node for node in owner.body if getattr(node, 'name', '') == 'auto_estimate'))
    namespace = {
        'np': np,
        'NamedTuple': NamedTuple,
        'find_peaks': find_peaks,
        'peak_widths': peak_widths,
        '_MIN_ANCHOR_POINTS': 2,
        'estimate': estimator,
        'enums': load_module(source / BACKGROUND / 'enums.py', '_reference_enums'),
        'log': logging.getLogger('reference'),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)  # noqa: S102 - pinned upstream functions
    return namespace['auto_estimate']


class Background:
    """Only the array and point storage that the unchanged upstream method consumes."""

    def __init__(self, values, excluded):
        x, y, _ = values.T
        included = np.ones(x.size, dtype=bool)
        for start, end in excluded:
            included &= ~((x >= start) & (x <= end))
        data = types.SimpleNamespace(
            x=x,
            unfiltered_x=x,
            intensity_meas=y,
            intensity_calc=np.zeros(x.size),
            intensity_bkg=np.zeros(x.size),
            calc_status=np.where(included, 'incl', 'excl'),
        )
        self._parent = types.SimpleNamespace(data=data)
        self._items = []

    def __len__(self):
        return len(self._items)

    def clear(self):
        self._items.clear()

    def create(self, *, id, position, intensity):
        self._items.append(
            types.SimpleNamespace(
                id=id,
                position=types.SimpleNamespace(value=position),
                intensity=types.SimpleNamespace(value=intensity, free=True),
            )
        )


def cases(source):
    tree = ast.parse((source / CORPUS).read_text())
    for function in tree.body:
        if isinstance(function, ast.FunctionDef) and function.name.startswith('test_'):
            call = function.body[0].value
            if (
                isinstance(call, ast.Call)
                and getattr(call.func, 'id', '') == '_assert_tracks_reference'
            ):
                yield tuple(ast.literal_eval(arg) for arg in call.args)


def retrieve(url, destination, expected=None):
    with urlopen(url, timeout=30) as response:  # noqa: S310 - fixed HTTPS corpus origin
        content = response.read()
    if expected and hashlib.sha256(content).hexdigest() != expected:
        message = f'Corpus checksum differs from the pinned index: {url}'
        raise ValueError(message)
    destination.write_bytes(content)


def generate(source, output):  # noqa: PLR0914 - retain the upstream metadata together
    output.mkdir(parents=True, exist_ok=True)
    log_module = types.ModuleType('easydiffraction.utils.logging')
    log_module.log = logging.getLogger('reference')
    sys.modules[log_module.__name__] = log_module
    estimator = load_module(source / BACKGROUND / 'estimate.py', '_reference_estimate')
    apply = adapter(source, estimator)
    estimate = estimator.estimate_background_curve
    observed = []

    def record(*args, **kwargs):
        result = estimate(*args, **kwargs)
        observed.append(result)
        return result

    estimator.estimate_background_curve = record
    ref = (source / 'src/easydiffraction/_data_index_ref.txt').read_text().strip()
    base = f'https://raw.githubusercontent.com/easyscience/diffraction/{ref}/data/'
    retrieve(base + 'index.json', output / 'data-index.json')
    index = json.loads((output / 'data-index.json').read_text())
    references = {
        'diffraction_lib_repository': 'https://github.com/easyscience/diffraction-lib',
        'diffraction_lib_commit': COMMIT,
        'data_commit': ref,
        'versions': {
            'python': platform.python_version(),
            'numpy': np.__version__,
            'scipy': scipy.__version__,
            'pybaselines': pybaselines.__version__,
        },
        'source_sha256': {
            str(path): digest(source / path)
            for path in (BACKGROUND / 'estimate.py', BACKGROUND / 'line_segment.py', CORPUS)
        },
        'command': REPRODUCTION_COMMAND,
        'cases': {},
    }
    for name, data_id, beam_mode, probe, excluded, _ in cases(source):
        entry = index[data_id]
        path = output / (data_id + '.xye')
        retrieve(base + entry['path'], path, entry['hash'].removeprefix('sha256:'))
        values = np.loadtxt(path)
        storage = Background(values, excluded)
        active = storage._parent.data.calc_status == 'incl'
        x, y, _ = values[active].T
        noise = estimator._robust_noise(y)
        width, peaks = estimator._measure_width(y, noise)
        half = int(np.ceil(width))
        row = {
            'data_id': data_id,
            'input_file': path.name,
            'input_sha256': digest(path),
            'beam_mode': beam_mode,
            'probe': probe,
            'excluded': excluded,
            'active_count': int(x.size),
            'active_endpoints': [float(x[0]), float(x[-1])],
            'active_sha256': hashlib.sha256(values[active].astype('<f8').tobytes()).hexdigest(),
            'peak_indices': peaks.tolist(),
            'peak_windows': [
                [float(x[max(0, int(p) - half)]), float(x[min(x.size - 1, int(p) + half)])]
                for p in peaks
            ],
            'derived_width': width,
            'derived_noise': noise,
            'derived_smoothing': estimator._derive_lam(x.size, width),
            'methods': {},
        }
        for method in METHODS:
            variants = {
                'default': {'method': method, 'use_model': False},
                'override': {
                    'method': method,
                    'width': width * 1.7,
                    'smoothness': row['derived_smoothing'] * 3.25,
                    'n_points': 7,
                    'use_model': False,
                },
            }
            row['methods'][method] = {}
            for variant, options in variants.items():
                apply(storage, **options)
                result = observed[-1]
                row['methods'][method][variant] = {
                    'options': options,
                    'anchors': [[p.position.value, p.intensity.value] for p in storage._items],
                    'raw_anchors': result.anchors.tolist(),
                    'width': result.width,
                    'noise': result.noise,
                    'tolerance': result.tolerance,
                    'backend_params': result.backend_params,
                }
        references['cases'][name] = row
    (output / 'reference.json').write_text(
        json.dumps(references, indent=2, allow_nan=False) + '\n'
    )
    for name, row in references['cases'].items():
        print(name, row['active_count'], row['derived_width'], row['derived_noise'])
        for method in METHODS:
            print(method, len(row['methods'][method]['default']['anchors']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generate(args.source.resolve(), args.output.resolve())
