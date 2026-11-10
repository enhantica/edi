"""The CLI admits supported experiment CIF content and keeps source bytes intact."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures import cif_accounting as account
from tests.fixtures import experiment_cif_refusal as case
from tests.fixtures import structure_cif_refusal as native

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('style', case.STYLES)
@pytest.mark.parametrize('layout', case.LAYOUTS)
def test_cli_discovers_experiment_cif_members(tmp_path, style, layout):
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
    assert result.returncode == 0, (
        'The CLI imports supported experiment CIF content independently of its suffix: '
        + result.stdout
        + result.stderr
    )
    if layout == 'shadow':
        assert 'bank.cif' in result.stderr and 'not read' in result.stderr, (
            'The CLI reports native precedence over a same-stem experiment CIF'
        )
    if account.API == 'edi':
        assert (tmp_path / 'report.html').is_file(), (
            'The CIF project report command produces its requested report'
        )
    assert native.snapshot(source) == before, (
        'CLI discovery preserves every native and CIF source byte'
    )
