"""gate 6: extension metadata follows the independent booklet comparison."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = json.loads((ROOT / 'tests/fixtures/c14_t4_neutron/rauch2003ext.json').read_text())


def test_named_default_extension_set_matches_booklet():
    # The served format rounds to four decimals; Si's rounding is not an extension.
    expected = sorted(
        element
        for element, row in REFERENCE['rows'].items()
        if row['b_real_fm'] != round(row['booklet_b_real_fm'], 4)
    )
    assert sorted(REFERENCE['extended_elements']) == expected, (
        ' gate 6 extensions must be exactly the independently measured booklet differences'
    )
