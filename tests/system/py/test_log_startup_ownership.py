"""Real processes meet at the ordinary same-timestamp log-start boundary."""

import json
import selectors
import subprocess
from contextlib import contextmanager
from pathlib import Path

from tests.system.py import test_onboarding_logging as logging_contract

logger_binary = logging_contract.logger_binary
invoke = logging_contract.invoke


@contextmanager
def held(binary, tmp_path, directory, operation, sentinel):
    directory.mkdir(parents=True, exist_ok=True)
    request = tmp_path / (sentinel + '.json')
    request.write_text(
        json.dumps({
            'directory': str(directory),
            'time': '2026-07-18T09:41:26.125+02:00',
            'header': {'app': 'independent ownership input'},
            'operation': operation,
            'sentinel': sentinel,
        }),
        encoding='utf-8',
    )
    process = subprocess.Popen(
        [str(binary), str(request)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            process.stdin.write('xx')
            process.stdin.flush()
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=3)


def receive(process):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        assert selector.select(timeout=3), (
            'The log owner reaches its declared IPC boundary promptly'
        )
    line = process.stdout.readline()
    assert line, 'The log process supplies a real ownership observation before exiting'
    return json.loads(line)


def release(process):
    process.stdin.write('x')
    process.stdin.flush()


def test_reserved_marker_before_log_creation_never_grants_another_run_ownership(
    logger_binary, tmp_path
):
    # Accident: a second launch arrives after the first reserves its marker, before its log open.
    directory = tmp_path / 'logs'
    with held(logger_binary, tmp_path, directory, 'reserve-slot', 'first') as owner:
        first = receive(owner)
        assert not Path(first['reserved']).exists(), (
            'The exercised collision window has an owned marker and no log file yet'
        )
        with held(logger_binary, tmp_path, directory, 'hold', 'second-run') as contender:
            second = receive(contender)
            release(owner)
            assert receive(owner)['written'], 'The first owner finishes opening its reserved file'
            first_bytes = Path(first['reserved']).read_text(encoding='utf-8')
            second_bytes = Path(second['path']).read_text(encoding='utf-8')
            violations = []
            if first['reserved'] == second['path']:
                violations.append('different live owners selected the same log')
            if second['owner_pid'] != contender.pid:
                violations.append('the second run does not own its crash marker')
            if first_bytes != 'first-run-owned-bytes\n':
                violations.append('the first owner lost its bytes')
            if 'second-run' not in second_bytes:
                violations.append('the second owner lost its bytes')
            assert not violations, (
                'A failed filename-lock acquisition never opens or truncates another run: '
                + str(violations)
            )


def test_two_simultaneous_launches_keep_separate_logs_markers_and_three_retained_runs(
    logger_binary, tmp_path
):
    # Accident: two app shortcuts launch in the same timestamp while older normal logs exist.
    directory = tmp_path / 'logs'
    for day in [11, 12, 13]:
        invoke(logger_binary, directory, f'2026-07-{day}T09:41:26.125+02:00')
    with (
        held(logger_binary, tmp_path, directory, 'coordinated', 'first-run') as first,
        held(logger_binary, tmp_path, directory, 'coordinated', 'second-run') as second,
    ):
        assert receive(first)['ready'] and receive(second)['ready'], (
            'Both app processes are alive before either starts the same-timestamp log'
        )
        release(first)
        release(second)
        one, two = receive(first), receive(second)
        paths = {Path(one['path']), Path(two['path'])}
        violations = []
        if len(paths) != 2:
            violations.append('simultaneous launches share one file')
        for result, process, sentinel in [
            (one, first, 'first-run'),
            (two, second, 'second-run'),
        ]:
            if result['owner_pid'] != process.pid:
                violations.append('a log has no marker owned by its own process')
            text = Path(result['path']).read_text(encoding='utf-8')
            if text.count(sentinel) != 1:
                violations.append('a live run lost or duplicated its own message')
            other = 'second-run' if sentinel == 'first-run' else 'first-run'
            if other in text:
                violations.append('another live run wrote into this log')
        assert not violations, (
            'Every simultaneous run retains separate bytes and its own crash marker: '
            + str(violations)
        )
    latest = invoke(logger_binary, directory, '2026-07-19T09:41:26.125+02:00')
    assert set(directory.glob('session-*.log')) == paths | {Path(latest['path'])}, (
        'Rotation retains the two completed concurrent runs and the new run, exactly three'
    )
    assert not latest['crashed'], 'Completed concurrent runs are not falsely reported as crashed'
