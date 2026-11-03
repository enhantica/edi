"""Real app fit, post-fit preview, persistence and invalidation of free Auto backgrounds."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('kind', 'suffix'),
    [('line-segment', 'points'), ('polynomial', 'polynomial'), ('chebyshev', 'chebyshev')],
)
@pytest.mark.parametrize('flow', ['retain', 'settings', 'data', 'manual-control'])
def test_app_free_auto_fit_retains_its_baseline_and_reports_due_replacement(kind, suffix, flow):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The Auto fit lifecycle gate requires the actual production Qt host'
    flow_suffix = {'data': 'measured', 'manual-control': 'manual'}.get(flow, flow)
    case = 'BackgroundFittedBaseline::test_' + suffix + '_' + flow_suffix
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_fitted_baseline.qml'),
            case,
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'Auto free-point/term fit must retain the calculated pattern and fitted baseline until '
        'data/settings change, then report replacement as information; reason: ' + output
    )
    assert (
        'BACKGROUND_FITTED_BASELINE '
        + kind
        + ' '
        + flow
        + ' fit=retained pattern=present mode='
        + ('manual' if flow == 'manual-control' else 'auto')
        in output
    ), 'Each real app lifecycle must reach its fitted retention or information-message assertion'

    assert 'BACKGROUND_FIT_FREE_ACTION setParametersFree=true' in output, (
        'The real fit must exercise the permitted action that frees current background rows'
    )
    if kind == 'line-segment' and flow == 'settings':
        assert 'BACKGROUND_POINT_COUNT_SET backgroundEstimatePoints=11' in output, (
            'The point-count lifecycle must verify its app property before judging refresh'
        )
