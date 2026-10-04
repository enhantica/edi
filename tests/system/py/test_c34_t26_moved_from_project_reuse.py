""": the public C++ project remains calculable after move and reuse."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    'mode',
    ['construct-copy', 'assign-copy', 'construct-collections', 'assign-collections'],
)
def test_c34_t26_moved_from_project_reuse_calculates_in_public_cpp_api(mode: str) -> None:
    build = 'ci-consumer' if os.environ.get('CRYSTA_CONSUMER_SRC') else 'ci'
    probe = ROOT / 'build' / build / 'core/e02_adapter_probe'
    if os.name == 'nt':
        probe = probe.with_suffix('.exe')
    assert probe.is_file(), ' public native move probe requires the prebuilt core probe'
    fixture = corpus_case_dir('cosio-d20-s1') / 'project'
    result = subprocess.run(
        [str(probe), '--move-reuse', mode, str(fixture)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        f' {mode} must leave a moved-from project with a live edit record and '
        f'a calculable measured bank; native exit {result.returncode}: '
        f'{result.stdout}{result.stderr}'
    )
