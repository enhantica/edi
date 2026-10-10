"""Malformed retained notes must produce one explicit CLI diagnostic."""

import os
import subprocess
import sys

import edi
import pytest
from edi.__main__ import _skipped_line  # noqa: PLC2701 - exercise the actual CLI reader

from tests.fixtures import phase_scan


@pytest.mark.parametrize('count', phase_scan.NOTES_CASES)
def test_cli_reports_malformed_notes_once(tmp_path, count):
    directory = phase_scan.materialize(tmp_path / 'project')
    (directory / 'analysis/scan-notes.csv').write_text(phase_scan.malformed_notes(count))
    diagnostic = _skipped_line(edi.Project.load(directory))
    assert len(diagnostic.splitlines()) == 1, (
        'The CLI must emit one malformed-notes diagnostic, never truncate or omit bad counts'
    )
    assert 'scan-notes.csv' in diagnostic and ('cannot' in diagnostic or 'not' in diagnostic), (
        'The CLI diagnostic must identify the unreadable retained notes and explain their refusal'
    )


@pytest.mark.parametrize('report', ['machine', 'human'])
@pytest.mark.parametrize('dry', [False, True])
@pytest.mark.parametrize('case', phase_scan.NOTES_CASES)
def test_cli_fit_refuses_no_results_notes_before_writing(tmp_path, report, dry, case):
    directory = phase_scan.retained_notes(tmp_path / 'project', edi, case, 'all-skipped')
    (directory / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name notes_boundary\n'
    )
    notes = directory / 'analysis/scan-notes.csv'
    before = notes.read_bytes(), notes.stat().st_ino
    args = [sys.executable, '-m', 'edi', 'fit', str(directory), '--report', report]
    if dry:
        args.append('--dry')
    result = subprocess.run(
        args, env=dict(os.environ), capture_output=True, text=True, timeout=5, check=False
    )
    assert result.returncode != 0, (
        'Actual CLI fitting, including dry runs, must refuse malformed notes without results: '
        + result.stdout
        + result.stderr
    )
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(lines) == 1 and 'scan-notes.csv' in lines[0], (
        'The actual CLI must name damaged retained notes in one explicit diagnostic'
    )
    assert (notes.read_bytes(), notes.stat().st_ino) == before, (
        'Both real and dry CLI refusal must preserve retained no-results notes exactly'
    )


@pytest.mark.parametrize('report', ['machine', 'human'])
@pytest.mark.parametrize('dry', [False, True])
def test_cli_accepts_valid_all_skipped_resume(tmp_path, report, dry):
    directory = phase_scan.materialize(tmp_path / 'project')
    (directory / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name notes_boundary\n'
    )
    for data in (directory / 'experiments/scan').glob('*.xy'):
        data.write_text(''.join(f'{x:.17g} 0 1\n' for x in phase_scan.support.grid()))
    edi.Project.load(directory).analysis.fit()
    notes = directory / 'analysis/scan-notes.csv'
    before = notes.read_bytes()
    args = [sys.executable, '-m', 'edi', 'fit', str(directory), '--report', report]
    if dry:
        args.append('--dry')
    result = subprocess.run(
        args, env=dict(os.environ), capture_output=True, text=True, timeout=5, check=False
    )
    assert result.returncode == 0, (
        'Actual real and dry CLI fitting must accept complete valid all-skipped retained notes: '
        + result.stdout
        + result.stderr
    )
    assert notes.read_bytes() == before, (
        'A valid all-skipped no-op resume must retain its complete notes, including dry runs'
    )
