"""A fit owns its Auto baseline; only data/settings invalidate that fitted baseline."""

# Saved Auto inputs now include the series basis in their independently authored
# provenance. The fit/retention assertions and numerical bounds remain unchanged.

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.fitted_baseline import (
    KINDS,
    curve,
    fit,
    load,
    refresh,
    stored_pattern,
    values,
)
from tests.fixtures.background_estimate.readonly import snapshot
from tests.fixtures.project_save.reference import six_digits


def assert_fitted_pattern(project):
    data = project.experiment.data
    calculated = np.asarray(data.intensity_calc)
    background = np.asarray(data.intensity_bkg)
    included = np.asarray(data.calc_status) == 'incl'
    assert included.any(), 'The fitted Auto pattern must include measured data points'
    assert np.isfinite(calculated[included]).all(), (
        'Fitted Auto must retain a finite calculated pattern on included measured points'
    )
    assert np.max(np.abs(calculated[included] - background[included])) > 1e-5, (
        'The fitted-baseline control must contain nonzero calculated crystal peaks'
    )
    np.testing.assert_allclose(
        background[included],
        curve(project)[included],
        rtol=1e-11,
        atol=1e-8,
        err_msg='The published background must evaluate the actual fitted points or coefficients',
    )


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('trigger', ['settings', 'data'])
@pytest.mark.parametrize('route', ['analysis', 'project'])
def test_auto_fit_retains_its_fitted_baseline_until_data_or_settings_change(
    tmp_path, kind, trigger, route
):
    control = load(engine, tmp_path / 'manual', kind)
    control.experiment.background_estimate.mode = 'manual'
    initial = snapshot(control)
    assert sum(parameter.free for parameter in control.parameters) == len(initial), (
        'Only the background rows may be free in the controlled Auto-versus-Manual fit'
    )
    fit(control, route)
    fitted_control = values(control)
    assert np.max(np.abs(fitted_control - np.asarray([r[2] for r in initial]))) > 1e-5, (
        'The Manual stimulus must actually change free background values; '
        f'{kind}: initial={[r[2] for r in initial]}, fitted={fitted_control.tolist()}'
    )
    project = load(engine, tmp_path / 'auto', kind)
    fit(project, route)
    fitted = snapshot(project)
    fitted_values = values(project)
    assert np.max(np.abs(fitted_values - np.asarray([r[2] for r in initial]))) > 1e-5, (
        'Auto itself must fit changed background values before retention can be judged; '
        f'{kind}: initial={[r[2] for r in initial]}, fitted={fitted_values.tolist()}'
    )
    assert [r[:2] for r in fitted] == [r[:2] for r in initial], (
        'An Auto fit must preserve row ids, positions/orders and layout while fitting values'
    )
    assert all(r[3] for r in fitted), (
        'An Auto fit must keep every explicitly freed background parameter free'
    )
    np.testing.assert_allclose(
        values(project),
        fitted_control,
        rtol=1e-11,
        atol=1e-8,
        err_msg='Auto and Manual must fit the same initial free parameters to the same values',
    )
    assert project.experiment.background_estimate.mode == 'auto', (
        'Fitting free background parameters must retain Auto estimation mode'
    )
    assert_fitted_pattern(project)
    fitted_rows = (
        project.experiment.background
        if kind == 'line-segment'
        else project.experiment.background_terms
    )
    parameter = fitted_rows[0].intensity if kind == 'line-segment' else fitted_rows[0].coef
    with pytest.raises(ValueError, match=r'(?i)manual') as refused:
        parameter.value += 1.25
    assert 'background' in str(refused.value).lower(), (
        'A genuine post-fit hand-edit refusal must name the background and required Manual mode'
    )
    assert snapshot(project) == fitted, (
        'Permitting fit write-back must not permit a later user value edit in Auto'
    )
    held = list(
        project.experiment.background
        if kind == 'line-segment'
        else project.experiment.background_terms
    )
    project.structure.cell.length_a.value += 0.00025
    project.analysis.calculate()
    assert snapshot(project) == fitted, (
        'A later calculation must neither refuse nor re-estimate the fitted Auto baseline'
    )
    current = list(
        project.experiment.background
        if kind == 'line-segment'
        else project.experiment.background_terms
    )
    assert all(a is b for a, b in zip(held, current, strict=True)), (
        'An unchanged Auto calculation must retain the fitted row objects without re-estimating'
    )
    assert_fitted_pattern(project)
    fitted_curve = curve(project).copy()
    refresh(project, engine, trigger)
    project.analysis.calculate()
    assert snapshot(project) != fitted, (
        'Changing measured data or estimate settings must replace the fitted Auto background'
    )
    assert np.max(np.abs(curve(project) - fitted_curve)) > 1e-5, (
        'A due post-fit refresh must change the actual background curve, not just row flags or ids'
    )
    assert project.experiment.background_estimate.mode == 'auto', (
        'A due re-estimate after fitting must retain Auto mode'
    )
    if trigger == 'settings':
        assert len(snapshot(project)) == (11 if kind == 'line-segment' else 1), (
            'The new saved point count or one-term cap must govern the post-fit settings refresh'
        )


@pytest.mark.parametrize('kind', KINDS)
def test_auto_value_edit_refusal_names_the_manual_mode_reason(tmp_path, kind):
    project = load(engine, tmp_path / 'auto', kind)
    before = snapshot(project)
    rows = (
        project.experiment.background
        if kind == 'line-segment'
        else project.experiment.background_terms
    )
    parameter = rows[0].intensity if kind == 'line-segment' else rows[0].coef
    with pytest.raises(ValueError, match=r'(?i)manual') as refused:
        parameter.value += 1.25
    reason = str(refused.value).lower()
    assert 'manual' in reason, (
        'An Auto edit refusal must explain that Manual mode permits editing: ' + reason
    )
    assert any(word in reason for word in ['background', 'point', 'term']), (
        'An Auto edit refusal must name the affected background: ' + reason
    )
    assert snapshot(project) == before, (
        'A reasoned Auto edit refusal must leave every stored value intact'
    )


@pytest.mark.parametrize('kind', KINDS)
def test_manual_control_reaches_the_same_fitted_pattern_and_saved_curve(tmp_path, kind):
    project = load(engine, tmp_path / 'manual', kind)
    project.experiment.background_estimate.mode = 'manual'
    fit(project)
    assert_fitted_pattern(project)
    project.save_as(tmp_path / 'saved')
    expected_curve = np.asarray([six_digits(value) for value in curve(project)])
    stored = stored_pattern(tmp_path / 'saved')
    assert len(stored) > 100, 'The Manual positive control must serialize its real fitted pattern'
    np.testing.assert_allclose(
        stored[:, 1],
        expected_curve,
        rtol=1e-11,
        atol=1e-8,
        err_msg='The saved Manual background must follow the adopted model and six-digit rule',
    )
