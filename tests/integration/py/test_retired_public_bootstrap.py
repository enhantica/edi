# SPDX-License-Identifier: BSD-3-Clause
"""The public repository no longer ships the one-time private cut-over kit."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('tool', ['cutover.py', 'snapshot.py', 'spdx.py'])
def test_one_time_public_bootstrap_entrypoints_are_retired(tool):
    path = ROOT / 'tools/public-release' / tool
    assert not path.exists() and not path.is_symlink(), (
        'Public bootstrap: retired cut-over executables cannot return as files or symlinks: '
        + tool
    )
