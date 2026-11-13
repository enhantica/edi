"""Bind historical inputs and the existing current native backend-parity domain."""

import hashlib
import json
import math
from pathlib import Path

from tests.fixtures.e04_t11_wasm.compare import compare
from tests.fixtures.metadata_transition import task_inputs

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
PATHS = {
    'historical_oracle': 'tests/fixtures/e04_t11_wasm/native.json',
    'historical_report': 'tests/fixtures/e04_t11_wasm/native-report.txt',
    'current_oracle': 'tests/fixtures/web_parallel/lbco-native.json',
    'current_report': 'tests/fixtures/web_parallel/lbco-native-report.txt',
    'transition_manifest': 'tests/fixtures/metadata_transition/task-inputs.json',
    'transition_archive': 'tests/fixtures/metadata_transition/task-inputs.zip',
}
PROJECT = 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project'
CONDITIONS = {'descent': 'ladder', 'stop_rules': 'chi_square_change', 'max_iterations': 1000}
ANALYSIS = 'analysis/analysis.edi'
SUFFIX = b'\n_minimizer.descent ladder\n_minimizer.stop_rules chi_square_change\n'


def fields(report):
    rows = [line.split('=', 1) for line in report.splitlines() if '=' in line]
    if len(rows) != len({key for key, _ in rows}):
        raise ValueError('A native condition report cannot contain duplicated fields')
    return dict(rows)


def domain(declaration=None):
    declared = (
        json.loads((HERE / 'cli-domains.json').read_text()) if declaration is None else declaration
    )
    if (
        declared.get('schema') != 'standalone-wasm-cli-domains/1'
        or declared.get('inputs') != PROJECT
        or declared.get('conditions') != CONDITIONS
        or set(declared.get('files', {})) != set(PATHS)
    ):
        raise ValueError('The backend vehicle requires its declared input and condition domain')
    for name, path in PATHS.items():
        row = declared['files'][name]
        if (
            row.get('path') != path
            or row.get('sha256') != hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        ):
            raise ValueError('The standalone vehicle cannot substitute a different native anchor')
    historical = json.loads((ROOT / PATHS['historical_oracle']).read_text())
    current = json.loads((ROOT / PATHS['current_oracle']).read_text())
    report = fields((ROOT / PATHS['current_report']).read_text())
    if (
        historical['project'] != PROJECT
        or current['project'] != PROJECT
        or report.get('descent') != CONDITIONS['descent']
        or (current['relative_tolerance'], current['absolute_tolerance'])
        != (historical['relative_tolerance'], historical['absolute_tolerance'])
    ):
        raise ValueError('The selected native anchor must retain the identical project and bounds')
    parameters = {
        key: float(value)
        for key, value in report.items()
        if key.startswith('param.') and key.endswith('.value')
    }
    if parameters.keys() != historical['parameters'].keys() or not all(
        math.isfinite(value) for value in parameters.values()
    ):
        raise ValueError('The current native anchor must retain every original fitted operand')
    return {
        'historical': historical,
        'oracle': {
            'status': report['status'],
            'converged': report['converged'],
            'parameters': parameters,
            'reduced_chi_square': float(report['reduced_chi_square']),
            'relative_tolerance': current['relative_tolerance'],
            'absolute_tolerance': current['absolute_tolerance'],
        },
    }


def input_bytes(root=ROOT):
    project = Path(root) / PROJECT
    return {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in sorted(project.rglob('*'))
        if path.is_file()
    }


def historical_bytes(actual, selected):
    if ANALYSIS not in actual:
        raise ValueError('The standalone vehicle must retain its minimizer declaration')
    before = dict(actual)
    row = task_inputs.rows()[PROJECT + '/' + ANALYSIS]
    if hashlib.sha256(actual[ANALYSIS]).hexdigest() != row['before_sha256']:
        raise ValueError('The declared current minimizer input changed')
    before[ANALYSIS] = task_inputs.archived(row['after_sha256'])
    digest = hashlib.sha256()
    for name, data in sorted(before.items()):
        digest.update(name.encode() + b'\0')
        digest.update(data)
    if digest.hexdigest() != selected['historical']['project_sha256']:
        raise ValueError('Only the exact archived stop-rule transition changes historical inputs')
    records = dict(
        line.split(maxsplit=1)
        for line in actual[ANALYSIS].decode().splitlines()
        if line.startswith('_')
    )
    if records.get('_minimizer.max_iterations') != str(CONDITIONS['max_iterations']):
        raise ValueError('The backend vehicle preserves its declared iteration bound')
    return before


def vehicle(destination):
    selected = domain()
    actual = input_bytes()
    historical_bytes(actual, selected)
    destination = Path(destination)
    destination.mkdir()
    for name, data in actual.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data + SUFFIX if name == ANALYSIS else data)
    verify_vehicle(destination, actual)
    return selected['oracle']


def verify_vehicle(destination, original):
    actual = {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in Path(destination).rglob('*')
        if path.is_file()
    }
    expected = dict(original)
    expected[ANALYSIS] += SUFFIX
    if actual != expected:
        raise ValueError('Only declared ladder and chi-square conditions enter the vehicle')


def compare_current(report, oracle):
    actual = fields(report)
    if (
        actual.get('descent') != CONDITIONS['descent']
        or actual.get('stopping_rule') != CONDITIONS['stop_rules']
    ):
        raise ValueError('The actual backend report must confirm its declared solver conditions')
    iterations = actual.get('iterations', '')
    if (
        not iterations.isascii()
        or not iterations.isdecimal()
        or not (0 < int(iterations) <= CONDITIONS['max_iterations'])
    ):
        raise ValueError('The actual backend report respects its declared iteration bound')
    compare(report, oracle)
