"""real page entrypoints, including the page's own fit, and selector escapes."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize('kind', ['fcj', 'beba', 'tof'])
def test_actual_page_rejects_disabled_profile(kind):
    root = Path(__file__).resolve().parents[3]
    helper = root / 'tests/system/manual/c11_t57_page_escapes.py'
    # Exercise the standalone page as notebook-tests does. Its fit is the delivered
    # verification-page workload, not a synthetic hidden-suite fit.
    result = subprocess.run(
        [sys.executable, str(helper), kind],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, (
        ' actual page must pass, then reject its disabled kernel at agreement: '
        + result.stderr[-4000:]
    )
    assert f' {kind}: original page green; disabled kernel rejected' in result.stdout, (
        ' page escape must reach and reject at the real reference agreement assertion'
    )
