"""Load CIF reaches the real application's existing structure-loading action."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_app_load_structure_accepts_and_loads_the_published_cif():
    source = (ROOT / 'app/qml/Pages/Structure/StructuresGroup.qml').read_text()
    assert '*.cif' in source, 'The real structure file picker offers published CIF files'
    configured = os.environ.get('EDI_APP_TEST_RUNNER')
    binary = Path(configured) if configured else ROOT / 'build/app/app/edi_app_tests'
    assert binary.is_file(), 'Load CIF is exercised through the production Qt test host'
    result = subprocess.run(
        [
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_cif_structure_import.qml'),
            'CifStructureImport::test_load_published_cif',
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env={**os.environ,
             'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
             'QT_QUICK_BACKEND': os.environ.get('QT_QUICK_BACKEND', 'software')},
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The real app loads the published structure cell and atoms: ' + output
    )
    assert 'PASS' in output and '0 failed' in output, (
        'The Load CIF actor reaches its cell, atom and structure-count assertions'
    )
