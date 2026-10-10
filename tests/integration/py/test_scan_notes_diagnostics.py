"""Malformed retained notes must produce one explicit CLI diagnostic."""

import os
import stat
import subprocess
import sys
from pathlib import Path

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


@pytest.mark.parametrize('surface', ['core', 'report', 'fit', 'dry'])
@pytest.mark.parametrize('kind', ['directory', 'fifo'])
def test_nonregular_notes_refuse_on_core_reporting_and_cli(tmp_path, surface, kind):

    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = phase_scan.materialize(tmp_path / 'project')
    (directory / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name notes_boundary\n'
    )
    notes = phase_scan.nonregular_notes(directory, kind)
    before = notes.lstat().st_ino, stat.S_IFMT(notes.lstat().st_mode)
    retained = {p.name: p.read_bytes() for p in (directory / 'analysis').iterdir() if p.is_file()}
    if surface in {'fit', 'dry'}:
        args = [sys.executable, '-m', 'edi', 'fit', str(directory), '--report', 'machine']
        if surface == 'dry':
            args.append('--dry')
    else:
        action = 'project._scan_notes()' if surface == 'core' else 'print(_skipped_line(project))'
        code = (
            'import edi,sys; from edi.__main__ import _skipped_line; '
            'project=edi.Project.load(sys.argv[1]); ' + action
        )
        args = [sys.executable, '-c', code, str(directory)]
    try:
        result = subprocess.run(
            args,
            env={
                **os.environ,
                'PYTHONPATH': str(Path(edi.__file__).resolve().parents[1])
                + os.pathsep
                + os.environ.get('PYTHONPATH', ''),
            },
            capture_output=True,
            text=True,
            timeout=0.8,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail('Core and CLI must refuse unsupported notes kinds before a FIFO open blocks')
    assert 'scan-notes.csv' in result.stdout + result.stderr, (
        'Every notes reader must name the existing unsupported retained notes path'
    )
    if surface != 'report':
        assert result.returncode != 0, (
            'Core and actual real/dry CLI fitting must refuse unsupported retained notes paths'
        )
    assert (notes.lstat().st_ino, stat.S_IFMT(notes.lstat().st_mode)) == before, (
        'Core and real/dry CLI refusal must preserve the original unsupported path'
    )
    assert {
        p.name: p.read_bytes() for p in (directory / 'analysis').iterdir() if p.is_file()
    } == retained, (
        'Real and dry CLI admission must refuse before changing any original analysis state'
    )
    if kind == 'directory':
        assert (notes / 'keep').read_text() == 'retained source state\n', (
            'Dry-run seeding must not discard or alter an existing notes directory'
        )
