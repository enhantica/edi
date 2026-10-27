"""Saved settings and automatic refresh are project invariants."""

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.settings import (
    DEFAULTS,
    REFERENCE,
    configured_project,
    points,
    read_settings,
    require_reference,
    write_settings,
)
from tests.fixtures.project_save.reference import six_digits

ROUNDTRIPS = [
    {**DEFAULTS, 'mode': 'manual', 'method': 'auto', 'use_model': 'subtract'},
    DEFAULTS,
    {
        **DEFAULTS,
        'mode': 'manual',
        'method': 'fabc',
        'width': 7.25,
        'smoothness': 12345.5,
        'tolerance': 0.75,
        'in_peaks': 'move',
        'n_points': 9,
    },
    {
        **DEFAULTS,
        'method': 'arpls',
        'width': 11.5,
        'smoothness': 4321.25,
        'n_points': 7,
        'use_model': 'subtract',
    },
]


@pytest.mark.parametrize(
    'settings',
    ROUNDTRIPS,
    ids=['manual-derived', 'auto-derived', 'manual-explicit', 'auto-explicit'],
)
def test_settings_and_saved_points_roundtrip_exactly(tmp_path, settings):
    project = engine.Project.load(configured_project(tmp_path / 'input', settings))
    original = points(project)
    first = tmp_path / 'first'
    project.save_as(first)
    assert read_settings(first) == settings, (
        'Saving must retain mode, method, optional overrides and use_model exactly'
    )
    reopened = engine.Project.load(first)
    assert points(reopened) == original, (
        'Loading saved settings must retain every saved background point'
    )
    second = tmp_path / 'second'
    reopened.save_as(second)
    assert read_settings(second) == settings, (
        'A reload and second save must preserve the complete category'
    )


@pytest.mark.parametrize('method', ['arpls', 'snip', 'fabc'])
def test_auto_calculation_uses_saved_derived_settings(tmp_path, method):
    settings = {**DEFAULTS, 'method': method}
    project = engine.Project.load(configured_project(tmp_path / 'input', settings))
    project.analysis.calculate()
    actual = points(project)
    require_reference([row[:2] for row in actual], method)
    project.analysis.calculate()
    assert points(project) == actual, (
        'Unchanged automatic inputs must retain the same points exactly'
    )
    project.save_as(tmp_path / 'saved')
    assert read_settings(tmp_path / 'saved') == settings, (
        'Resolving derived values must leave the saved overrides blank'
    )


def test_manual_mode_keeps_saved_points_during_calculation(tmp_path):
    settings = {**DEFAULTS, 'mode': 'manual'}
    project = engine.Project.load(configured_project(tmp_path / 'input', settings))
    original = points(project)
    project.analysis.calculate()
    assert points(project) == original, (
        'Manual mode must calculate with the saved points without estimating'
    )


def test_saved_setting_change_invalidates_the_previous_estimate(tmp_path):
    project = engine.Project.load(configured_project(tmp_path / 'input'))
    project.analysis.calculate()
    original = points(project)
    saved = tmp_path / 'saved'
    project.save_as(saved)
    override = REFERENCE['cases']['hrpt']['methods']['arpls']['override']['options']
    settings = {**DEFAULTS, **override, 'method': 'arpls'}
    write_settings(saved, settings)
    reloaded = engine.Project.load(saved)
    reloaded.analysis.calculate()
    assert points(reloaded) != original, (
        'Changed stored estimator settings must invalidate the previous points'
    )
    require_reference([row[:2] for row in points(reloaded)], 'arpls', variant='override')


def test_data_replacement_refreshes_auto_like_an_explicit_call(tmp_path):
    project = engine.Project.load(configured_project(tmp_path / 'input'))
    project.analysis.calculate()
    original = points(project)
    data = project.experiment.data
    axis = np.asarray(data.two_theta).copy()
    measured = np.asarray(data.intensity_meas).copy() + 13.25
    sigma = np.asarray(data.intensity_meas_su).copy()
    project.experiment.data = engine.PdCwlData(
        two_theta=axis, intensity_meas=measured, intensity_meas_su=sigma
    )
    project.analysis.calculate()
    actual = points(project)
    assert actual != original, (
        'Replacing measured intensities must invalidate automatic background points'
    )
    control = engine.Project.load(
        configured_project(tmp_path / 'control', {**DEFAULTS, 'mode': 'manual'})
    )
    control.experiment.data = engine.PdCwlData(
        two_theta=axis, intensity_meas=measured, intensity_meas_su=sigma
    )
    control.experiment.background.auto_estimate(
        method='snip', use_model=False, tolerance=2.0, in_peaks='drop'
    )
    assert actual == points(control), (
        'Automatic refresh and an explicit call must agree on identical changed input data'
    )


@pytest.mark.parametrize('field', ['position', 'intensity', 'free'])
def test_auto_point_flags_toggle_but_values_need_manual_before_calculation(tmp_path, field):
    # Auto permits fit flags; value and position edits still require explicit Manual.
    project = engine.Project.load(configured_project(tmp_path / 'input'))
    project.analysis.calculate()
    before = points(project)
    point = project.experiment.background[0]

    def change():
        if field == 'position':
            point.position += 0.0625
        elif field == 'intensity':
            point.intensity.value += 0.125
        else:
            point.intensity.free = not point.intensity.free

    # Before: free was refused. After: either free/fixed direction is permitted in Auto.
    if field == 'free':
        change()
        expected_flag = [(*before[0][:-1], not before[0][-1]), *before[1:]]
        assert points(project) == expected_flag, (
            'Auto must permit a free/fixed toggle without changing point values or layout'
        )
        assert project.experiment.background_estimate.mode == 'auto', (
            'A permitted free/fixed toggle must preserve Auto before the next operation'
        )
        change()
    else:
        with pytest.raises(ValueError, match=r'(?i)manual'):
            change()
    assert points(project) == before, (
        'A reverse free toggle or refused value edit must preserve the original Auto points'
    )
    assert project.experiment.background_estimate.mode == 'auto', (
        'Permitted flag toggles and refused value edits must leave Auto selected'
    )
    project.experiment.background_estimate.mode = 'manual'
    change()
    edited = points(project)
    project.save_as(tmp_path / 'edited')
    assert read_settings(tmp_path / 'edited')['mode'] == 'manual', (
        'An explicit Manual selection must persist with the permitted point edit'
    )
    project.analysis.calculate()
    expected = [(x, six_digits(y), free) for x, y, free in edited]
    assert points(project) == expected, (
        'After Save a calculation retains the independently rounded Manual edit and flags'
    )


def test_legacy_authored_settings_leave_new_optional_items_undeclared(tmp_path):
    legacy = {
        name: value for name, value in DEFAULTS.items() if name not in {'tolerance', 'in_peaks'}
    }
    source = configured_project(tmp_path / 'input', legacy)
    project = engine.Project.load(source)
    assert project.experiment.background_estimate.tolerance is None, (
        'Existing six-field authored inputs must leave the new tolerance derived'
    )
    assert project.experiment.background_estimate.in_peaks == 'move', (
        'An undeclared replacement rule in an existing input must use the new public default'
    )
    assert project.experiment.background_estimate.use_model == 'ignore', (
        'Adding optional settings must preserve explicitly authored prior settings'
    )
