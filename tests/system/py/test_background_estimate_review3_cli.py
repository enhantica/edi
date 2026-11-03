"""Calc persistence includes every estimate row, constant and provenance tag."""

# Saved Auto inputs now include the series basis in their independently authored
# provenance. The fit/retention assertions and numerical bounds remain unchanged.

import re
import subprocess
import sys
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.review3 import (
    KINDS,
    calculated,
    estimate_control,
    materialize,
    persisted_settings,
    rows,
    state,
)

ROOT = Path(__file__).resolve().parents[3]


def calc(source):
    command = [sys.executable, '-m', 'edi', 'calc', str(source)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    assert result.returncode == 0, (
        'The ordinary calc CLI must persist a complete due estimate: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('trigger', ['initial', 'settings', 'data', 'provenance-only'])
def test_calc_persists_the_complete_estimate_state_and_reloads_without_refresh(
    tmp_path, kind, trigger
):
    source = materialize(tmp_path / 'input', kind)
    p = engine.Project.load(source)
    p.experiment.background_estimate.use_model = 'ignore'
    p.analysis.calculate()
    p.save_as(tmp_path / 'settled')
    source = tmp_path / 'settled'
    file = source / 'experiments/d20.edi'
    text = file.read_text()
    if trigger == 'initial':
        text = (
            '\n'.join(
                line
                for line in text.splitlines()
                if not line.startswith((
                    '_background_estimate.inputs_digest',
                    '_background_estimate.points_digest',
                ))
            )
            + '\n'
        )
    elif trigger == 'settings':
        field, old, new = (
            ('n_points', '9', '11') if kind == 'line-segment' else ('max_terms', '3', '1')
        )
        text = text.replace(
            '_background_estimate.' + field + ' ' + old,
            '_background_estimate.' + field + ' ' + new,
        )
    elif trigger == 'provenance-only':
        # New requested method token, identical resolved arPLS curve and row values.
        text = text.replace(
            '_background_estimate.method arpls', '_background_estimate.method auto'
        )
    else:
        lines = text.splitlines()
        tags = []
        for index, line in enumerate(lines):
            if line == 'loop_':
                tags = []
            elif line.startswith('_data.') and len(line.split()) == 1:
                tags.append(line)
            elif '_data.intensity_meas' in tags and len(line.split()) == len(tags):
                fields = line.split()
                j = tags.index('_data.intensity_meas')
                fields[j] = format(float(fields[j]) + 125, '.17g')
                lines[index] = ' '.join(fields)
        text = '\n'.join(lines) + '\n'
    file.write_text(text)
    control = engine.Project.load(source)
    control.analysis.calculate()
    control.save_as(tmp_path / 'python')
    calc(source)
    actual = engine.Project.load(source)
    expected = engine.Project.load(tmp_path / 'python')
    assert state(actual.experiment) == state(expected.experiment), (
        'Calc must save exactly the Python rows, type, basis constants and mode'
    )
    assert persisted_settings(source) == persisted_settings(tmp_path / 'python'), (
        'Calc must save complete refreshed provenance even when the estimated rows are equal'
    )
    np.testing.assert_allclose(
        calculated(source),
        [float(format(v, '.6g')) for v in calculated(tmp_path / 'python')],
        rtol=1e-11,
        atol=1e-8,
        err_msg='CLI six-significant-digit profile must equal the rounded Python calculation',
    )
    before = rows(actual.experiment)
    actual.analysis.calculate()
    assert rows(actual.experiment) == before, (
        'An unchanged CLI-saved Auto estimate must reload and calculate without estimating again'
    )


@pytest.mark.parametrize(
    ('kind', 'change'),
    [
        ('polynomial', 'origin'),
        ('chebyshev', 'x_min'),
        ('chebyshev', 'x_max'),
        ('polynomial', 'type'),
        ('chebyshev', 'type'),
    ],
)
@pytest.mark.parametrize('operation', ['calc', 'fit'])
def test_both_cli_consumers_refresh_persisted_series_type_and_basis(
    tmp_path, kind, change, operation
):
    project = engine.Project.load(materialize(tmp_path / 'input', kind))
    project.experiment.background_estimate.use_model = 'ignore'
    project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    source = tmp_path / 'saved'
    file = source / 'experiments/d20.edi'
    text = file.read_text()
    target = kind
    if change == 'type':
        target = 'chebyshev' if kind == 'polynomial' else 'polynomial'
        text = text.replace('_background.type ' + kind, '_background.type ' + target)
        text = (
            '\n'.join(
                line
                for line in text.splitlines()
                if not line.startswith((
                    '_background.origin ',
                    '_background.x_min ',
                    '_background.x_max ',
                ))
            )
            + '\n'
        )
        text += (
            '_background.origin 80\n'
            if target == 'polynomial'
            else '_background.x_min 8.0953\n_background.x_max 149.7953\n'
        )
    else:
        value = {'origin': 105.25, 'x_min': 3.375, 'x_max': 160.625}[change]
        text = re.sub(
            r'(?m)^_background\.' + change + r' .*$',
            '_background.' + change + ' ' + str(value),
            text,
        )
    file.write_text(text)
    if operation == 'fit':
        structure = source / 'structures/cosio.edi'
        structure.write_text(re.sub(r'(?m)^(_cell.length_a \S+)$', r'\1()', structure.read_text()))
    control = engine.Project.load(source)
    estimate_control(control)
    control.experiment.background_estimate.mode = 'auto'
    if operation == 'fit':
        # The normalized reference must itself have current Auto provenance.
        control.analysis.calculate()
        control.fit()
    else:
        control.analysis.calculate()
    control.save_as(tmp_path / 'expected')
    command = [sys.executable, '-m', 'edi', operation, str(source)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    assert completed.returncode == 0, (
        'Both ordinary CLIs must accept a legitimate saved Auto type or basis change: '
        + completed.stdout
        + completed.stderr
    )
    actual = engine.Project.load(source)
    expected = engine.Project.load(tmp_path / 'expected')
    assert state(actual.experiment) == state(expected.experiment), (
        'CLI calc and fit must normalize the edited basis before using old coefficients'
    )
    assert persisted_settings(source) == persisted_settings(tmp_path / 'expected'), (
        'Both CLI consumers must persist provenance for the new declared series basis and type'
    )


@pytest.mark.parametrize('kind', KINDS)
def test_unchanged_manual_cli_calculation_keeps_all_background_model_inputs(tmp_path, kind):
    project = engine.Project.load(materialize(tmp_path / 'input', kind))
    project.experiment.background_estimate.mode = 'manual'
    project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    source = tmp_path / 'saved'
    before = state(engine.Project.load(source).experiment)
    settings = persisted_settings(source)
    calc(source)
    assert state(engine.Project.load(source).experiment) == before, (
        'The calc persistence repair must keep unchanged Manual background rows and constants'
    )
    assert persisted_settings(source) == settings, (
        'An unchanged Manual calculation must not invent or replace Auto provenance'
    )
