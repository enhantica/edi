"""measured real publication; M3 forbids absolute speed thresholds."""

import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def bank_module():
    spec = importlib.util.spec_from_file_location(
        'e04_t10_latency_bank', ROOT / 'tools/ci/latency_bank.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_structure_metrics_extend_the_existing_ratchet():
    table = {
        'rows': [
            {'dataset': dataset, 'scenario': scenario, metric: {'median_ms': 3.5, 'p95_ms': 90}}
            for dataset in ('T1', 'G1')
            for scenario, metric in (('V1', 'presentation'), ('V2', 'overhead'))
        ]
    }
    values = bank_module().table_medians(table)
    assert set(values) == {
        (dataset, scenario, metric)
        for dataset in ('T1', 'G1')
        for scenario, metric in (('V1', 'presentation'), ('V2', 'overhead'))
    }, ' M5 the existing bank compares both core structure medians'


@pytest.fixture(scope='module')
def structure_measurements(tmp_path_factory):
    # One full statistical experiment is shared by every dataset/scenario check.
    # Its real cost is recorded as module-cost by the existing fixture instrument.
    # No sample count, requested-state observer or measurement is removed.
    tmp_path = tmp_path_factory.mktemp('-measurements')
    probe = ROOT / 'build/ci/core/e04_t10_latency_probe'
    assert probe.is_file(), ' M2 hidden structure probe must be built into the core gate'
    env = dict(
        os.environ,
        EDI_TEST_COMMIT=subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
        ).strip(),
    )
    # The probe changes its working directory to the input root, so the table is
    # copied out from there after the actual measurement, never synthesized.
    result = subprocess.run(
        [str(probe), str(ROOT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, (
        ' M6 actual publication presents the independently requested state: ' + result.stderr
    )
    table = json.loads(result.stdout)
    emitted = tmp_path / 'latency-table.json'
    assert emitted.is_file(), ' M4 real probe writes the common latency-bank input artifact'
    assert json.loads(emitted.read_text()) == table, (
        ' M4 the persisted bank input equals the actually measured stdout table'
    )
    return table, env, tmp_path


def test_real_structure_probe_reports_requested_state_and_measured_statistics(
    structure_measurements,
):
    table, env, tmp_path = structure_measurements
    assert table['samples'] == 50 and table['warmups'] == 5, (
        ' M2 each metric has fifty samples after five discarded warmups'
    )
    assert table['commit'] == env['EDI_TEST_COMMIT'], (
        ' M4 measured table is attributable to the executed product head'
    )
    assert {(row['dataset'], row['scenario']) for row in table['rows']} == {
        (dataset, scenario) for dataset in ('T1', 'G1') for scenario in ('V1', 'V2')
    }, ' M1 M2 both named datasets exercise real presentation and real updates'
    assert len(table['rows']) == 4, ' M4 duplicate rows cannot hide an unmeasured scenario'
    output = tmp_path / 'structure-latency-table.json'
    output.write_text(json.dumps(table))
    bank = ROOT / 'tests/latency-bank.json'
    if not bank.is_file():
        assert not os.environ.get('CI'), ' M5 CI requires committed structure latency banks'
        bank = tmp_path / 'unbanked-hand.json'
        bank.write_text(json.dumps({'schema': 1, 'machines': {}}))
    compared = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tools/ci/latency_bank.py'),
            '--check',
            '--table',
            str(output),
            '--bank',
            str(bank),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415 - defer cross-module test wiring
        jobs,
        public_profile,
    )

    banked = json.loads(bank.read_text())['machines'].get(table['machine'])
    if public_profile(jobs()) and not banked:
        assert compared.returncode != 0 and 'a CI machine is banked before it gates' in (
            compared.stdout + compared.stderr
        ), 'hosted latency reporting must retain the explicit unbanked-machine refusal'
        print('Hosted hardware has no committed latency bank; measured table retained')
        return
    assert compared.returncode == 0, (
        ' M5 measured structure medians reach the existing bank comparison: '
        + compared.stdout
        + compared.stderr
    )


@pytest.mark.parametrize('dataset', ['T1', 'G1'])
@pytest.mark.parametrize('scenario', ['V1', 'V2'])
def test_real_structure_metric_statistics(structure_measurements, dataset, scenario):
    table, _, _ = structure_measurements
    matches = [
        row for row in table['rows'] if row['dataset'] == dataset and row['scenario'] == scenario
    ]
    assert len(matches) == 1, ' M4 each independently named measurement has exactly one row'
    row = matches[0]
    for metric in (
        ('presentation',) if scenario == 'V1' else ('latency', 'calculation', 'overhead')
    ):
        stats = row[metric]
        assert 0 <= stats['median_ms'] <= stats['p95_ms'] and math.isfinite(stats['p95_ms']), (
            ' M4 monotonic timing statistics are finite without absolute speed limits'
        )
