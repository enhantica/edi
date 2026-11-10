"""Retained scan inputs are proved before resume can change or discard them."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import edi as engine
import pytest

from tests.fixtures import phase_scan


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('history', ['all-skipped', 'fitted'])
@pytest.mark.parametrize('case', phase_scan.NOTES_CASES)
def test_native_resume_refuses_malformed_notes_and_preserves_them(tmp_path, mode, history, case):
    directory = phase_scan.retained_notes(tmp_path / 'project', engine, case, history, mode)
    notes = directory / 'analysis/scan-notes.csv'
    before = notes.read_bytes(), notes.stat().st_ino
    assert (directory / 'analysis/results.csv').exists() == (history == 'fitted'), (
        'The all-skipped resume witness has retained notes and no results, '
        'while the fitted witness exercises ordinary retained-result validation'
    )
    with pytest.raises((ValueError, RuntimeError)) as refusal:
        engine.Project.load(directory).analysis.fit()
    diagnostic = str(refusal.value)
    assert 'scan-notes.csv' in diagnostic and len(diagnostic.splitlines()) == 1, (
        'Every malformed retained notes shape must cause one explicit native resume diagnostic'
    )
    assert (notes.read_bytes(), notes.stat().st_ino) == before, (
        'Refusing damaged notes must preserve their bytes and inode, including no-results resumes'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('notes_form', ['absent', 'header', 'bare', 'qualified'])
def test_native_resume_accepts_valid_dataset_notes(tmp_path, mode, notes_form):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    notes = directory / 'analysis/scan-notes.csv'
    if notes_form != 'absent':
        text = 'file_path,negative_points,skipped_dataset,refusal\n'
        if notes_form != 'header':
            name = '01.xy' if notes_form == 'bare' else 'experiments/scan/01.xy'
            text += f'{name},0,False,\n'
        notes.write_text(text)
    engine.Project.load(directory).analysis.fit()
    assert (directory / 'analysis/results.csv').is_file(), (
        'Absent notes, a complete header and one real dataset identity must permit fitting'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('history', ['all-skipped', 'fitted'])
def test_native_resume_accepts_complete_retained_history(tmp_path, mode, history):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    if history == 'all-skipped':
        for data in (directory / 'experiments/scan').glob('*.xy'):
            data.write_text(''.join(f'{x:.17g} 0 1\n' for x in phase_scan.support.grid()))
    engine.Project.load(directory).analysis.fit()
    notes = directory / 'analysis/scan-notes.csv'
    if not notes.exists():
        notes.write_text(
            'file_path,negative_points,skipped_dataset,refusal\nexperiments/scan/01.xy,0,False,\n'
        )
    before = notes.read_bytes()
    engine.Project.load(directory).analysis.fit()
    assert notes.read_bytes() == before, (
        'A valid no-op resume must retain complete notes with and without fitted results'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('with_results', [False, True])
@pytest.mark.parametrize('kind', ['directory', 'fifo'])
def test_native_resume_refuses_nonregular_notes_without_blocking(
    tmp_path, mode, with_results, kind
):

    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    if with_results:
        engine.Project.load(directory).analysis.fit()
    notes = phase_scan.nonregular_notes(directory, kind)
    before = notes.lstat().st_ino, stat.S_IFMT(notes.lstat().st_mode)
    retained = {p.name: p.read_bytes() for p in (directory / 'analysis').iterdir() if p.is_file()}
    code = (
        'import sys; sys.meta_path[:]=[f for f in sys.meta_path '
        'if type(f).__module__!="_crysta_editable"]; '
        'import edi as engine; '
        'engine.Project.load(sys.argv[1]).analysis.fit()'
    )
    try:
        result = subprocess.run(
            [sys.executable, '-c', code, str(directory)],
            env={
                **os.environ,
                'PYTHONPATH': str(Path(engine.__file__).resolve().parents[1])
                + os.pathsep
                + os.environ.get('PYTHONPATH', ''),
            },
            capture_output=True,
            text=True,
            timeout=0.8,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail('Native resume must refuse a non-regular notes path before a FIFO open blocks')
    assert result.returncode != 0, (
        'Native resume must distinguish absence from an existing unsupported notes kind'
    )
    assert 'scan-notes.csv' in result.stderr, (
        'The native non-regular notes refusal must identify the retained input path'
    )
    assert (notes.lstat().st_ino, stat.S_IFMT(notes.lstat().st_mode)) == before, (
        'Native refusal must preserve the non-regular source path and its inode'
    )
    assert {
        p.name: p.read_bytes() for p in (directory / 'analysis').iterdir() if p.is_file()
    } == retained, 'Unsupported notes admission must refuse before any analysis output is written'
    if kind == 'directory':
        assert (notes / 'keep').read_text() == 'retained source state\n', (
            'Refusing a notes directory must preserve its retained contents'
        )


@pytest.fixture(scope='module')
def complete_results_history(tmp_path_factory):
    """Reuse immutable complete history; timed node work is only the boundary under test."""
    root = tmp_path_factory.mktemp('complete-results-history')
    histories = {}
    for mode in ('sequential', 'independent'):
        directory = phase_scan.materialize(root / mode, mode)
        engine.Project.load(directory).analysis.fit()
        histories[mode] = directory
    return histories


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('filename', ['results.csv', 'results-provenance.csv'])
@pytest.mark.parametrize('kind', ['directory', 'fifo', 'absent', 'symlink'])
def test_native_results_state_distinguishes_absence_regular_and_unsupported(
    tmp_path, complete_results_history, mode, filename, kind
):
    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = tmp_path / 'project'
    if kind == 'absent' and filename == 'results.csv':
        phase_scan.materialize(directory, mode)
    else:
        shutil.copytree(complete_results_history[mode], directory)
    state = phase_scan.scan_state_path(directory, filename, kind)
    before = state.lstat() if kind != 'absent' else None
    code = (
        'import sys; sys.meta_path[:]=[f for f in sys.meta_path '
        'if type(f).__module__!="_crysta_editable"]; '
        'import edi as engine; engine.Project.load(sys.argv[1]).analysis.fit()'
    )
    try:
        result = subprocess.run(
            [sys.executable, '-c', code, str(directory)],
            env={
                **os.environ,
                'PYTHONPATH': str(Path(engine.__file__).resolve().parents[1])
                + os.pathsep
                + os.environ.get('PYTHONPATH', ''),
            },
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail('Native state admission must refuse unsupported paths before a blocking open')
    if kind in {'absent', 'symlink'}:
        assert result.returncode == 0, (
            'Genuine absence and regular symlinks must remain supported scan state: '
            + result.stderr
        )
    else:
        assert result.returncode != 0, 'Native admission must refuse unsupported results state'
        assert filename in result.stderr, (
            'Native admission must diagnose unsupported results/provenance paths'
        )
        assert (state.lstat().st_ino, stat.S_IFMT(state.lstat().st_mode)) == (
            before.st_ino,
            stat.S_IFMT(before.st_mode),
        ), 'A refused results-state input must retain its inode and file kind'
        if kind == 'directory':
            assert (state / 'keep').read_text() == 'retained source state\n', (
                'Results-state refusal must preserve an existing directory and its contents'
            )
