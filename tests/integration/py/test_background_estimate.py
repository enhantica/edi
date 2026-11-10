"""Check the consumer against the same independent estimator corpus."""

import json
from pathlib import Path

import edi
import numpy as np
import pytest

from tests.fixtures.background_estimate.project import materialize

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures/background_estimate'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())


@pytest.mark.parametrize('case', tuple(REFERENCE['cases']))
@pytest.mark.parametrize('method', ['arpls', 'snip', 'fabc'])
def test_python_estimation_matches_the_independent_engine_reference(tmp_path, case, method):
    row = REFERENCE['cases'][case]
    project = edi.Project.load(materialize(tmp_path, row))
    background = project.experiment.background
    assert callable(getattr(background, 'auto_estimate', None)), (
        'The consumer must expose the same background estimation call as its engine'
    )
    background.auto_estimate(tolerance=2.0, in_peaks='drop', method=method, use_model=False)
    actual = np.asarray([
        [getattr(p.position, 'value', p.position), p.intensity.value]
        for p in project.experiment.background
    ])
    expected = np.asarray(row['methods'][method]['default']['anchors'])
    assert actual.shape == expected.shape, (
        'The consumer must preserve the independent anchor count'
    )
    assert np.allclose(actual[:, 0], expected[:, 0], rtol=0, atol=1e-9), (
        'The consumer must keep the reference sample positions'
    )
    assert np.allclose(
        actual[:, 1],
        expected[:, 1],
        rtol=1e-10 if method == 'snip' else 1e-6,
        atol=1e-12 if method == 'snip' else 1e-9,
    ), 'Consumer anchor heights must meet the same method tolerances as the engine'
