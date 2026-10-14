"""Three page files are added; only the two LiF cases count toward parity."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = {
    'pd-xray-cwl_LiF_doublet',
    'pd-xray-cwl_LiF_single_absorption',
    'pd-xray-cwl_PbSO4_round-robin',
}


def test_xray_page_filename_delta_preserves_prior_pages_and_adds_exactly_three():
    before = set(
        json.loads((ROOT / 'tests/fixtures/xray_doublet/page-baseline.json').read_text())[
            'before_pages'
        ]
    )
    after = {path.stem for path in (ROOT / 'docs/dev/verification').glob('*.py')}
    assert before <= after, 'Adding the X-ray cases must preserve every existing verification page'
    assert after - before == OWNED, (
        'The filename counter must add exactly doublet, absorption and round-robin pages'
    )
    nonparity = {'pd-xray-cwl_PbSO4_round-robin'}
    assert (after - nonparity) - before == OWNED - nonparity, (
        'Diffraction-lib parity must move by exactly the doublet and absorption pages'
    )
    page = ROOT / 'docs/dev/verification/pd-xray-cwl_PbSO4_round-robin.py'
    prose = page.read_text().lower()
    assert 'regression pin' in prose and 'parity' in prose, (
        'The round-robin page must label its pins and explain its parity exclusion'
    )
