"""Dispatch online-load cases to one production Qt host per test module."""

import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import monotonic

import pytest

ROOT = Path(__file__).resolve().parents[3]


class OnlineHost:
    def __init__(self, process, mailbox):
        self.process = process
        self.mailbox = mailbox
        self.lines = Queue()
        self.sequence = 0
        self.failed = False
        self.reader = Thread(target=self._read_output, daemon=True)
        self.reader.start()

    def _read_output(self):
        for line in self.process.stdout:
            self.lines.put(line.rstrip())
        self.lines.put(None)

    def receive(self, marker):
        output = []
        deadline = monotonic() + 30
        while (remaining := deadline - monotonic()) > 0:
            try:
                line = self.lines.get(timeout=remaining)
            except Empty:
                pytest.fail(f'The Qt host timed out waiting for {marker}: {output}')
            if line is None:
                pytest.fail(f'The Qt host exited before emitting {marker}: {output}')
            if f'qml: {marker}' in line:
                return line.split(f'qml: {marker}', 1)[1], '\n'.join(output)
            output.append(line)
        pytest.fail(f'The Qt host timed out waiting for {marker}: {output}')

    def send(self, case, tag=''):
        self.sequence += 1
        pending = self.mailbox / 'pending'
        pending.write_text(json.dumps({'id': self.sequence, 'case': case, 'tag': tag}))
        pending.replace(self.mailbox / 'request')

    def check(self, case, tag=''):
        self.send(case, tag)
        receipt, output = self.receive('ONLINE_RESULT ')
        passed = json.loads(receipt) == {'id': self.sequence, 'passed': True}
        self.failed |= not passed
        assert passed, (
            f'The production Qt case {case}/{tag} must pass with its own receipt:\n{output}'
        )


@contextmanager
def run_online_host(
    mailbox,
    *,
    load_groups_only=False,
    offline_http=False,
    failure_entries=True,
    collection_root=None,
    session_type='OnlineLoadSession',
    hover_enabled=None,
):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Online loading requires the built production Qt host'
    test_file = mailbox / 'tst_online_session.qml'
    mailbox.mkdir(parents=True, exist_ok=True)
    scratch = mailbox / 'tmp'
    scratch.mkdir(exist_ok=True)
    test_types = (ROOT / 'tests/unit/app').as_uri()
    test_file.write_text(
        f'import "{test_types}" as Online\n'
        f'Online.{session_type} {{\n'
        '    mailbox: Qt.resolvedUrl(".")\n'
        f'    loadGroupsOnly: {json.dumps(load_groups_only)}\n'
        '}\n'
    )
    fixtures = ROOT / 'tests/fixtures/online_sources'
    collection = (
        Path(collection_root) if collection_root is not None else fixtures / 'easydiffraction'
    )
    if load_groups_only and failure_entries:
        collection = mailbox / 'collection'
        shutil.copytree(fixtures / 'easydiffraction', collection)
        index = collection / 'index.json'
        values = json.loads(index.read_text())
        values['entries'].extend(json.loads((fixtures / 'failure_entries.json').read_text()))
        index.write_text(json.dumps(values))
        for name in ('corrupt.xye', 'three_points.xye'):
            shutil.copyfile(fixtures / name, collection / 'data' / name)
        shutil.copyfile(
            ROOT / 'tests/fixtures/single_crystal/fullprof/sc-neut-cwl_tbti_basic/tbti.int',
            collection / 'data/unsupported-probe.int',
        )
    cod = 'https://cod.invalid/cod' if offline_http else (mailbox / 'unreachable').as_uri()
    sources = ';'.join((
        f'cod={cod}',
        f'easydiffraction={collection.as_uri()}',
        f'easydiffraction-mirror={(mailbox / "unused-mirror").as_uri()}',
    ))
    environment = {
        **os.environ,
        'TMPDIR': str(scratch),
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'EDI_ONLINE_SOURCES': sources,
        'OMP_NUM_THREADS': '1',
    }
    if hover_enabled is not None:
        environment['QT_QUICK_CONTROLS_HOVER_ENABLED'] = '1' if hover_enabled else '0'
    command = [str(runner), '-input', str(test_file), '-o', '-,txt', '-maxwarnings', '0']
    with subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as process:
        host = OnlineHost(process, mailbox)
        try:
            host.receive('ONLINE_READY')
            yield host
            if process.poll() is None:
                host.send('stop')
                process.wait(timeout=5)
            assert host.failed or process.returncode == 0, (
                'A passing shared Qt host must exit cleanly after its final case'
            )
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            host.reader.join(timeout=5)
