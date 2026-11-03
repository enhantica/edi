"""Existing CLIs obey the saved term cap without new estimation flags."""

import subprocess
import sys
from pathlib import Path

import edi as engine
import pytest

from tests.fixtures.background_estimate.series import project, terms
from tests.fixtures.background_estimate.settings import DEFAULTS, read_settings, write_settings

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
@pytest.mark.parametrize('cap', [2, 6])
def test_saved_auto_series_cap_agrees_between_cli_and_python(tmp_path, kind, cap):
    source = project(tmp_path / 'input', kind)
    settings = {
        **DEFAULTS,
        'method': 'arpls',
        'width': 6.0,
        'smoothness': 1000.0,
        'in_peaks': 'move',
        'max_terms': cap,
        'use_model': False,
    }
    write_settings(source, settings)
    loaded = engine.Project.load(source)
    loaded.analysis.calculate()
    loaded.save_as(tmp_path / 'python')
    command = [sys.executable, '-m', 'edi', 'calc', str(source)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=4, check=False)
    assert completed.returncode == 0, (
        'The existing calc command must estimate each series using its saved cap: '
        + completed.stderr
    )
    assert terms(source) == terms(tmp_path / 'python'), (
        'CLI and Python must publish exactly the same coefficients from '
        'the same saved automatic settings'
    )
    assert len(terms(source)) == (2 if cap == 2 else 4), (
        'The CLI must detect the cubic order or stop at the exact two-term cap'
    )
    assert read_settings(source)['max_terms'] == cap, (
        'CLI calculation must preserve max_terms as a saved user override'
    )
