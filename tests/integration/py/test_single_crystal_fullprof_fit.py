"""Fit measured reflections against the frozen FullProf fitting twins."""

import json
import shutil

import numpy as np
import pytest

from tests.integration.py.test_single_crystal import FIXTURE, calculated, engine

REFERENCES = json.loads((FIXTURE / 'fitting/fullprof.json').read_text())['cases']


@pytest.mark.parametrize('case', tuple(REFERENCES))
def test_fit_reaches_fullprof_scale_and_objective(tmp_path, case):
    reference = REFERENCES[case]
    source = FIXTURE / 'fitting/fullprof' / reference['project_id']
    expected = json.loads((source / 'expected.json').read_text())['quantities']
    destination = tmp_path / 'project'
    shutil.copytree(source / 'project', destination)
    model = engine().Project.load(destination)
    experiment = model.experiments[0]
    scale = experiment.linked_structure.scale
    assert float(scale.value) == pytest.approx(reference['start_scale'], rel=0, abs=1e-12), (
        'Each measured-data fit must start from the page scale'
    )
    assert scale.free, 'Each page requires a free scale'
    if 'extinction' in case:
        assert experiment.extinction.radius.free, 'The extinction page requires a free radius'
        assert not experiment.extinction.mosaicity.free, (
            'The extinction page keeps mosaicity fixed; the correlated pair must not '
            'be freed together'
        )
    assert len(experiment.refln.intensity_meas) == reference['n_selected'], (
        'The FullProf comparison must use exactly its observation selection'
    )
    result = model.analysis.fit()
    scale_reference = reference['parameters'][0]
    assert float(scale.value) == pytest.approx(
        scale_reference['value'],
        abs=scale_reference['su'] + 0.0000005,
        rel=0,
    ), 'The fitted scale must reach FullProf within its reported uncertainty'
    target = expected['reduced_chi_square']
    assert abs(result.reduced_chi_square - target['value']) <= target['tol_abs'], (
        'The fitted objective must reach the FullProf N-minus-p reference within '
        'its absolute numerical budget; empirical extinction remains a model mismatch'
    )
    assert abs(result.reduced_chi_square / target['value'] - 1) <= target['tol_rel'], (
        'The fitted objective must also satisfy the FullProf relative numerical budget'
    )
    observed = np.asarray(experiment.refln.intensity_meas)
    sigma = np.asarray(experiment.refln.intensity_meas_su)
    residual_sum = np.sum(((observed - calculated(model)) / sigma) ** 2)
    n_free = len(reference['parameters'])
    assert result.reduced_chi_square == pytest.approx(
        residual_sum / (len(observed) - n_free),
        rel=1e-9,
        abs=1e-9,
    ), 'The reported reduced objective must divide the fitted residual sum by N minus p'
