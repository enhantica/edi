"""actual page kernel escape, bounded like the prior  page gates."""

import subprocess
import sys
from pathlib import Path


def test_actual_lif_page_rejects_disabled_xray_kernel():
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, str(root / 'tests/system/manual/c15_t1_page_escape.py')],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        ' actual LiF page must pass and reject the disabled X-ray kernel: ' + result.stderr
    )
    assert 'disabled X-ray rejected at agreement' in result.stdout, (
        ' escape must reach the real page agreement assertion'
    )

    assert 'disabled dispersion rejected at agreement' in result.stdout, (
        ' dispersion-disable escape must reach the real page agreement assertion'
    )
