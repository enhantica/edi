"""Guard real process entry points before any private app compilation starts."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path

from tests.fixtures.fast_ci.policy import app_build_sites, app_command, command_tokens


@contextmanager
def process_guard(root):
    root = Path(root)
    checked_helpers = {}
    state = {'active': True, 'launched': [], 'blocked': []}
    transport = tempfile.TemporaryDirectory(prefix='edi-pr-child-guard-')
    bootstrap = Path(transport.name)
    process_log = bootstrap / 'processes.jsonl'
    process_log.write_text('')
    (bootstrap / 'sitecustomize.py').write_text(
        'import os, runpy\nrunpy.run_path(os.environ["EDI_GATE_CHILD"]) ["install"]()\n'
    )
    injected = {
        'EDI_GATE_ROOT': str(root),
        'EDI_GATE_PROCESS_LOG': str(process_log),
        'EDI_GATE_CHILD': str(Path(__file__).with_name('child_guard.py')),
        'PYTHONPATH': str(bootstrap) + ':' + str(root) + ':' + os.environ.get('PYTHONPATH', ''),
    }
    previous = {key: os.environ.get(key) for key in injected}
    os.environ.update(injected)

    def helper_builds(word):
        helper = Path(word) if Path(word).is_absolute() else root / word
        if helper not in checked_helpers:
            checked_helpers[helper] = helper.is_file() and bool(
                app_build_sites(root, entrypoints=[helper])
            )
        return checked_helpers[helper]

    original_popen = subprocess.Popen

    def guarded_popen(*args, **kwargs):
        if kwargs.get('env') is not None:
            kwargs['env'] = {**kwargs['env'], **injected}
        return original_popen(*args, **kwargs)

    subprocess.Popen = guarded_popen

    def audit(event, args):
        if not state['active'] or event not in {
            'subprocess.Popen',
            'os.system',
            'os.exec',
            'os.spawn',
            'os.posix_spawn',
        }:
            return
        argv = (
            args[1]
            if event in {'subprocess.Popen', 'os.exec', 'os.spawn', 'os.posix_spawn'}
            else args[0]
        )
        if isinstance(argv, bytes):
            argv = argv.decode()
        words = (
            [str(word) for word in argv]
            if isinstance(argv, (tuple, list))
            else command_tokens(argv)
        )
        state['launched'].append(words)
        if app_command(words) or any(
            helper_builds(word) for word in words if word.endswith(('.mjs', '.sh'))
        ):
            state['blocked'].append(words)
            raise RuntimeError('A PR fixture attempted a private app build before execution')

    sys.addaudithook(audit)
    try:
        yield state
    finally:
        state['active'] = False
        subprocess.Popen = original_popen
        for line in process_log.read_text().splitlines():
            record = json.loads(line)
            state['launched'].append(record['argv'])
            if record['blocked']:
                state['blocked'].append(record['argv'])
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        transport.cleanup()


def process_family(pid):
    command = [shutil.which('ps'), '-axo', 'pid=,ppid=']
    result = subprocess.run(command, capture_output=True, text=True, timeout=1, check=True)
    parents = {int(row.split()[0]): int(row.split()[1]) for row in result.stdout.splitlines()}
    family = {pid}
    while True:
        larger = family | {child for child, parent in parents.items() if parent in family}
        if larger == family:
            return family
        family = larger


def observer_processes(process):
    argv = list(process.args)
    if '--test-observer' not in argv:
        return set()
    index = argv.index('--test-observer')
    binary, project = str(argv[index - 1]), str(argv[index + 2])
    result = subprocess.run(
        [shutil.which('ps'), '-axo', 'pid=,command='],
        capture_output=True,
        text=True,
        check=True,
        timeout=1,
    )
    owned = set()
    for line in result.stdout.splitlines():
        pid, _, text = line.strip().partition(' ')
        words = command_tokens(text)
        if binary in words and project in words and '--test-observer' in words:
            owned.add(int(pid))
    return owned


def stop_observer_tree(process):
    # Enumerate before killing pixi, while parentage still proves ownership. Stop
    # each generation first so descendants cannot fork or become orphaned mid-walk.
    family = {process.pid} | observer_processes(process)
    for _ in range(3):
        for pid in family:
            with suppress(ProcessLookupError):
                os.kill(pid, signal.SIGSTOP)
        expanded = process_family(process.pid)
        if expanded <= family:
            break
        family |= expanded
    for pid in family - {process.pid}:
        with suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)
    with suppress(ProcessLookupError):
        os.kill(process.pid, signal.SIGCONT)
    try:
        process.communicate(timeout=0.3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=2)
    return family
