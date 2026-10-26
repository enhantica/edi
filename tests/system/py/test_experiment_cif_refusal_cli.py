"""Both CLIs preserve main native-only discovery and unsupported native-file refusal."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures import cif_accounting as account
from tests.fixtures import experiment_cif_refusal as case
from tests.fixtures import structure_cif_refusal as native
from tests.integration.py import experiment_cif_refusal_checks as checks

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('style', case.STYLES)
@pytest.mark.parametrize('layout', case.LAYOUTS)
def test_cli_preserves_main_experiment_discovery_and_refusal(tmp_path, style, layout):
    source = case.poisoned_project(tmp_path, style, layout)
    before = native.snapshot(source)
    if account.API == 'edi':
        command = [
            sys.executable,
            '-m',
            'edi',
            'report',
            str(source),
            '--output',
            str(tmp_path / 'report.html'),
        ]
    else:
        binary = Path(os.environ.get('CRYSTA_REFUSAL_CLI', ROOT / 'build/crysta'))
        assert binary.is_file(), 'The experiment refusal actor uses the actual built CLI'
        command = [str(binary), str(source), 'calc', '--dry']
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    if layout == 'native-suffix':
        assert result.returncode != 0, 'Main refuses this unsupported CIF in a native .edi file'
        checks.reason(result.stderr)
        assert not (tmp_path / 'report.html').exists(), (
            'Refused experiment input writes no partial report'
        )
    else:
        assert result.returncode == 0, (
            'Main ignores sidecar experiment CIFs through the real CLI: '
            + result.stdout
            + result.stderr
        )
        assert 'Reading CIF files is not supported yet' not in result.stderr, (
            'An ignored experiment sidecar does not turn a native project into a refusal'
        )
        if account.API == 'edi':
            assert (tmp_path / 'report.html').is_file(), (
                'The actual native-only report command still produces its requested report'
            )
    assert native.snapshot(source) == before, (
        'CLI discovery preserves every native and CIF source byte'
    )
