"""The lazy-input boundary and an exercised eager-reader escape."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import _build_native_observer  # noqa: PLC2701 - reuse the shared test observer

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/scan_template/project'


def assert_lazy(observation):
    opened = observation['files']
    assert not observation['unresolved'], (
        'Scale: every native input open must retain its path identity'
    )
    assert opened, 'Scale: the observer must reach native data-file opens before judging laziness'
    assert len(opened) <= 5, (
        'Scale: before the first result only its file and four read-ahead files open'
    )


@pytest.fixture(scope='module')
def input_observations(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-input')
    library, preload = _build_native_observer(root)
    observations = {}
    for mode in ('lazy', 'eager-load', 'eager-load-relative', 'eager-load-openat'):
        project_dir = root / mode
        shutil.copytree(FIXTURE, project_dir)
        scan = project_dir / 'experiments/d20_scan'
        data = (scan / 'all594791.dat').read_bytes()
        for file in scan.glob('*.dat'):
            file.unlink()
        for index in range(20):
            (scan / f'{index:04d}.dat').write_bytes(data)
        analysis = project_dir / 'analysis/analysis.edi'
        analysis.write_text(
            analysis.read_text().replace(
                '_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'
            )
        )
        environment = {
            **os.environ,
            preload: str(library),
            'OMP_NUM_THREADS': '1',
            'EDI_C08_NATIVE_OBSERVER_LOG': str(root / f'{mode}.log'),
        }
        if sys.platform == 'darwin':
            environment['DYLD_FORCE_FLAT_NAMESPACE'] = '1'
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / 'tests/fixtures/scan_template/io_probe.py'),
                str(project_dir),
                mode,
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert result.returncode == 0, (
            'Scale: the observed real-driver run must complete before its I/O record is used: '
            + result.stdout
            + result.stderr
        )
        observations[mode] = json.loads(result.stdout)
    return observations


def test_driver_opens_only_current_file_and_bounded_read_ahead(input_observations):
    assert_lazy(input_observations['lazy'])


@pytest.mark.parametrize('escape', ['eager-load', 'eager-load-relative', 'eager-load-openat'])
def test_gate_rejects_an_exercised_read_all_files_before_fitting_escape(
    input_observations, escape
):
    observation = input_observations[escape]
    assert len(observation['files']) == 20, (
        'Scale: the escape must actually reach every input file before the first result'
    )
    with pytest.raises(AssertionError, match='four read-ahead'):
        assert_lazy(observation)
