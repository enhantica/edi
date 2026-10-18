"""P2: fitted values and e.s.d.s are results in the project model.

The fit result supplies the unrounded values and uncertainties. An independent
decimal reference predicts their saved spelling; the stale seed remains a
separate negative control.
"""

from __future__ import annotations

import importlib
import math
import os
import re
from pathlib import Path
from typing import Any

import pytest

from conftest import crysta_reference_source
from tests.fixtures.saved_spelling.reference import saved_pair, spelling

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

    original_cell = tuple(getattr(project.structure.cell, 'length_' + axis) for axis in 'abc')
    assert tuple(item.value for item in original_cell) == pytest.approx((expected_value,) * 3), (
        'The fitted cubic cell keeps the declared a=b=c values before serialization'
    )
    written_cell = tuple(
        saved_pair(item.value, item.uncertainty)[0] if item.free else item.value
        for item in original_cell
    )
    saved = tmp_path / 'saved-project'
    project.save_as(saved)
    reloaded_cell = LIB.Project.load(saved).structure.cell
    reloaded = reloaded_cell.length_a
    written_value, written_su = saved_pair(expected_value, expected_uncertainty)
    structure = next((saved / 'structures').glob('*.edi')).read_text()
    assert re.findall(r'(?m)^_cell.length_a\s+(\S+)', structure) == [
        spelling(expected_value, expected_uncertainty)
    ], 'The saved fitted token uses the independently derived IUCr value and uncertainty'
    assert float(reloaded.value) == pytest.approx(written_value, rel=0, abs=0), (
        'The fitted value reloads at its independently derived written precision'
    )
    assert float(reloaded.uncertainty) == pytest.approx(written_su, rel=0, abs=0), (
        'The saved uncertainty follows the fitted result and IUCr ceiling, never the stale seed'
    )
    assert tuple(
        float(parameter.value)
        for parameter in (
            reloaded_cell.length_a,
            reloaded_cell.length_b,
            reloaded_cell.length_c,
        )
    ) == pytest.approx(written_cell, rel=0, abs=0), (
        'The cubic cell reloads each fitted axis at its declared free or fixed written precision'
    )
