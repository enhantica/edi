"""Both public fit commands preserve independently fitted datasets and uncertainties."""

import os
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.fixtures.independent_experiments.reference import BANKS, optimum, project_files
from tests.fixtures.report_units.iucr_reference import rounded_pair

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def command_results(tmp_path_factory):
    directory = tmp_path_factory.mktemp('independent-commands')
    candidates = [
        os.environ.get('EDI_CLI_EXECUTABLE'),
        ROOT / 'build/ci-consumer/cli/easydiffraction',
        ROOT / 'build/ci/cli/easydiffraction',
    ]
    binary = next((Path(p) for p in candidates if p and Path(p).is_file()), None)
    assert binary is not None, (
        'Independent fitting must be exercised through the built standalone command'
    )
    results = {}
    for entry, prefix in [
        ('module', [sys.executable, '-m', 'edi']),
        ('standalone', [str(binary)]),
    ]:
        source = project_files(directory / entry / 'input')
        output = directory / entry / 'output'
        run = subprocess.run(
            [
                *prefix,
                'fit',
                str(source),
                '--report',
                'machine',
                '--verbosity',
                'full',
                '--output',
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
            env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        )
        results[entry] = run, output
    return results


@pytest.mark.parametrize('entry', ['module', 'standalone'])
@pytest.mark.parametrize('name', BANKS)
def test_each_command_preserves_its_independent_dataset_result(entry, name, command_results):
    run, folder = command_results[entry]
    assert run.returncode == 0, (
        'The public command fits non-scan independent experiments: ' + run.stdout + run.stderr
    )
    machine = dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line)
    assert machine['mode'] == 'independent', 'The command reports the mode it actually dispatched'
    expected = optimum([name])
    assert float(machine[f'bank.{name}.chi_square']) == pytest.approx(
        expected['chi'], rel=2e-5, abs=1e-9
    ), 'The command retains each independent dataset residual sum'
    assert float(machine[f'bank.{name}.rwp']) == pytest.approx(
        expected['rwp'], rel=2e-5, abs=1e-9
    ), 'The command retains each independent dataset agreement'
    model = edi.Project.load(folder)
    structure = next(row for row in model.structures if row.name == BANKS[name]['phase'])
    actual = next(row for row in structure.atom_sites if row.id == 'Ni').occupancy
    value, su = rounded_pair(expected['value'], expected['su'], 'iucr_99')
    assert actual.value == pytest.approx(value, rel=0, abs=1e-8), (
        'The written independent value follows the isolated optimum and declared save precision'
    )
    assert actual.uncertainty == pytest.approx(su, rel=0, abs=1e-9), (
        'The written independent uncertainty follows its own variance and declared save precision'
    )
