"""The actual CLI discovers CIF members, with native shadowing and ambiguity refusal."""

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
def test_cli_discovers_structure_cif_members(tmp_path, style, layout):
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
    if style == 'multiblock' and layout != 'shadow':
        assert result.returncode != 0 and '2 structure blocks' in result.stderr, (
            'The CLI refuses an ambiguous discovered CIF member before producing a report'
        )
        assert not (tmp_path / 'report.html').exists(), (
            'A refused project never leaves a partial report'
        )
    else:
        assert result.returncode == 0, (
            'The CLI admits supported CIF members and retains native shadow precedence: '
            + result.stdout
            + result.stderr
        )
        if layout == 'shadow':
            assert 'phase.cif' in result.stderr and 'not read' in result.stderr, (
                'The CLI names the shadowed CIF member without importing it twice'
            )
        if account.API == 'edi':
            assert (tmp_path / 'report.html').is_file(), (
                'A discovered supported project produces its requested report'
            )
    assert case.snapshot(source) == before, 'CLI discovery preserves every source byte'
