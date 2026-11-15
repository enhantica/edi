"""Observe actual joint solve starts across modes and a skipped point."""

import subprocess
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.joint_series import cases, oracle, prepare_native

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def start_probe():
    return prepare_native.prepared(ROOT, engine)


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('skip', [False, True])
@pytest.mark.parametrize('workers', [1, 3])
def test_actual_joint_fit(tmp_path, start_probe, mode, skip, workers):
    root = cases.generated_series(
        tmp_path / 'project', engine, mode=mode, keys=('0007', '07', 'T300K', 'T500K', 'T900K')
    )
    structure = root / 'structures/phase.edi'
    structure.write_text(structure.read_text().replace('4.1()', '4.09()'))
    for index, old, new in [(0, '2.0()', '1.8()'), (1, '5.0()', '4.7()')]:
        path = root / 'experiments' / f'{index}_{cases.BANKS[index]}.edi'
        path.write_text(path.read_text().replace(old, new))
    if skip:
        (root / 'scan/T300K_b1.xy').write_text('broken numeric input\n')
    run = subprocess.run(
        [str(start_probe), str(root), str(workers)],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert run.returncode == 0, (
        'A bad point must not prevent observing subsequent actual joint starts: ' + run.stderr
    )
    _, points = cases.csv_rows(root / 'analysis/results.csv')
    _, banks = cases.csv_rows(root / 'analysis/results_experiments.csv')
    observed = {}
    for line in run.stdout.splitlines():
        point, name, value = line.split('\t')
        observed.setdefault(point.removesuffix('_b5.xy'), {})[name] = float(value)
    for row in points:
        oracle.outcome(row)
    keys = [row['point'] for row in points]
    actual = [
        [
            observed.get(key, {}).get('phase.cell.length_a', np.nan),
            observed.get(key, {}).get('zeta.linked_structure.phase.scale', np.nan),
            observed.get(key, {}).get('alpha.linked_structure.phase.scale', np.nan),
        ]
        for key in keys
    ]
    fitted = [
        [
            float(row['phase.cell.length_a']),
            *[
                float(
                    next(
                        bank
                        for bank in banks
                        if bank['point'] == row['point'] and bank['experiment'] == name
                    )['linked_structure.phase.scale']
                )
                for name in cases.BANKS
            ],
        ]
        for row in points
    ]
    assert not np.allclose(fitted[0], [4.09, 1.8, 4.7]), (
        'The first successful fit must differ from the template to expose a skip reset'
    )
    oracle.starts(
        actual,
        [4.09, 1.8, 4.7],
        fitted,
        chained=mode == 'sequential',
    )
