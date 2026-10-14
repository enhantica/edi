"""Fitted profile metrics compared with a committed FullProf summary."""

import re
from pathlib import Path

from conftest import corpus_case_dir
from tests.system.py.test_latest_fit_uncertainty import ENGINE
from tests.system.py.test_powder_r_factors import record


def test_fitted_lbco_factors_agree_with_the_committed_fullprof_summary(tmp_path):
    root = Path(__file__).resolve().parents[3]
    case = root / 'tests/fixtures/fit_quality'
    summary = (case / 'lbco.sum').read_text()
    match = re.search(r'Rp:\s+([\d.]+)\s+Rwp:\s+([\d.]+)\s+Rexp:\s+([\d.]+)', summary)
    assert match is not None, (
        'The independent FullProf summary must supply its printed profile factors'
    )
    expected = dict(
        zip(
            ('prof_r_factor', 'prof_wr_factor', 'prof_wr_expected'),
            map(float, match.groups()),
            strict=True,
        )
    )
    source = corpus_case_dir('lbco-hrpt-s2') / 'project'
    project = ENGINE.Project.load(source)
    project.analysis.fit()
    _, banks = record(project, tmp_path / 'saved')
    assert len(banks) == 1, 'The fitted FullProf comparison must retain its single experiment row'
    # The existing LBCO corpus records Rwp=0.07233610852 against FullProf 7.22 percent.
    # Four times that pre-task model discrepancy plus printed rounding is the comparison envelope.
    allowance = 4 * abs(100 * 0.07233610852 - expected['prof_wr_factor']) + 0.005
    for field, value in expected.items():
        assert '_fit_result_bank.' + field in banks[0], (
            'The fitted FullProf comparison must expose every profile factor'
        )
        assert abs(100 * float(banks[0]['_fit_result_bank.' + field]) - value) <= allowance, (
            'The fitted profile factors must agree with the independent FullProf '
            f'summary within the recorded model envelope: {field} obtained '
            f'{100 * float(banks[0]["_fit_result_bank." + field]):.12g}%, '
            f'expected {value:.12g}%, allowance {allowance:.12g} percentage points'
        )
