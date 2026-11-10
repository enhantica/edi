"""Surviving  C++ probes and stateless Python contract."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import edi
import numpy as np
import pytest

from tests.model_calculation import calculate_on_grid

ROOT = Path(__file__).resolve().parents[3]
from conftest import corpus_case_dir  # noqa: E402


def _load_cheap_project() -> object:
    return edi.Project.load(corpus_case_dir('cosio-d20-s1') / 'project')


def _run_checked(
    command: list[str], *, cwd: Path, timeout: int = 600
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture(scope='session')
def c09_t7_internal_probe() -> Path:
    build = 'ci-consumer' if os.environ.get('CRYSTA_CONSUMER_SRC') else 'ci'
    executable = (
        ROOT
        / 'build'
        / build
        / 'core'
        / ('c09_t7_internal_probe.exe' if os.name == 'nt' else 'c09_t7_internal_probe')
    )
    assert executable.is_file(), (
        'the pre-built internal probe is missing - run `pixi run core-build` first'
    )
    sources = [ROOT / 'tests/unit/cpp/c09_t7_internal_probe.cpp']
    sources.extend(
        path
        for directory in ('src', 'include')
        for path in (ROOT / 'core' / directory).rglob('*')
        if path.is_file()
    )
    built_ns = executable.stat().st_mtime_ns
    stale = [path for path in sources if path.stat().st_mtime_ns > built_ns]
    assert not stale, (
        f'the pre-built internal probe is older than {stale[0]} - run `pixi run core-build` first'
    )
    return executable


def test_c09_t7_v1_rejects_a_deliberately_transposed_index(
    c09_t7_internal_probe: Path,
) -> None:
    _run_checked(
        [
            str(c09_t7_internal_probe),
            'v1',
            str(corpus_case_dir('si-sepd-s2') / 'project'),
        ],
        cwd=ROOT,
        timeout=60,
    )


def test_c09_t7_stateless_api_remains_the_default() -> None:
    project = _load_cheap_project()
    data = project.experiments[0].data
    assert data is not None, 'the stateless fit witness must carry model-owned measured data'
    grid = np.asarray(data.axis())
    assert not hasattr(project.calculate, '__cached_model_default__')
    assert calculate_on_grid(edi, project, grid).shape == grid.shape, (
        'the stateless compatibility calculation must preserve the provided observation grid'
    )
    outcome = project.fit()
    assert outcome.converged is True, 'the model-only stateless fit must still converge'
