"""Malformed retained notes must produce one explicit CLI diagnostic."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import edi
import pytest
from edi.__main__ import _skipped_line  # noqa: PLC2701 - exercise the actual CLI reader

from tests.fixtures import phase_scan
from tests.integration.py.test_scan_notes_resume import complete_results_history as history_fixture


@pytest.fixture(scope='module')
def complete_results_history(tmp_path_factory):
    return history_fixture.__wrapped__(tmp_path_factory)


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


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('filename', ['results.csv', 'results-provenance.csv'])
@pytest.mark.parametrize('kind', ['directory', 'fifo', 'absent', 'symlink'])
@pytest.mark.parametrize('surface', ['core', 'report', 'events', 'dry-events'])
def test_results_state_readers_prove_the_supported_kind(
    tmp_path, complete_results_history, mode, filename, kind, surface
):
    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = tmp_path / 'project'
    if kind == 'absent' and filename == 'results.csv':
        phase_scan.materialize(directory, mode)
    else:
        shutil.copytree(complete_results_history[mode], directory)
    phase_scan.scan_state_path(directory, filename, kind)
    before = phase_scan.scan_state_fingerprint(directory)
    actions = {
        'core': 'print(project._scan_notes())',
        'report': 'print(_skipped_line(project))',
        'events': 'project.analysis.fit(on_scan_start=lambda _: print("PREAMBLE", flush=True))',
        'dry-events': (
            'project._dry_run_into(sys.argv[2]); '
            'project.analysis.fit(on_scan_start=lambda _: print("PREAMBLE", flush=True))'
        ),
    }
    code = (
        'import edi,sys; from edi.__main__ import _skipped_line; '
        'project=edi.Project.load(sys.argv[1]); ' + actions[surface]
    )
    try:
        result = subprocess.run(
            [sys.executable, '-c', code, str(directory), str(tmp_path / 'dry')],
            env={
                **os.environ,
                'PYTHONPATH': str(Path(edi.__file__).resolve().parents[1])
                + os.pathsep
                + os.environ.get('PYTHONPATH', ''),
            },
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail('State readers must refuse unsupported paths before a FIFO open blocks')
    if kind in {'absent', 'symlink'}:
        assert result.returncode == 0, (
            'Absence and regular symlinks remain valid for every results-state reader: '
            + result.stderr
        )
        assert 'cannot read' not in result.stdout, (
            'Valid state controls must not emit a results-state refusal'
        )
    else:
        assert filename in result.stdout + result.stderr, (
            'Every results/provenance reader must identify the unsupported persisted-state path'
        )
        if surface != 'report':
            assert result.returncode != 0, (
                'Core and event-enabled real/dry scans must refuse unsupported results state'
            )
        assert 'PREAMBLE' not in result.stdout, (
            'A scan must prove supported retained state before publishing a preamble'
        )
        assert phase_scan.scan_state_fingerprint(directory) == before, (
            'State refusal and dry-run seeding must retain every analysis entry'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('kind', ['directory', 'fifo'])
def test_event_termination_reader_refuses_a_replaced_provenance_path(tmp_path, mode, kind):
    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    code = """
import edi, os, sys
from pathlib import Path
project = edi.Project.load(sys.argv[1])
state = Path(sys.argv[1]) / 'analysis/results-provenance.csv'
injected = False
def replace(_):
    global injected
    if not injected:
        state.rename(state.with_name('provenance.retained'))
        if sys.argv[2] == 'fifo':
            os.mkfifo(state)
        else:
            state.mkdir()
        injected = True
        print('INJECTED', flush=True)
project.analysis.fit(on_scan_start=lambda _: None, on_iteration=replace,
                     on_file_complete=lambda _: print(
                         'ADOPTED-AFTER' if injected else 'BEFORE', flush=True))
"""
    try:
        result = subprocess.run(
            [sys.executable, '-c', code, str(directory), kind],
            env={
                **os.environ,
                'PYTHONPATH': str(Path(edi.__file__).resolve().parents[1])
                + os.pathsep
                + os.environ.get('PYTHONPATH', ''),
            },
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            'The live termination reader must refuse a replaced provenance FIFO before opening it'
        )
    assert 'INJECTED' in result.stdout, (
        'A real iteration must replace provenance after native preflight and stream creation'
    )
    assert result.returncode != 0 and 'results-provenance.csv' in result.stderr, (
        'The termination reader must diagnose unsupported provenance after writes'
    )
    assert 'ADOPTED-AFTER' not in result.stdout, (
        'Unsupported live provenance must refuse before publishing a completed file record'
    )
