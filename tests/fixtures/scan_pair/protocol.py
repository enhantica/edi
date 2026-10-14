"""Read actual normal-app events and time commands on the caller's monotonic clock."""

import hashlib
import json
import os
import selectors
import subprocess
import time
from collections import deque
from contextlib import ExitStack
from pathlib import Path

from tests.fixtures.fast_ci.processes import stop_observer_tree


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bundle(path):
    path = Path(path).resolve()
    receipt = json.loads((path / 'receipt.json').read_text())
    if receipt.get('schema') != 1 or receipt.get('kind') != 'normal-app':
        raise ValueError('The scan measurement requires a delivered normal-app build receipt')
    executable = path / 'edi_app'
    if receipt.get('binary_sha256') != digest(executable):
        raise ValueError('The measured app must match its build receipt binary hash')
    return executable, receipt


class App:
    def __init__(self, executable, project, operation, environment, log, timeout=180):
        self.project = Path(project).resolve()
        self.deadline = time.monotonic() + timeout
        self.resources = ExitStack()
        self.stderr = self.resources.enter_context(Path(log).open('wb'))  # noqa: SIM115 — spans the app process
        self.process = subprocess.Popen(
            [
                'pixi',
                'run',
                '--as-is',
                '-e',
                'app',
                str(executable),
                '--test-observer',
                'scan-cycle',
                str(self.project),
                operation,
            ],
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            start_new_session=True,
            bufsize=0,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.pending = deque()
        self.events = []

    def send(self, command, nonce):
        sent = time.monotonic_ns()
        self.process.stdin.write(json.dumps({'command': command, 'nonce': nonce}).encode() + b'\n')
        self.process.stdin.flush()
        return sent

    def receive(self):
        while not self.pending:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise TimeoutError('The normal app did not finish its scan/reset observation')
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                raise ValueError('The normal app exited before publishing the required boundary')
            self.buffer += data
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                if line.startswith(b'{'):
                    self.pending.append(json.loads(line))
        event = self.pending.popleft()
        received = time.monotonic_ns()
        if event.get('project') != str(self.project):
            raise ValueError('Every app event must belong to the supplied measured project')
        self.events.append(dict(event, received_ns=received))
        return event, received

    def until(self, kind, nonce=None):
        while True:
            event, received = self.receive()
            if nonce is not None and event.get('nonce') != nonce:
                raise ValueError('The observed boundary must acknowledge this actual command')
            if event.get('event') == 'error':
                raise ValueError(str(event.get('error', 'The app refused the observation')))
            if event.get('event') == kind:
                return event, received

    def close(self):
        if self.process.poll() is None:
            stop_observer_tree(self.process)
        self.selector.close()
        self.resources.close()
