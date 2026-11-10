"""Owner 2026-11-03 catalogue delta; the earlier reference selection stays frozen.

The morning record adds the magnetic 2.3 K example after the nuclear CoSiO4
case. The 18:45 record replaces the app/tutorial scan by the 213-frame magnetic
scan, keeping the old project available for CLI fixtures and external references.
"""

import json
from pathlib import Path


def current_cases():
    original = json.loads((Path(__file__).parent / 'catalogue-selection.json').read_text())[
        'cases'
    ]
    result = []
    for previous in original:
        row = previous
        if row['id'] == 'pd-neut-cwl_cosio-d20_scan':
            row = dict(row, id='pd-neut-cwl_cosio-d20_scan-213f')
        result.append(row)
        if row['id'] == 'pd-neut-cwl_cosio-d20':
            result.append({'id': 'pd-neut-cwl_cosio-d20_2k', 'group': row['group']})
    return result
