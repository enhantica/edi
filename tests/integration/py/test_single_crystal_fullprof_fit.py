"""Fit measured reflections against independent model-equivalent fitting references."""

import json
import shutil

import numpy as np
import pytest

from tests.conftest import corpus_case_dir
from tests.integration.py.test_single_crystal import FIXTURE, calculated, engine

REFERENCES = json.loads((FIXTURE / 'fitting/fullprof.json').read_text())['cases']


def _staged_reference_project(tmp_path, case, expected):
    destination = tmp_path / 'project'
    case_id = 'single-crystal-page-' + case.removeprefix('sc-neut-').replace('_', '-')
    corpus = corpus_case_dir(case_id) / 'project'
    assert json.loads((corpus.parent / 'expected.json').read_text())['quantities'] == {
        key: dict(value, tol_abs=value.get('tol_abs'), tol_rel=value.get('tol_rel'))
        for key, value in expected.items()
    }, 'The shared selected-observation corpus must retain the independent reference quantities'
    destination.mkdir()
    for name in ('structures', 'experiments'):
        (destination / name).symlink_to(corpus / name, target_is_directory=True)
    shutil.copytree(corpus / 'analysis', destination / 'analysis')
    return engine().Project.load(destination)


@pytest.mark.parametrize('case', tuple(REFERENCES))
def test_fit_reaches_fullprof_scale_and_objective(tmp_path, case):
    reference = REFERENCES[case]
    source = FIXTURE / 'fitting/fullprof' / reference['project_id']
    if 'extinction' in case:
        source = FIXTURE / 'fitting/becker-coppens' / reference['project_id']
        reference = dict(
            reference, parameters=json.loads((source / 'reference.json').read_text())['parameters']
        )
    expected = json.loads((source / 'expected.json').read_text())['quantities']
    model = _staged_reference_project(tmp_path, case, expected)
    experiment = model.experiments[0]
    scale = experiment.linked_structure.scale
    assert float(scale.value) == pytest.approx(reference['start_scale'], rel=0, abs=1e-12), (
        'Each measured-data fit must start from the page scale'
    )
    assert scale.free, 'Each page requires a free scale'
    if 'extinction' in case:
        assert experiment.extinction.domain_radius.free, (
            'The extinction page requires a free radius'
        )
        assert not experiment.extinction.mosaic_spread.free, (
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
    ), 'The fitted scale must reach the model-equivalent reference within its uncertainty'
    if 'extinction' in case:
        radius_reference = reference['parameters'][1]
        assert float(experiment.extinction.domain_radius.value) == pytest.approx(
            radius_reference['value'],
            abs=radius_reference['su'],
            rel=0,
        ), 'The fitted radius must reach the independent Becker-Coppens value within its s.u.'
    target = expected['reduced_chi_square']
    assert abs(result.reduced_chi_square - target['value']) <= target['tol_abs'], (
        'The fitted objective must reach the independent N-minus-p reference within '
        'its unchanged absolute numerical budget'
    )
    assert abs(result.reduced_chi_square / target['value'] - 1) <= target['tol_rel'], (
        'The fitted objective must also satisfy the unchanged relative numerical budget'
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


def test_joint_larson_constraints_recover_closed_form_values(tmp_path):
    source = corpus_case_dir('single-crystal-joint-larson') / 'project'
    staged = tmp_path / 'joint'
    staged.mkdir()
    for name in ('structures', 'experiments'):
        (staged / name).symlink_to(source / name, target_is_directory=True)
    shutil.copytree(source / 'analysis', staged / 'analysis')
    p = engine().Project.load(staged)
    result = p.analysis.fit()
    assert result.reduced_chi_square < 1e-10, (
        'Joint Larson fit must recover exact closed-form observations'
    )
    for experiment, scale in zip(p.experiments, (1.7, 0.8), strict=True):
        assert experiment.linked_structure.scale.value == pytest.approx(scale, rel=1e-7), (
            'Each joint single-crystal experiment must retain its independent scale'
        )
        assert experiment.extinction.coefficient.value == pytest.approx(600, rel=1e-7), (
            'Cross-experiment extinction equality must fit the one shared crystal coefficient'
        )
