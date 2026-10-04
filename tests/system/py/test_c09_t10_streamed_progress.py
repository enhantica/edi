"""Hidden  gates for edi's live human and machine progress surfaces."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import edi
import edi.__main__ as cli

from conftest import corpus_case_dir

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]
JOINT_FIXTURE = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption'


# Resolved LAZILY - see above: an import-time call breaks collection for the whole suite.
def _joint_project() -> Path:
    return corpus_case_dir('ncaf-wish-3bank-s5') / 'project'


JOINT_ORACLE = JOINT_FIXTURE / 'crysta_cli_joint_fit.json'
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')
ELAPSED = re.compile(r'[+-]?\d+\.\d{3}')
PROGRESS_KEYS = ('schema', 'record', 'iter', 'rwp', 'reduced_chi_square', 'elapsed_ms')


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment['OMP_DYNAMIC'] = 'FALSE'
    environment['OMP_NUM_THREADS'] = '2'
    return environment


def _run_edi(*arguments: str, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, '-m', 'edi', *arguments],
        cwd=ROOT,
        env=_environment(),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed


def _split_records(text: str) -> list[str]:
    assert text.endswith('\n'), 'machine records must be newline-terminated'
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line == 'schema=8']
    assert starts, text
    assert starts[0] == 0, text
    starts.append(len(lines))
    return ['\n'.join(lines[start:stop]) + '\n' for start, stop in pairwise(starts)]


def _parse_record(text: str) -> tuple[list[str], dict[str, str]]:
    keys: list[str] = []
    values: dict[str, str] = {}
    for line in text.splitlines():
        assert '=' in line, line
        key, value = line.split('=', maxsplit=1)
        assert key, line
        assert value, line
        assert key not in values, line
        keys.append(key)
        values[key] = value
    assert keys[:2] == ['schema', 'record']
    assert values['schema'] == '8', (
        "the _parse_record requirement must hold: values['schema'] == '8'"
    )
    return keys, values


def _new_iteration(
    edi: Any,
    iteration: int,
    rwp: float,
    reduced_chi_square: float,
) -> Any:
    record = edi.IterationRecord()
    record.iteration = iteration
    record.rwp = rwp
    record.reduced_chi_square = reduced_chi_square
    return record


def test_c09_t10_surviving_core_formats_keep_nontrivial_iteration_change() -> None:
    required = (
        'FitPreamble',
        'stream_header',
        'summary_line',
        'parameter_table',
        'progress_report',
    )
    assert all(hasattr(edi, name) for name in required), ' core formatters are not bound'

    pre_fit = _new_iteration(edi, 0, 0.2222, 24.2159)
    preamble = edi.FitPreamble()
    preamble.pre_fit = pre_fit

    header = edi.stream_header(preamble, 'demo')
    assert header.splitlines() == [
        'edi fit: project demo, 0 pts fitted / 0 loaded, 0 free',
        '   iter   time (s)       Rwp          χ²   change',
        '                      0.2222     24.2159',
    ], 'the stream header must preserve its three-line core format'

    first = _new_iteration(edi, 1, 0.1811, 16.8435)
    second = _new_iteration(edi, 2, 0.1520, 11.8646)
    first_line = edi.iteration_line(first, pre_fit.reduced_chi_square)
    second_line = edi.iteration_line(second, first.reduced_chi_square)
    # Closed forms, independently hand-computed from the fixed reduced-chi-square sequence:
    # |16.8435-24.2159|/24.2159 = 30.4%; |11.8646-16.8435|/16.8435 = 29.6%.
    assert first_line.endswith('30.4% ↓'), 'the first iteration must report change from pre-fit'
    assert second_line.endswith('29.6% ↓'), (
        'the second iteration must report change from its predecessor'
    )
    assert re.fullmatch(r'\s*1\s+0\.00\s+0\.1811\s+16\.8435\s+30\.4% ↓', first_line), (
        'the first iteration line must retain its core columns'
    )

    progress = edi.progress_report(first)
    assert progress == (
        'schema=8\nrecord=progress\niter=1\nrwp=0.1811\n'
        'reduced_chi_square=16.8435\nelapsed_ms=0.000\n'
    ), 'the progress record must preserve its machine-readable schema'


class _FlushSpy:
    def __init__(self) -> None:
        self.pending = ''
        self.chunks: list[str] = []

    def write(self, text: str) -> int:
        self.pending += text
        return len(text)

    def flush(self) -> None:
        if self.pending:
            self.chunks.append(self.pending)
            self.pending = ''


def test_c09_t10_human_cli_flushes_each_injected_callback_before_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    rows = [
        SimpleNamespace(iteration=1, reduced_chi_square=16.8435),
        SimpleNamespace(iteration=2, reduced_chi_square=11.8646),
    ]
    preamble = SimpleNamespace(pre_fit=SimpleNamespace(reduced_chi_square=24.2159))

    class FakeProject:
        fitting_mode = 'single'

        @property
        def analysis(self) -> FakeProject:
            return self

        def fit(self, *, on_iteration: Any, on_start: Any) -> Any:
            assert self.fitting_mode == 'single'
            events.append('fit-enter')
            on_start(preamble)
            events.append('after-start')
            for row in rows:
                on_iteration(row)
                events.append(f'after-{row.iteration}')
            events.append('fit-return')
            return SimpleNamespace()

    class FakeProjectType:
        @staticmethod
        def load(_path: str) -> FakeProject:
            return FakeProject()

    monkeypatch.setattr(cli.edi, 'Project', FakeProjectType)
    monkeypatch.setattr(cli.edi, 'stream_header', lambda _p, _name: 'HEADER\n')
    monkeypatch.setattr(cli.edi, 'iteration_line', lambda row, _previous: f'ROW {row.iteration}')
    monkeypatch.setattr(cli.edi, 'summary_line', lambda _outcome: 'SUMMARY\n')
    monkeypatch.setattr(cli.edi, 'parameter_table', lambda _outcome: 'PARAMETERS\n')
    spy = _FlushSpy()
    monkeypatch.setattr(cli.sys, 'stdout', spy)

    args = argparse.Namespace(
        project='demo',
        report='human',
        verbosity='compact',
        stream=False,
        dry=True,
    )
    assert cli.run_fit(args) == 0
    spy.flush()
    assert spy.chunks == ['HEADER\n', 'ROW 1\n', 'ROW 2\n', 'SUMMARY\n']
    assert events == [
        'fit-enter',
        'after-start',
        'after-1',
        'after-2',
        'fit-return',
    ]


def _streamed_joint_fit() -> list[tuple[list[str], dict[str, str]]]:
    completed = _run_edi(
        'fit',
        str(_joint_project()),
        '--dry',
        '--report',
        'machine',
        '--stream',
        '--verbosity',
        'full',
    )
    assert not completed.stderr
    return [_parse_record(record) for record in _split_records(completed.stdout)]
