"""Authored transport controls for the work validator; these are not measurements."""

import copy
import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.scan_timing.contract import (
    RESUME_FILES,
    compare,
    parse_app_timings,
    prepare_input,
    prepared_analysis,
    subject,
    validate_retained_sdk,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('saved_name', ['d20.scale', 'd20.cosio.scale'])
@pytest.mark.parametrize('boundary', [b'\n', b'loop_\n', b'_another.scalar 2.75\n'])
def test_prepared_analysis_omits_only_saved_fit_starts(saved_name, boundary):
    before = b'_fitting_mode.type sequential\n_minimizer.max_iterations 1000\n'
    saved = (
        b'loop_\n_fit_parameter.unique_name\n_fit_parameter.value\n'
        + saved_name.encode()
        + b' 1.25\n'
    )
    after = b'_fit_parameter_correlation.id\n_fit_parameter_correlation.correlation\npair17 0.50\n'
    expected_boundary = b'' if boundary == b'\n' else boundary
    assert (
        prepared_analysis(before + saved + boundary + after) == before + expected_boundary + after
    ), 'Preparing either historical saved-start spelling must preserve all other exact input bytes'
    untouched = before + b'loop_\n' + after
    assert prepared_analysis(untouched) == untouched, (
        'The fit-start projection must leave correlation rows and unrelated loops byte-identical'
    )


def test_actual_scratch_copies_hash_identically_without_fit_starts_or_resume_files(tmp_path):
    declared = (
        b'_fitting_mode.type sequential\n_minimizer.max_iterations 1000\n'
        b'_sequential_fit.data_dir experiments/bank\n_sequential_fit.file_pattern *.dat\n'
    )
    hashes = []
    for version, name in [('baseline', b'd20.scale'), ('fixed', b'd20.cosio.scale')]:
        source = tmp_path / version
        (source / 'analysis').mkdir(parents=True)
        (source / 'experiments/bank').mkdir(parents=True)
        (source / 'model.edi').write_bytes(b'_model.start 2.75\n')
        for index in range(162):
            (source / 'experiments/bank' / f'{index:03}.dat').write_bytes(b'1.25 31.75 0.5\n')
        (source / 'analysis/analysis.edi').write_bytes(
            declared
            + b'loop_\n_fit_parameter.unique_name\n_fit_parameter.value\n'
            + name
            + b' 9.5\n'
        )
        for filename in RESUME_FILES:
            (source / 'analysis' / filename).write_bytes(b'previous run\n')
        target = tmp_path / (version + '-scratch')
        observed = prepare_input(source, target)
        physical = {
            path.relative_to(target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in target.rglob('*')
            if path.is_file()
        }
        assert physical == observed['input_sha256'] == subject(source)['input_sha256'], (
            'Each actual scratch hash must cover its exact bytes '
            'after the allowed fit-start projection'
        )
        assert (target / 'analysis/analysis.edi').read_bytes() == declared, (
            'Both loaders must receive the same declared settings with no saved fit-start loop'
        )
        assert (target / 'model.edi').read_bytes() == b'_model.start 2.75\n', (
            'Preparing fresh input must retain the actual model start values byte-for-byte'
        )
        assert not any((target / 'analysis' / name).exists() for name in RESUME_FILES), (
            'Every actual scratch must remove all declared resume records before dispatch'
        )
        hashes.append(physical)
    assert hashes[0] == hashes[1], (
        'Different saved-start spellings must produce identical physical input for both builds'
    )


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
        {
            'name': 'delay-fit',
            'returncode': 0,
            'interval': 'fit',
            'delay_start_ms': 5813,
            'delay_end_ms': 7813,
            'interval_ms': 7916,
        },
        {
            'name': 'delay-reset',
            'returncode': 0,
            'interval': 'reset',
            'delay_start_ms': 48,
            'delay_end_ms': 2048,
            'interval_ms': 2129,
        },
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
            'native_configuration': {'CMAKE_BUILD_TYPE': 'Release', 'compiler': 'authored'},
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
        receipt['controls'][2]['delay_end_ms'] -= 0.001
    if escape == 'passing-slow-control':
        receipt['controls'][4]['comparator_returncode'] = 0
    if escape == 'nan-time':
        receipt['runs'][0]['intervals']['process_ms'] = float('nan')
    with pytest.raises(ValueError, match=r'.'):
        compare(receipt, spec)


@pytest.mark.parametrize(
    ('field', 'value'), [('CMAKE_BUILD_TYPE', 'Debug'), ('compiler', 'different')]
)
def test_actual_native_builds_require_matching_release_configuration(field, value):
    receipt, spec = authored_receipt()
    receipt['builds']['fixed']['native_configuration'][field] = value
    with pytest.raises(ValueError, match='same actual Release configuration'):
        compare(receipt, spec)


def test_comparison_process_exits_nonzero_for_a_slow_fixed_build(tmp_path):
    receipt, _ = authored_receipt()
    # The real CLI boundary must fail, not merely print a table with a red ratio.
    project = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project'
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


@pytest.mark.parametrize('at_endpoint', [False, True], ids=['inside', 'at-endpoint'])
def test_contained_delay_accepts_worker_overlap_on_its_own_clock(at_endpoint):
    receipt, spec = authored_receipt()
    if at_endpoint:
        for row in receipt['controls'][2:4]:
            row['interval_ms'] = row['delay_end_ms']
    assert compare(receipt, spec)['within_bound'], (
        'A real two-second slot contained on its interval clock must pass despite worker overlap'
    )


@pytest.mark.parametrize('interval', ['fit', 'reset'])
@pytest.mark.parametrize(
    'escape',
    [
        'missing-start',
        'short',
        'reversed',
        'negative',
        'nan-start',
        'inf-end',
        'nan-endpoint',
        'early-endpoint',
        'unassociated',
        'failed',
    ],
)
def test_delay_control_refuses_excluded_or_invalid_clock_records(interval, escape):
    receipt, spec = authored_receipt()
    row = receipt['controls'][2 if interval == 'fit' else 3]
    if escape == 'missing-start':
        del row['delay_start_ms']
    elif escape == 'short':
        row['delay_end_ms'] = row['delay_start_ms'] + 1999.999
    elif escape == 'reversed':
        row['delay_end_ms'] = row['delay_start_ms'] - 2000
    elif escape == 'negative':
        row['delay_start_ms'] = -1
    elif escape == 'nan-start':
        row['delay_start_ms'] = float('nan')
    elif escape == 'inf-end':
        row['delay_end_ms'] = float('inf')
    elif escape == 'nan-endpoint':
        row['interval_ms'] = float('nan')
    elif escape == 'early-endpoint':
        row['interval_ms'] = row['delay_end_ms'] - 0.001
    elif escape == 'unassociated':
        row['interval'] = 'reset' if interval == 'fit' else 'fit'
    else:
        row['returncode'] = 1
    with pytest.raises(ValueError, match=r'clock|slot'):
        compare(receipt, spec)


@pytest.mark.parametrize(
    'escape',
    [
        'missing',
        'duplicate-delay',
        'duplicate-endpoint',
        'short',
        'reversed',
        'negative',
        'nan-start',
        'inf-end',
        'nan-endpoint',
        'early-endpoint',
        'unassociated',
        'wrong-scenario',
        'unknown',
        'out-of-order',
        'unexpected-delay',
    ],
)
def test_native_clock_parser_refuses_malformed_or_unassociated_records(escape):
    text = 'perf-162f\tdelay from 5813 to\t7813\nperf-162f\tfit\t7916\n'
    text += 'perf-162f\tdelay from 48 to\t2048\nperf-162f\treset\t2129\n'
    changes = {
        'missing': ('perf-162f\tdelay from 5813 to\t7813\n', ''),
        'duplicate-delay': (
            'perf-162f\tfit',
            'perf-162f\tdelay from 5813 to\t7813\nperf-162f\tfit',
        ),
        'short': ('\t7813\n', '\t7812.999\n'),
        'reversed': ('\t7813\n', '\t3813\n'),
        'negative': ('from 5813', 'from -1'),
        'nan-start': ('from 5813', 'from nan'),
        'inf-end': ('\t7813\n', '\tinf\n'),
        'nan-endpoint': ('fit\t7916', 'fit\tnan'),
        'early-endpoint': ('fit\t7916', 'fit\t7812.999'),
        'wrong-scenario': ('perf-162f', 'another'),
        'unknown': ('\tfit\t', '\tother\t'),
        'out-of-order': ('\tfit\t', '\treset\t'),
    }
    if escape == 'duplicate-endpoint':
        text += 'perf-162f\treset\t2129\n'
    elif escape == 'unassociated':
        text += 'perf-162f\tdelay from 0 to\t2000\n'
    elif escape != 'unexpected-delay':
        text = text.replace(*changes[escape], 1)
    with pytest.raises(ValueError, match=r'record|clock|slot|interval|scenario'):
        parse_app_timings(text, 'perf-162f', expect_delay=escape != 'unexpected-delay')


def test_native_clock_parser_keeps_each_slot_with_its_interval():
    text = 'perf-162f\tdelay from 5813 to\t7813\nperf-162f\tfit\t7916\n'
    text += 'perf-162f\tdelay from 48 to\t2048\nperf-162f\treset\t2129\n'
    intervals, slots = parse_app_timings(text, 'perf-162f', expect_delay=True)
    assert intervals == {'fit_ms': 7916, 'reset_ms': 2129}, (
        'Native parsing must retain precisely the two real measured endpoints'
    )
    assert slots['fit']['delay_start_ms'] == 5813 and slots['fit']['delay_end_ms'] == 7813, (
        'The post-scan delay must stay associated with the fit clock'
    )
    assert slots['reset']['delay_start_ms'] == 48 and slots['reset']['delay_end_ms'] == 2048, (
        'The reset delay must stay associated with its reset clock'
    )
    ordinary, absent = parse_app_timings(
        'perf-162f\tfit\t6491\nperf-162f\treset\t108\n', 'perf-162f'
    )
    assert ordinary == {'fit_ms': 6491, 'reset_ms': 108} and absent == {}, (
        'Ordinary timing must preserve endpoints without inventing delay records'
    )


@pytest.mark.parametrize(
    'field',
    [
        'edi_source',
        'compiled_edi_source',
        'compiled_cli_sha256',
        'sdk_manifest_sha256',
        'missing-field',
        'not-a-record',
    ],
)
def test_historical_sdk_locator_requires_its_retained_binary_bond(field):
    retained = {
        'edi_source': 'a' * 40,
        'compiled_edi_source': 'a' * 40,
        'compiled_cli_sha256': 'b' * 64,
        'sdk_manifest_sha256': 'c' * 64,
    }
    validate_retained_sdk(retained, 'a' * 40, 'b' * 64, 'c' * 64)
    if field == 'not-a-record':
        retained = None
    elif field == 'missing-field':
        del retained['sdk_manifest_sha256']
    else:
        retained[field] = 'changed'
    with pytest.raises(ValueError, match='unchanged compiled command'):
        validate_retained_sdk(retained, 'a' * 40, 'b' * 64, 'c' * 64)
