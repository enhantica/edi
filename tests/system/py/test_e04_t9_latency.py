"""O1-O5, L1-L10: run the test-owned real-publish measurement probe."""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def publication_measurements(tmp_path_factory):
    # Match 's statistical-experiment fixture: retain the complete real
    # probe and account its cost once through the existing module-cost instrument.
    tmp_path = tmp_path_factory.mktemp('-measurements')
    probe = ROOT / 'build/ci/core/e04_t9_latency_probe'
    assert probe.is_file(), ' P7 the hidden latency oracle must be built into the core gate'
    env = dict(
        os.environ,
        EDI_TEST_COMMIT=subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
        ).strip(),
    )
    result = subprocess.run(
        [str(probe), str(ROOT)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        # This is a hung-process ceiling, not a performance acceptance bound.
        # Match 's ceiling; all measured medians still reach the ratchet.
        timeout=120,
    )
    assert result.returncode == 0, (
        ' O2 L10 real publication presents the independently expected final state: '
        + result.stderr
    )
    output = tmp_path / 'latency-table.json'
    assert output.is_file(), ' L5 the real publish probe must persist its measured latency table'
    return output, env['EDI_TEST_COMMIT']


def test_real_publication_probe_reports_all_datasets_scenarios_and_requested_states(
    publication_measurements, tmp_path
):
    output, commit = publication_measurements
    table = json.loads(output.read_text())
    assert table['commit'] == commit, (
        ' L5 the measured table names the revision explicitly supplied to the real probe'
    )
    artifact = ROOT / 'build//latency-table.json'
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(output.read_bytes())
    print(output.read_text())
    assert table['samples'] >= 50 and table['warmups'] >= 5, (
        ' L2 each dataset scenario uses fifty samples after five discarded warmups'
    )
    identities = {(row['dataset'], row['scenario']) for row in table['rows']}
    assert identities == {(d, s) for d in ('D1', 'D2', 'D3') for s in ('S1', 'S2', 'S3')}, (
        ' L1 L5 all committed stress and view-change datasets are reported'
    )
    assert len(identities) == len(table['rows']), (
        ' L5 no duplicate row can hide an unmeasured scenario'
    )
    for row in table['rows']:
        for metric in ('latency', 'calculation', 'wait', 'overhead'):
            assert all(math.isfinite(row[metric][name]) for name in ('median_ms', 'p95_ms')), (
                ' L5 all measured statistics must be finite attributable numbers'
            )
        assert row['latency']['median_ms'] > 0, (
            ' O1 O2 measured completion must follow the test-owned start'
        )
        if row['scenario'] == 'S3':
            assert row['presentation']['median_ms'] > 0, (
                ' L6 view-change ratchet names measured presentation work'
            )
    bank = ROOT / 'tests/latency-bank.json'
    if not bank.is_file():
        assert not os.environ.get('CI'), ' L6 a CI machine requires its committed bank'
        bank = tmp_path / 'unbanked-hand-host.json'
        bank.write_text(json.dumps({'schema': 1, 'machines': {}}))
    checker = ROOT / 'tools/ci/latency_bank.py'
    assert checker.is_file(), ' L6 the measured table must reach the declared ratchet'
    compared = subprocess.run(
        [sys.executable, str(checker), '--check', '--table', str(output), '--bank', str(bank)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
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
        ' L6 actual measured medians satisfy the bank or report an unbanked hand host: '
        + compared.stdout
        + compared.stderr
    )
