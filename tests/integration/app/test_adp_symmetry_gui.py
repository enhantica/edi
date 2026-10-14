"""Exercise site followers and owner-approved labels through actual Qt input."""

import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.adp_site_symmetry.model import KINDS, SITES
from tests.integration.app.test_e04_t1_projects import runner

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('channel', ['tensor', 'labels'])
@pytest.mark.parametrize(('name', 'kind'), [(name, kind) for name in SITES for kind in KINDS])
def test_same_site_followers_and_tensor_equivalents_in_the_normal_qt_host(name, kind, channel):
    prefix = 'labels_' if channel == 'labels' else ''
    case = f'AdpSiteSymmetry::test_{prefix}{name}_{kind}'
    result = subprocess.run(
        [
            str(runner()),
            '-input',
            str(ROOT / 'tests/unit/app/tst_adp_site_symmetry.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    output = result.stdout + result.stderr
    assert f'PASS   : edi_app::{case}()' in output, (
        'Each independent site/type GUI control must execute through the CI-built Qt host: '
        + output
    )
    assert result.returncode == 0, (
        'Actual editing must preserve followers, equivalents and the owner-approved ADP labels: '
        + output
    )
