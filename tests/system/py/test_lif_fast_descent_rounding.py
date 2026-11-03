# SPDX-License-Identifier: BSD-3-Clause
"""The documented LiF fit keeps its stop decision under one-ULP start changes."""

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'


@pytest.mark.parametrize(
    'mu_r',
    [math.nextafter(0.7, -math.inf), 0.7, math.nextafter(0.7, math.inf)],
    ids=['one-ulp-down', 'original', 'one-ulp-up'],
)
def test_lif_rounding_preserves_fast_descent_status_and_iteration_regression_pin(tmp_path, mu_r):
    source = CLI / 'pd-xray-cwl_lif_single'
    target = tmp_path / 'project'
    shutil.copytree(source / 'project', target)
    experiment = target / 'experiments/cu_ka.edi'
    text = experiment.read_text()
    original = '_absorption.mu_r 0.7()'
    assert text.count(original) == 1, (
        'the rounding witness must change exactly the declared free absorption start'
    )
    experiment.write_text(text.replace(original, f'_absorption.mu_r {mu_r:.17g}()'))
    analysis = target / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + '\n_minimizer.descent fast_descent\n')
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(target),
            '--report',
            'machine',
            '--verbosity',
            'full',
        ],
        cwd=ROOT,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, 'the real LiF fit must complete: ' + result.stderr
    record = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    assert record.get('status') == 'done', (
        'a one-ULP absorption-start perturbation must retain converged status: ' + result.stdout
    )
    expected = json.loads((source / 'expected.json').read_text())
    pin = expected['variants']['fast-descent']['quantities']['iterations']['value']
    assert pin == 5 and float(record['iterations']) == pin, (
        'a one-ULP absorption-start perturbation must retain the original five-iteration '
        'regression pin: ' + result.stdout
    )
