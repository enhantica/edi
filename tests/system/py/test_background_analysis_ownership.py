"""Every Analysis user value entry protects Auto backgrounds before mutation."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
KINDS = ['line-segment', 'polynomial', 'chebyshev']


def actor(case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Analysis ownership acceptance requires the production Qt host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_analysis_ownership.qml'),
            'BackgroundAnalysisOwnership::' + case,
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
    assert result.returncode == 0 and 'PASS   :' in output, (
        'Every real Analysis value input must protect Auto before mutation, while Manual '
        'values and Auto free/fixed remain usable: ' + output
    )
    return output


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('route', ['cell', 'slider', 'model', 'binding'])
@pytest.mark.parametrize('state', ['free', 'fixed', 'manual'])
def test_analysis_value_entries_protect_auto_and_keep_manual_live(kind, route, state):
    output = actor('test_entries:' + kind + '_' + route + '_' + state)
    assert (
        'BACKGROUND_ANALYSIS_OWNERSHIP '
        + kind
        + ' '
        + route
        + ' mode='
        + ('manual' if state == 'manual' else 'auto')
        + ' checked=true'
    ) in output, 'Each selected Analysis input must complete its actual ownership checks'


@pytest.mark.parametrize('kind', KINDS)
def test_analysis_free_fixed_remains_a_real_permitted_auto_action(kind):
    output = actor('test_free_fixed:' + kind)
    assert 'BACKGROUND_ANALYSIS_FREE_FIXED ' + kind + ' checked=true' in output, (
        'Both actual Analysis variability checkboxes must remain usable for Auto backgrounds'
    )
