"""Public defaults and saved overrides, independent of implementation-selected anchors."""

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.project import materialize
from tests.fixtures.background_estimate.settings import REFERENCE, points


def blank(tmp_path):
    return engine.Project.load(materialize(tmp_path, REFERENCE['cases']['hrpt']))


def test_blank_project_retains_the_new_defaults_through_two_saves(tmp_path):
    # Before: unconditional subtraction. After: the saved three-way choice defaults to auto.
    project = blank(tmp_path / 'input')
    for turn in range(2):
        settings = project.experiment.background_estimate
        assert settings.tolerance in {None, 2.0}, (
            'A blank project must resolve to twice-noise tolerance; a blank override stays derived'
        )
        assert settings.in_peaks == 'move', (
            'Blank projects must save and load the replacement rule'
        )
        assert settings.use_model == 'auto', (
            'Blank projects must save and load automatic calculated-peak selection'
        )
        project.save_as(tmp_path / f'saved-{turn}')
        project = engine.Project.load(tmp_path / f'saved-{turn}')
    project.experiment.background_estimate.tolerance = 0.5
    project.save_as(tmp_path / 'explicit')
    text = (tmp_path / 'explicit/experiments/bank.edi').read_text()
    assert '_background_estimate.tolerance' in text, (
        'An explicitly chosen half-noise override must be stored in the project category'
    )
    assert engine.Project.load(
        tmp_path / 'explicit'
    ).experiment.background_estimate.tolerance == pytest.approx(0.5, rel=0, abs=0), (
        'An explicit half-noise setting must reload exactly'
    )


@pytest.mark.parametrize('method', ['arpls', 'snip', 'fabc'])
@pytest.mark.parametrize('count', [2, 7, 17])
def test_explicit_point_count_places_exactly_that_many_points(tmp_path, method, count):
    project = blank(tmp_path / 'input')
    project.experiment.background.auto_estimate(method=method, n_points=count)
    actual = points(project)
    assert len(actual) == count, (
        'The default move policy must place exactly n_points, including both endpoints'
    )
    assert len({row[0] for row in actual}) == count, (
        'Count fulfillment cannot duplicate an anchor coordinate'
    )
    assert [actual[0][0], actual[-1][0]] == REFERENCE['cases']['hrpt']['active_endpoints'], (
        'An explicit count must still retain both included-grid endpoints'
    )
    for low, high in REFERENCE['cases']['hrpt']['peak_windows']:
        assert all(not low <= row[0] <= high for row in actual[1:-1]), (
            'A fixed count must still avoid every independently detected peak window'
        )


def test_default_call_matches_explicit_auto_with_a_nonzero_calculated_model(tmp_path):
    source = materialize(tmp_path / 'input', REFERENCE['cases']['hrpt'])
    path = source / 'experiments/bank.edi'
    path.write_text(path.read_text().replace('phase 0\n', 'phase 3.25\n'))
    project = engine.Project.load(source)
    project.analysis.calculate()
    assert (
        np.max(
            np.abs(
                np.asarray(project.experiment.data.intensity_calc)
                - np.asarray(project.experiment.data.intensity_bkg)
            )
        )
        > 1
    ), 'The default-policy control must contain a nonzero calculated pattern'
    project.experiment.background.auto_estimate()
    default = points(project)
    project.experiment.background.auto_estimate(tolerance=2.0, in_peaks='move', use_model='auto')
    assert points(project) == default, (
        'The default call must equal explicit auto calculated-peak selection at twice the noise'
    )
    project.experiment.background.auto_estimate(
        tolerance=2.0, in_peaks='move', use_model='subtract'
    )
    subtract = points(project)
    project.experiment.background.auto_estimate(tolerance=2.0, in_peaks='move', use_model='ignore')
    assert points(project) != subtract, (
        'The nonzero model must distinguish the forced subtract and ignore controls'
    )


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), 0, -0.5, 10**400])
@pytest.mark.parametrize('entry', ['direct', 'saved-setting'])
def test_invalid_tolerance_refuses_without_changing_points_or_settings(tmp_path, value, entry):
    project = blank(tmp_path / 'input')
    before = points(project)
    previous = project.experiment.background_estimate.tolerance
    if entry == 'direct':
        with pytest.raises((ValueError, RuntimeError, OverflowError, TypeError)):
            project.experiment.background.auto_estimate(tolerance=value)
    else:
        with pytest.raises((ValueError, RuntimeError, OverflowError, TypeError)):
            project.experiment.background_estimate.tolerance = value
    assert points(project) == before, (
        'A nonfinite or unrepresentable tolerance must refuse before point mutation'
    )
    assert project.experiment.background_estimate.tolerance == previous, (
        'An invalid tolerance setter must preserve the previous saved override'
    )


@pytest.mark.parametrize('token', ['nan', 'inf', '-inf', '1e400', '0', '-0.5'])
def test_invalid_persisted_tolerance_refuses_at_load(tmp_path, token):
    source = materialize(tmp_path / 'input', REFERENCE['cases']['hrpt'])
    path = source / 'experiments/bank.edi'
    path.write_text(path.read_text() + f'\n_background_estimate.tolerance {token}\n')
    before = path.read_bytes()
    with pytest.raises((ValueError, RuntimeError, OverflowError)):
        engine.Project.load(source)
    assert path.read_bytes() == before, (
        'Rejecting persisted estimator options must leave the input project untouched'
    )


@pytest.mark.parametrize(
    ('authored', 'expected'),
    [
        ('auto', 'auto'),
        ('subtract', 'subtract'),
        ('ignore', 'ignore'),
        ('true', 'subtract'),
        ('false', 'ignore'),
    ],
)
def test_model_policy_and_legacy_booleans_roundtrip_as_canonical_tokens(
    tmp_path, authored, expected
):
    source = materialize(tmp_path / 'input', REFERENCE['cases']['hrpt'])
    path = source / 'experiments/bank.edi'
    path.write_text(path.read_text() + f'\n_background_estimate.use_model {authored}\n')
    project = engine.Project.load(source)
    before = points(project)
    for turn in range(2):
        assert project.experiment.background_estimate.use_model == expected, (
            'The public field must expose auto/subtract/ignore '
            'and map old true/false to subtract/ignore'
        )
        destination = tmp_path / f'saved-{turn}'
        project.save_as(destination)
        saved = (destination / 'experiments/bank.edi').read_text()
        import re  # noqa: PLC0415

        assert re.findall(r'(?m)^_background_estimate\.use_model\s+(\S+)', saved) == [expected], (
            'Every save must write exactly one canonical policy token, never an old Boolean'
        )
        project = engine.Project.load(destination)
        assert points(project) == before, (
            'Policy migration and save/load must preserve the saved point rows exactly'
        )


@pytest.mark.parametrize('policy', ['auto', 'subtract', 'ignore'])
def test_python_policy_setter_saves_the_chosen_token(tmp_path, policy):
    project = blank(tmp_path / 'input')
    project.experiment.background_estimate.use_model = policy
    assert project.experiment.background_estimate.use_model == policy, (
        'The Python category setter must accept every canonical calculated-peaks choice'
    )
    project.save_as(tmp_path / 'saved')
    assert (
        engine.Project.load(tmp_path / 'saved').experiment.background_estimate.use_model == policy
    ), 'A Python-assigned model policy must survive ordinary project saving and loading'
