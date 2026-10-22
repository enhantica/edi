"""Every checked-in calculated example obeys the excluded-row convention."""

import subprocess
from pathlib import Path

from tests.integration.py.test_excluded_serialization import data_loop

ROOT = Path(__file__).resolve().parents[3]


def test_committed_examples_do_not_claim_excluded_zero_calculations():
    result = subprocess.run(
        ['git', 'ls-files', '-z', '*.edi'], cwd=ROOT, capture_output=True, check=True
    )
    problems = []
    for name in result.stdout.decode().split('\0'):
        if not name:
            continue
        path = ROOT / name
        text = path.read_text()
        if '_data.calc_status' not in text:
            continue
        _, rows = data_loop(text)
        for row in rows:
            if row.get('_data.calc_status') != 'excl':
                continue
            invalid = row.get('_data.d_spacing') in {None, '.', '?', '0', '0.'}
            invalid |= any(
                row.get('_data.' + column, '.') != '.'
                for column in ('intensity_calc', 'intensity_bkg', 'intensity_diff')
            )
            if invalid:
                problems.append(name)
                break
    assert not problems, (
        'Every committed calculated example must use physical d-spacing '
        'and absent excluded derived values: '
    ) + ', '.join(problems)
