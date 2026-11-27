# SPDX-License-Identifier: BSD-3-Clause
"""A pytest plugin for crysta's tests in edi's CI: a part of the files, a record without messages.

    PYTHONPATH=<edi>/tools/ci PYTEST_ADDOPTS='-p crysta_pytest' ...

CRYSTA_PYTEST_PART=k/n keeps every n-th test file of the sorted collection, starting at the k-th,
so the parts of one tier share no file and together hold all of it. CRYSTA_PYTEST_RECORD names a
file that gets one JSON line per test phase: node id, file, line, phase, outcome and seconds. It
never holds a test's message or traceback, which can quote crysta's source (ADR-0083).
"""

from __future__ import annotations

import json
import os
import pathlib
import re

import pytest

PART = re.compile(r'^([1-9][0-9]*)/([1-9][0-9]*)$')


def part() -> tuple[int, int] | None:
    """The part asked for, or None for the whole collection."""
    text = os.environ.get('CRYSTA_PYTEST_PART', '')
    if not text:
        return None
    match = PART.match(text)
    if not match or int(match[1]) > int(match[2]):
        raise pytest.UsageError(f'CRYSTA_PYTEST_PART must be k/n with 1 <= k <= n, not {text!r}')
    return int(match[1]), int(match[2])


def pytest_collection_modifyitems(config, items) -> None:
    """Keep this part's files only."""
    asked = part()
    if asked is None:
        return
    k, n = asked
    files = sorted({item.nodeid.split('::', 1)[0] for item in items})
    mine = set(files[k - 1 :: n])
    kept = [item for item in items if item.nodeid.split('::', 1)[0] in mine]
    gone = [item for item in items if item.nodeid.split('::', 1)[0] not in mine]
    if gone:
        config.hook.pytest_deselected(items=gone)
    items[:] = kept


def pytest_runtest_logreport(report) -> None:
    """One line per phase; a passed setup or teardown is left out."""
    path = os.environ.get('CRYSTA_PYTEST_RECORD')
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
    }
    with pathlib.Path(path).open('a', encoding='utf-8') as sink:
        sink.write(json.dumps(row) + '\n')
