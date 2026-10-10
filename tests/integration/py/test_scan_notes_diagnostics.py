"""Malformed retained notes must produce one explicit CLI diagnostic."""

import edi
import pytest
from edi.__main__ import _skipped_line  # noqa: PLC2701 - exercise the actual CLI reader

from tests.fixtures import phase_scan


@pytest.mark.parametrize('count', ['1.5', '18446744073709551616', '-1', 'torn', 'duplicate'])
def test_cli_reports_malformed_notes_once(tmp_path, count):
    directory = phase_scan.materialize(tmp_path / 'project')
    row = f'experiments/scan/01.xy,{count},True,\n'
    if count == 'torn':
        row = 'experiments/scan/01.xy,1,True,'
    elif count == 'duplicate':
        row = 'experiments/scan/01.xy,1,True,\n' * 2
    (directory / 'analysis/scan-notes.csv').write_text(
        'file_path,negative_points,skipped_dataset,refusal\n' + row
    )
    diagnostic = _skipped_line(edi.Project.load(directory))
    assert len(diagnostic.splitlines()) == 1, (
        'The CLI must emit one malformed-notes diagnostic, never truncate or omit bad counts'
    )
    assert 'scan-notes.csv' in diagnostic and ('cannot' in diagnostic or 'not' in diagnostic), (
        'The CLI diagnostic must identify the unreadable retained notes and explain their refusal'
    )
