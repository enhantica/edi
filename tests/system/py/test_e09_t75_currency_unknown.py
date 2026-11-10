"""Review18 F03: an unreadable landed proof cannot admit the main-pin fallback.

Accident: clone and tag fetch work, but rev-parse/log cannot read retained data.
A successfully read nonmatching history remains the legitimate negative control.
"""

from __future__ import annotations

import os
import sys

import pytest

from tests.system.py.test_e09_t75_pin_currency import currency_world


@pytest.mark.parametrize('failure', ['tree', 'history'])
def test_required_currency_refuses_unknown_before_main_pin_fallback(tmp_path, failure):
    build, _ = currency_world(tmp_path, 'unpaired-main-pin')
    control = build.run('crysta-source.sh', '--currency')
    assert control.returncode == 0, (
        ' review18 F03 a readable unlanded build may use the equal edi-main pin'
    )
    assert "edi main's" in control.stdout, (
        ' review18 F03 the control must reach the main-pin fallback'
    )
    bin_dir = tmp_path / 'fault-bin'
    bin_dir.mkdir()
    marker = tmp_path / 'failed-local-observation'
    proxy = bin_dir / 'git'
    proxy.write_text(
        f'#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\n'
        f'a=sys.argv[1:]; failure={failure!r}\n'
        'tree="rev-parse" in a and any(v.endswith("^{tree}") for v in a)\n'
        'history="log" in a and "--format=%T" in a and "main" in a\n'
        'if (failure=="tree" and tree) or (failure=="history" and history):\n'
        f' Path({str(marker)!r}).write_text("attempted and unreadable")\n'
        ' sys.exit(73)\n'
        f'os.execv({build.git!r},[{build.git!r},*a])\n'
    )
    proxy.chmod(0o755)
    build.env['PATH'] = str(bin_dir) + os.pathsep + build.env['PATH']
    result = build.run('crysta-source.sh', '--currency')
    assert marker.exists(), ' review18 F03 the actual retained tree/history lookup must fail'
    assert result.returncode != 0, (
        ' review18 F03 unknown landed status cannot be converted to a matching fallback'
    )
    assert "edi main's" not in result.stdout, (
        ' review18 F03 a failed authority cannot receive currency credit'
    )
