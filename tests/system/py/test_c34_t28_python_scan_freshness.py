"""I23: the declared three-frame scan retains pre-move freshness."""

import json
from pathlib import Path

from tests.fixtures.c34_t28_baseline import generate_freshness as reference

ROOT = Path(__file__).resolve().parents[3]


def test_scan_keeps_the_pre_move_freshness_regression_pin(tmp_path):
    baseline = json.loads((reference.HERE / 'freshness.json').read_text())
    observed = reference.observe('sequential', tmp_path / 'scan', ROOT)
    assert observed == baseline['routes']['sequential'], (
        ' I23 scan publication preserves exactly the old held and saved freshness'
    )
