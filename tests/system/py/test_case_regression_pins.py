"""Gate 2: three real interfaces agree with explicitly labelled regression pins."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.fixtures.tutorial_cases.contract import CASES, CONTRACT, ROOT
from tests.fixtures.tutorial_cases.pins import compare_regression_pin, machine_values, pinned_start


def initial_parameters(project):
    document = json.loads(project.report.model().to_json())
    return document['parameters']


def calculation_record(project):
    project.analysis.calculate()
    values = []
    for experiment in project.experiments:
        data = (
            experiment.refln
            if experiment.experiment_type.sample_form == edi.SampleFormEnum.SINGLE_CRYSTAL
            else experiment.data
        )
        values.extend(data.intensity_calc)
    return {'n_points': len(values), 'checksum': sum(values)}


def app_result(case, simulation, tmp_path):
    candidates = (
        [Path(os.environ['EDI_APP_TEST_RUNNER'])]
        if 'EDI_APP_TEST_RUNNER' in os.environ
        else [
            ROOT / 'build/app/app/edi_app_tests',
            ROOT / 'build/app/edi_app_tests',
        ]
    )
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, (
        'Gate 2: app-build must provide the real Qt host for example fitting'
    )
    receipt = tmp_path / 'app.json'
    env = {
        **os.environ,
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'EDI_CASE_PIN_ID': case,
        'EDI_CASE_PIN_OPERATION': 'calc' if simulation else 'fit',
        'EDI_CASE_PIN_RECEIPT': str(receipt),
        'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
    }
    run = subprocess.run(
        [
            str(binary),
            '-input',
            str(ROOT / 'tests/system/app/tst_case_regression_pin.qml'),
            'CaseRegressionPin::test_real_app_example_result',
            '-o',
            '-,txt',
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3600,
    )
    assert run.returncode == 0 and receipt.is_file(), (
        'Gate 2: the app must actually open and run this bundled case: '
        + case
        + run.stdout
        + run.stderr
    )
    document = json.loads(receipt.read_text())
    assert document['case'] == case and document['operation'] == (
        'calc' if simulation else 'fit'
    ), 'Gate 2: the app receipt identifies the actual requested example and operation'
    assert document['completed'] is True, (
        'Gate 2: the app worker must finish before comparing values'
    )
    return document


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('surface', ['cli', 'python', 'app'])
def test_each_interface_matches_its_committed_regression_pin(case, surface, tmp_path):
    quantities = pinned_start(case)
    simulation = case in CONTRACT['simulations']
    source = ROOT / 'docs/user/cli' / case / 'project'
    destination = tmp_path / 'project'
    shutil.copytree(source, destination)
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    if surface == 'cli':
        operation = 'calc' if simulation else 'fit'
        run = subprocess.run(
            [
                sys.executable,
                '-m',
                'edi',
                operation,
                str(destination),
                '--report',
                'machine',
                '--verbosity',
                'full',
            ],
            env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
            capture_output=True,
            text=True,
            check=False,
            timeout=3600,
        )
        assert run.returncode == 0, (
            'Gate 2: the real CLI must finish the example: ' + run.stdout + run.stderr
        )
        actual = machine_values(run.stdout)
    elif surface == 'python':
        project = edi.Project.load(destination)
        if simulation:
            actual = calculation_record(project)
        else:
            result = project.analysis.fit()
            actual = machine_values(edi.machine_report(project, result, edi.VerbosityEnum.FULL))
    else:
        expected_start = initial_parameters(edi.Project.load(source))
        document = app_result(case, simulation, tmp_path)
        assert document['initial_parameters'] == expected_start, (
            'Gate 2: the app bundle starts with the same values and flags as Python and CLI'
        )
        actual = machine_values(document['machine'])
    compare_regression_pin(actual, quantities)
    assert before == {
        p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()
    }, 'Gate 2: fitting disposable examples must preserve the committed starting project'


@pytest.mark.parametrize('damage', ['unchanged', 'structure', 'analysis', 'extra-file'])
def test_catalogue_fit_policy_admits_only_whole_declared_starts(tmp_path, damage):
    source = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project'
    destination = tmp_path / 'project'
    shutil.copytree(source, destination)
    if damage == 'extra-file':
        (destination / 'unexpected.edi').write_text('data_unregistered\n')
    elif damage != 'unchanged':
        folder = 'structures' if damage == 'structure' else 'analysis'
        path = next((destination / folder).glob('*.edi'))
        path.write_text(path.read_text() + '\n# unregistered recipe or data mutation\n')
    project = edi.Project.load(destination)
    with pytest.raises((TypeError, RuntimeError)) as caught:
        project.fit(case_gate_invalid_operand=True)
    expected = 'TypeError' if damage == 'unchanged' else 'FitPolicyViolation'
    assert type(caught.value).__name__ == expected, (
        'Gate 2: exact catalogue admission reaches operand validation; '
        'every altered copy is refused before fitting'
    )
