"""FCJ adjustment eligibility, preserved starts and truthful public diagnostics."""

import importlib
import math
import re
import subprocess

import pytest

from conftest import corpus_case_dir
from tests.system.py.test_latest_fit_uncertainty import local_cli

ENGINE = importlib.import_module('edi')


def project_from(start, free):
    project = ENGINE.Project.load(corpus_case_dir('lab6-echidna-fcj') / 'project')
    for parameter in project.parameters:
        parameter.free = False
    peak = project.experiments[0].peak
    for parameter, value, active in zip(
        (peak.asym_fcj_1, peak.asym_fcj_2), start, free, strict=True
    ):
        parameter.value = value
        parameter.free = active
    project.experiments[0].linked_structures[0].scale.free = True
    return project


def widths(project):
    peak = project.experiments[0].peak
    return (peak.asym_fcj_1.value, peak.asym_fcj_2.value)


def test_zero_fcj_start_reaches_the_nonzero_start_minimum():
    zero = project_from((0.0, 0.0), (True, True))
    result = zero.analysis.fit()
    positive = project_from((0.08, 0.08), (True, True))
    reference = positive.analysis.fit()
    assert all(value > 0 for value in widths(zero)), (
        'Each free zero FCJ coefficient must leave zero'
    )
    assert result.reduced_chi_square == pytest.approx(reference.reduced_chi_square, rel=2e-5), (
        'The FCJ minimum must be independent of zero or positive starting widths'
    )
    assert sorted(widths(zero)) == pytest.approx(sorted(widths(positive)), rel=2e-3, abs=2e-5), (
        'Exchange-equivalent source and detector widths must reach the same fitted pair'
    )


ELIGIBILITY = [
    ((0.0, 0.0), (True, True)),
    ((0.0, 0.0), (True, False)),
    ((0.0, 0.0), (False, True)),
    ((0.0, 0.073), (True, False)),
    ((0.021, 0.0), (False, True)),
    ((0.0, 0.073), (True, True)),
    ((0.021, 0.0), (True, True)),
    ((0.021, 0.073), (True, True)),
    ((0.021, 0.073), (False, False)),
    ((0.0, 0.0), (False, False)),
    ((0.0, 0.073), (False, False)),
    ((0.021, 0.0), (False, False)),
]


@pytest.mark.parametrize(('start', 'free'), ELIGIBILITY)
def test_only_each_free_zero_coefficient_is_adjusted_before_any_optimizer_step(start, free):
    project = project_from(start, free)
    result = project.fit(should_cancel=lambda: True)
    assert result.iterations == 0, 'The starting-value witness must stop before any optimizer step'
    for value, original, active in zip(widths(project), start, free, strict=True):
        if active and original == 0:
            assert math.isfinite(value), 'Every eligible FCJ adjustment must be finite'
            assert 1e-5 <= value <= 1e-3, (
                'An eligible zero starts within a broad order-of-magnitude envelope '
                'around the owner suggestion'
            )
        else:
            assert value == original, (
                'Fixed or nonzero FCJ inputs must retain their actual starting meaning'
            )


@pytest.mark.parametrize(('start', 'free'), [case for case in ELIGIBILITY if not all(case[1])])
def test_completed_fit_preserves_every_fixed_fcj_coefficient(start, free):
    project = project_from(start, free)
    result = project.analysis.fit()
    assert result.success, 'The fixed-input protection must reach a completed FCJ fit'
    for value, original, active in zip(widths(project), start, free, strict=True):
        if not active:
            assert value == original, (
                'Every fixed FCJ coefficient must keep its input value through fit completion'
            )


def adjustment_values(log, index):
    labels = (r'(?:S\s*/\s*L|S_L|asym_fcj_1)', r'(?:D\s*/\s*L|D_L|asym_fcj_2)')
    number = r'(?<![\w.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
    values = []
    for line in log.splitlines():
        if re.search(labels[index], line, re.IGNORECASE) and re.search(
            r'seed|adjust|positive|start.*(?:from|instead|->)', line, re.IGNORECASE
        ):
            numbers = [float(token) for token in re.findall(number, line)]
            if 0 in numbers or re.search(r'\bzero\b', line, re.IGNORECASE):
                values.extend(value for value in numbers if 1e-5 <= value <= 1e-3)
    return values


@pytest.mark.parametrize(
    ('start', 'free'),
    [
        ((0.0, 0.0), (True, True)),
        ((0.0, 0.073), (True, False)),
        ((0.021, 0.0), (False, True)),
        ((0.021, 0.073), (True, True)),
        ((0.0, 0.073), (False, True)),
    ],
)
def test_public_fit_log_truthfully_identifies_each_actual_adjustment(tmp_path, start, free):
    cancelled = project_from(start, free)
    cancelled.fit(should_cancel=lambda: True)
    starts = widths(cancelled)
    project = project_from(start, free)
    project.save_as(tmp_path / 'project')
    result = subprocess.run(
        [*local_cli(), 'fit', str(tmp_path / 'project'), '--verbosity', 'full'],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, 'The public CLI must complete its declared FCJ fit'
    log = result.stdout + result.stderr
    for index, (original, active) in enumerate(zip(start, free, strict=True)):
        adjusted = adjustment_values(log, index)
        assert bool(adjusted) == (active and original == 0), (
            'The log must identify the affected coefficient, its zero input and '
            'its actual small positive start'
        )
        if adjusted:
            assert starts[index] == pytest.approx(adjusted[-1], rel=1e-12), (
                'The logged FCJ adjustment must equal the value observed before optimizer steps'
            )
