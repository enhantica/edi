"""Project-file inputs and readers for saved background-estimation settings."""

import argparse
import json
import shlex
from pathlib import Path

import numpy as np

from tests.fixtures.background_estimate.project import materialize

HERE = Path(__file__).resolve().parent
FIELDS = (
    'mode',
    'method',
    'width',
    'smoothness',
    'n_points',
    'max_terms',
    'tolerance',
    'in_peaks',
    'use_model',
)
REFERENCE = json.loads((HERE / 'reference.json').read_text())
# Explicit diffraction-lib reference profile; these are fixture settings, not product defaults.
DEFAULTS = {
    'mode': 'auto',
    'method': 'snip',
    'width': None,
    'smoothness': None,
    'n_points': None,
    'max_terms': None,
    'tolerance': 2.0,
    'in_peaks': 'drop',
    'use_model': 'ignore',
}


def write_settings(project, values, *, experiment='bank'):
    path = Path(project) / 'experiments' / f'{experiment}.edi'
    text = path.read_text()
    text = ''.join(
        line
        for line in text.splitlines(keepends=True)
        if not line.startswith('_background_estimate.')
    )
    lines = []
    for name in FIELDS:
        if name in {'tolerance', 'in_peaks', 'max_terms'} and name not in values:
            continue
        value = values[name]
        token = (
            '.' if value is None else str(value).lower() if isinstance(value, bool) else str(value)
        )
        lines.append(f'_background_estimate.{name} {token}\n')
    path.write_text(text.rstrip() + '\n\n' + ''.join(lines))


def read_settings(project, *, experiment='bank'):
    text = (Path(project) / 'experiments' / f'{experiment}.edi').read_text()
    raw = {}
    for line in text.splitlines():
        if line.startswith('_background_estimate.'):
            words = shlex.split(line, comments=True)
            if len(words) == 2:
                raw[words[0].split('.', 1)[1]] = words[1]
    result = {}
    for name in FIELDS:
        value = raw.get(name)
        if value in {None, '.', '?'}:
            result[name] = None
        elif name in {'width', 'smoothness', 'tolerance'}:
            result[name] = float(value)
        elif name in {'n_points', 'max_terms'}:
            result[name] = int(value)
        elif name == 'use_model':
            legacy = {
                'true': 'subtract',
                'yes': 'subtract',
                '1': 'subtract',
                'false': 'ignore',
                'no': 'ignore',
                '0': 'ignore',
            }
            token = legacy.get(value.lower(), value.lower())
            if token not in {'auto', 'subtract', 'ignore'}:
                message = 'Saved use_model must be auto, subtract or ignore (or a legacy Boolean)'
                raise ValueError(message)
            result[name] = token
        else:
            result[name] = value
    return result


def configured_project(destination, values=None):
    destination = materialize(destination, REFERENCE['cases']['hrpt'])
    write_settings(destination, DEFAULTS if values is None else values)
    return destination


def points(project):
    return [
        (float(point.position), point.intensity.value, point.intensity.free)
        for point in project.experiment.background
    ]


def saved_points(project, *, experiment='bank'):
    lines = (Path(project) / 'experiments' / f'{experiment}.edi').read_text().splitlines()
    rows = []
    tags = []
    in_loop = False
    for line in lines:
        words = shlex.split(line, comments=True)
        if words == ['loop_']:
            tags, in_loop = [], True
        elif in_loop and words and words[0].startswith('_'):
            if len(words) == 1:
                tags.append(words[0])
            else:
                in_loop = False
        elif in_loop and words:
            if len(words) != len(tags):
                message = 'Saved project loop rows must retain their declared column count'
                raise ValueError(message)
            if '_background.position' in tags:
                row = dict(zip(tags, words, strict=True))
                rows.append((
                    float(row['_background.position']),
                    float(row['_background.intensity']),
                ))
    return rows


def require_reference(actual, method, *, variant='default'):
    expected = REFERENCE['cases']['hrpt']['methods'][method][variant]['anchors']
    actual = np.asarray(actual, dtype=float)
    expected = np.asarray(expected, dtype=float)
    if actual.shape != expected.shape:
        message = 'Automatic mode must retain the independent anchor count'
        raise AssertionError(message)
    np.testing.assert_allclose(
        actual[:, 0],
        expected[:, 0],
        rtol=0,
        atol=1e-9,
        err_msg='Automatic mode must select the independent reference samples',
    )
    np.testing.assert_allclose(
        actual[:, 1],
        expected[:, 1],
        rtol=1e-10 if method == 'snip' else 1e-6,
        atol=1e-12 if method == 'snip' else 1e-9,
        err_msg='Automatic mode must meet the unchanged independent method tolerance',
    )


def app_cases():
    override = dict(REFERENCE['cases']['hrpt']['methods']['arpls']['override']['options'])
    # Reference metadata preserves diffraction-lib's Boolean input; saved projects
    # use the canonical three-way category without changing that independent oracle.
    if isinstance(override.get('use_model'), bool):
        override['use_model'] = 'subtract' if override['use_model'] else 'ignore'
    return {
        'auto-derived': {'settings': DEFAULTS, 'method': 'snip', 'variant': 'default'},
        'auto-overrides': {
            'settings': {**DEFAULTS, **override, 'method': 'arpls'},
            'method': 'arpls',
            'variant': 'override',
        },
    }


def generate_app_projects():
    cases = app_cases()
    for name, case in cases.items():
        configured_project(HERE / 'projects' / name, case['settings'])
    (HERE / 'settings-cases.json').write_text(json.dumps(cases, indent=2) + '\n')


def freeze_cli_before():
    root = HERE.parents[2]
    source = root / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2'
    for name, relative in (
        ('cli-before.edi', 'project/experiments/hrpt.edi'),
        ('cli-expected-before.json', 'expected.json'),
    ):
        target = HERE / name
        if target.exists():
            message = 'The pre-extension CLI regression witness must not be overwritten'
            raise FileExistsError(message)
        target.write_bytes((source / relative).read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-cli', action='store_true')
    args = parser.parse_args()
    generate_app_projects()
    if args.freeze_cli:
        freeze_cli_before()
