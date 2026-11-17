"""Observe read-only model descriptions and native atom-site moment creation."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    'case',
    [
        'type_column_is_disabled_after_name',
        'create_structure_is_atom_based',
        'moments_appear_and_disappear_via_atom_site_input',
        'legacy_saved_project_regression_pin_retains_bytes',
        'magnetic_structure_bytes_survive_save_and_reload',
    ],
)
def test_structure_description_through_real_controls(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Structure description acceptance requires the current Qt test host'
    family = (
        'LegacyStructurePersistence'
        if case.startswith('legacy_saved_')
        else 'StructureDescription'
    )
    result = subprocess.run(
        [
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_structure_description.qml'),
            family + '::test_' + case,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'Description and magnetic creation satisfy the rendered control contract: ' + output
    )
    assert 'PASS ' in output and '::test_' + case + '()' in output and '0 failed' in output, (
        'The requested description actor reaches its native assertions without an empty selection'
    )
    assert 'SKIP' not in output, 'Every description and magnetic creation requirement executes'
