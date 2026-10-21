"""Every automatic estimate must use the relation-applied nonzero model."""

import subprocess
import sys
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.conftest import corpus_case_dir
from tests.fixtures.background_estimate.lifecycle import persisted_points
from tests.fixtures.background_estimate.relation_order import relation_input, scan_files
from tests.fixtures.background_estimate.settings import points

ROOT = Path(__file__).resolve().parents[3]
SOURCE = corpus_case_dir('lbco-hrpt-s2') / 'project'
ENTRIES = [
    'calculate',
    'fit-single',
    'fit-joint',
    'fit-independent',
    'fit-sequential',
    'cli-calc',
    'cli-fit-single',
    'cli-fit-joint',
    'cli-fit-independent',
    'cli-fit-sequential',
]


def run_python_fit(project):
    project.analysis.fit()


def run_cli_fit(source):
    return subprocess.run(
        [sys.executable, '-m', 'edi', 'fit', str(source)],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )


def run_entry(source, entry):
    project = engine.Project.load(source)
    if entry.startswith('cli-'):
        completed = (
            run_cli_fit(source)
            if entry.startswith('cli-fit')
            else subprocess.run(
                [sys.executable, '-m', 'edi', 'calc', str(source)],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        )
        assert completed.returncode == 0, (
            'The public CLI must accept the valid related-model project: ' + completed.stderr
        )
        return persisted_points(source, experiment='hrpt')
    if entry == 'calculate':
        project.analysis.calculate()
    else:
        run_python_fit(project)
    return [row[:2] for row in points(project)]


@pytest.mark.parametrize('relation', ['scale', 'cell'])
@pytest.mark.parametrize('entry', ENTRIES)
def test_auto_refresh_matches_the_explicitly_relation_applied_nonzero_control(
    tmp_path, relation, entry
):
    mode = entry.split('fit-')[-1] if 'fit-' in entry else 'single'
    paths = [
        relation_input(tmp_path / name, SOURCE, relation, normalized=normalized, mode=mode)
        for name, normalized in [('due', False), ('applied', True)]
    ]
    # An explicit manual calculation evaluates both the declared relation and its
    # symmetry dependents without producing the control's automatic estimate.
    control = engine.Project.load(paths[1])
    control.experiment.background_estimate.mode = 'manual'
    control.analysis.calculate()
    data = control.experiment.data
    assert np.any(
        np.abs(np.asarray(data.intensity_calc) - np.asarray(data.intensity_bkg)) > 1e-8
    ), 'The relation-order witness must retain a nonzero model; a data-only input hides the defect'
    if relation == 'cell':
        assert all(
            getattr(control.structure.cell, 'length_' + axis).value
            == pytest.approx(3.9375, abs=0, rel=0)
            for axis in 'abc'
        ), 'The explicitly applied control must complete the cubic symmetry dependents'
    control.experiment.background.auto_estimate(
        method='snip', width=7.25, n_points=9, use_model=True
    )
    explicit = [row[:2] for row in points(control)]
    control.experiment.background.auto_estimate(
        method='snip', width=7.25, n_points=9, use_model=False
    )
    data_only = [row[:2] for row in points(control)]
    assert len(data_only) != len(explicit) or not np.allclose(
        data_only, explicit, rtol=2e-12, atol=1e-9
    ), 'The authored input must distinguish the guided relation-applied estimate from data alone'
    if mode in {'independent', 'sequential'}:
        for path in paths:
            scan_files(engine.Project.load(path), path, mode)
    expected = run_entry(paths[1], entry)
    assert len(expected) == len(explicit), (
        'A normalized entry must retain the explicitly estimated post-relation anchor count'
    )
    assert np.allclose(expected, explicit, rtol=2e-12, atol=1e-9), (
        'A normalized entry must match explicit estimation after declared and symmetry application'
    )
    actual = run_entry(paths[0], entry)
    assert len(actual) == len(expected), (
        'Every public calculation/fit entry must estimate after relations, including symmetry, '
        'before freezing an automatic background: ' + entry + '/' + relation
    )
    assert np.allclose(actual, expected, rtol=2e-12, atol=1e-9), (
        'A stale stored relation target must not supply model peaks to auto estimation; '
        'points must equal an explicitly relation-applied nonzero-model control: '
        + entry
        + '/'
        + relation
    )
