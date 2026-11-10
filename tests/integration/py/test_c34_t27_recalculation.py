"""unit 0: edi Python reads calculate, including after loading saved columns."""

from __future__ import annotations

import os
from pathlib import Path

import edi
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting'))


def test_loaded_non_ui_read_matches_explicit_recalculation():
    path = CORPUS / 'si-sepd-s2/project'
    lazy = edi.Project.load(path)
    observed = np.asarray(lazy.experiment.data.intensity_calc)
    explicit = edi.Project.load(path)
    explicit.analysis.calculate()
    expected = np.asarray(explicit.experiment.data.intensity_calc)
    assert observed.size and observed.size == expected.size, (
        ' unit 0 an edi non-UI read must calculate every input row, not return empty'
    )
    assert np.allclose(observed, expected, rtol=2e-12, atol=1e-12), (
        ' unit 0 lazy and explicit calculation must use the same current inputs'
    )


def test_refused_lazy_recalculation_never_returns_earlier_values():
    project = edi.Project.load(CORPUS / 'si-sepd-s2/project')
    project.analysis.calculate()
    project.structure.cell.length_a.value = 0
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)cell|calculat|invalid'):
        _ = project.experiment.data.intensity_calc
