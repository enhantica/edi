"""The actual CLI preserves main native-only structure file discovery."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures import cif_accounting as account
from tests.fixtures import structure_cif_refusal as case

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('style', ['dot', 'underscore', 'upper', 'multiblock'])
@pytest.mark.parametrize('layout', ['distinct', 'shadow', 'upper-suffix'])
def test_cli_keeps_main_native_only_structure_discovery(tmp_path, style, layout):
    source = case.poisoned_project(tmp_path, style, layout)
    before = case.snapshot(source)
    if account.API == 'edi':
        output = tmp_path / 'report.html'
        command = [sys.executable, '-m', 'edi', 'report', str(source), '--output', str(output)]
    else:
        binary = Path(os.environ.get('CRYSTA_REFUSAL_CLI', ROOT / 'build/crysta'))
        assert binary.is_file(), 'The structure refusal uses the actual built native CLI'
        command = [str(binary), str(source), 'calc', '--dry']
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=15)
    assert result.returncode == 0, (
        'Main ignores sidecar structure CIFs through the actual CLI: '
        + result.stdout
        + result.stderr
    )
    assert 'Reading CIF files is not supported yet' not in result.stderr, (
        'Main-accepted native projects never acquire a CIF refusal from ignored sidecar files'
    )
    assert case.snapshot(source) == before, 'Native-only CLI discovery preserves all source bytes'
    if account.API == 'edi':
        assert (tmp_path / 'report.html').is_file(), (
            'The actual native-only report command still produces its requested report'
        )
