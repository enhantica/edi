"""Retained scan inputs are proved before resume can change or discard them."""

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
