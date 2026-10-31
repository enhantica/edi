"""An adopting save recalculates rounded current inputs without consuming due estimates."""

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from tests.fixtures.project_save.boundaries import (
    agreement,
    bank_state,
    mixed_measurements,
    prepared_mixed,
    rounded_bank_state,
)
from tests.integration.py.test_anisotropic_adps import loop_rows

ENGINE = importlib.import_module('edi')
OPERATIONS = ['save', 'save-as', 'cli-output']


def perform_save(project, source, destination, operation):
    if operation == 'save':
        project.save()
    elif operation == 'save-as':
        project.save_as(destination)
    elif operation == 'cli-output':
        # Exercise the production CLI output stage before its explicitly requested calculation.
        runner = importlib.import_module('edi.__main__')
        args = runner.build_parser().parse_args([
            'calc',
            str(source),
            '--output',
            str(destination),
        ])
        return runner._open(args)
    else:
        message = 'Unknown save boundary'
        raise ValueError(message)
    return project


def digests(path):
    return dict(re.findall(r'(?m)^(_background_estimate\.\w+_digest)\s+(\S+)', path.read_text()))


def fresh_pattern(destination, single):
    shutil.copytree(destination, single)
    (single / 'experiments/due.edi').unlink()
    analysis = single / 'analysis/analysis.edi'
    analysis.write_text(re.sub(r'(?m)^due .*\n', '', analysis.read_text()))
    project = ENGINE.Project.load(single)
    project.calculate()
    return np.array(project.experiment.data.intensity_calc, copy=True)


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
@pytest.mark.parametrize('empty', [False, True], ids=['points', 'empty'])
@pytest.mark.parametrize('provenance', ['stale', 'absent'])
@pytest.mark.parametrize('operation', OPERATIONS)
def test_due_background_rounds_and_adopts_without_estimation_beside_a_current_bank(
    tmp_path, empty, provenance, operation, kind
):
    project, source = prepared_mixed(
        ENGINE, tmp_path / 'input', empty=empty, provenance=provenance, kind=kind
    )
    due = project.experiments['due']
    before = bank_state(due)
    before_digest = digests(source / 'experiments/due.edi')
    expected = rounded_bank_state(before)
    assert bool(before['rows'] or before['terms']) is not empty, (
        'The due witness exercises populated and empty bases'
    )
    assert before['mode'] == 'auto', (
        'The measured due bank explicitly requests automatic estimation'
    )
    if not empty:
        assert (before['rows'] or before['terms'])[0][2].hex() == float('2.34567891').hex(), (
            'The due witness starts with an independently authored value '
            'moved by six-digit rounding'
        )
    destination = source if operation == 'save' else tmp_path / 'saved'
    project = perform_save(project, source, destination, operation)
    assert bank_state(project.experiments['due']) == expected, (
        'An adopting save rounds ordinary due values and adopts them without estimation; '
        'row identities, free flags, mode and settings remain unchanged'
    )
    again = ENGINE.Project.load(destination)
    assert bank_state(again.experiments['due']) == expected, (
        'The file and adopted live due bank agree, including an empty automatic basis '
        'whose origin or domain remains absent'
    )
    saved_digest = digests(destination / 'experiments/due.edi')
    inputs = '_background_estimate.inputs_digest'
    if inputs in before_digest:
        assert saved_digest.get(inputs) == before_digest[inputs], (
            'Rounding due rows never replaces their existing estimate-input provenance'
        )
    # The native/app observers separately compare the loader's raw digest state and
    # canonical points hash. Here the public API proves durable digest idempotence.
    repeat = tmp_path / 'repeat-due'
    again.save_as(repeat)
    assert digests(repeat / 'experiments/due.edi') == saved_digest, (
        'A reconciled due points digest and stale input provenance remain stable after reopen/save'
    )
    assert bank_state(again.experiments['due']) == expected, (
        'Digest reconciliation and a second save never estimate the due background'
    )


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
@pytest.mark.parametrize('empty', [False, True], ids=['points', 'empty'])
@pytest.mark.parametrize('provenance', ['stale', 'absent'])
@pytest.mark.parametrize('operation', OPERATIONS)
def test_current_bank_inputs_arrays_and_factors_match_independent_rounded_calculation(
    tmp_path, empty, provenance, operation, kind
):
    project, source = prepared_mixed(
        ENGINE, tmp_path / 'input', empty=empty, provenance=provenance, kind=kind
    )
    bank = project.experiments['current']
    before = np.array([
        float(row['_data.intensity_calc'])
        for row in loop_rows((source / 'experiments/current.edi').read_text(), '_data')
    ])
    np.testing.assert_array_equal(
        before,
        np.full(4, 1.23456789),
        err_msg='Zero scale and constant background give the independently authored pattern',
    )
    destination = source if operation == 'save' else tmp_path / 'saved'
    project = perform_save(project, source, destination, operation)
    bank = project.experiments['current']
    expected = np.full(4, 1.23457)
    np.testing.assert_array_equal(
        bank.data.intensity_calc,
        expected,
        err_msg='The live current bank recalculates from independently six-digit-rounded inputs',
    )
    assert not np.array_equal(before, expected), 'The rounding witness actually moves the pattern'
    values = (
        [point.intensity.value for point in bank.background]
        if kind == 'line-segment'
        else [term.coef.value for term in bank.background_terms]
    )
    assert values == ([1.23457, 1.23457] if kind == 'line-segment' else [1.23457]), (
        'The live current inputs adopt the rounded values used to calculate the saved pattern'
    )
    again = ENGINE.Project.load(destination)
    np.testing.assert_array_equal(
        again.experiments['current'].data.intensity_calc,
        expected,
        err_msg='Reopened current-bank calculated columns equal the live adopted pattern',
    )
    np.testing.assert_array_equal(
        fresh_pattern(destination, tmp_path / 'fresh-current'),
        expected,
        err_msg='A fresh independent current-only calculation reproduces the saved columns',
    )
    rows = loop_rows((destination / 'analysis/analysis.edi').read_text(), '_fit_result_bank')
    current = next(
        (row for row in rows if row['_fit_result_bank.experiment_id'] == 'current'), None
    )
    assert current is not None, 'The saved current bank retains a real agreement-factor record'
    reference = agreement(1.23457)
    for name, value in reference.items():
        assert float(current['_fit_result_bank.' + name]) == pytest.approx(
            float(format(value, '.6g')), rel=1e-12
        ), (
            'Saved agreement factors follow an independent weighted-residual calculation '
            'from rounded current inputs'
        )


@pytest.mark.parametrize('operation', OPERATIONS)
def test_adopting_save_of_measured_and_axis_only_banks_never_crashes_or_invents_agreement(
    tmp_path, operation
):
    source = mixed_measurements(tmp_path / 'input')
    destination = source if operation == 'save' else tmp_path / 'saved'
    paths = [str(Path(next(iter(ENGINE.__path__))).parent), *sys.path]
    extension = sys.modules[ENGINE.__name__ + '._' + ENGINE.__name__]
    environment = dict(os.environ)
    if ENGINE.__name__ == 'edi':
        environment['EDI_EXTENSION_DIR'] = str(Path(extension.__file__).parent)
    runner = Path(__file__).resolve().parents[2] / 'fixtures/project_save/measurement_save.py'
    result = subprocess.run(
        [
            sys.executable,
            '-S',
            str(runner),
            json.dumps(paths),
            ENGINE.__name__,
            str(source),
            str(destination),
            operation,
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'Saving a measured bank beside a simulated axis-only bank must finish without '
        'a native crash or refusal: ' + result.stderr
    )
    observed = json.loads(result.stdout.splitlines()[-1])
    assert observed['extension'] == str(Path(extension.__file__).resolve()), (
        'The crash-isolated consumer must use the same qualified native extension as its parent'
    )
    assert observed['banks']['current']['measured'] == 4, (
        'The mixed save retains every measured sample in its real observed bank'
    )
    simulated_data = loop_rows(observed['simulated_file'], '_data')
    assert all(row.get('_data.intensity_meas', '.') in {'.', '?'} for row in simulated_data), (
        'A saved simulated bank writes no invented measured intensities'
    )
    assert observed['banks']['due']['measured'] == 0, (
        'The simulated bank retains an axis without invented measured columns'
    )
    assert len(observed['banks']['due']['calculated']) == 4, (
        'The simulated bank still carries its calculated pattern on every requested axis point'
    )
    assert np.isfinite(observed['banks']['due']['calculated']).all(), (
        'A valid simulated bank retains finite calculated values without inventing measurements'
    )
    records = loop_rows(observed['analysis'], '_fit_result_bank')
    current = next(
        (row for row in records if row['_fit_result_bank.experiment_id'] == 'current'), None
    )
    assert current is not None, 'The real measured bank retains its agreement-factor record'
    simulated = [row for row in records if row['_fit_result_bank.experiment_id'] == 'due']
    for row in simulated:
        assert all(
            value in {'.', '?'}
            for key, value in row.items()
            if key not in {'_fit_result_bank.experiment_id', '_fit_result_bank.n_data_points'}
        ), 'A simulated bank has no agreement factors, rather than zero or fabricated observations'
        assert row.get('_fit_result_bank.n_data_points', '0') == '0', (
            'A simulated axis cannot contribute observed points to agreement statistics'
        )
    for key, value in agreement(1.23457).items():
        assert (
            float(current['_fit_result_bank.' + key]).hex() == float(format(value, '.6g')).hex()
        ), (
            'Measured-bank agreement uses independent residuals '
            'without reading simulated observations'
        )
