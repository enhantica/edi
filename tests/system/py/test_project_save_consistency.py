"""The saved model and its calculation agree with independently rounded inputs."""

import math
import shlex
import shutil
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.project_save.reference import PAIRS, expected_pair, six_digits
from tests.integration.py.test_report_iucr_persistence import project as numeric_project


@pytest.mark.parametrize(
    'rule', [None, 'iucr_19', 'iucr_99'], ids=['default', 'iucr', 'two-digits']
)
@pytest.mark.parametrize(('value', 'su'), PAIRS)
def test_saved_values_follow_the_decimal_rule_and_sigma_bound(tmp_path, rule, value, su):
    source = numeric_project(tmp_path, '4()', rule)
    loaded = engine.Project.load(source)
    parameter = loaded.experiments['bank'].background[0].intensity
    parameter.value, parameter.uncertainty, parameter.free = value, su, True
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    restored = engine.Project.load(destination)
    actual = restored.experiments['bank'].background[0].intensity
    expected = expected_pair(value, su, rule)
    assert (actual.value, actual.uncertainty) == expected, (
        'Saved values and uncertainties use two upward-rounded su digits by default '
        'and preserve a declared IUCr choice'
    )
    bound = 0.25 if rule == 'iucr_19' else 0.05
    assert abs(actual.value - value) <= bound * su, (
        'Save moves a parameter by at most 0.05 sigma for two digits or 0.25 sigma for IUCr'
    )
    assert (parameter.value, parameter.uncertainty) == expected, (
        'The open project adopts exactly the independently rounded saved value and uncertainty'
    )
    assert '_su_format.rule ' + (rule or 'iucr_99') in (destination / 'project.edi').read_text(), (
        'Save declares its default and retains an explicit project rule'
    )


@pytest.mark.parametrize('value', [1.23456789, -1.23456789, 12345678.9, 0.00000123456789])
@pytest.mark.parametrize('free', [False, True], ids=['fixed', 'free-without-su'])
def test_values_without_uncertainty_use_six_significant_digits(tmp_path, value, free):
    loaded = engine.Project.load(numeric_project(tmp_path, '4()', None))
    parameter = loaded.experiments['bank'].background[0].intensity
    parameter.value, parameter.uncertainty, parameter.free = value, None, free
    loaded.save_as(tmp_path / 'saved')
    actual = engine.Project.load(tmp_path / 'saved').experiments['bank'].background[0].intensity
    assert actual.value == six_digits(value), (
        'Fixed and free values without an uncertainty save with six significant digits'
    )
    assert parameter.value == actual.value, 'Save adopts the six-digit value in the open project'
    expected_su = None if free else 0.0
    assert actual.uncertainty == expected_su, (
        'Free absent uncertainty stays absent; a bare fixed token retains its engaged-zero decode'
    )
    assert actual.free is free, 'Rounding never changes a parameter free flag'


@pytest.mark.parametrize('rule', [None, 'iucr_19', 'iucr_99'])
@pytest.mark.parametrize('operation', ['save', 'save-as'])
def test_save_recomputes_the_pattern_after_adopting_rounded_model(tmp_path, rule, operation):
    loaded = engine.Project.load(numeric_project(tmp_path, '4()', rule))
    experiment = loaded.experiments['bank']
    for point in experiment.background:
        point.intensity.value = 2.16352
        point.intensity.uncertainty = 0.00481
        point.intensity.free = True
    experiment.linked_structure.scale.value = 0
    loaded.calculate()
    previous = np.array(experiment.data.intensity_calc, copy=True)
    assert np.all(previous == 2.16352), (
        'Zero structure scale and constant authored background '
        'independently give a constant pattern'
    )
    destination = Path(loaded.metadata.path) if operation == 'save' else tmp_path / 'saved'
    loaded.save() if operation == 'save' else loaded.save_as(destination)
    expected, _ = expected_pair(2.16352, 0.00481, rule)
    saved = np.array(experiment.data.intensity_calc, copy=True)
    assert np.all(saved == expected) and not np.array_equal(saved, previous), (
        'Save recomputes every calculated point from the adopted rounded model before writing'
    )
    reopened = engine.Project.load(destination)
    assert np.array_equal(saved, reopened.experiments['bank'].data.intensity_calc), (
        'The serialized pattern is exactly the open project pattern after Save'
    )
    reopened.calculate()
    assert np.array_equal(saved, reopened.experiments['bank'].data.intensity_calc), (
        'A fresh calculation after reopen exactly reproduces every saved calculated point'
    )


@pytest.mark.parametrize('rule', [None, 'iucr_19', 'iucr_99'])
def test_saved_r_factors_use_the_written_model_residuals(tmp_path, rule):
    root = Path(__file__).resolve().parents[3]
    source = tmp_path / 'project'
    shutil.copytree(root / 'tests/fixtures/report_options/nontrivial', source)
    record = source / 'project.edi'
    lines = [
        line for line in record.read_text().splitlines() if not line.startswith('_su_format.rule')
    ]
    if rule is not None:
        lines.append('_su_format.rule ' + rule)
    record.write_text('\n'.join(lines) + '\n')
    loaded = engine.Project.load(source)
    experiment = loaded.experiments['bank']
    experiment.linked_structure.scale.value = 0
    for point in experiment.background:
        point.intensity.value, point.intensity.uncertainty = 2.16352, 0.00481
    loaded.calculate()
    loaded.save()
    written = dict(
        shlex.split(line)
        for line in (source / 'analysis/analysis.edi').read_text().splitlines()
        if line.startswith('_fit_result.')
    )
    expected, _ = expected_pair(2.16352, 0.00481, rule)
    observed = np.array(experiment.data.intensity_meas)
    objective = float(sum((float(value) - expected) ** 2 for value in observed))
    rwp = math.sqrt(objective / sum(float(value) ** 2 for value in observed))
    assert float(written['_fit_result.prof_wr_factor']) == six_digits(rwp), (
        'Saved Rwp is the six-digit weighted-residual norm of the written rounded model'
    )
    dof = int(written['_fit_result.degrees_of_freedom'])
    assert dof == 3, 'The authored nine-point six-free-parameter fit has three degrees of freedom'
    assert float(written['_fit_result.reduced_chi_square']) == six_digits(objective / dof), (
        'Saved chi square uses the rounded-model residuals '
        'and independently counted degrees of freedom'
    )
    reopened = engine.Project.load(source)
    reopened.calculate()
    assert np.array_equal(
        experiment.data.intensity_calc, reopened.experiments['bank'].data.intensity_calc
    ), 'The reopened calculation exactly reproduces the pattern underlying the saved R factors'
