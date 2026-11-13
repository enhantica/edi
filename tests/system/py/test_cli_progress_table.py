"""Actual shared progress values, fixed count slots and both real CLI terminal adapters."""

import csv
import errno
import fcntl
import math
import os
import pty
import re
import selectors
import shutil
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

import edi
import pytest

from tests.conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/cli_performance'
BINS = ROOT / 'build/ci/cli_performance'


def projection(host, kind, *args):
    if host == 'binding':
        function = getattr(edi._edi, '_scan_progress_' + kind, None)
        assert callable(function), (
            'The CLI must consume the actual shared private progress projection'
        )
        return function(*args)
    arguments = [
        '-' if value is None else str(int(value)) if isinstance(value, bool) else str(value)
        for value in args
    ]
    result = subprocess.run(
        [str(BINS / 'edi_cli_progress_probe'), kind, *arguments],
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, (
        'The native shared renderer must accept the declared progress facts'
    )
    return result.stdout.decode()


@pytest.mark.parametrize('host', ['native', 'binding'])
@pytest.mark.parametrize(
    ('facts', 'expected'),
    [
        ((1, 3, 61.0, 1, 1, 0, 3.91), ['1/3', '33.3%', '1m01s', '2m02s', '1', '0', '3.91']),
        ((2, 3, 161.0, 2, 1, 1, 8.44), ['2/3', '66.7%', '2m41s', '1m21s', '1', '1', '8.44']),
        ((3, 3, 300.0, 3, 2, 1, 4.81), ['3/3', '100.0%', '5m00s', '2', '1']),
        (
            (40, 213, 30.0, 1, 39, 1, 4.81),
            ['40/213', '18.8%', '30s', '1h26m30s', '39', '1', '4.81'],
        ),
        ((10001, None, 61.0, 1, 9998, 3, 4.81), ['10001', '1m01s', '9998', '3', '4.81']),
        ((0, 5, 0.0, 0, 0, 0, math.nan), ['0/5', '0.0%', '0s', '0', '0']),
    ],
)
def test_numeric_projection_retains_exact_count_time_eta_and_failure_facts(host, facts, expected):
    row = projection(host, 'row', *facts, 0)
    assert row.split() == expected, (
        'Numeric cells retain exact counts, rounded clocks and this-run ETA without filenames'
    )
    assert row.isascii() and '\r' not in row and '\n' not in row, (
        'A shared numeric row is one ASCII line without cursor control'
    )
    assert not re.search(r'\b(?:this|run|elapsed|eta|ok|failed|files)\b', row, re.IGNORECASE), (
        'Labels and resumed time-basis prose belong to the static heading only'
    )


@pytest.mark.parametrize('host', ['native', 'binding'])
@pytest.mark.parametrize('resumed', [False, True])
def test_heading_identifies_project_estimated_eta_and_resumed_time_basis(host, resumed):
    heading = projection(host, 'heading', 'scan-demo', True, 20001, resumed, 0)
    assert heading.count('scan-demo') == 1 and heading.startswith('Sequential fit:'), (
        'The static heading names the actual project and scan mode once'
    )
    for label in ('Completed', 'Progress', 'Elapsed', 'OK', 'Failed', 'chi2'):
        assert label in heading, 'The static heading declares every retained numeric column'
    assert re.search(r'(?:ETA|Remaining).*est', heading, re.IGNORECASE), (
        'Remaining time is explicitly labelled as an estimate'
    )
    assert ('this run' in heading) is resumed, (
        'A resumed heading distinguishes the measured invocation from historical completed rows'
    )


@pytest.mark.parametrize('host', ['native', 'binding'])
@pytest.mark.parametrize('total', [20001, None])
def test_count_slots_stay_fixed_across_thousand_and_ten_thousand_boundaries(host, total):
    ends = []
    lengths = []
    for count in (9, 99, 999, 1000, 9999, 10000, 10001):
        row = projection(host, 'row', count, total, 61.0, count, count - 1, 1, 4.81, 0)
        fields = list(re.finditer(r'\S+', row))
        ends.append([fields[i].end() for i in ((0, 4, 5) if total else (0, 2, 3))])
        lengths.append(len(row))
    assert len({tuple(item) for item in ends}) == 1, (
        'Completed, OK and Failed retain their column boundaries beyond ten thousand files'
    )
    assert len(set(lengths)) == 1, (
        'Counter digit growth cannot stretch the fixed projected numeric row'
    )


@pytest.mark.parametrize('host', ['native', 'binding'])
@pytest.mark.parametrize('columns', [1, 8, 20, 40, 64, 80, 120])
def test_resize_and_erase_padding_never_use_the_terminal_wrap_column(host, columns):
    previous = projection(host, 'row', 10000, 20001, 61.0, 10000, 9983, 17, 4.81, 160)
    row = projection(host, 'row', 10001, 20001, 62.0, 10001, 9984, 17, math.nan, columns)
    write = projection(host, 'rewrite', row, len(previous), columns)
    assert write.startswith('\r') and '\n' not in write, (
        'TTY projection performs one in-place rewrite without an added line'
    )
    assert len(write[1:]) <= columns - 1, (
        'Both new numeric cells and trailing erasure respect the resized one-column safety margin'
    )
    if columns >= 64:
        assert all(value in row.split() for value in ('10001/20001', '9984', '17')), (
            'Completed, successful and failed totals remain visible when their stable slots fit'
        )


def stage(tmp_path):
    target = tmp_path / 'scan-project'
    shutil.copytree(corpus_case_dir('cosio-d20-scan-3f') / 'project', target)
    for name in ('results.csv', 'results-provenance.csv'):
        (target / 'analysis' / name).unlink(missing_ok=True)
    return target


def host_command(host, *, controlled=False):
    if host == 'native':
        binary = (
            BINS / 'edi_cli_performance_observer'
            if controlled
            else ROOT / 'build/ci/cli/easydiffraction'
        )
        return [str(binary)]
    return (
        [sys.executable, str(FIXTURE / 'observe_progress.py')]
        if controlled
        else [sys.executable, '-m', 'edi']
    )


def host_env():
    return {
        **os.environ,
        'OMP_NUM_THREADS': '1',
        'OMP_DYNAMIC': 'FALSE',
        'OMP_WAIT_POLICY': 'passive',
        'OPENBLAS_NUM_THREADS': '1',
        'EDI_CLI_PROGRESS_CONTROL': '1',
    }


@pytest.mark.parametrize('host', ['native', 'python'])
def test_real_piped_scan_has_one_static_header_and_one_numeric_row_per_file(host, tmp_path):
    project = stage(tmp_path)
    result = subprocess.run(
        [*host_command(host), 'fit', str(project), '--report', 'human', '--threads', '1'],
        env=host_env(),
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=20,
    )
    stdout = result.stdout.decode()
    assert result.returncode == 0, (
        'The actual tiny corpus scan must complete through the real host'
    )
    assert '\r' not in stdout, 'Piped scan output preserves ordinary line boundaries'
    lines = stdout.splitlines()
    rows = [line for line in lines if re.match(r'^\s*\d+/3\s', line)]
    assert len(rows) == 3 and [line.split()[0] for line in rows] == ['1/3', '2/3', '3/3'], (
        'The real host emits exactly one ordered numeric line for each actual file completion'
    )
    assert stdout.count('Sequential fit:') == stdout.count('Completed') == 1, (
        'The project heading and field labels are static rather than repeated with each completion'
    )
    assert all('.dat' not in row and row.isascii() for row in rows), (
        'Real numeric rows contain values rather than rolling filenames or non-ASCII glyphs'
    )
    with (project / 'analysis/results.csv').open(newline='') as stream:
        saved = list(csv.DictReader(stream))
    failed = sum(row['fit_result.success'].lower() != 'true' for row in saved)
    summaries = [line for line in lines if line.startswith('scan ·')]
    assert len(summaries) == 1, 'The existing whole-scan summary is emitted exactly once'
    assert f'{failed} failed' in summaries[0], (
        'The existing truthful summary retains failures independently of the new table shape'
    )


@pytest.mark.parametrize('host', ['native', 'python'])
def test_real_tty_hosts_resize_each_actual_completion_without_wrapping(host, tmp_path):  # noqa: PLR0912, PLR0914, PLR0915
    project = stage(tmp_path)
    master, slave = pty.openpty()
    widths = (80, 40, 100)
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, widths[0], 0, 0))
    process = subprocess.Popen(
        [
            *host_command(host, controlled=True),
            'fit',
            str(project),
            '--report',
            'human',
            '--threads',
            '1',
        ],
        cwd=ROOT,
        env=host_env(),
        stdin=subprocess.PIPE,
        stdout=slave,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None and process.stderr is not None, (
        'Real host callbacks require independent resize acknowledgement and diagnostic pipes'
    )
    output, errors, pending = bytearray(), bytearray(), bytearray()
    boundaries = 0
    deadline = time.monotonic() + 20
    selector = selectors.DefaultSelector()
    selector.register(master, selectors.EVENT_READ, 'output')
    selector.register(process.stderr, selectors.EVENT_READ, 'error')
    try:
        while selector.get_map():
            assert time.monotonic() < deadline, (
                'The actual tiny scan completes inside its fixed deadline'
            )
            if process.poll() is not None and slave >= 0:
                os.close(slave)
                slave = -1
            for key, _ in selector.select(0.1):
                try:
                    chunk = os.read(key.fd, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    chunk = b''
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == 'output':
                    output.extend(chunk)
                    continue
                errors.extend(chunk)
                pending.extend(chunk)
                while b'\n' in pending:
                    line, _, rest = pending.partition(b'\n')
                    pending[:] = rest
                    if line == b'EDI_PROGRESS_BOUNDARY':
                        assert boundaries < len(widths), (
                            'Only actual corpus-file boundaries may request a terminal resize'
                        )
                        fcntl.ioctl(
                            slave,
                            termios.TIOCSWINSZ,
                            struct.pack('HHHH', 24, widths[boundaries], 0, 0),
                        )
                        boundaries += 1
                        process.stdin.write(b'continue\n')
                        process.stdin.flush()
        assert process.wait(timeout=5) == 0, (
            'The real resized CLI must finish without a scientific or protocol error: '
            + errors.decode(errors='replace')
        )
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdin.close()
        process.stderr.close()
        if slave >= 0:
            os.close(slave)
        os.close(master)
    text = output.decode()
    writes = [
        part.split('\n', 1)[0] for part in text.split('\r') if re.match(r'^\s*\d+/3\s', part)
    ]
    assert boundaries == len(writes) == 3, (
        'Both actual hosts render one acknowledged row for each real engine completion'
    )
    assert [row.split()[0] for row in writes] == ['1/3', '2/3', '3/3'], (
        'Resizing preserves the actual ordered whole-scan completion counts'
    )
    for row, width in zip(writes, widths, strict=True):
        assert row.isascii() and len(row) <= width - 1, (
            'Every real TTY update including erase padding stays before the physical wrap column'
        )
        assert '.dat' not in row, 'The rolling real TTY row contains no filename identity'
    assert text.count('Sequential fit:') == text.count('Completed') == 1, (
        'A resized real scan keeps one static project header and one field-label heading'
    )


@pytest.mark.parametrize('host', ['native', 'python'])
def test_machine_channel_keeps_machine_records_without_numeric_ui_table(host, tmp_path):
    project = stage(tmp_path)
    result = subprocess.run(
        [*host_command(host), 'fit', str(project), '--report', 'machine', '--threads', '1'],
        cwd=ROOT,
        env=host_env(),
        capture_output=True,
        check=False,
        timeout=20,
    )
    stdout = result.stdout.decode()
    assert result.returncode == 0, (
        'The real machine-channel scan completes through its existing host'
    )
    assert re.search(r'^schema=\d+\nrecord=', stdout), (
        'Machine output retains the versioned public emitter record'
    )
    assert not any(
        label in stdout for label in ('Sequential fit:', 'Completed', 'Elapsed', '\r')
    ), 'Human progress projection and cursor control never enter the machine channel'
