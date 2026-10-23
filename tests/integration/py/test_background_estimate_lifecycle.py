"""Estimation provenance, model publication and edits before the first calculation."""

from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.conftest import corpus_case_dir
from tests.fixtures.background_estimate.lifecycle import (
    edit,
    expected_background,
    model_input,
    persisted_points,
    prime,
)
from tests.fixtures.background_estimate.settings import (
    DEFAULTS,
    configured_project,
    points,
    read_settings,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = corpus_case_dir('lbco-hrpt-s2') / 'project'


def test_nonzero_model_publication_uses_the_live_automatic_points(tmp_path):
    project = prime(engine, tmp_path / 'input', SOURCE)
    assert np.any(
        np.abs(
            np.asarray(project.experiment.data.intensity_calc)
            - np.asarray(project.experiment.data.intensity_bkg)
        )
        > 1e-8
    ), 'The host/engine consistency witness must start with nonzero calculated peaks'
    project.analysis.calculate()
    actual = np.asarray(project.experiment.data.intensity_bkg)
    expected = expected_background(project)
    included = np.asarray(project.experiment.data.calc_status) == 'incl'
    assert np.allclose(actual[included], expected[included], rtol=1e-12, atol=1e-9), (
        'A calculation must publish the piecewise-linear background of its visible auto points; '
        'a converted engine must not estimate a second background'
    )


def test_nonzero_model_delegated_save_keeps_the_visible_estimate(tmp_path):
    project = prime(engine, tmp_path / 'input', SOURCE)
    project.analysis.calculate()
    before = points(project)
    project.save_as(tmp_path / 'saved')
    assert persisted_points(tmp_path / 'saved', experiment='hrpt') == [
        row[:2] for row in before
    ], (
        'Delegated save must serialize the live model-guided points '
        'without a second engine estimate'
    )
    assert points(project) == before, (
        'Saving a guided automatic estimate must not mutate live points'
    )


def test_nonzero_auto_reload_calculates_without_replacing_persisted_points(tmp_path):
    project = engine.Project.load(model_input(tmp_path / 'input', SOURCE, mode='auto'))
    project.analysis.calculate()
    assert np.any(
        np.abs(
            np.asarray(project.experiment.data.intensity_calc)
            - np.asarray(project.experiment.data.intensity_bkg)
        )
        > 1e-8
    ), 'Reload stability must include a nonzero calculated model rather than a data-only control'
    project.save_as(tmp_path / 'saved')
    reopened = engine.Project.load(tmp_path / 'saved')
    before = points(reopened)
    held = list(reopened.experiment.background)
    reopened.analysis.calculate()
    assert points(reopened) == before, (
        'Unchanged auto data and settings must retain the saved points '
        'after reload and calculation'
    )
    assert all(a is b for a, b in zip(held, reopened.experiment.background, strict=True)), (
        'An unchanged loaded auto project must not replace its saved rows with another estimate'
    )


@pytest.mark.parametrize('kind', ['position', 'intensity', 'free', 'add', 'remove'])
@pytest.mark.parametrize('transition', [False, True], ids=['loaded-auto', 'manual-to-auto'])
@pytest.mark.parametrize('operation', ['save', 'calculate'])
def test_first_auto_flags_toggle_but_other_edits_require_explicit_manual(
    tmp_path, kind, transition, operation
):

    values = {**DEFAULTS, 'mode': 'manual' if transition else 'auto'}
    project = engine.Project.load(configured_project(tmp_path / 'input', values))
    if transition:
        project.experiment.background_estimate.mode = 'auto'
    # First-operation controls exercise allowed flags separately from forbidden values.
    before = points(project)
    # Before: free was refused. After: either free/fixed direction is permitted in Auto.
    if kind == 'free':
        edit(project, engine, kind)
        expected_flag = [(*before[0][:-1], not before[0][-1]), *before[1:]]
        assert points(project) == expected_flag, (
            'Auto must permit a free/fixed toggle without changing point values or layout'
        )
        assert project.experiment.background_estimate.mode == 'auto', (
            'A permitted free/fixed toggle must preserve Auto before the next operation'
        )
        edit(project, engine, kind)
    else:
        with pytest.raises(ValueError, match=r'(?i)manual'):
            edit(project, engine, kind)
    assert points(project) == before, (
        'A reverse free toggle or refused value edit must preserve the original Auto points'
    )
    assert project.experiment.background_estimate.mode == 'auto', (
        'Permitted flag toggles and refused value edits must leave Auto selected'
    )
    project.experiment.background_estimate.mode = 'manual'
    edit(project, engine, kind)
    expected = points(project)
    observed_mode = project.experiment.background_estimate.mode
    if operation == 'calculate':
        project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    assert observed_mode == 'manual', (
        'A first edit must succeed after an explicit Manual choice, including after choosing Auto'
    )
    assert read_settings(tmp_path / 'saved')['mode'] == 'manual', (
        'The first operation after a hand edit must persist manual mode'
    )
    assert points(project) == expected, (
        'The first operation must retain every hand-edited point value'
    )
    assert points(engine.Project.load(tmp_path / 'saved')) == expected, (
        'Saving and reloading the first manual edit must preserve every point exactly'
    )


def test_hand_edit_with_no_measured_data_stays_manual_when_data_arrive(tmp_path):
    project = engine.Project.load(configured_project(tmp_path / 'input'))
    data = project.experiment.data
    axis = np.asarray(data.two_theta).copy()
    y = np.asarray(data.intensity_meas).copy()
    sigma = np.asarray(data.intensity_meas_su).copy()
    project.experiment.data = engine.PdCwlData(
        two_theta=[], intensity_meas=[], intensity_meas_su=[]
    )
    with pytest.raises(ValueError, match=r'(?i)manual'):
        edit(project, engine, 'intensity')
    project.experiment.background_estimate.mode = 'manual'
    edit(project, engine, 'intensity')
    expected = points(project)
    observed_mode = project.experiment.background_estimate.mode
    project.experiment.data = engine.PdCwlData(
        two_theta=axis, intensity_meas=y, intensity_meas_su=sigma
    )
    project.analysis.calculate()
    assert observed_mode == 'manual', (
        'An empty-data load must permit the edit only after the explicit Manual selection'
    )
    assert points(project) == expected, (
        'Arriving measurements must preserve the pending manual edit'
    )
