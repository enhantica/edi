"""L6-L8: handwritten medians banks, independent of measured product speed."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / 'tools/ci/latency_bank.py'


def inputs(machine='test-runner'):
    table = {
        'schema': 1,
        'machine': machine,
        'commit': 'a' * 40,
        'samples': 50,
        'warmups': 5,
        'rows': [],
    }
    rows = []
    for dataset in ('D1', 'D2', 'D3'):
        for scenario in ('S1', 'S2', 'S3'):
            row = {'dataset': dataset, 'scenario': scenario}
            metrics = ('presentation',) if scenario == 'S3' else ('latency', 'overhead')
            row.update({key: {'median_ms': 10.0, 'p95_ms': 2000.0} for key in metrics})
            table['rows'].append(row)
            rows.append({
                'dataset': dataset,
                'scenario': scenario,
                'commit': 'a' * 40,
                'run': '123/1',
                'metrics': {
                    key: {
                        'banked_ms': 10.0,
                        'margin_ms': 2.0,
                        'values_ms': [9.5, 9.6, 9.7, 9.8, 10.0, 10.0, 10.2, 10.3, 10.4, 10.5],
                    }
                    for key in metrics
                },
            })
    return table, {'schema': 1, 'machines': {machine: {'rows': rows}}}


def check(tmp_path, table, bank, *, ci=True):
    assert TOOL.is_file(), ' L6 the accepted latency bank checker must exist'
    table_path, bank_path = tmp_path / 'table.json', tmp_path / 'bank.json'
    table_path.write_text(json.dumps(table))
    bank_path.write_text(json.dumps(bank))
    env = os.environ.copy()
    if ci:
        env['CI'] = 'true'
        env['RUNNER_NAME'] = table['machine']
    else:
        env.pop('CI', None)
        env.pop('RUNNER_NAME', None)
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            '--check',
            '--table',
            str(table_path),
            '--bank',
            str(bank_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=tmp_path,
    )


@pytest.mark.parametrize('value', [8.0, 10.0, 12.0])
def test_inclusive_margin_passes_without_absolute_speed_limits(tmp_path, value):
    table, bank = inputs()
    for row in table['rows']:
        for metric in ('latency', 'overhead', 'presentation'):
            if metric in row:
                row[metric]['median_ms'] = value
    result = check(tmp_path, table, bank)
    assert result.returncode == 0, (
        ' L4 L6 inclusive bank margins pass and reported p95 targets never reject'
    )


@pytest.fixture(scope='module')
def ratcheted_median_results(tmp_path_factory):
    # Retain every CLI input; account for their process startup once as a module cost.
    directory = tmp_path_factory.mktemp('ratcheted-medians')
    results = {}
    for template in inputs()[0]['rows']:
        dataset, scenario = template['dataset'], template['scenario']
        for metric in ('latency', 'overhead', 'presentation'):
            if metric not in template:
                continue
            for value, reason in ((12.001, 'regression'), (7.999, 're-bank')):
                table, bank = inputs()
                for row in table['rows']:
                    if row['dataset'] == dataset and row['scenario'] == scenario:
                        row[metric]['median_ms'] = value
                case = directory / f'{dataset}-{scenario}-{metric}-{reason}'
                case.mkdir()
                results[dataset, scenario, metric, value, reason] = check(case, table, bank)
    return results


@pytest.mark.parametrize('dataset', ['D1', 'D2', 'D3'])
@pytest.mark.parametrize(
    ('scenario', 'metric'),
    [
        ('S1', 'latency'),
        ('S1', 'overhead'),
        ('S2', 'latency'),
        ('S2', 'overhead'),
        ('S3', 'presentation'),
    ],
)
@pytest.mark.parametrize(('value', 'reason'), [(12.001, 'regression'), (7.999, 're-bank')])
def test_each_ratcheted_median_rejects_slowdowns_and_reports_faster_rebank_due(
    ratcheted_median_results, dataset, scenario, metric, value, reason
):
    # Decision 2026-10-03 (development hub ): before, both out-of-margin directions
    # failed; after, regressions still fail and faster medians pass with a named notice.
    result = ratcheted_median_results[dataset, scenario, metric, value, reason]
    if reason == 'regression':
        assert result.returncode != 0, (
            ' L6 every declared dataset and median metric rejects an out-of-margin change'
        )
        assert reason in (result.stdout + result.stderr).lower(), (
            ' L6 failures distinguish regressions from improvements that owe re-banking'
        )
    else:
        assert result.returncode == 0, (
            ' L6 the 2026-10-03 decision lets faster out-of-margin medians pass'
        )
        assert f'{dataset} {scenario} {metric}: re-bank due:' in (result.stdout + result.stderr), (
            ' L6 a faster median names its dataset scenario metric and re-bank due'
        )


@pytest.mark.parametrize('route', ['machine', 'row', 'metric', 'nan', 'bank_nan', 'margin_nan'])
def test_ci_missing_or_untrustworthy_values_refuse(tmp_path, route):
    table, bank = inputs()
    if route == 'machine':
        bank['machines'].clear()
    elif route == 'row':
        bank['machines']['test-runner']['rows'].pop()
    elif route == 'metric':
        bank['machines']['test-runner']['rows'][0]['metrics'].pop('overhead')
    elif route == 'bank_nan':
        bank['machines']['test-runner']['rows'][0]['metrics']['latency']['banked_ms'] = float(
            'nan'
        )
    elif route == 'margin_nan':
        bank['machines']['test-runner']['rows'][0]['metrics']['latency']['margin_ms'] = float(
            'nan'
        )
    else:
        table['rows'][0]['latency']['median_ms'] = float('nan')
    result = check(tmp_path, table, bank)
    assert result.returncode != 0, (
        ' L6 CI refuses missing machine rows metrics and nonfinite median evidence'
    )


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
def test_writer_refuses_nonfinite_measurement_values(tmp_path, value):
    assert TOOL.is_file(), ' L7 the noise writer must reject untrustworthy input evidence'
    directory = tmp_path / 'measurements'
    directory.mkdir()
    for number in range(10):
        table, _bank = inputs()
        table['rows'][0]['latency']['median_ms'] = value
        (directory / f'run-{number:02}.json').write_text(json.dumps(table))
    output = tmp_path / 'bank.json'
    result = subprocess.run(
        [sys.executable, str(TOOL), '--measurements', str(directory), '--bank', str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0 and not output.exists(), (
        ' L7 L8 nonfinite run values refuse before any bank is written'
    )


def test_unbanked_hand_host_reports_without_comparison(tmp_path):
    table, bank = inputs('hand:test-host')
    bank['machines'].clear()
    result = check(tmp_path, table, bank, ci=False)
    assert result.returncode == 0, (
        ' L6 a hand host without a bank reports without claiming comparison'
    )


def test_checker_does_not_rewrite_evidence_or_bank(tmp_path):
    table, bank = inputs()
    expected = copy.deepcopy(bank)
    result = check(tmp_path, table, bank)
    assert result.returncode == 0, ' L6 check is separate from the ten-run banking writer'
    assert json.loads((tmp_path / 'bank.json').read_text()) == expected, (
        ' L8 checking a passing sample cannot silently re-bank it'
    )


@pytest.mark.parametrize(
    ('values', 'margin'),
    [([10.0] * 10, 1.0), ([9.5, 9.6, 9.7, 9.8, 10.0, 10.0, 10.2, 10.3, 10.4, 10.5], 2.0)],
)
def test_banking_uses_ten_run_median_and_closed_form_noise_margin(tmp_path, values, margin):
    assert TOOL.is_file(), ' L7 the ten-run noise banking writer must exist'
    directory = tmp_path / 'measurements'
    directory.mkdir()
    for number, value in enumerate(values):
        table, _bank = inputs()
        for row in table['rows']:
            for metric in ('latency', 'overhead', 'presentation'):
                if metric in row:
                    row[metric]['median_ms'] = value
        (directory / f'run-{number:02}.json').write_text(json.dumps(table))
    output = tmp_path / 'bank.json'
    result = subprocess.run(
        [sys.executable, str(TOOL), '--measurements', str(directory), '--bank', str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, ' L8 ten retained measurement tables form the initial bank'
    bank = json.loads(output.read_text())
    for row in bank['machines']['test-runner']['rows']:
        for metric in row['metrics'].values():
            assert metric['banked_ms'] == 10.0, ' L8 banked metric is the ten-run median'
            assert metric['margin_ms'] == margin, ' L7 margin uses the floor and twice spread'
            assert metric['values_ms'] == values, ' L7 noise provenance retains ten run values'


@pytest.mark.parametrize(('previous', 'allowed'), [(9.0, False), (11.0, True)])
def test_banking_down_is_free_and_up_needs_a_named_decision(tmp_path, previous, allowed):
    assert TOOL.is_file(), ' L8 changing a bank requires the declared banking writer'
    directory = tmp_path / 'measurements'
    directory.mkdir()
    table, bank = inputs()
    for number in range(10):
        (directory / f'run-{number:02}.json').write_text(json.dumps(table))
    for row in bank['machines']['test-runner']['rows']:
        row['commit'] = 'b' * 40
        for metric in row['metrics'].values():
            metric['banked_ms'] = previous
            metric['values_ms'] = [value + previous - 10 for value in metric['values_ms']]
    output = tmp_path / 'bank.json'
    before = json.dumps(bank)
    output.write_text(before)
    result = subprocess.run(
        [sys.executable, str(TOOL), '--measurements', str(directory), '--bank', str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (result.returncode == 0) == allowed, (
        ' L8 bank decreases freely and increases refuse without a committed decision'
    )
    if not allowed:
        assert output.read_text() == before, (
            ' L8 a refused bank increase leaves prior evidence unchanged'
        )
