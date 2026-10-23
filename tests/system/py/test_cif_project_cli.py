"""The CLI project loader follows the same published structure CIF path."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_cli_project_loads_a_published_cif_and_reports_its_cell_atoms_and_symmetry(tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    (source / 'structures/phase.edi').unlink()
    shutil.copyfile(
        ROOT / 'tests/fixtures/dictionary_display/published_cod_1000236.cif',
        source / 'structures/phase.cif',
    )
    destination = tmp_path / 'report.html'
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'report', str(source), '--output', str(destination)],
        env={
            **os.environ,
            'PYTHONPATH': str(ROOT / 'lib') + os.pathsep + os.environ.get('PYTHONPATH', ''),
        },
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, (
        'The real CLI project entrance loads its structure from a published CIF: ' + result.stderr
    )
    html = destination.read_text()
    assert '10.257' in html, 'The CLI report retains the published COD cell length'
    assert 'Ca1' in html and 'F3' in html, 'The CLI report retains the published COD atom rows'
    assert 'I 21 3' in html, 'The CLI report retains the published COD space group'
