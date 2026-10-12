"""Authored transport controls for the work validator; these are not measurements."""

import copy
import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.scan_timing.contract import compare

ROOT = Path(__file__).resolve().parents[3]


def authored_receipt():
    files = [f'{index:03}.dat' for index in range(162)]
    spec = {
        'files': files,
        'settings': {'_minimizer.max_iterations': '1000'},
        'input_sha256': {'analysis/analysis.edi': 'a' * 64},
    }
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['file_path', 'fit_result.success'])
    writer.writerows((file, 'True') for file in files)
    work = {
        'input_sha256': spec['input_sha256'],
        'preexisting_results': [],
        'mode': 'sequential',
        'settings': spec['settings'],
        'results_csv': stream.getvalue(),
        'skipped': [],
        'refused': [],
        'unfinished': [],
        'machine': 'record=fit\nstatus=done\n',
        'follow': 'adaptive',
        'terminal_published': True,
        'outcome': 'success',
        'calculation_pending': False,
        'calculation_stale': False,
        'reset': {
            'remaining_files': [],
            'result_rows': [],
            'dataset_fit_outcomes': [],
            'dataset_correlations': [],
            'prefit_values_restored': True,
            'undo_available': True,
            'calculation_pending': False,
        },
    }
    controls = [
        {'name': 'refused-start', 'returncode': 1, 'timing_credit': False, 'completed_files': 0},
        {
            'name': 'cancel-after-40',
            'returncode': 1,
            'timing_credit': False,
            'completed_files': 40,
        },
        {'name': 'delay-fit', 'returncode': 0, 'normal_ms': 123.25, 'delayed_ms': 2123.25},
        {'name': 'delay-reset', 'returncode': 0, 'normal_ms': 31.25, 'delayed_ms': 2031.25},
        {
            'name': 'slow-fit',
            'fixed_source': 'bd72193898d2dc6fefb1d692703d1f7a4137c731',
            'comparator_returncode': 1,
            'baseline_fit_ms': 100,
            'fixed_fit_ms': 316,
        },
    ]
    for index, control in enumerate(controls, 1):
        control.update(sequence=index, real_timing_path=True, command_sha256='b' * 64)
    builds = {}
    for name, source in [('baseline', '2e04556' + '0' * 33), ('fixed', 'c' * 40)]:
        builds[name] = {
            'edi_source': source,
            'compiled_edi_source': source,
            'crysta_source': 'fb153aeb' + '0' * 32,
            'command_sha256': 'b' * 64,
            'configuration': {'CMAKE_BUILD_TYPE': 'Release', 'compiler': 'authored'},
        }
    rows = []
    for rep in range(1, 6):
        for build in ['baseline', 'fixed']:
            for path in ['cli', 'app']:
                rows.append({
                    'repetition': rep,
                    'build': build,
                    'path': path,
                    'sequence': len(rows) + 6,
                    'host': 'authored-host',
                    'returncode': 0,
                    'work': copy.deepcopy(work),
                    'intervals': {'process_ms': 100}
                    if path == 'cli'
                    else {'fit_ms': 100, 'reset_ms': 20},
                })
    return {
        'schema': 1,
        'builds': builds,
        'runs': rows,
        'controls': controls,
        'host': 'authored-host',
    }, spec


@pytest.mark.parametrize('interval', ['process_ms', 'fit_ms', 'reset_ms'])
@pytest.mark.parametrize(('factor', 'passes'), [(1.05, True), (1.050001, False), (1.07, False)])
def test_owner_bound_rejects_each_slow_interval_and_keeps_boundary(interval, factor, passes):
    receipt, spec = authored_receipt()
    for row in receipt['runs']:
        if row['build'] == 'fixed' and interval in row['intervals']:
            row['intervals'][interval] *= factor
    result = compare(receipt, spec)
    assert result['within_bound'] == passes, (
        'Every end-to-end interval must enforce the bound of baseline median times 1.05'
    )


WORK_ESCAPES = [
    ('cli', 'preexisting_results', ['results.csv']),
    ('cli', 'mode', 'single'),
    ('cli', 'settings', {'_minimizer.max_iterations': '1'}),
    ('cli', 'input_sha256', {}),
    ('cli', 'skipped', ['000.dat']),
    ('cli', 'refused', ['001.dat']),
    ('cli', 'unfinished', ['002.dat']),
    ('cli', 'machine', 'record=fit\nstatus=cancelled\n'),
    ('cli', 'machine', 'record=fit\nstatus=done\nstatus=done\n'),
    ('app', 'follow', 'locked'),
    ('app', 'terminal_published', False),
    ('app', 'outcome', 'Stopped'),
    ('app', 'outcome', 'Failed'),
    ('app', 'calculation_pending', True),
    ('app', 'calculation_stale', True),
]


@pytest.mark.parametrize(('path', 'field', 'value'), WORK_ESCAPES)
def test_incomplete_work_never_gets_a_fast_time(path, field, value):
    receipt, spec = authored_receipt()
    row = next(row for row in receipt['runs'] if row['path'] == path)
    row['work'][field] = value
    row['intervals'] = dict.fromkeys(row['intervals'], 0.001)
    with pytest.raises(ValueError, match=r'.'):
        compare(receipt, spec)


@pytest.mark.parametrize(
    'field',
    [
        'remaining_files',
        'result_rows',
        'dataset_fit_outcomes',
        'dataset_correlations',
        'prefit_values_restored',
        'undo_available',
        'calculation_pending',
    ],
)
def test_each_actual_reset_condition_is_required_before_timing_credit(field):
    receipt, spec = authored_receipt()
    reset = receipt['runs'][1]['work']['reset']
    reset[field] = not reset[field] if isinstance(reset[field], bool) else ['retained']
    with pytest.raises(ValueError, match='Reset fits'):
        compare(receipt, spec)


@pytest.mark.parametrize('escape', ['missing', 'duplicate', 'bad-success', 'extra-column'])
def test_physical_results_inventory_rejects_each_population_escape(escape):
    receipt, spec = authored_receipt()
    work = receipt['runs'][0]['work']
    lines = work['results_csv'].splitlines()
    if escape == 'missing':
        lines.pop()
    if escape == 'duplicate':
        lines[-1] = lines[-2]
    if escape == 'bad-success':
        lines[-1] = lines[-1].replace('True', 'False')
    if escape == 'extra-column':
        lines[-1] += ',unfinished'
    work['results_csv'] = '\n'.join(lines) + '\n'
    with pytest.raises(ValueError, match='results'):
        compare(receipt, spec)


@pytest.mark.parametrize(
    'escape',
    [
        'drop-run',
        'reorder',
        'host',
        'debug',
        'wrong-baseline',
        'wrong-compiled-source',
        'missing-control',
        'control-credit',
        'late-control',
        'short-delay',
        'passing-slow-control',
        'nan-time',
    ],
)
def test_provenance_ordering_and_negative_controls_fail_closed(escape):
    receipt, spec = authored_receipt()
    if escape == 'drop-run':
        receipt['runs'].pop()
    if escape == 'reorder':
        receipt['runs'].reverse()
    if escape == 'host':
        receipt['runs'][0]['host'] = 'another-host'
    if escape == 'debug':
        receipt['builds']['fixed']['configuration']['CMAKE_BUILD_TYPE'] = 'Debug'
    if escape == 'wrong-baseline':
        receipt['builds']['baseline']['edi_source'] = 'wrong'
    if escape == 'wrong-compiled-source':
        receipt['builds']['fixed']['compiled_edi_source'] = 'stale'
    if escape == 'missing-control':
        receipt['controls'].pop()
    if escape == 'control-credit':
        receipt['controls'][1]['timing_credit'] = True
    if escape == 'late-control':
        receipt['controls'][1]['sequence'] = 100
    if escape == 'short-delay':
        receipt['controls'][2]['delayed_ms'] -= 0.001
    if escape == 'passing-slow-control':
        receipt['controls'][4]['comparator_returncode'] = 0
    if escape == 'nan-time':
        receipt['runs'][0]['intervals']['process_ms'] = float('nan')
    with pytest.raises(ValueError, match=r'.'):
        compare(receipt, spec)


def test_comparison_process_exits_nonzero_for_a_slow_fixed_build(tmp_path):
    receipt, _ = authored_receipt()
    # The real CLI boundary must fail, not merely print a table with a red ratio.
    project = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project'
    from tests.fixtures.scan_timing.contract import subject  # noqa: PLC0415

    spec = subject(project)
    for row in receipt['runs']:
        row['work']['input_sha256'] = spec['input_sha256']
        row['work']['settings'] = spec['settings']
        lines = ['file_path,fit_result.success', *[name + ',True' for name in spec['files']]]
        row['work']['results_csv'] = '\n'.join(lines) + '\n'
        if row['build'] == 'fixed':
            row['intervals'] = {key: value * 2 for key, value in row['intervals'].items()}
    path = tmp_path / 'authored-receipt.json'
    path.write_text(json.dumps(receipt))
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tests/fixtures/scan_timing/contract.py'),
            str(path),
            str(project),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, 'The actual comparison process must reject a slow fixed median'
    assert '"within_bound": false' in result.stdout, (
        'The nonzero comparator must publish the interval results that explain its refusal'
    )


def test_fit_and_reset_sum_is_compared_per_run_not_as_a_sum_of_medians():
    receipt, spec = authored_receipt()
    for row in receipt['runs']:
        if row['path'] == 'app':
            index = row['repetition'] - 1
            row['intervals']['fit_ms'] = [100, 100, 100, 1, 1][index]
            row['intervals']['reset_ms'] = (
                [1, 1, 100, 100, 100] if row['build'] == 'baseline' else [100, 100, 100, 1, 1]
            )[index]
    result = compare(receipt, spec)
    assert result['failed'] == ['app.sum_ms'], (
        'The app sum must enforce the bound even when each component median independently passes'
    )
