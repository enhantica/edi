"""P1 fit inputs: exclusions and iteration budget live in the project.

A fit is an
integration-tier operation under , even when an all-excluded project
refuses before the solver starts.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

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
    message = "the  fit-input gates require crysta's committed fitting corpus"
    raise AssertionError(message)


def _case_project(case_id: str) -> Path:
    project = _crysta_root() / 'tests' / 'fitting' / case_id / 'project'
    assert project.is_dir(), f'missing committed corpus project {case_id!r}'
    return project


def test_declared_exclusions_are_applied_without_a_regions_argument() -> None:
    project = LIB.Project.load(_case_project('lbco-hrpt-s2'))
    axis = np.asarray(project.experiment.data.axis(), dtype=np.float64)
    project.experiment.excluded_regions = [(float(axis.min() - 1.0), float(axis.max() + 1.0))]

    with pytest.raises(ValueError, match='no measured data remains'):
        project.analysis.fit()


def test_public_fit_routes_reject_positional_and_keyword_data() -> None:
    project = LIB.Project.load(_case_project('lbco-hrpt-s2'))
    empty = np.asarray([], dtype=np.float64)
    calls = [
        ('Analysis.fit positional data', lambda: project.analysis.fit(empty, empty, empty)),
        (
            'Analysis.fit keyword data',
            lambda: project.analysis.fit(grid=empty, observed=empty, sigma=empty),
        ),
    ]
    if LIB.__name__ == 'edi':
        assert hasattr(project, 'fit'), 'D3 requires edi to retain the direct fit name'
        assert hasattr(project, 'fit_joint'), 'D3 requires edi to retain the direct joint-fit name'
        calls.extend([
            ('Project.fit positional data', lambda: project.fit(empty, empty, empty)),
            (
                'Project.fit keyword data',
                lambda: project.fit(grid=empty, observed=empty, sigma=empty),
            ),
            ('Project.fit_joint positional data', lambda: project.fit_joint([])),
            (
                'Project.fit_joint keyword data',
                lambda: project.fit_joint(patterns=[]),
            ),
        ])

    failures = []
    for route, call in calls:
        try:
            call()
        except TypeError:
            continue
        except ValueError as error:
            failures.append(
                f'{route} accepted caller-supplied measured data and reached '
                f'{type(error).__name__}: {error}'
            )
        else:
            failures.append(f'{route} accepted caller-supplied measured data without refusing it')
    assert not failures, (
        'every public fit route must reject both positional and keyword measured data; '
        + '; '.join(failures)
    )
