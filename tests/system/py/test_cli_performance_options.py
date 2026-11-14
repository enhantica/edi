"""Actual CLI process controls preserve scientific precision and scan grouping."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from operator import itemgetter
from pathlib import Path

import pytest

from tests.conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/cli_performance'
ENTRIES = [('native', 'fit'), ('python', 'fit'), ('python', 'calc')]
INVALID = ['', '0', '-1', '+1', '1.0', '1e2', ' 2', '2 ', '1_0', '٢', '²', '2147483648', '9' * 200]


def executable(*, observer=False):
    if observer:
        candidates = [
            os.environ.get('EDI_CLI_PERFORMANCE_OBSERVER'),
            ROOT / 'build/ci/cli_performance/edi_cli_performance_observer',
        ]
    else:
        candidates = [os.environ.get('EDI_CLI_EXECUTABLE'), ROOT / 'build/ci/cli/easydiffraction']
    found = next((Path(p) for p in candidates if p and Path(p).is_file()), None)
    assert found is not None, 'The CLI performance contract requires its real built host'
    return found


def command(entry, *, observed=False):
    if entry == 'native':
        return [str(executable(observer=observed))]
    return (
        [sys.executable, str(FIXTURE / 'observe_python.py')]
        if observed
        else [sys.executable, '-m', 'edi']
    )


def run(argv, *, trace=None):
    env = {
        **os.environ,
        'OMP_NUM_THREADS': '1',
        'OMP_DYNAMIC': 'FALSE',
        'OMP_WAIT_POLICY': 'passive',
        'OPENBLAS_NUM_THREADS': '1',
    }
    if trace is not None:
        env['EDI_CLI_PERFORMANCE_TRACE'] = str(trace)
    return subprocess.run(
        argv, cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=20
    )


@pytest.mark.parametrize(('entry', 'operation'), ENTRIES)
def test_help_advertises_calculation_threads_and_fit_parallelism(entry, operation):
    result = run([*command(entry), operation, '--help'])
    assert result.returncode == 0, 'The requested operation advertises its accepted options'
    assert '--threads' in result.stdout and 'auto' in result.stdout.lower(), (
        'Both hosts document Auto or a positive per-calculation thread count'
    )
    assert ('--parallel-fits' in result.stdout) is (operation == 'fit'), (
        'Only a fit offers the process-wide parallel scan selection'
    )


@pytest.mark.parametrize(('entry', 'operation'), ENTRIES)
@pytest.mark.parametrize('value', ['auto', '1', '2', '0002', '2147483647'])
def test_valid_thread_tokens_reach_project_loading(entry, operation, value, tmp_path):
    missing = tmp_path / 'absent-project'
    for options in (['--threads', value], [f'--threads={value}']):
        result = run([*command(entry), operation, str(missing), *options])
        assert result.returncode == 1 and '--threads' not in result.stderr, (
            'A valid bounded thread token is accepted before the real missing-project refusal'
        )


@pytest.mark.parametrize(('entry', 'operation'), ENTRIES)
@pytest.mark.parametrize('value', INVALID + ['AUTO', 'Auto'])
def test_invalid_thread_tokens_refuse_before_work(entry, operation, value, tmp_path):
    for options in (['--threads', value], [f'--threads={value}']):
        result = run([*command(entry), operation, str(tmp_path / 'absent'), *options])
        assert result.returncode == 2 and '--threads' in result.stderr, (
            'Malformed thread counts refuse with a named parse error before project loading'
        )
        assert not result.stdout, 'A parse refusal produces no fit/calculation record'


@pytest.mark.parametrize('entry', ['native', 'python'])
@pytest.mark.parametrize('value', INVALID + ['auto'])
def test_invalid_scan_parallelism_refuses_before_work(entry, value, tmp_path):
    for options in (['--parallel-fits', value], [f'--parallel-fits={value}']):
        result = run([*command(entry), 'fit', str(tmp_path / 'absent'), *options])
        assert result.returncode == 2 and '--parallel-fits' in result.stderr, (
            'Malformed parallel counts refuse with a named parse error before project loading'
        )
        assert not result.stdout, 'A parse refusal produces no fitting record'


@pytest.mark.parametrize(('entry', 'operation'), ENTRIES)
@pytest.mark.parametrize('tail', [['--threads'], ['--threads', '--dry']])
def test_missing_thread_value_refuses_before_work(entry, operation, tail, tmp_path):
    result = run([*command(entry), operation, str(tmp_path / 'absent'), *tail])
    assert result.returncode == 2 and '--threads' in result.stderr, (
        'A missing thread count refuses with its option name before loading'
    )


@pytest.mark.parametrize('entry', ['native', 'python'])
@pytest.mark.parametrize('tail', [['--parallel-fits'], ['--parallel-fits', '--dry']])
def test_missing_parallel_value_refuses_before_work(entry, tail, tmp_path):
    result = run([*command(entry), 'fit', str(tmp_path / 'absent'), *tail])
    assert result.returncode == 2 and '--parallel-fits' in result.stderr, (
        'A missing parallel count refuses with its option name before loading'
    )


@pytest.mark.parametrize('entry', ['native', 'python'])
@pytest.mark.parametrize('value', ['1', '2', '0002', '2147483647'])
def test_valid_parallel_tokens_reach_project_loading(entry, value, tmp_path):
    for options in (['--parallel-fits', value], [f'--parallel-fits={value}']):
        result = run([*command(entry), 'fit', str(tmp_path / 'absent'), *options])
        assert result.returncode == 1 and '--parallel-fits' not in result.stderr, (
            'A bounded positive scan count reaches the real missing-project refusal'
        )


def test_calculation_rejects_scan_only_selection(tmp_path):
    result = run([*command('python'), 'calc', str(tmp_path / 'absent'), '--parallel-fits', '2'])
    assert result.returncode == 2 and '--parallel-fits' in result.stderr, (
        'Forward calculation cannot accept a scan fitting selection'
    )


def stage(tmp_path):
    source = corpus_case_dir('cosio-d20-scan-3f') / 'project'
    target = tmp_path / 'input'
    shutil.copytree(source, target)
    (target / 'analysis/results.csv').unlink(missing_ok=True)
    (target / 'analysis/results-provenance.csv').unlink(missing_ok=True)
    return target


def science(record):
    return {
        key: value
        for line in record.splitlines()
        if '=' in line
        for key, value in [line.split('=', 1)]
        if not key.endswith(('elapsed_ms', 'fitting_time'))
    }


@pytest.mark.parametrize(('entry', 'operation'), ENTRIES)
@pytest.mark.parametrize(
    ('options', 'threads', 'parallel'),
    [
        ([], 0, 1),
        (['--threads', '1'], 1, 1),
        (['--threads=2', '--threads', '3'], 3, 1),
        (['--threads', '2', '--threads=auto'], 0, 1),
    ],
)
def test_real_settings_apply_before_actual_work_and_stay_process_only(
    entry, operation, options, threads, parallel, tmp_path
):
    project = stage(tmp_path)
    before = {p.relative_to(project): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    trace = tmp_path / 'trace.json'
    result = run(
        [
            *command(entry, observed=True),
            operation,
            str(project),
            '--dry',
            '--report',
            'machine',
            '--verbosity',
            'full',
            *options,
        ],
        trace=trace,
    )
    assert result.returncode == 0, (
        'The real operation must succeed: ' + result.stdout + result.stderr
    )
    if entry == 'native':
        events = [json.loads(line) for line in trace.read_text().splitlines()]
        starts = [event for event in events if event['kind'] == 'start']
        assert len(starts) == 3, 'The real native scan must fit every tiny witness file'
        assert all((row['threads'], row['parallel']) == (threads, parallel) for row in starts), (
            'Every actual file fit observes the requested process settings'
        )
        assert (events[-1]['threads'], events[-1]['parallel']) == (threads, parallel), (
            'The native invocation replaces seeded settings with explicit or default values'
        )
    else:
        events = json.loads(trace.read_text())
        work = next(index for index, event in enumerate(events) if event['kind'] == operation)
        assert {'kind': '_set_engine_threads', 'value': threads} in events[:work], (
            'The real thread setter is forwarded before the actual calculation or fit'
        )
        assert {'kind': '_set_scan_workers', 'value': parallel} in events[:work], (
            'Each operation resets the real parallel setting before actual work'
        )
    assert before == {
        p.relative_to(project): p.read_bytes() for p in project.rglob('*') if p.is_file()
    }, 'Machine selections and --dry must preserve every source-project byte'


@pytest.mark.parametrize(('entry', 'operation'), ENTRIES)
def test_explicit_one_thread_preserves_all_scientific_output(entry, operation, tmp_path):
    project = stage(tmp_path)
    base = [
        *command(entry),
        operation,
        str(project),
        '--dry',
        '--report',
        'machine',
        '--verbosity',
        'full',
    ]
    original = run(base)
    one = run([*base, '--threads', '1', *(['--parallel-fits', '1'] if operation == 'fit' else [])])
    several = run([*base, '--threads', '3'])
    assert original.returncode == one.returncode == several.returncode == 0, (
        'Default and explicit thread choices each complete the real scientific operation'
    )
    assert science(original.stdout) == science(one.stdout) == science(several.stdout), (
        'Thread choice preserves every scientific field, status and iteration without a tolerance'
    )


@pytest.mark.parametrize('entry', ['native', 'python'])
def test_parallel_scan_selection_reaches_real_grouped_engine(entry, tmp_path):
    project = stage(tmp_path)
    rows = {}
    traces = {}
    for count in (1, 2):
        target = tmp_path / f'output-{count}'
        trace = tmp_path / f'trace-{count}.json'
        result = run(
            [
                *command(entry, observed=True),
                'fit',
                str(project),
                '--output',
                str(target),
                '--threads=3',
                '--parallel-fits=1',
                '--parallel-fits',
                str(count),
                '--report',
                'machine',
                '--verbosity',
                'compact',
            ],
            trace=trace,
        )
        assert result.returncode == 0, (
            'The real operation must succeed: ' + result.stdout + result.stderr
        )
        with (target / 'analysis/results.csv').open(newline='') as stream:
            rows[count] = list(csv.DictReader(stream))
        assert len(rows[count]) == 3, 'Parallel selection preserves every input scan file'
        for path in target.rglob('*.edi'):
            tags = [
                line.split()[0] for line in path.read_text().splitlines() if line.startswith('_')
            ]
            assert not any(
                tag.endswith((
                    '.threads',
                    '.parallel_fits',
                    '.max_workers',
                    '.engine_threads',
                    '.scan_workers',
                ))
                for tag in tags
            ), 'No process performance selection is persisted as project preference state'
        traces[count] = trace
    assert [row['file_path'] for row in rows[1]] == [row['file_path'] for row in rows[2]], (
        'Parallel grouping retains the declared serial output file order'
    )
    if entry == 'native':
        starts = {}
        for count, path in traces.items():
            events = [json.loads(line) for line in path.read_text().splitlines()]
            starts[count] = sorted(
                (row for row in events if row['kind'] == 'start'), key=itemgetter('file')
            )
            assert all(
                row['parallel'] == count and row['threads'] == 3 for row in starts[count]
            ), 'Every native scan start sees the selected workers and calculation threads'
        assert starts[1][0]['values'] != starts[1][1]['values'], (
            'The serial predecessor chain genuinely changes the second file start'
        )
        assert starts[2][0]['values'] == starts[2][1]['values'], (
            'The two-file group starts both files from the same untouched group seed'
        )
        assert starts[2][2]['values'] != starts[2][1]['values'], (
            'The next group starts from the completed prior group rather than the initial seed'
        )
    else:
        for count, path in traces.items():
            events = json.loads(path.read_text())
            at = next(i for i, row in enumerate(events) if row['kind'] == 'fit')
            assert {'kind': '_set_scan_workers', 'value': count} in events[:at], (
                'The actual Python worker selection precedes the real grouped scan fit'
            )
        native_target = tmp_path / 'native-parallel'
        native = run([
            *command('native'),
            'fit',
            str(project),
            '--output',
            str(native_target),
            '--threads',
            '3',
            '--parallel-fits',
            '2',
            '--verbosity',
            'off',
        ])
        assert native.returncode == 0, 'The native parity witness performs the same grouped fit'
        with (native_target / 'analysis/results.csv').open(newline='') as stream:
            native_rows = list(csv.DictReader(stream))
        assert rows[2] == native_rows, (
            'The Python binding applies actual grouping and matches every native reported value'
        )
