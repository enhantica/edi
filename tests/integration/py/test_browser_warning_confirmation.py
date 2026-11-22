"""Browser confirmation uses the actual hook's visual-item observation domain."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def observer_receipts():
    # Source/model loading and the actual JS helpers are shared by the eight checks.
    return subprocess.run(
        ['node', str(ROOT / 'tests/fixtures/project_archive/check_warning_confirmation.mjs')],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize(
    'scenario',
    [
        'visual-observations',
        'popup-geometry',
        'popup-native',
        'popup-hidden',
        'early-download',
        'not-visible',
        'not-closed',
        'no-confirmation',
    ],
)
def test_warning_confirmation_uses_supported_visual_observers(scenario, observer_receipts):
    run = observer_receipts
    assert run.returncode == 0, (
        'Warning Save-as must observe its real visual child before confirmation '
        'and after closure, '
        'reject Popup targets and retain pending-download checks: ' + run.stdout + run.stderr
    )
    assert run.stdout.splitlines().count('PASS ' + scenario) == 1, (
        'Every visual-observer and confirmation escape must produce its own completed receipt: '
        + scenario
    )
