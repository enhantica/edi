"""M5/M7: every bank writer enforces the GPU-only app boundary.

Handwritten timings prove eligibility and retention, never measured product speed.
The run routes inject collected tables at the measurement seam; parsing, dispatch,
comparison, eligibility and filesystem writes remain production behavior.
"""

from __future__ import annotations

import copy
import io
import json
import runpy
from contextlib import redirect_stderr, redirect_stdout
from itertools import product
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
DECISION = 'owner 2026-10-03: accept CI-measured values, '
DEFECTS = (
    'llvmpipe',
    'softpipe',
    'swrast',
    'lavapipe',
    'swiftshader',
    'basic render',
    'absent-renderer',
    'inconsistent-renderer',
    'false',
    'absent-allowed',
    'zero',
    'one',
    'string',
)


def table(scenario, *, mixed=False):
    metric = 'frame' if scenario == 'A1' else 'update'
    rows = [{'dataset': 'T1', 'scenario': scenario, metric: {'median_ms': 16.0, 'p95_ms': 32.0}}]
    if mixed:
        rows.insert(
            0,
            {
                'dataset': 'D1',
                'scenario': 'S1',
                'latency': {'median_ms': 14.0},
                'overhead': {'median_ms': 3.0},
            },
        )
    return {
        'schema': 1,
        'machine': 'bank-test',
        'commit': 'a' * 40,
        'samples': 50,
        'warmups': 5,
        'renderer': 'Metal',
        'bank_allowed': True,
        'rows': rows,
    }


def bank():
    rows = []
    for dataset, scenario, metrics in (
        ('D1', 'S1', ('latency', 'overhead')),
        ('D1', 'S2', ('latency', 'overhead')),
        ('D1', 'S3', ('presentation',)),
        ('T1', 'V1', ('presentation',)),
        ('T1', 'A1', ('frame',)),
        ('T1', 'A2', ('update',)),
    ):
        row = {
            'dataset': dataset,
            'scenario': scenario,
            'commit': 'b' * 40,
            'run': 'original/1',
            'metrics': {
                metric: {'banked_ms': 1.0, 'margin_ms': 2.5, 'values_ms': [0.5, 1.0, 1.5]}
                for metric in metrics
            },
        }
        if scenario.startswith('A'):
            row['renderer'] = 'Metal'
        rows.append(row)
    return {
        'schema': 1,
        'machines': {'bank-test': {'rows': rows}, 'unrelated': {'rows': copy.deepcopy(rows)}},
    }


def destinations(directory, destination):
    bank_path = directory / 'bank.json'
    bank_path.write_text(json.dumps(bank()) + '\n', encoding='utf-8')
    output = None if destination == 'in-place' else directory / 'output.json'
    if destination == 'existing-out':
        output.write_text('existing output must survive refusal\n', encoding='utf-8')
    return bank_path, output


def invoke(writer, directory, route, tables, bank_path, output):
    measurements = directory / 'measurements'
    measurements.mkdir()
    paths = []
    for number, measured in enumerate(tables):
        path = measurements / f'run-{number:02}.json'
        path.write_text(json.dumps(measured), encoding='utf-8')
        paths.append(path)
    args = ['--bank', str(bank_path), '--decision', DECISION]
    if output is not None:
        args += ['--out', str(output)]
    if route == 'accept':
        args += ['--accept', *map(str, paths)]
    elif route == 'measurements':
        args += ['--measurements', str(measurements)]
    else:

        def measure(target, _revision):
            target.mkdir(parents=True, exist_ok=True)
            for number, measured in enumerate(tables):
                (target / f'run-{number:02}.json').write_text(
                    json.dumps(measured), encoding='utf-8'
                )
            return []

        globals_ = writer.main.__globals__
        writer.patch.setitem(globals_, 'measured_revision', lambda _bank: 'a' * 40)
        writer.patch.setitem(globals_, 'measure' if route == 'run' else 'measure_app', measure)
        args += ['--run' if route == 'run' else '--run-app']
    return writer.main(args)


def refusal_result(writer, case_dir, route_shape, scenario, destination, defect):
    route, mixed = route_shape
    case = case_dir / defect
    case.mkdir()
    bank_path, output = destinations(case, destination)
    before = bank_path.read_bytes()
    before_output = output.read_bytes() if output is not None and output.exists() else None
    tables = [table(scenario, mixed=mixed) for _ in range(10)]
    victim = tables[-1]  # a later invalid table must block earlier native/app rows too
    if defect in DEFECTS[:6]:
        for measured in tables:
            measured['renderer'] = f'Test {defect.upper()} renderer'
    elif defect == 'absent-renderer':
        for measured in tables:
            measured.pop('renderer')
    elif defect == 'inconsistent-renderer':
        victim['renderer'] = 'Vulkan'
    elif defect == 'absent-allowed':
        victim.pop('bank_allowed')
    else:
        victim['bank_allowed'] = {'false': False, 'zero': 0, 'one': 1, 'string': 'true'}[defect]
    code = invoke(writer, case, route, tables, bank_path, output)
    output_unchanged = output is None or (
        not output.exists() if before_output is None else output.read_bytes() == before_output
    )
    return code, bank_path.read_bytes() == before and output_unchanged


def native_result(writer, case_dir, destination):
    bank_path, output = destinations(case_dir, destination)
    before = bank_path.read_bytes()
    tables = []
    for revision, value in (('c', 14.0), ('d', 18.0)):
        rows = []
        for scenario, metrics in (
            ('S1', ('latency', 'overhead')),
            ('S2', ('latency', 'overhead')),
            ('S3', ('presentation',)),
        ):
            rows.append({
                'dataset': 'D1',
                'scenario': scenario,
                **{metric: {'median_ms': value} for metric in metrics},
            })
        tables.append({'schema': 1, 'machine': 'bank-test', 'commit': revision * 40, 'rows': rows})
    expected = bank()
    for row in expected['machines']['bank-test']['rows']:
        if row['scenario'].startswith('S'):
            row['decision'] = DECISION
            for metric in row['metrics'].values():
                metric['banked_ms'] = 16.0  # closed-form median of 14 and 18
                metric['accepted'] = {
                    'replaced_ms': 1.0,
                    'measured_ms': [14.0, 18.0],
                    'commits': ['c' * 40, 'd' * 40],
                }
    code = invoke(writer, case_dir, 'accept', tables, bank_path, output)
    target = output if output is not None else bank_path
    return (
        code,
        json.loads(target.read_text()),
        expected,
        output is None or bank_path.read_bytes() == before,
    )


def gpu_result(writer, case_dir, scenario):
    bank_path, output = destinations(case_dir, 'new-out')
    code = invoke(
        writer,
        case_dir,
        'measurements',
        [table(scenario) for _ in range(10)],
        bank_path,
        output,
    )
    result = json.loads(output.read_text())
    row = next(
        row for row in result['machines']['bank-test']['rows'] if row['scenario'] == scenario
    )
    metric = 'frame' if scenario == 'A1' else 'update'
    return code, row['renderer'], row['metrics'][metric]['banked_ms']


@pytest.fixture(scope='module')
def matrix(tmp_path_factory):
    # Execute all inputs once, accounting filesystem/setup work as one shared cost.
    # Each node below still checks its own independent requirement and outcome.
    namespace = runpy.run_path(str(ROOT / 'tools/ci/latency_bank.py'))
    workspace = tmp_path_factory.mktemp('bank-eligibility')
    results = {}

    def exercise(key, helper, *args):
        directory = workspace / str(len(results))
        directory.mkdir()
        out, err = io.StringIO(), io.StringIO()
        with pytest.MonkeyPatch.context() as patch, redirect_stdout(out), redirect_stderr(err):
            writer = SimpleNamespace(**namespace, patch=patch)
            observed = helper(writer, directory, *args)
        results[key] = observed, err.getvalue()

    shapes = [
        (route, mixed)
        for route in ('accept', 'measurements', 'run', 'run-app')
        for mixed in (False, True)
    ]
    for shape, scenario, destination, defect in product(
        shapes, ('A1', 'A2'), ('in-place', 'new-out', 'existing-out'), DEFECTS
    ):
        key = shape, scenario, destination, defect
        exercise(key, refusal_result, shape, scenario, destination, defect)
    for destination in ('in-place', 'new-out', 'existing-out'):
        exercise(('native', destination), native_result, destination)
    for scenario in ('A1', 'A2'):
        exercise(('gpu', scenario), gpu_result, scenario)
    results['renderer-types'] = renderer_results(tmp_path_factory)
    return results


@pytest.mark.parametrize(
    'route_shape',
    [
        (route, mixed)
        for route in ('accept', 'measurements', 'run', 'run-app')
        for mixed in (False, True)
    ],
    ids=[
        f'{route}-{shape}'
        for route in ('accept', 'measurements', 'run', 'run-app')
        for shape in ('pure-app', 'native-and-app')
    ],
)
@pytest.mark.parametrize('scenario', ['A1', 'A2'])
@pytest.mark.parametrize('defect', DEFECTS)
@pytest.mark.parametrize('destination', ['in-place', 'new-out', 'existing-out'])
def test_every_writer_refuses_ineligible_app_before_any_write(
    matrix, route_shape, scenario, destination, defect
):
    (code, unchanged), error = matrix[route_shape, scenario, destination, defect]
    assert code != 0 and 'REFUSED' in error, (
        ' M5/M7 every bank writer rejects ineligible app input; '
        f'route={route_shape}, scenario={scenario}, defect={defect}'
    )
    assert unchanged, (
        ' M5/M7 ineligible app input leaves bank and explicit output byte-for-byte '
        f'unchanged without creating a new output; route={route_shape}, defect={defect}'
    )


@pytest.mark.parametrize('destination', ['in-place', 'new-out', 'existing-out'])
def test_authorized_native_acceptance_keeps_margins_runs_and_unrelated_rows(matrix, destination):
    (code, actual, expected, source_unchanged), error = matrix['native', destination]
    assert code == 0 and not error, (
        ' gate 4 authorized native S1/S2/S3 acceptance remains supported'
    )
    assert actual == expected, (
        ' gate 4 authorized native acceptance changes only medians and decision '
        'receipts, keeping margins, original runs, app/V rows and other machines'
    )
    assert source_unchanged, (
        ' gate 4 explicit native acceptance output leaves the source bank unchanged'
    )


@pytest.mark.parametrize('scenario', ['A1', 'A2'])
def test_eligible_gpu_measurements_remain_bankable(matrix, scenario):
    (code, renderer, median), error = matrix['gpu', scenario]
    assert code == 0 and not error and renderer == 'Metal', (
        ' M5/M7 ten consistent hardware-GPU tables with bank_allowed true bank'
    )
    assert median == 16.0, ' M5 hardware banking preserves the handwritten constant median'


# These raw JSON inputs are evidence-shape witnesses, not renderer names obtained
# from the implementation. The spellings intentionally collide after str().
BAD_RENDERERS = (
    ('null', None),
    ('false', False),
    ('true', True),
    ('zero', 0),
    ('integer', 42),
    ('float', 1.5),
    ('empty-list', []),
    ('list', ['Metal']),
    ('empty-object', {}),
    ('object', {'name': 'Metal'}),
    ('empty-string', ''),
    ('whitespace', ' \t\r\n '),
)
PLACEMENTS = ('all', 'first', 'last', 'type-collision')


def renderer_inputs(items, value, placement):
    """Apply malformed evidence to the whole input, either end, or a str collision."""
    if placement == 'all':
        for item in items:
            item['renderer'] = copy.deepcopy(value)
    else:
        if placement == 'type-collision':
            for item in items:
                item['renderer'] = str(value)
        victim = items[0] if placement == 'first' else items[-1]
        victim['renderer'] = copy.deepcopy(value)


def drawn_log(scenario, value, placement):
    records = []
    for app in ('A1', 'A2'):
        metric = 'frame' if app == 'A1' else 'update'
        records.append({
            'dataset': 'T1',
            'scenario': app,
            'samples': 50,
            'warmups': 5,
            'renderer': 'Metal',
            'bankAllowed': True,
            metric: {'median_ms': 16.0, 'p95_ms': 32.0},
        })
    # Put the chosen scenario at either end, exercising both raw record positions.
    records.sort(key=lambda record: record['scenario'] != scenario)
    if placement == 'last':
        records.reverse()
    renderer_inputs(records, value, placement)
    return (
        'edi_app_tests: built at '
        + 'a' * 40
        + '\n'
        + '\n'.join('qml: ' + json.dumps(record) for record in records)
    )


def typed_writer_result(writer, directory, route_shape, scenario, destination, value, placement):
    route, mixed = route_shape
    bank_path, output = destinations(directory, destination)
    before = bank_path.read_bytes()
    before_output = output.read_bytes() if output is not None and output.exists() else None
    tables = [table(scenario, mixed=mixed) for _ in range(10)]
    renderer_inputs(tables, value, placement)
    code = invoke(writer, directory, route, tables, bank_path, output)
    unchanged = bank_path.read_bytes() == before and (
        output is None
        or (not output.exists() if before_output is None else output.read_bytes() == before_output)
    )
    return code, unchanged


def raw_writer_result(writer, directory, route, scenario, destination, value, placement):
    bank_path, output = destinations(directory, destination)
    before = bank_path.read_bytes()
    target = output if output is not None else bank_path
    before_target = target.read_bytes() if target.exists() else None
    log = drawn_log(scenario, value, placement)
    if route == 'collect':
        source = directory / 'drawn.log'
        source.write_text(log, encoding='utf-8')
        code = writer.main(['--collect', str(source), '--table', str(target)])
    else:
        globals_ = writer.main.__globals__
        writer.patch.setitem(globals_, 'measured_revision', lambda _bank: 'a' * 40)
        writer.patch.setenv('RUNNER_NAME', 'bank-test')
        # Only the external process is substituted: production measure_app,
        # collect, median_table, compare and write_bank all remain active.
        writer.patch.setattr(
            globals_['subprocess'],
            'run',
            lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=log, stderr=''),
        )
        args = [
            '--run-app',
            '--bank',
            str(bank_path),
            '--decision',
            DECISION,
            '--tables',
            str(directory / 'runs'),
        ]
        if output is not None:
            args += ['--out', str(output)]
        code = writer.main(args)
    return code, bank_path.read_bytes() == before and (
        not target.exists() if before_target is None else target.read_bytes() == before_target
    )


def renderer_results(tmp_path_factory):
    namespace = runpy.run_path(str(ROOT / 'tools/ci/latency_bank.py'))
    workspace = tmp_path_factory.mktemp('typed-renderer')
    results = {}
    shapes = [
        (route, mixed)
        for route in ('accept', 'measurements', 'run', 'run-app')
        for mixed in (False, True)
    ]
    routes = shapes + [('collect-raw', False), ('run-app-raw', False)]
    case_number = 0
    for shape, scenario, destination in product(
        routes, ('A1', 'A2'), ('in-place', 'new-out', 'existing-out')
    ):
        observations = []
        for (name, value), placement in product(BAD_RENDERERS, PLACEMENTS):
            directory = workspace / str(case_number)
            case_number += 1
            directory.mkdir()
            out, err = io.StringIO(), io.StringIO()
            with pytest.MonkeyPatch.context() as patch, redirect_stdout(out), redirect_stderr(err):
                writer = SimpleNamespace(**namespace, patch=patch)
                if shape[0].endswith('-raw'):
                    code, unchanged = raw_writer_result(
                        writer,
                        directory,
                        shape[0].removesuffix('-raw'),
                        scenario,
                        destination,
                        value,
                        placement,
                    )
                else:
                    code, unchanged = typed_writer_result(
                        writer,
                        directory,
                        shape,
                        scenario,
                        destination,
                        value,
                        placement,
                    )
            observations.append((name, placement, code, unchanged, err.getvalue()))
        results[shape, scenario, destination] = observations
    return results


@pytest.fixture(scope='module')
def renderer_matrix(matrix):
    return matrix['renderer-types']


@pytest.mark.parametrize(
    'route_shape',
    [
        (route, mixed)
        for route in ('accept', 'measurements', 'run', 'run-app')
        for mixed in (False, True)
    ]
    + [('collect-raw', False), ('run-app-raw', False)],
    ids=[
        f'{route}-{shape}'
        for route in ('accept', 'measurements', 'run', 'run-app')
        for shape in ('pure-app', 'native-and-app')
    ]
    + ['collect-raw', 'run-app-raw'],
)
@pytest.mark.parametrize('scenario', ['A1', 'A2'])
@pytest.mark.parametrize('destination', ['in-place', 'new-out', 'existing-out'])
def test_renderer_types_are_refused_before_bank_or_output_write(
    renderer_matrix, route_shape, scenario, destination
):
    failures = [
        (name, placement, code, unchanged, error)
        for name, placement, code, unchanged, error in renderer_matrix[
            route_shape, scenario, destination
        ]
        if code == 0 or not unchanged or 'REFUSED' not in error
    ]
    assert not failures, (
        ' M5/M7 renderer evidence must be a nonblank JSON string, without raw-type '
        'collisions or partial bank/output writes; '
        f'route={route_shape}, scenario={scenario}, destination={destination}, failures={failures}'
    )


@pytest.mark.parametrize('boundary', ['app_renderer', 'gpu_renderer', 'median_table', 'compare'])
@pytest.mark.parametrize('scenario', ['A1', 'A2'])
@pytest.mark.parametrize('placement', PLACEMENTS)
def test_renderer_entry_boundaries_validate_raw_evidence(boundary, scenario, placement):
    namespace = runpy.run_path(str(ROOT / 'tools/ci/latency_bank.py'))
    failures = []
    for name, value in BAD_RENDERERS:
        tables = [table(scenario) for _ in range(10)]
        renderer_inputs(tables, value, placement)
        victim = tables[0] if placement == 'first' else tables[-1]
        args = (
            (victim, bank())
            if boundary == 'compare'
            else ((victim,) if boundary == 'app_renderer' else (tables,))
        )
        try:
            namespace[boundary](*args)
        except namespace['RefusedError']:
            continue
        failures.append(name)
    assert not failures, (
        ' M5/M7 every renderer entry rejects non-string/blank evidence and repeat '
        f'type mismatches before aggregation or comparison; boundary={boundary}, '
        f'scenario={scenario}, placement={placement}, accepted={failures}'
    )


@pytest.mark.parametrize('renderer', ['Metal', '  Metal  ', 'Mesa llvmpipe'])
def test_valid_renderer_names_preserve_hardware_and_software_reports(renderer):
    namespace = runpy.run_path(str(ROOT / 'tools/ci/latency_bank.py'))
    log = drawn_log('A1', renderer, 'all')
    collected, _ = namespace['collect'](log, 'independent raw records')
    assert collected['renderer'] == renderer, (
        ' M4 renderer reports preserve the original nonblank string'
    )
    assert collected['bank_allowed'] is (renderer != 'Mesa llvmpipe'), (
        ' M5/M7 hardware remains eligible and software remains report-only'
    )
    findings, notes = namespace['compare'](collected, {'schema': 1})
    assert not findings and notes, (
        ' M4/M7 valid software and unbanked hardware measurements remain reportable'
    )
