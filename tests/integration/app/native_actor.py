"""An on-demand Qt host; setup and each row remain separately measured (ADR-0076)."""

import mmap
import os
import re
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def runner_has_method(runner, name):
    with (
        runner.open('rb') as stream,
        mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as binary,
    ):
        return binary.find(b'\x00' + name.encode() + b'\x00') >= 0


def require_pointer_driver(runner):
    assert runner.is_file(), 'Shared control acceptance requires the production Qt host'
    assert runner_has_method(runner, 'movePointer'), (
        'Shared UI acceptance requires the compiled TooltipClock pointer driver; '
        'rebuild edi_app_tests from the current test helpers before qualification'
    )


class NativeActor:
    def __init__(self, folder, file, selections):
        self.selections = selections
        self.index = 0
        self.failures = 0
        self.log_path = folder / 'native-owner-stream.txt'
        self.permit = Path(str(self.log_path) + '.permit')
        self.permit.write_text('')
        runner = ROOT / 'build/app/app/edi_app_tests'
        require_pointer_driver(runner)
        if file == 'tst_tooltip_contract.qml':
            assert runner_has_method(runner, 'armAll'), (
                'ADR-0076: competing owners require the compiled multi-popup delay clock'
            )
        self.console = (folder / 'native-console.txt').open('w')
        self.process = subprocess.Popen(
            [
                str(runner),
                '-input',
                str(ROOT / 'tests/unit/app' / file),
                *selections,
                '-o',
                str(self.log_path) + ',txt',
            ],
            stdout=self.console,
            stderr=subprocess.STDOUT,
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        )
        self.reader = None
        try:
            self._until('NATIVE_OWNER_READY ', selections[0])
        except BaseException:
            self.close()
            raise

    def _until(self, prefix, selected):
        deadline = time.monotonic() + 20
        lines = []
        while time.monotonic() < deadline:
            if self.reader is None and self.log_path.exists():
                self.reader = self.log_path.open()
            line = self.reader.readline() if self.reader else ''
            ended = self.process.poll() is not None
            if not line and ended and self.reader:
                line = self.reader.readline()
            if line:
                lines.append(line)
                if prefix is None:
                    if line.startswith(('PASS ', 'FAIL!', 'SKIP')) and selected in line:
                        return ''.join(lines)
                elif prefix in line:
                    actual = line.split(prefix, 1)[1].strip()
                    assert actual == selected, (
                        'ADR-0076: the native host must acknowledge exactly the requested row: '
                        + repr((selected, actual))
                    )
                    return ''.join(lines)
            elif ended:
                raise AssertionError(
                    'ADR-0076: the native host cannot exit before completing its selected row: '
                    + ''.join(lines)
                )
            else:
                time.sleep(0.005)
        raise AssertionError(
            'ADR-0076: the native row must finish within its bounded protocol deadline: '
            + ''.join(lines)
        )

    def run(self, selected):
        assert self.index < len(self.selections) and selected == self.selections[self.index], (
            'ADR-0076: each Python row executes its own native input once in collection order'
        )
        if self.index:
            self._until('NATIVE_OWNER_READY ', selected)
        pending = self.permit.with_suffix('.next')
        pending.write_text(selected)
        pending.replace(self.permit)
        output = self._until('NATIVE_OWNER_DONE ', selected)
        self.index += 1
        suite, rest = selected.split('::', 1)
        name, separator, tag = rest.partition(':')
        marker = f'::{suite}::{name}' + (f'({tag})' if separator else '()')
        rows = [line for line in output.splitlines() if marker in line]
        if not any(line.startswith(('PASS ', 'FAIL!', 'SKIP')) for line in rows):
            output += self._until(None, marker)
            rows = [line for line in output.splitlines() if marker in line]
        failed = any(line.startswith('FAIL!') for line in rows)
        self.failures += int(failed)
        assert not any(line.startswith('SKIP') for line in rows), (
            'ADR-0076: every requested native row executes without a skip: ' + output
        )
        assert not failed and any(line.startswith('PASS ') for line in rows), (
            'ADR-0076: the original native row passes its approved ownership assertions: ' + output
        )

    def close(self):
        complete = self.index == len(self.selections)
        try:
            if complete:
                self.process.wait(timeout=10)
            elif self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=5)
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=5)
            if self.reader:
                self.reader.close()
            self.console.close()
        if complete:
            output = self.log_path.read_text()
            totals = re.findall(r'Totals: (\d+) passed, (\d+) failed, (\d+) skipped', output)
            assert totals and tuple(map(int, totals[-1])) == (
                len(self.selections) - self.failures + 2,
                self.failures,
                0,
            ), 'ADR-0076: native totals retain every requested row and both lifecycle controls'
            assert self.process.returncode >= 0 and (
                (self.process.returncode == 0) == (self.failures == 0)
            ), 'ADR-0076: the host exit preserves its native failures and rejects crashes'


@pytest.fixture(scope='module')
def streamed_actor(request, tmp_path_factory):
    mapping = request.module.NATIVE_SELECTORS
    selected = [
        item.name
        for item in request.session.items
        if getattr(item, 'module', None) is request.module and item.name in mapping
    ]
    assert selected == [name for name in mapping if name in set(selected)], (
        'ADR-0076: native selections follow the declared Qt function and data-row order'
    )
    actor = NativeActor(
        tmp_path_factory.mktemp('native-ui-owner'),
        request.module.NATIVE_FILE,
        [mapping[name] for name in selected],
    )
    try:
        yield actor
    finally:
        actor.close()
