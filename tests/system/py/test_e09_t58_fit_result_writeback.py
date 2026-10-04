"""P2: fitted values and e.s.d.s are results in the project model.

This file is intentionally byte-identical in crysta and edi.  The fit result is
the independent producer for the expected values and uncertainties; reloading
the saved project proves the writer did not preserve plausible-looking stale
uncertainties.
"""

from __future__ import annotations

import importlib
import math
import os
from pathlib import Path
from typing import Any

import pytest

from conftest import crysta_reference_source

ROOT = Path(__file__).resolve().parents[3]
LIB = importlib.import_module('edi')
STALE_UNCERTAINTY = 8.75


def _crysta_root() -> Path:
    candidates = []
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    if override:
        candidates.append(Path(override).resolve().parents[1])
    candidates.extend((ROOT, crysta_reference_source()))
    for candidate in candidates:
        if (candidate / 'tests/fitting/manifest.yml').is_file():
            return candidate
    message = "the  result gate requires crysta's committed fitting corpus"
    raise AssertionError(message)


def _cell_length_key(result: Any) -> str:
    candidates = [
        str(key) for key in result.values if 'cell' in str(key) and str(key).endswith('length_a')
    ]
    assert len(candidates) == 1, f'expected one cell-length result key, found {candidates!r}'
    return candidates[0]


def test_fit_result_uncertainty_replaces_stale_model_and_serialized_state(
    tmp_path: Path,
) -> None:
    source = _crysta_root() / 'tests/fitting/lbco-hrpt-s2/project'
    project = LIB.Project.load(source)
    parameter = project.structure.cell.length_a
    parameter.uncertainty = STALE_UNCERTAINTY

    result = project.analysis.fit()
    key = _cell_length_key(result)
    expected_value = float(result.values[key])
    expected_uncertainty = float(result.uncertainty[key])
    assert math.isfinite(expected_uncertainty), (
        'the fit result must report a finite uncertainty suitable for model persistence'
    )
    assert expected_uncertainty >= 0.0, (
        'the fit result uncertainty must remain a non-negative estimated standard deviation'
    )
    assert expected_uncertainty != pytest.approx(STALE_UNCERTAINTY), (
        'the negative case must distinguish a freshly fitted e.s.d. from stale model state'
    )

    assert float(parameter.value) == pytest.approx(expected_value), (
        'the fitted value reported by FitResult must be written back into the model'
    )
    assert float(parameter.uncertainty) == pytest.approx(expected_uncertainty), (
        'a fit that updates the value but leaves a stale model uncertainty is not write-back'
    )

    saved = tmp_path / 'saved-project'
    project.save_as(saved)
    reloaded_cell = LIB.Project.load(saved).structure.cell
    reloaded = reloaded_cell.length_a
    assert float(reloaded.value) == pytest.approx(expected_value), (
        'the fitted value reported by FitResult must survive model serialization and reload'
    )
    assert float(reloaded.uncertainty) == pytest.approx(expected_uncertainty), (
        'the serialized su must come from the fit result, not the pre-fit stale uncertainty'
    )
    assert tuple(
        float(parameter.value)
        for parameter in (
            reloaded_cell.length_a,
            reloaded_cell.length_b,
            reloaded_cell.length_c,
        )
    ) == pytest.approx((expected_value, expected_value, expected_value)), (
        'the saved cubic cell must apply its declared a=b=c ties to the refined length'
    )
