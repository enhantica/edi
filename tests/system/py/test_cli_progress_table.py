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
from tests.fixtures.cli_performance.table_assertions import cells, table_rows, terminal_lines

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/cli_performance'
BINS = ROOT / 'build/ci/cli_performance'


def projection(host, kind, *args):
    if kind == 'row' and len(args) == 8:
        args = (*args[:-1], args[6], args[6], 'completed-file.dat', args[-1])
    if host == 'binding' and kind == 'sequence':
        columns = args[0]
        return (
            edi._edi._scan_progress_heading('widths', True, 2, False, columns)
            + '\n'
            + edi._edi._scan_progress_row(
                1, 2, 59.0, 1, 1, 0, 4.81, 4.81, 4.81, 'scan-first.dat', columns
            )
            + edi._edi._scan_progress_row(
                2,
                2,
                36611.0,
                2,
                2,
                0,
                4.81,
                3.91,
                8.44,
                'scan-last-abcdefghijklmnopqrstuvwxyz-abcdefghijklmnopqrstuvwxyz-tail.dat',
                columns,
            )
            + '\n'
        )
    if host == 'binding':
        function = getattr(edi._edi, '_scan_progress_' + kind, None)
        assert callable(function), (
            'The CLI must consume the actual shared private progress projection'
        )
        if kind == 'row':
            edi._edi._scan_progress_heading('projection', False, args[1], False, 0)
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
    completed, total, _elapsed, _measured, ok, failed, chi2 = facts
    bound = chi2 if math.isfinite(chi2) else math.nan
    row = projection(host, 'row', *facts, bound, bound, 'completed-file.dat', 0)
    actual = cells(row)
    offset = 2 if total else 1
    elapsed = expected[offset]
    left = expected[offset + 1] if total and 0 < completed < total else ''
    assert actual['count'] == (f'{completed}/{total}' if total else str(completed)), (
        'Progress retains the exact completed count and known total inside its own group'
    )
    assert actual['percent'] == (expected[1] if total else ''), (
        'Known totals retain the independently calculated percent; unknown totals invent none'
    )
    assert (actual['elapsed'], actual['left']) == (elapsed, left), (
        'The new clock group preserves the original rounded elapsed and measured-run ETA facts'
    )
    assert (actual['ok'], actual['failed']) == (str(ok), str(failed)), (
        'Successful and failed counts remain independent through the grouped table projection'
    )
    number = f'{chi2:.2f}' if math.isfinite(chi2) else ''
    assert (actual['chi2'], actual['range']) == (number, f'{number}-{number}' if number else ''), (
        'The final row retains the last metric and complete range; absent metrics stay empty'
    )
    assert actual['file'] == 'completed-file', (
        'File is the last group and preserves the completed file stem without its extension'
    )
    bars = {1: '███░░░░░░░', 2: '███████░░░', 3: '██████████', 40: '██░░░░░░░░', 0: '░░░░░░░░░░'}
    assert actual['bar'] == (bars[completed] if total else ''), (
        'The progress bar has ten terminal cells at the nontrivial independently checked fractions'
    )
    assert '\r' not in row and '\n' not in row, (
        'A log projection is one complete Unicode line without terminal controls'
    )
    with pytest.raises(AssertionError, match='five groups'):
        cells(row.replace(' │ ', ' | ', 1))


@pytest.mark.parametrize('host', ['native', 'binding'])
@pytest.mark.parametrize('resumed', [False, True])
def test_heading_identifies_project_estimated_eta_and_resumed_time_basis(host, resumed):
    heading = projection(host, 'heading', 'scan-demo', True, 20001, resumed, 0)
    assert heading.count('scan-demo') == 1 and heading.startswith('Sequential fit:'), (
        'The heading names the actual project and scan mode once'
    )
    columns = heading.splitlines()[-1].split(' │ ')
    assert [part.split() for part in columns] == [
        ['Progress'],
        ['OK', 'Failed'],
        ['Elapsed', 'Left'],
        ['Chi2', 'Chi2', 'range'],
        ['File'],
    ], 'The final owner layout groups every heading in order and puts the file last'
    assert 'this run' not in heading and len(columns[2]) == 15, (
        'Elapsed is always headed Elapsed, seven columns wide in ordinary fixed-width logs'
    )


@pytest.mark.parametrize('host', ['native', 'binding'])
@pytest.mark.parametrize('total', [20001, None])
def test_count_slots_stay_fixed_across_thousand_and_ten_thousand_boundaries(host, total):
    ends = []
    lengths = []
    for count in (9, 99, 999, 1000, 9999, 10000, 10001):
        row = projection(host, 'row', count, total, 61.0, count, count - 1, 1, 4.81, 0)
        groups = row.split(' │ ')
        ends.append([match.start() for match in re.finditer(r' │ ', row)][:2])
        assert groups[0].split()[-1] == (f'{count}/{total}' if total else str(count)), (
            'Digit-boundary checks retain the original actual completed and total counts'
        )
        lengths.append((len(groups[0]), len(groups[1])))
    assert len({tuple(item) for item in ends}) == 1, (
        'Progress and outcome group boundaries remain fixed across '
        'thousand and ten-thousand counts'
    )
    assert len(set(lengths)) == 1, (
        'Counter growth cannot stretch its reserved progress and outcome groups'
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

    if columns == 120:
        stream = projection(host, 'sequence', columns)
        screen = terminal_lines(stream)
        assert len(screen) == 4 and '\x1b[1A' in stream, (
            'A wider live clock redraws the actual heading and final values together'
        )
        header, final = screen[-2:]
        assert [m.start() for m in re.finditer(r' │ ', header)] == [
            m.start() for m in re.finditer(r' │ ', final)
        ], 'Every redrawn heading group aligns with its current values after a width change'
        facts = cells(final)
        assert (facts['elapsed'], facts['left'], facts['chi2'], facts['range']) == (
            '10h10m11s',
            '',
            '4.81',
            '3.91-8.44',
        ), 'Width adaptation preserves independently specified final clocks and scientific metrics'
        assert facts['file'].startswith('scan-last-') and facts['file'].endswith('-tail'), (
            'A shortened last-file stem retains both its identifying prefix and suffix'
        )
        assert '…' in facts['file'] and all(len(line) <= columns - 1 for line in screen), (
            'The middle ellipsis and block bar consume terminal cells rather than UTF-8 bytes'
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
    rows = table_rows(stdout)
    assert len(rows) == 3 and [cells(line)['count'] for line in rows] == ['1/3', '2/3', '3/3'], (
        'The real host emits exactly one ordered numeric line for each actual file completion'
    )
    assert stdout.count('Sequential fit:') == stdout.count('Progress') == 1, (
        'The project heading and field labels are static rather than repeated with each completion'
    )
    assert all('.dat' not in row and cells(row)['file'] for row in rows), (
        'Real progress rows retain the completed file stem and use the approved Unicode bar'
    )
    with (project / 'analysis/results.csv').open(newline='') as stream:
        saved = list(csv.DictReader(stream))
    failed = sum(row['fit_result.success'].lower() != 'true' for row in saved)
    assert not any(line.startswith('scan ·') for line in lines), (
        'The completed final table row replaces the retired separate scan summary'
    )
    final = cells(rows[-1])
    assert (final['count'], final['ok'], final['failed'], final['left']) == (
        '3/3',
        str(3 - failed),
        str(failed),
        '',
    ), 'The final row keeps truthful complete counts and no remaining-time estimate'
    finite = [float(item['fit_result.reduced_chi_square']) for item in saved]
    assert final['chi2'] == f'{finite[-1]:.2f}' and final['range'] == (
        f'{min(finite):.2f}-{max(finite):.2f}'
    ), 'The final table metric and range come from the actual saved per-file results'


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
    writes = re.findall(r'[█░]{10}  [^\r\n\x1b]+', text)
    counts = [int(re.search(r'(\d+)/3', row)[1]) for row in writes]
    assert boundaries == 3 and 2 <= len(writes) <= 3, (
        'Every engine boundary is acknowledged; terminal updates may coalesce at ten per second'
    )
    assert counts[0] == 1 and counts[-1] == 3 and counts == sorted(set(counts)), (
        'Resizing preserves truthful ordered completions and always draws the final total'
    )
    for row, count in zip(writes, counts, strict=True):
        assert len(row) <= widths[count - 1] - 1, (
            'Unicode terminal cells, including erase padding, stay before the physical wrap column'
        )
        assert '.dat' not in row, 'The completed file is displayed without its extension'
    visible = terminal_lines(text)
    saved = [line for line in visible if line.startswith('Saving project to ')]
    assert saved == ([f"Saving project to '{project}'"] if host == 'python' else []), (
        'The Python host retains its ordinary save announcement outside the progress table'
    )
    visible = [line for line in visible if line not in saved]
    assert text.count('Sequential fit:') == 1 and len(visible) == 4, (
        'Resizing redraws the heading with its values and leaves one final row without a summary'
    )
    assert 'Progress' in visible[2] and '3/3' in visible[3], (
        'The final visible heading and completed row occupy their own aligned terminal lines'
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
        label in stdout
        for label in ('Sequential fit:', 'Progress', 'Elapsed', 'Chi2 range', '█', '\r')
    ), 'Human progress projection and cursor control never enter the machine channel'
