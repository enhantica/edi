"""Fit the declared single-crystal corpus against an independent weighted optimum."""

import shutil

import numpy as np
import pytest

from tests.conftest import corpus_case_dir
from tests.integration.py.test_single_crystal import (
    NO_EXTINCTION,
    REFERENCE,
    engine,
)


@pytest.mark.parametrize('case', NO_EXTINCTION)
def test_scale_fit_matches_independent_weighted_linear_solution(tmp_path, case):
    source = (
        corpus_case_dir(case.replace('sc-neut-', 'single-crystal-').replace('_', '-')) / 'project'
    )
    staged = tmp_path / 'fit'
    staged.mkdir()
    for name in ('structures', 'experiments'):
        (staged / name).symlink_to(source / name, target_is_directory=True)
    shutil.copytree(source / 'analysis', staged / 'analysis')
    model = engine().Project.load(staged)
    experiment = model.experiments[0]
    scale = experiment.linked_structure.scale
    original = float(scale.value) / 0.71
    reference = REFERENCE[case]
    basis = np.asarray([row['f2_calc'] for row in reference['calculated_rows']]) / original
    measured = np.asarray(reference['input_rows'])[:, 3]
    sigma = np.asarray(reference['input_rows'])[:, 4]
    expected = np.sum(basis * measured / sigma**2) / np.sum((basis / sigma) ** 2)
    expected_chi2 = np.sum(((measured - expected * basis) / sigma) ** 2) / (len(basis) - 1)
    scale.value = original * 0.71
    scale.free = True
    result = model.analysis.fit()
    assert float(scale.value) == pytest.approx(expected, rel=2e-4, abs=2e-5), (
        'A scale fit must reach the independent weighted least-squares optimum over all '
        'reflections'
    )
    assert result.reduced_chi_square == pytest.approx(expected_chi2, rel=3e-4, abs=0.002), (
        'Reported reduced chi-square must equal the all-reflection residual sum divided '
        'by N minus one'
    )
