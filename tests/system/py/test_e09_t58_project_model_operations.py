"""P1 system-scale witnesses for model-declared fit and calculation inputs."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from conftest import crysta_reference_source

ROOT = Path(__file__).resolve().parents[3]
LIB = importlib.import_module('edi')


def _crysta_root() -> Path:
    candidates = []
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    if override:
        candidates.append(Path(override).resolve().parents[1])
    candidates.extend((ROOT, crysta_reference_source()))
    for candidate in candidates:
        if (candidate / 'tests/fitting/manifest.yml').is_file():
            return candidate
    message = "the  operation gates require crysta's committed fitting corpus"
    raise AssertionError(message)


def _case_project(case_id: str) -> Path:
    project = _crysta_root() / 'tests' / 'fitting' / case_id / 'project'
    assert project.is_dir(), f'missing committed corpus project {case_id!r}'
    return project


def _calculate(project: Any) -> list[np.ndarray]:
    returned = project.analysis.calculate()
    assert returned is None, (
        'model calculation must write results into experiments rather than return a side result'
    )
    return [
        np.asarray(experiment.data.intensity_calc, dtype=np.float64).copy()
        for experiment in project.experiments
    ]


def _set_number(owner: Any, name: str, value: float) -> None:
    current = getattr(owner, name)
    if hasattr(current, 'value'):
        current.value = value
    else:
        setattr(owner, name, value)


def _bounded_project(tmp_path: Path) -> tuple[Path, int]:
    case = _crysta_root() / 'tests' / 'fitting' / 'ncaf-wish-3bank-s5'
    staged = tmp_path / 'bounded-project'
    staged.mkdir()
    for child in ('experiments', 'structures'):
        (staged / child).symlink_to(case / 'project' / child, target_is_directory=True)
    project_file = case / 'project' / 'project.edi'
    if project_file.is_file():
        (staged / 'project.edi').symlink_to(project_file)
    (staged / 'analysis').mkdir()
    analysis = (case / 'bounded-analysis' / 'analysis.edi').read_text(encoding='utf-8')
    (staged / 'analysis' / 'analysis.edi').write_text(analysis, encoding='utf-8')
    assert '_minimizer.max_iterations 2' in analysis, (
        'the bounded fit fixture must declare the two-iteration model budget under test'
    )
    return staged, 2


def _assert_refused_fit_preserves_pattern() -> None:
    project = LIB.Project.load(_case_project('lbco-hrpt-s2'))
    before = _calculate(project)
    #  makes the live getter lazy. Retain pre-edit columns to inspect a
    # refused publication without asking the invalid edited model to calculate.
    snapshots = [experiment.data.intensity_calc for experiment in project.experiments]
    axis = np.asarray(project.experiment.data.axis(), dtype=np.float64)
    project.experiment.excluded_regions = [(float(axis.min() - 1.0), float(axis.max() + 1.0))]
    with pytest.raises(ValueError, match='no measured data remains'):
        project.analysis.fit()
    after = [np.asarray(snapshot, dtype=np.float64).copy() for snapshot in snapshots]
    assert all(old.tobytes() == new.tobytes() for old, new in zip(before, after, strict=True)), (
        ' requires a refused fit to leave every retained intensity_calc byte-identical'
    )
    with pytest.raises(ValueError, match='no point remains'):
        _ = project.experiment.data.intensity_calc


def test_declared_iteration_budget_is_authoritative(tmp_path: Path) -> None:
    project_root, declared_budget = _bounded_project(tmp_path)
    project = LIB.Project.load(project_root)
    result = project.analysis.fit()
    assert result.iterations <= declared_budget, (
        'the project-declared minimizer budget must replace the former public default of 50'
    )
    with pytest.raises(TypeError):
        project.analysis.fit(max_iterations=50)

    fitted = LIB.Project.load(_case_project('ncaf-wish-3bank-s5'))
    names = tuple(str(experiment.name) for experiment in fitted.experiments)
    before = _calculate(fitted)
    outcome = fitted.analysis.fit()
    assert outcome.converged is True, (
        ' requires a successful converged fit before judging pattern refresh'
    )
    stored = [
        np.asarray(experiment.data.intensity_calc, dtype=np.float64).copy()
        for experiment in fitted.experiments
    ]

    saved = tmp_path / 'fitted-reference'
    fitted.save_as(saved)
    reference = LIB.Project.load(saved)
    fresh = _calculate(reference)
    unchanged = [
        name
        for name, old, current in zip(names, before, stored, strict=True)
        if np.array_equal(old, current, equal_nan=True)
    ]
    mismatched = [
        name
        for name, current, expected in zip(names, stored, fresh, strict=True)
        if not np.array_equal(current, expected, equal_nan=True)
    ]
    failures = []
    if unchanged:
        failures.append(f'did not change from pre-fit: {unchanged!r}')
    if mismatched:
        failures.append(f'did not equal fresh fitted-state calculation: {mismatched!r}')
    assert not failures, (
        ' requires both refresh halves for every fitted experiment intensity_calc; '
        + '; '.join(failures)
    )

    _assert_refused_fit_preserves_pattern()


def test_declared_tof_bank_angle_reaches_calculation() -> None:
    baseline = LIB.Project.load(_case_project('ncaf-wish-3bank-s5'))
    changed = LIB.Project.load(_case_project('ncaf-wish-3bank-s5'))
    _set_number(changed.experiments[0].instrument, 'setup_twotheta_bank', 144.845)

    baseline_pattern = _calculate(baseline)[0]
    changed_pattern = _calculate(changed)[0]

    assert not np.array_equal(baseline_pattern, changed_pattern, equal_nan=True), (
        'the non-trivial bank-angle declaration must reach the Lorentz-factor calculation'
    )
