"""Real app estimation and layout use separate bounded system workflows."""

import json
import os
import re
import subprocess
from pathlib import Path

import edi
import pytest

from tests.fixtures.background_estimate.series import terms

ROOT = Path(__file__).resolve().parents[3]


def run_actor(kind, phase):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Series app acceptance requires the built production Qt host'
    case = 'BackgroundEstimateSettings::test_series_' + phase + '_' + kind.replace('-', '_')
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_estimate_settings.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'The bounded real app workflow must satisfy its public background '
        + phase
        + ' contract: '
        + output
    )
    rows = re.findall(r'BACKGROUND_SERIES_' + phase.upper() + r' (\{[^\n]+\})', output)
    assert len(rows) == 1, 'Each type must complete exactly one real app workflow receipt'
    return json.loads(rows[0])


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_every_background_has_shared_grid_and_its_own_count(kind):
    receipt = run_actor(kind, 'layout')
    assert receipt == {
        'type': kind,
        'countField': 'n_points' if kind == 'line-segment' else 'max_terms',
        'method': 'auto',
        'resolved': 'arpls',
    }, 'Extra must expose the type-specific field and resolved auto method in its approved grid'


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_every_series_estimate_matches_python_is_undoable_and_reloads(kind, tmp_path):
    receipt = run_actor(kind, 'action')
    source = ROOT / 'tests/fixtures/background_estimate/projects' / ('series-' + kind)
    loaded = edi.Project.load(source)
    loaded.experiment.background.auto_estimate(
        method='auto',
        width=6,
        smoothness=1000,
        tolerance=2,
        use_model=False,
        max_terms=2,
    )
    loaded.save_as(tmp_path / 'python')
    assert receipt == {'type': kind, 'terms': [list(row) for row in terms(tmp_path / 'python')]}, (
        'Actual Main Estimate must save exactly the capped Python series, undo, and reload it'
    )
