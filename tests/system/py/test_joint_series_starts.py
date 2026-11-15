"""Observe actual joint solve starts across modes and a skipped point."""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.joint_series import cases, oracle

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def start_probe(tmp_path_factory):
    build = tmp_path_factory.mktemp('joint-start-probe')
    prefix = Path(sys.prefix)
    if engine.__name__ == 'edi':
        sdk = importlib.import_module('tests.conftest').crysta_reference_prefix()
        artifact = Path(engine._edi.__file__).resolve().parents[2]
        libraries = [artifact / 'core/libedi_core.a', sdk / 'lib/libcrysta_core.a']
        includes = [ROOT / 'core/include', sdk / 'include']
        defines = ['-DEDI_PROBE']
    else:
        candidates = list((ROOT / 'build').glob('cp*/libcrysta_core.a'))
        library = (
            Path(os.environ['JOINT_SERIES_CORE'])
            if 'JOINT_SERIES_CORE' in os.environ
            else max(candidates, key=lambda p: p.stat().st_mtime_ns)
        )
        libraries, includes, defines = (
            [library],
            [Path(os.environ.get('JOINT_SERIES_INCLUDE', ROOT / 'include'))],
            [],
        )
    command = [
        os.environ.get('CXX', 'c++'),
        '-std=c++20',
        '-O0',
        *defines,
        *['-I' + str(p) for p in [*includes, prefix / 'include/eigen3']],
        str(ROOT / 'tests/fixtures/joint_series/starts.cpp'),
        *map(str, libraries),
        '-L' + str(prefix / 'lib'),
        '-Wl,-rpath,' + str(prefix / 'lib'),
        '-lsleef',
        '-fopenmp',
        '-pthread',
        '-o',
        str(build / 'starts'),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=90)
    assert result.returncode == 0, (
        'The start observer must link to the real selected engine: ' + result.stderr
    )
    return build / 'starts'


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('skip', [False, True])
def test_actual_joint_fit(tmp_path, start_probe, mode, skip):
    root = cases.generated_series(tmp_path / 'project', engine, mode=mode)
    structure = root / 'structures/phase.edi'
    structure.write_text(structure.read_text().replace('4.1()', '4.09()'))
    for index, old, new in [(0, '2.0()', '1.8()'), (1, '5.0()', '4.7()')]:
        path = root / 'experiments' / f'{index}_{cases.BANKS[index]}.edi'
        path.write_text(path.read_text().replace(old, new))
    if skip:
        (root / 'scan/T300K_b1.xy').write_text('broken numeric input\n')
    run = subprocess.run(
        [str(start_probe), str(root)], capture_output=True, text=True, check=False, timeout=20
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
    oracle.starts(actual, [4.09, 1.8, 4.7], fitted, chained=mode == 'sequential')
