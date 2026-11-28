# SPDX-License-Identifier: BSD-3-Clause
"""A pytest plugin for crysta's tests in edi's CI: a part of the files, a record without messages.

    PYTHONPATH=<edi>/tools/ci PYTEST_ADDOPTS='-p crysta_pytest' ...

CRYSTA_PYTEST_FOLDER=tests/system/ keeps the files under that folder and !tests/system/ the rest.
CRYSTA_PYTEST_PART=k/n then keeps every n-th test file of the sorted collection, starting at the
k-th, so the parts share no file and together hold all of it. CRYSTA_PYTEST_RECORD names a
file that gets one JSON line per test phase: node id, file, line, phase, outcome and seconds. It
never holds a test's message or traceback, which can quote crysta's source (ADR-0083), only the
class of a failure's exception.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from collections.abc import Generator
from typing import Any

import pytest

PART = re.compile(r'^([1-9][0-9]*)/([1-9][0-9]*)$')
HERE = pathlib.Path(__file__).resolve().parent


def _elsewhere(entry: str) -> bool:
    return bool(entry) and pathlib.Path(entry).resolve() != HERE


# pytest has read its options when it loads this plugin. crysta's tests start pytest themselves,
# and such a run must not inherit this one's options, part or record, nor find edi's scripts first.
ASKED = {
    name: os.environ.pop(name, '')
    for name in ('CRYSTA_PYTEST_FOLDER', 'CRYSTA_PYTEST_PART', 'CRYSTA_PYTEST_RECORD')
}
os.environ.pop('PYTEST_ADDOPTS', None)
if kept := os.pathsep.join(filter(_elsewhere, os.environ.pop('PYTHONPATH', '').split(os.pathsep))):
    os.environ['PYTHONPATH'] = kept
sys.path[:] = [entry for entry in sys.path if not entry or _elsewhere(entry)]
# crysta's tools take the repository they work on from GitHub's variable, which names edi here.
os.environ['GITHUB_REPOSITORY'] = 'enhantica/crysta'


def part() -> tuple[int, int] | None:
    """The part asked for, or None for the whole collection."""
    text = ASKED['CRYSTA_PYTEST_PART']
    if not text:
        return None
    match = PART.match(text)
    if not match or int(match[1]) > int(match[2]):
        raise pytest.UsageError(f'CRYSTA_PYTEST_PART must be k/n with 1 <= k <= n, not {text!r}')
    return int(match[1]), int(match[2])


def in_folder(file: str) -> bool:
    """Whether a test file is in the folder asked for (all are when none is)."""
    folder = ASKED['CRYSTA_PYTEST_FOLDER']
    if folder.startswith('!'):
        return not file.startswith(folder[1:])
    return file.startswith(folder)


def pytest_collection_modifyitems(config, items) -> None:
    """Keep this folder's and this part's files only."""
    asked = part()
    files = sorted({item.nodeid.split('::', 1)[0] for item in items})
    files = [file for file in files if in_folder(file)]
    k, n = asked or (1, 1)
    mine = set(files[k - 1 :: n])
    kept = [item for item in items if item.nodeid.split('::', 1)[0] in mine]
    gone = [item for item in items if item.nodeid.split('::', 1)[0] not in mine]
    if gone:
        config.hook.pytest_deselected(items=gone)
    items[:] = kept


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(call) -> Generator[None, Any, None]:
    """Keep the class of a failure's exception; its message can quote crysta's source."""
    outcome = yield
    outcome.get_result().crysta_error = call.excinfo.typename if call.excinfo else None


def pytest_runtest_logreport(report) -> None:
    """One line per phase; a passed setup or teardown is left out."""
    path = ASKED['CRYSTA_PYTEST_RECORD']
    if not path or (report.when != 'call' and report.passed):
        return
    file, line, _ = report.location
    row = {
        'nodeid': report.nodeid,
        'file': file,
        'line': None if line is None else line + 1,
        'when': report.when,
        'outcome': report.outcome,
        'seconds': round(report.duration, 3),
        'error': getattr(report, 'crysta_error', None) if report.failed else None,
    }
    with pathlib.Path(path).open('a', encoding='utf-8') as sink:
        sink.write(json.dumps(row) + '\n')
