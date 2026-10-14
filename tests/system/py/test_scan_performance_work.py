"""The declared same-host measurement is a gate, never an unverified printed table."""

import json
from pathlib import Path

from tests.fixtures.scan_timing.contract import compare, source_hashes, subject

ROOT = Path(__file__).resolve().parents[3]


def test_scan_performance_proves_complete_work_controls_and_the_owner_bound():
    path = ROOT / 'tests/fixtures/scan_timing/measurement.json'
    assert path.is_file(), (
        'The actual CLI and demo-driver measurements and real negative controls must be recorded'
    )
    receipt = json.loads(path.read_text())
    assert receipt['builds']['fixed']['source_sha256'] == source_hashes(ROOT), (
        'The measurement must cover all of the current product and timing observer source bytes'
    )
    spec = subject(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project')
    result = compare(receipt, spec)
    assert result['within_bound'], (
        'Every retained same-host Release median must be within baseline times 1.05: '
        + repr(result['failed'])
    )
